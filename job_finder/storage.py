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
            # Tracker table for companies/roles user is interested in
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tracker (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company TEXT NOT NULL,
                    role TEXT,
                    status TEXT DEFAULT 'Interested',
                    referral TEXT,
                    notes TEXT,
                    job_id TEXT,
                    job_company TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    FOREIGN KEY (job_id, job_company) REFERENCES jobs(id, company)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tracker_company ON tracker(company)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tracker_status ON tracker(status)
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
                    "SELECT * FROM jobs WHERE company = ? COLLATE NOCASE ORDER BY first_seen DESC",
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

    def delete_jobs_by_company(self, company: str) -> int:
        """Delete all jobs for a given company. Returns number of deleted rows."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM jobs WHERE company = ? COLLATE NOCASE", (company,)
            )
            conn.commit()
            return cursor.rowcount

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

    # Tracker methods
    def add_tracker_entry(
        self,
        company: str,
        role: Optional[str] = None,
        status: str = "Interested",
        referral: Optional[str] = None,
        notes: Optional[str] = None,
        job_id: Optional[str] = None,
        job_company: Optional[str] = None,
    ) -> int:
        """
        Add a new entry to the tracker.

        Returns:
            The ID of the newly created entry.
        """
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO tracker (company, role, status, referral, notes, job_id, job_company, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (company, role, status, referral, notes, job_id, job_company, now, now),
            )
            conn.commit()
            return cursor.lastrowid

    def update_tracker_entry(
        self,
        entry_id: int,
        company: Optional[str] = None,
        role: Optional[str] = None,
        status: Optional[str] = None,
        referral: Optional[str] = None,
        notes: Optional[str] = None,
        job_id: Optional[str] = None,
        job_company: Optional[str] = None,
    ) -> bool:
        """
        Update an existing tracker entry.

        Returns:
            True if the entry was updated, False if not found.
        """
        updates = []
        values = []

        if company is not None:
            updates.append("company = ?")
            values.append(company)
        if role is not None:
            updates.append("role = ?")
            values.append(role)
        if status is not None:
            updates.append("status = ?")
            values.append(status)
        if referral is not None:
            updates.append("referral = ?")
            values.append(referral)
        if notes is not None:
            updates.append("notes = ?")
            values.append(notes)
        if job_id is not None:
            updates.append("job_id = ?")
            values.append(job_id)
        if job_company is not None:
            updates.append("job_company = ?")
            values.append(job_company)

        if not updates:
            return False

        updates.append("updated_at = ?")
        values.append(datetime.now().isoformat())
        values.append(entry_id)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                f"UPDATE tracker SET {', '.join(updates)} WHERE id = ?",
                values,
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_tracker_entry(self, entry_id: int) -> bool:
        """
        Delete a tracker entry.

        Returns:
            True if the entry was deleted, False if not found.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM tracker WHERE id = ?", (entry_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_all_tracker_entries(self) -> List[dict]:
        """
        Get all tracker entries with linked job info if available.

        Returns:
            List of tracker entries as dictionaries.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT t.id, t.company, t.role, t.status, t.referral, t.notes,
                       t.job_id, t.job_company, t.created_at, t.updated_at,
                       j.title as job_title, j.url as job_url, j.location as job_location
                FROM tracker t
                LEFT JOIN jobs j ON t.job_id = j.id AND t.job_company = j.company
                ORDER BY t.updated_at DESC
                """
            )
            columns = [
                "id", "company", "role", "status", "referral", "notes",
                "job_id", "job_company", "created_at", "updated_at",
                "job_title", "job_url", "job_location"
            ]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_tracker_entry(self, entry_id: int) -> Optional[dict]:
        """Get a single tracker entry by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT t.id, t.company, t.role, t.status, t.referral, t.notes,
                       t.job_id, t.job_company, t.created_at, t.updated_at,
                       j.title as job_title, j.url as job_url, j.location as job_location
                FROM tracker t
                LEFT JOIN jobs j ON t.job_id = j.id AND t.job_company = j.company
                WHERE t.id = ?
                """,
                (entry_id,),
            )
            row = cursor.fetchone()
            if row:
                columns = [
                    "id", "company", "role", "status", "referral", "notes",
                    "job_id", "job_company", "created_at", "updated_at",
                    "job_title", "job_url", "job_location"
                ]
                return dict(zip(columns, row))
            return None

    def is_job_tracked(self, job_id: str, job_company: str) -> bool:
        """Check if a job is already in the tracker."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM tracker WHERE job_id = ? AND job_company = ? LIMIT 1",
                (job_id, job_company),
            )
            return cursor.fetchone() is not None

    def get_tracked_job_ids(self) -> Set[tuple]:
        """Get all tracked job (id, company) pairs for quick lookup."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT job_id, job_company FROM tracker WHERE job_id IS NOT NULL")
            return {(row[0], row[1]) for row in cursor.fetchall()}
