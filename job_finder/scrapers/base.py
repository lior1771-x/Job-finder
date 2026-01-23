"""Base scraper interface."""

from abc import ABC, abstractmethod
from typing import List

from ..models import Job


class BaseScraper(ABC):
    """Abstract base class for job scrapers."""

    company_name: str = "Unknown"

    @abstractmethod
    def fetch_jobs(self) -> List[Job]:
        """
        Fetch current job postings from the company's career page.

        Returns:
            List of Job objects representing current openings.
        """
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} for {self.company_name}>"
