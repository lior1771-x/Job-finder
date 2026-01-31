"""Ramp job scraper using Ashby API."""

import logging
import re
from datetime import datetime
from typing import List

import requests

from ..models import Job
from .base import BaseScraper

logger = logging.getLogger(__name__)


class RampScraper(BaseScraper):
    """Scraper for Ramp jobs via Ashby API."""

    company_name = "Ramp"
    # Ashby public API endpoint for Ramp
    API_URL = "https://api.ashbyhq.com/posting-api/job-board/ramp"

    def fetch_jobs(self) -> List[Job]:
        """Fetch jobs from Ramp's Ashby board."""
        jobs = []
        try:
            response = requests.get(
                self.API_URL,
                timeout=30,
                headers={"User-Agent": "JobFinder/1.0"},
            )
            response.raise_for_status()
            data = response.json()

            for job_data in data.get("jobs", []):
                job = self._parse_job(job_data)
                if job:
                    jobs.append(job)

            logger.info(f"Fetched {len(jobs)} jobs from Ramp")

        except requests.RequestException as e:
            logger.error(f"Error fetching Ramp jobs: {e}")

        return jobs

    def _parse_job(self, data: dict) -> Job | None:
        """Parse a job from Ashby API response."""
        try:
            # Get location
            location = data.get("location", "Unknown")
            if data.get("isRemote"):
                location = f"{location} (Remote)" if location != "Unknown" else "Remote"

            # Get department/team
            department = data.get("department", "")
            if data.get("team"):
                department = f"{department} - {data['team']}" if department else data["team"]

            # Parse posted date
            posted_date = None
            if data.get("publishedAt"):
                try:
                    posted_date = datetime.fromisoformat(
                        data["publishedAt"].replace("Z", "+00:00")
                    )
                except ValueError:
                    pass

            # Extract description (Ashby provides descriptionPlain or descriptionHtml)
            description = data.get("descriptionPlain")
            if not description:
                html = data.get("descriptionHtml") or data.get("description", "")
                if html:
                    description = re.sub(r"<[^>]+>", " ", html)
                    description = re.sub(r"\s+", " ", description).strip()

            return Job(
                id=data["id"],
                company=self.company_name,
                title=data.get("title", "Unknown"),
                location=location,
                url=data.get("jobUrl", ""),
                department=department,
                posted_date=posted_date,
                description=description if description else None,
            )
        except (KeyError, TypeError) as e:
            logger.warning(f"Error parsing Ramp job: {e}")
            return None
