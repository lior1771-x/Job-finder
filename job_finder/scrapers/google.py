"""Google job scraper using careers API."""

import logging
from datetime import datetime
from typing import List

import requests

from ..models import Job
from .base import BaseScraper

logger = logging.getLogger(__name__)


class GoogleScraper(BaseScraper):
    """Scraper for Google jobs via careers API."""

    company_name = "Google"
    # Google Careers API endpoint
    API_URL = "https://careers.google.com/api/v3/search/"

    def fetch_jobs(self) -> List[Job]:
        """Fetch jobs from Google Careers."""
        jobs = []
        page_token = None

        try:
            while True:
                params = {
                    "page_size": 100,
                    "q": "",  # Empty query to get all jobs
                }
                if page_token:
                    params["page_token"] = page_token

                response = requests.get(
                    self.API_URL,
                    params=params,
                    timeout=30,
                    headers={
                        "User-Agent": "JobFinder/1.0",
                        "Accept": "application/json",
                    },
                )
                response.raise_for_status()
                data = response.json()

                for job_data in data.get("jobs", []):
                    job = self._parse_job(job_data)
                    if job:
                        jobs.append(job)

                # Check for next page
                page_token = data.get("next_page_token")
                if not page_token:
                    break

                # Safety limit
                if len(jobs) > 5000:
                    logger.warning("Hit safety limit for Google jobs")
                    break

            logger.info(f"Fetched {len(jobs)} jobs from Google")

        except requests.RequestException as e:
            logger.error(f"Error fetching Google jobs: {e}")

        return jobs

    def _parse_job(self, data: dict) -> Job | None:
        """Parse a job from Google Careers API response."""
        try:
            # Extract job ID from the name field (format: jobs/ID)
            job_id = data.get("id", {}).get("job_id", "")
            if not job_id:
                name = data.get("name", "")
                job_id = name.split("/")[-1] if "/" in name else name

            # Get locations
            locations = data.get("locations", [])
            location_names = []
            for loc in locations:
                if isinstance(loc, dict):
                    location_names.append(loc.get("display", loc.get("city", "Unknown")))
                elif isinstance(loc, str):
                    location_names.append(loc)
            location = ", ".join(location_names) if location_names else "Unknown"

            # Get department/category
            categories = data.get("categories", [])
            department = ", ".join(categories) if categories else ""

            # Build URL
            url = f"https://careers.google.com/jobs/results/{job_id}"
            if data.get("apply_url"):
                url = data["apply_url"]

            return Job(
                id=job_id,
                company=self.company_name,
                title=data.get("title", "Unknown"),
                location=location,
                url=url,
                department=department,
                posted_date=None,  # Google API doesn't expose posting date
            )
        except (KeyError, TypeError) as e:
            logger.warning(f"Error parsing Google job: {e}")
            return None
