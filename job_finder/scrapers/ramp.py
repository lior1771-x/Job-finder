"""Ramp job scraper using Lever API."""

import logging
from datetime import datetime
from typing import List

import requests

from ..models import Job
from .base import BaseScraper

logger = logging.getLogger(__name__)


class RampScraper(BaseScraper):
    """Scraper for Ramp jobs via Lever API."""

    company_name = "Ramp"
    # Lever public API endpoint for Ramp
    API_URL = "https://api.lever.co/v0/postings/ramp"

    def fetch_jobs(self) -> List[Job]:
        """Fetch jobs from Ramp's Lever board."""
        jobs = []
        try:
            response = requests.get(
                self.API_URL,
                params={"mode": "json"},
                timeout=30,
                headers={"User-Agent": "JobFinder/1.0"},
            )
            response.raise_for_status()
            data = response.json()

            for job_data in data:
                job = self._parse_job(job_data)
                if job:
                    jobs.append(job)

            logger.info(f"Fetched {len(jobs)} jobs from Ramp")

        except requests.RequestException as e:
            logger.error(f"Error fetching Ramp jobs: {e}")

        return jobs

    def _parse_job(self, data: dict) -> Job | None:
        """Parse a job from Lever API response."""
        try:
            # Get location
            location = data.get("categories", {}).get("location", "Unknown")

            # Get department/team
            department = data.get("categories", {}).get("team", "")

            # Parse posted date (Lever uses milliseconds timestamp)
            posted_date = None
            if data.get("createdAt"):
                try:
                    posted_date = datetime.fromtimestamp(data["createdAt"] / 1000)
                except (ValueError, TypeError):
                    pass

            return Job(
                id=data["id"],
                company=self.company_name,
                title=data.get("text", "Unknown"),
                location=location,
                url=data.get("hostedUrl", ""),
                department=department,
                posted_date=posted_date,
            )
        except (KeyError, TypeError) as e:
            logger.warning(f"Error parsing Ramp job: {e}")
            return None
