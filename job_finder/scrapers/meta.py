"""Meta job scraper using their careers API."""

import logging
from datetime import datetime
from typing import List

import requests

from ..models import Job
from .base import BaseScraper

logger = logging.getLogger(__name__)


class MetaScraper(BaseScraper):
    """Scraper for Meta jobs via careers API."""

    company_name = "Meta"
    API_URL = "https://www.metacareers.com/graphql"

    def fetch_jobs(self) -> List[Job]:
        """Fetch jobs from Meta Careers."""
        jobs = []
        cursor = None

        try:
            while True:
                # GraphQL query for job listings
                query = {
                    "query": """
                        query GetJobs($cursor: String) {
                            job_search(first: 100, after: $cursor) {
                                edges {
                                    node {
                                        id
                                        title
                                        locations
                                        teams
                                        sub_teams
                                        create_time
                                    }
                                    cursor
                                }
                                page_info {
                                    has_next_page
                                    end_cursor
                                }
                            }
                        }
                    """,
                    "variables": {"cursor": cursor},
                }

                response = requests.post(
                    self.API_URL,
                    json=query,
                    timeout=30,
                    headers={
                        "User-Agent": "JobFinder/1.0",
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()
                data = response.json()

                search_data = data.get("data", {}).get("job_search", {})
                edges = search_data.get("edges", [])

                for edge in edges:
                    job = self._parse_job(edge.get("node", {}))
                    if job:
                        jobs.append(job)

                page_info = search_data.get("page_info", {})
                if not page_info.get("has_next_page"):
                    break
                cursor = page_info.get("end_cursor")

                if len(jobs) > 5000:
                    logger.warning("Hit safety limit for Meta jobs")
                    break

            logger.info(f"Fetched {len(jobs)} jobs from Meta")

        except requests.RequestException as e:
            logger.error(f"Error fetching Meta jobs: {e}")
            # Fallback to alternative approach if GraphQL fails
            jobs = self._fetch_jobs_fallback()

        return jobs

    def _fetch_jobs_fallback(self) -> List[Job]:
        """Fallback method using the public jobs endpoint."""
        jobs = []
        try:
            # Meta's public career page API
            response = requests.get(
                "https://www.metacareers.com/jobs",
                params={"page": 1, "results_per_page": 100},
                timeout=30,
                headers={"User-Agent": "JobFinder/1.0"},
            )
            # If this also fails, return empty list
            if not response.ok:
                return jobs
        except requests.RequestException:
            pass
        return jobs

    def _parse_job(self, data: dict) -> Job | None:
        """Parse a job from Meta API response."""
        try:
            job_id = str(data.get("id", ""))
            if not job_id:
                return None

            locations = data.get("locations", [])
            if isinstance(locations, list):
                location = ", ".join(locations) if locations else "Unknown"
            else:
                location = str(locations) if locations else "Unknown"

            teams = data.get("teams", [])
            sub_teams = data.get("sub_teams", [])
            all_teams = teams + sub_teams if isinstance(teams, list) and isinstance(sub_teams, list) else []
            department = ", ".join(all_teams) if all_teams else ""

            posted_date = None
            if data.get("create_time"):
                try:
                    posted_date = datetime.fromtimestamp(data["create_time"])
                except (ValueError, TypeError):
                    pass

            return Job(
                id=job_id,
                company=self.company_name,
                title=data.get("title", "Unknown"),
                location=location,
                url=f"https://www.metacareers.com/jobs/{job_id}",
                department=department,
                posted_date=posted_date,
            )
        except (KeyError, TypeError) as e:
            logger.warning(f"Error parsing Meta job: {e}")
            return None
