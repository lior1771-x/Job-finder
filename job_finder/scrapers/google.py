"""Google job scraper using careers sitemap + page titles."""

import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List

import requests

from ..models import Job
from .base import BaseScraper

logger = logging.getLogger(__name__)

# PM-related keywords to identify product management slugs
PM_SLUG_KEYWORDS = [
    "product-manager", "product-management", "product-lead",
    "product-owner", "product-director", "head-of-product",
    "group-product-manager",
]


class GoogleScraper(BaseScraper):
    """Scraper for Google jobs via careers sitemap + page title enrichment."""

    company_name = "Google"
    SITEMAP_URL = "https://careers.google.com/jobs/sitemap"
    SESSION = requests.Session()
    SESSION.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    })

    def fetch_jobs(self) -> List[Job]:
        """Fetch jobs from Google Careers sitemap, enriching PM roles with full titles."""
        jobs = []
        try:
            response = self.SESSION.get(self.SITEMAP_URL, timeout=30)
            response.raise_for_status()

            root = ET.fromstring(response.content)
            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

            entries = root.findall("sm:url", ns)
            logger.info(f"Found {len(entries)} entries in Google sitemap")

            for url_elem in entries:
                job = self._parse_sitemap_entry(url_elem, ns)
                if job:
                    jobs.append(job)

            # Enrich PM jobs with full titles from their pages
            pm_jobs = [j for j in jobs if self._is_pm_slug(j)]
            logger.info(f"Enriching {len(pm_jobs)} PM jobs with full titles...")

            for job in pm_jobs:
                full_title = self._fetch_full_title(job.url)
                if full_title:
                    job.title = full_title

            logger.info(f"Fetched {len(jobs)} jobs from Google ({len(pm_jobs)} PM enriched)")

        except requests.RequestException as e:
            logger.error(f"Error fetching Google jobs: {e}")
        except ET.ParseError as e:
            logger.error(f"Error parsing Google sitemap XML: {e}")

        return jobs

    @staticmethod
    def _is_pm_slug(job: Job) -> bool:
        """Check if a job's URL slug indicates a PM role."""
        url_lower = job.url.lower()
        return any(kw in url_lower for kw in PM_SLUG_KEYWORDS)

    def _fetch_full_title(self, url: str) -> str | None:
        """Fetch the full job title from the page's <title> tag."""
        try:
            resp = self.SESSION.get(url, timeout=10)
            if resp.status_code != 200:
                return None

            match = re.search(r"<title>(.*?)</title>", resp.text)
            if match:
                title = match.group(1)
                # Remove " — Google Careers" suffix
                title = re.sub(r"\s*[—–-]\s*Google Careers\s*$", "", title)
                return title.strip() if title.strip() else None

        except requests.RequestException:
            pass
        return None

    def _parse_sitemap_entry(self, url_elem, ns: dict) -> Job | None:
        """Parse a job from a sitemap <url> entry."""
        try:
            loc = url_elem.findtext("sm:loc", default="", namespaces=ns)
            lastmod = url_elem.findtext("sm:lastmod", default="", namespaces=ns)

            if not loc:
                return None

            match = re.search(r"/results/(\d+)-(.+?)/?$", loc)
            if not match:
                return None

            job_id = match.group(1)
            title_slug = match.group(2)
            title = title_slug.replace("-", " ").title()

            posted_date = None
            if lastmod:
                try:
                    posted_date = datetime.fromisoformat(
                        lastmod.replace("Z", "+00:00")
                    )
                except ValueError:
                    pass

            return Job(
                id=job_id,
                company=self.company_name,
                title=title,
                location="Unknown",
                url=loc,
                department="",
                posted_date=posted_date,
            )
        except (KeyError, TypeError) as e:
            logger.warning(f"Error parsing Google sitemap entry: {e}")
            return None
