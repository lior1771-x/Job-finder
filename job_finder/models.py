"""Data models for job postings."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Job:
    """Represents a job posting."""

    id: str
    company: str
    title: str
    location: str
    url: str
    department: str = ""
    posted_date: Optional[datetime] = None
    first_seen: datetime = field(default_factory=datetime.now)
    description: Optional[str] = None

    def matches_keywords(self, keywords: list[str]) -> bool:
        """Check if job title matches any of the given keywords (case-insensitive)."""
        if not keywords:
            return True
        title_lower = self.title.lower()
        return any(kw.lower() in title_lower for kw in keywords)

    def matches_locations(self, locations: list[str]) -> bool:
        """Check if job location matches any of the given locations (case-insensitive)."""
        if not locations:
            return True
        location_lower = self.location.lower()
        return any(loc.lower() in location_lower for loc in locations)

    def __hash__(self) -> int:
        return hash((self.id, self.company))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Job):
            return False
        return self.id == other.id and self.company == other.company
