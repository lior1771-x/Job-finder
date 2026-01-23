"""SQLite storage for tracking job postings."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set

from .models import Job


class JobStorage:
    """SQLite-based storage for job postings."""

    def __init__(self, db_path: str = "jobs.db"):
        """
        Initialize the job storage.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT,
                    company TEXT,
                    title TEXT,
                    location TEXT,
                    url TEXT,
                    department TEXT,
                    posted_date TEXT,
                    first_seen TEXT,
                    PRIMARY KEY (id, company)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_company ON jobs(company)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_first_seen ON jobs(first_seen)
            """)
            conn.commit()

    def get_known_job_ids(self, company: str) -> Set[str]:
        """
        Get all known job IDs for a company.

        Args:
            company: Company name.

        Returns:
            Set of job IDs already in the database.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT id FROM jobs WHERE company = ?", (company,)
            )
            return {row[0] for row in cursor.fetchall()}

    def add_jobs(self, jobs: List[Job]) -> List[Job]:
        """
        Add new jobs to the database.

        Args:
            jobs: List of jobs to add.

        Returns:
            List of jobs that were actually new (not already in DB).
        """
        new_jobs = []
        with sqlite3.connect(self.db_path) as conn:
            for job in jobs:
                try:
                    conn.execute(
                        """
                        INSERT INTO jobs (id, company, title, location, url, department, posted_date, first_seen)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            job.id,
                            job.company,
                            job.title,
                            job.location,
                            job.url,
                            job.department,
                            job.posted_date.isoformat() if job.posted_date else None,
                            job.first_seen.isoformat(),
                        ),
                    )
                    new_jobs.append(job)
                except sqlite3.IntegrityError:
                    # Job already exists
                    pass
            conn.commit()
        return new_jobs

    def find_new_jobs(self, jobs: List[Job]) -> List[Job]:
        """
        Filter a list of jobs to only those not already in the database.

        Args:
            jobs: List of jobs to check.

        Returns:
            List of jobs not already in the database.
        """
        if not jobs:
            return []

        # Group jobs by company for efficient lookup
        jobs_by_company: dict[str, List[Job]] = {}
        for job in jobs:
            jobs_by_company.setdefault(job.company, []).append(job)

        new_jobs = []
        for company, company_jobs in jobs_by_company.items():
            known_ids = self.get_known_job_ids(company)
            for job in company_jobs:
                if job.id not in known_ids:
                    new_jobs.append(job)

        return new_jobs

    def get_job(self, job_id: str, company: str) -> Optional[Job]:
        """
        Get a specific job from the database.

        Args:
            job_id: Job ID.
            company: Company name.

        Returns:
            Job object if found, None otherwise.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM jobs WHERE id = ? AND company = ?",
                (job_id, company),
            )
            row = cursor.fetchone()
            if row:
                return Job(
                    id=row[0],
                    company=row[1],
                    title=row[2],
                    location=row[3],
                    url=row[4],
                    department=row[5],
                    posted_date=datetime.fromisoformat(row[6]) if row[6] else None,
                    first_seen=datetime.fromisoformat(row[7]),
                )
            return None

    def get_all_jobs(self, company: Optional[str] = None) -> List[Job]:
        """
        Get all jobs from the database.

        Args:
            company: Optional company filter.

        Returns:
            List of all jobs.
        """
        with sqlite3.connect(self.db_path) as conn:
            if company:
                cursor = conn.execute(
                    "SELECT * FROM jobs WHERE company = ? ORDER BY first_seen DESC",
                    (company,),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM jobs ORDER BY first_seen DESC"
                )

            return [
                Job(
                    id=row[0],
                    company=row[1],
                    title=row[2],
                    location=row[3],
                    url=row[4],
                    department=row[5],
                    posted_date=datetime.fromisoformat(row[6]) if row[6] else None,
                    first_seen=datetime.fromisoformat(row[7]),
                )
                for row in cursor.fetchall()
            ]

    def get_stats(self) -> dict:
        """Get statistics about stored jobs."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT company, COUNT(*) FROM jobs GROUP BY company"
            )
            by_company = dict(cursor.fetchall())

            cursor = conn.execute("SELECT COUNT(*) FROM jobs")
            total = cursor.fetchone()[0]

            return {"total": total, "by_company": by_company}
