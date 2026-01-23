"""Uber job scraper using careers API."""

import logging
from datetime import datetime
from typing import List

import requests

from ..models import Job
from .base import BaseScraper

logger = logging.getLogger(__name__)


class UberScraper(BaseScraper):
    """Scraper for Uber jobs via careers API."""

    company_name = "Uber"
    # Uber Careers API endpoint
    API_URL = "https://www.uber.com/api/loadSearchJobsResults"

    def fetch_jobs(self) -> List[Job]:
        """Fetch jobs from Uber Careers."""
        jobs = []
        page = 0

        try:
            while True:
                payload = {
                    "params": {
                        "page": page,
                        "limit": 100,
                        "location": [],
                        "team": [],
                    }
                }

                response = requests.post(
                    self.API_URL,
                    json=payload,
                    timeout=30,
                    headers={
                        "User-Agent": "JobFinder/1.0",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "x-csrf-token": "x",
                    },
                )
                response.raise_for_status()
                data = response.json()

                job_list = data.get("data", {}).get("results", [])
                if not job_list:
                    break

                for job_data in job_list:
                    job = self._parse_job(job_data)
                    if job:
                        jobs.append(job)

                page += 1

                # Safety limit
                if page > 50:
                    logger.warning("Hit safety limit for Uber jobs")
                    break

            logger.info(f"Fetched {len(jobs)} jobs from Uber")

        except requests.RequestException as e:
            logger.error(f"Error fetching Uber jobs: {e}")
            # Fall back to alternate method
            jobs = self._fetch_jobs_alternate()

        return jobs

    def _fetch_jobs_alternate(self) -> List[Job]:
        """Alternate fetch method using Greenhouse (Uber also uses Greenhouse)."""
        jobs = []
        try:
            # Uber also has a Greenhouse board
            response = requests.get(
                "https://api.greenhouse.io/v1/boards/uber/jobs",
                params={"content": "true"},
                timeout=30,
                headers={"User-Agent": "JobFinder/1.0"},
            )
            response.raise_for_status()
            data = response.json()

            for job_data in data.get("jobs", []):
                job = self._parse_greenhouse_job(job_data)
                if job:
                    jobs.append(job)

            logger.info(f"Fetched {len(jobs)} jobs from Uber (Greenhouse)")

        except requests.RequestException as e:
            logger.error(f"Error fetching Uber jobs from Greenhouse: {e}")

        return jobs

    def _parse_job(self, data: dict) -> Job | None:
        """Parse a job from Uber API response."""
        try:
            # Get location
            locations = data.get("location", [])
            if isinstance(locations, list):
                location = ", ".join(locations) if locations else "Unknown"
            else:
                location = str(locations) if locations else "Unknown"

            # Get department/team
            teams = data.get("team", [])
            if isinstance(teams, list):
                department = ", ".join(teams) if teams else ""
            else:
                department = str(teams) if teams else ""

            return Job(
                id=str(data.get("id", "")),
                company=self.company_name,
                title=data.get("title", "Unknown"),
                location=location,
                url=data.get("url", f"https://www.uber.com/careers/list/{data.get('id', '')}"),
                department=department,
                posted_date=None,
            )
        except (KeyError, TypeError) as e:
            logger.warning(f"Error parsing Uber job: {e}")
            return None

    def _parse_greenhouse_job(self, data: dict) -> Job | None:
        """Parse a job from Greenhouse API response."""
        try:
            locations = []
            for office in data.get("offices", []):
                if office.get("name"):
                    locations.append(office["name"])
            location = ", ".join(locations) if locations else "Unknown"

            departments = []
            for dept in data.get("departments", []):
                if dept.get("name"):
                    departments.append(dept["name"])
            department = ", ".join(departments) if departments else ""

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
            logger.warning(f"Error parsing Uber Greenhouse job: {e}")
            return None
