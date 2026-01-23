"""PayPal job scraper."""

import logging
from datetime import datetime
from typing import List

import requests
from bs4 import BeautifulSoup

from ..models import Job
from .base import BaseScraper

logger = logging.getLogger(__name__)


class PayPalScraper(BaseScraper):
    """Scraper for PayPal jobs."""

    company_name = "PayPal"
    # PayPal uses Workday, we'll use their job search API
    API_URL = "https://paypal.wd1.myworkdayjobs.com/wday/cxs/paypal/jobs/jobs"

    def fetch_jobs(self) -> List[Job]:
        """Fetch jobs from PayPal Careers (Workday)."""
        jobs = []
        offset = 0
        limit = 50

        try:
            while True:
                payload = {
                    "appliedFacets": {},
                    "limit": limit,
                    "offset": offset,
                    "searchText": "",
                }

                response = requests.post(
                    self.API_URL,
                    json=payload,
                    timeout=30,
                    headers={
                        "User-Agent": "JobFinder/1.0",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                )
                response.raise_for_status()
                data = response.json()

                job_postings = data.get("jobPostings", [])
                if not job_postings:
                    break

                for job_data in job_postings:
                    job = self._parse_job(job_data)
                    if job:
                        jobs.append(job)

                offset += limit

                # Check if we've fetched all jobs
                total = data.get("total", 0)
                if offset >= total:
                    break

                # Safety limit
                if offset > 5000:
                    logger.warning("Hit safety limit for PayPal jobs")
                    break

            logger.info(f"Fetched {len(jobs)} jobs from PayPal")

        except requests.RequestException as e:
            logger.error(f"Error fetching PayPal jobs: {e}")

        return jobs

    def _parse_job(self, data: dict) -> Job | None:
        """Parse a job from PayPal Workday API response."""
        try:
            # Extract job ID from external path
            external_path = data.get("externalPath", "")
            job_id = external_path.split("/")[-1] if external_path else str(hash(data.get("title", "")))

            # Get location
            location = data.get("locationsText", "Unknown")

            # Build URL
            base_url = "https://paypal.wd1.myworkdayjobs.com/jobs"
            url = f"{base_url}{external_path}" if external_path else base_url

            # Get posted date
            posted_date = None
            if data.get("postedOn"):
                try:
                    # Workday uses format like "Posted 30+ Days Ago" or dates
                    posted_text = data["postedOn"]
                    if "today" in posted_text.lower():
                        posted_date = datetime.now()
                except (ValueError, AttributeError):
                    pass

            return Job(
                id=job_id,
                company=self.company_name,
                title=data.get("title", "Unknown"),
                location=location,
                url=url,
                department=data.get("categoryHierarchy", [""])[0] if data.get("categoryHierarchy") else "",
                posted_date=posted_date,
            )
        except (KeyError, TypeError, IndexError) as e:
            logger.warning(f"Error parsing PayPal job: {e}")
            return None
