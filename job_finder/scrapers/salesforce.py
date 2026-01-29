"""Salesforce job scraper using their careers API."""

import logging
from datetime import datetime
from typing import List

import requests

from ..models import Job
from .base import BaseScraper

logger = logging.getLogger(__name__)


class SalesforceScraper(BaseScraper):
    """Scraper for Salesforce jobs via careers API."""

    company_name = "Salesforce"
    API_URL = "https://salesforce.wd12.myworkdayjobs.com/wday/cxs/salesforce/External_Career_Site/jobs"

    def fetch_jobs(self) -> List[Job]:
        """Fetch jobs from Salesforce Workday careers."""
        jobs = []
        offset = 0
        limit = 20

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

                total = data.get("total", 0)
                offset += limit
                if offset >= total:
                    break

                if len(jobs) > 5000:
                    logger.warning("Hit safety limit for Salesforce jobs")
                    break

            logger.info(f"Fetched {len(jobs)} jobs from Salesforce")

        except requests.RequestException as e:
            logger.error(f"Error fetching Salesforce jobs: {e}")

        return jobs

    def _parse_job(self, data: dict) -> Job | None:
        """Parse a job from Salesforce Workday API response."""
        try:
            # Extract job ID from external path
            external_path = data.get("externalPath", "")
            job_id = external_path.split("/")[-1] if external_path else str(data.get("bulletFields", [""])[0])

            location = data.get("locationsText", "Unknown")

            posted_date = None
            if data.get("postedOn"):
                try:
                    posted_date = datetime.strptime(data["postedOn"], "%Y-%m-%d")
                except ValueError:
                    pass

            return Job(
                id=job_id,
                company=self.company_name,
                title=data.get("title", "Unknown"),
                location=location,
                url=f"https://salesforce.wd12.myworkdayjobs.com/en-US/External_Career_Site{external_path}",
                department="",
                posted_date=posted_date,
            )
        except (KeyError, TypeError) as e:
            logger.warning(f"Error parsing Salesforce job: {e}")
            return None
