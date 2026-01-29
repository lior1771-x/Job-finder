"""Google job scraper using careers sitemap."""

import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List

import requests

from ..models import Job
from .base import BaseScraper

logger = logging.getLogger(__name__)


class GoogleScraper(BaseScraper):
    """Scraper for Google jobs via careers sitemap."""

    company_name = "Google"
    SITEMAP_URL = "https://careers.google.com/jobs/sitemap"

    def fetch_jobs(self) -> List[Job]:
        """Fetch jobs from Google Careers sitemap."""
        jobs = []
        try:
            response = requests.get(
                self.SITEMAP_URL,
                timeout=30,
                headers={"User-Agent": "JobFinder/1.0"},
            )
            response.raise_for_status()

            # Parse XML sitemap
            root = ET.fromstring(response.content)
            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

            for url_elem in root.findall("sm:url", ns):
                job = self._parse_sitemap_entry(url_elem, ns)
                if job:
                    jobs.append(job)

            logger.info(f"Fetched {len(jobs)} jobs from Google")

        except requests.RequestException as e:
            logger.error(f"Error fetching Google jobs: {e}")
        except ET.ParseError as e:
            logger.error(f"Error parsing Google sitemap XML: {e}")

        return jobs

    def _parse_sitemap_entry(self, url_elem, ns: dict) -> Job | None:
        """Parse a job from a sitemap <url> entry."""
        try:
            loc = url_elem.findtext("sm:loc", default="", namespaces=ns)
            lastmod = url_elem.findtext("sm:lastmod", default="", namespaces=ns)

            if not loc:
                return None

            # Extract job ID and title slug from URL
            # Format: https://careers.google.com/jobs/results/12345-job-title-slug/
            match = re.search(r"/results/(\d+)-(.+?)/?$", loc)
            if not match:
                return None

            job_id = match.group(1)
            title_slug = match.group(2)

            # Convert slug to readable title
            title = self._slug_to_title(title_slug)

            # Parse lastmod date
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

    @staticmethod
    def _slug_to_title(slug: str) -> str:
        """Convert URL slug to a properly cased title."""
        # Known acronyms/abbreviations that should stay uppercase
        uppercase_words = {
            "ai", "ml", "api", "apis", "ar", "vr", "xr", "ui", "ux",
            "sre", "swe", "tpm", "pm", "hr", "it", "ab", "qa",
            "gcp", "gtm", "sql", "css", "html", "ios", "tv", "hq",
            "crm", "erp", "saas", "b2b", "b2c", "emea", "apac",
            "npi", "ops", "devops", "devsecops",
        }
        # Known words that should keep specific casing
        special_words = {
            "youtube": "YouTube",
            "google": "Google",
            "android": "Android",
            "chrome": "Chrome",
            "pixel": "Pixel",
            "waymo": "Waymo",
            "deepmind": "DeepMind",
            "tensorflow": "TensorFlow",
            "firebase": "Firebase",
            "fitbit": "Fitbit",
            "waze": "Waze",
        }

        words = slug.split("-")
        result = []
        for word in words:
            word_lower = word.lower()
            if word_lower in uppercase_words:
                result.append(word.upper())
            elif word_lower in special_words:
                result.append(special_words[word_lower])
            else:
                result.append(word.capitalize())

        # Fix roman numerals (I, II, III, IV)
        title = " ".join(result)
        title = re.sub(r'\bIii\b', 'III', title)
        title = re.sub(r'\bIi\b', 'II', title)
        title = re.sub(r'\bIv\b', 'IV', title)

        return title
