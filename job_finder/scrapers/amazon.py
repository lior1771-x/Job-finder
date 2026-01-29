"""Amazon job scraper using their jobs API."""

import logging
from datetime import datetime
from typing import List

import requests

from ..models import Job
from .base import BaseScraper

logger = logging.getLogger(__name__)


class AmazonScraper(BaseScraper):
    """Scraper for Amazon jobs via jobs API."""

    company_name = "Amazon"
    API_URL = "https://www.amazon.jobs/en/search.json"

    def fetch_jobs(self) -> List[Job]:
        """Fetch jobs from Amazon Jobs."""
        jobs = []
        offset = 0
        limit = 100

        try:
            while True:
                params = {
                    "radius": "24km",
                    "facets[]": [
                        "normalized_country_code",
                        "normalized_state_name",
                        "normalized_city_name",
                        "location",
                        "business_category",
                        "category",
                        "schedule_type_id",
                        "employee_class",
                        "normalized_location",
                        "job_function_id",
                    ],
                    "offset": offset,
                    "result_limit": limit,
                    "sort": "recent",
                    "category[]": "product-management",
                }

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

                job_list = data.get("jobs", [])
                if not job_list:
                    break

                for job_data in job_list:
                    job = self._parse_job(job_data)
                    if job:
                        jobs.append(job)

                hits = data.get("hits", 0)
                offset += limit
                if offset >= hits:
                    break

                if len(jobs) > 5000:
                    logger.warning("Hit safety limit for Amazon jobs")
                    break

            logger.info(f"Fetched {len(jobs)} jobs from Amazon")

        except requests.RequestException as e:
            logger.error(f"Error fetching Amazon jobs: {e}")

        return jobs

    def _parse_job(self, data: dict) -> Job | None:
        """Parse a job from Amazon Jobs API response."""
        try:
            job_id = data.get("id_icims", "") or data.get("id", "")

            location = data.get("normalized_location", data.get("location", "Unknown"))

            category = data.get("business_category", "")
            job_category = data.get("category", [])
            if isinstance(job_category, list):
                department = ", ".join(job_category) if job_category else category
            else:
                department = str(job_category) if job_category else category

            posted_date = None
            if data.get("posted_date"):
                try:
                    posted_date = datetime.strptime(data["posted_date"], "%B %d, %Y")
                except ValueError:
                    try:
                        posted_date = datetime.fromisoformat(data["posted_date"].replace("Z", "+00:00"))
                    except ValueError:
                        pass

            job_path = data.get("job_path", "")
            url = f"https://www.amazon.jobs{job_path}" if job_path else ""

            return Job(
                id=str(job_id),
                company=self.company_name,
                title=data.get("title", "Unknown"),
                location=location,
                url=url,
                department=department,
                posted_date=posted_date,
            )
        except (KeyError, TypeError) as e:
            logger.warning(f"Error parsing Amazon job: {e}")
            return None
