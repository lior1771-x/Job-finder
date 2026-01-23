"""Stripe job scraper using Greenhouse API."""

import logging
from datetime import datetime
from typing import List

import requests

from ..models import Job
from .base import BaseScraper

logger = logging.getLogger(__name__)


class StripeScraper(BaseScraper):
    """Scraper for Stripe jobs via Greenhouse API."""

    company_name = "Stripe"
    # Greenhouse public API endpoint for Stripe
    API_URL = "https://api.greenhouse.io/v1/boards/stripe/jobs"

    def fetch_jobs(self) -> List[Job]:
        """Fetch jobs from Stripe's Greenhouse board."""
        jobs = []
        try:
            response = requests.get(
                self.API_URL,
                params={"content": "true"},
                timeout=30,
                headers={"User-Agent": "JobFinder/1.0"},
            )
            response.raise_for_status()
            data = response.json()

            for job_data in data.get("jobs", []):
                job = self._parse_job(job_data)
                if job:
                    jobs.append(job)

            logger.info(f"Fetched {len(jobs)} jobs from Stripe")

        except requests.RequestException as e:
            logger.error(f"Error fetching Stripe jobs: {e}")

        return jobs

    def _parse_job(self, data: dict) -> Job | None:
        """Parse a job from Greenhouse API response."""
        try:
            # Get location from offices
            locations = []
            for office in data.get("offices", []):
                if office.get("name"):
                    locations.append(office["name"])
            location = ", ".join(locations) if locations else "Unknown"

            # Get department
            departments = []
            for dept in data.get("departments", []):
                if dept.get("name"):
                    departments.append(dept["name"])
            department = ", ".join(departments) if departments else ""

            # Parse posted date
            posted_date = None
            if data.get("updated_at"):
                try:
                    posted_date = datetime.fromisoformat(
                        data["updated_at"].replace("Z", "+00:00")
                    )
                except ValueError:
                    pass

            return Job(
                id=str(data["id"]),
                company=self.company_name,
                title=data.get("title", "Unknown"),
                location=location,
                url=data.get("absolute_url", ""),
                department=department,
                posted_date=posted_date,
            )
        except (KeyError, TypeError) as e:
            logger.warning(f"Error parsing Stripe job: {e}")
            return None
