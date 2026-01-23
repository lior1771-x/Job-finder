"""Terminal notifier using Rich for formatted output."""

from typing import List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..models import Job


class TerminalNotifier:
    """Notifier that outputs job postings to the terminal with rich formatting."""

    def __init__(self):
        self.console = Console()

    def notify(self, jobs: List[Job], title: str = "New Job Postings") -> None:
        """
        Display jobs in a formatted table.

        Args:
            jobs: List of jobs to display.
            title: Title for the output.
        """
        if not jobs:
            self.console.print(
                Panel(
                    "[dim]No new jobs found[/dim]",
                    title=title,
                    border_style="dim",
                )
            )
            return

        # Group jobs by company
        jobs_by_company: dict[str, List[Job]] = {}
        for job in jobs:
            jobs_by_company.setdefault(job.company, []).append(job)

        # Create main panel
        self.console.print()
        self.console.print(
            Panel(
                f"[bold green]Found {len(jobs)} new job(s)![/bold green]",
                title=title,
                border_style="green",
            )
        )
        self.console.print()

        # Display jobs by company
        for company, company_jobs in jobs_by_company.items():
            table = Table(
                title=f"[bold]{company}[/bold] ({len(company_jobs)} jobs)",
                show_header=True,
                header_style="bold cyan",
                border_style="blue",
                expand=True,
            )

            table.add_column("Title", style="white", no_wrap=False)
            table.add_column("Location", style="yellow", no_wrap=False)
            table.add_column("Department", style="magenta", no_wrap=False)
            table.add_column("URL", style="blue", no_wrap=False)

            for job in company_jobs:
                # Truncate URL for display
                url_display = job.url
                if len(url_display) > 50:
                    url_display = url_display[:47] + "..."

                table.add_row(
                    job.title,
                    job.location,
                    job.department or "-",
                    url_display,
                )

            self.console.print(table)
            self.console.print()

    def notify_error(self, message: str) -> None:
        """Display an error message."""
        self.console.print(f"[bold red]Error:[/bold red] {message}")

    def notify_info(self, message: str) -> None:
        """Display an info message."""
        self.console.print(f"[dim]{message}[/dim]")

    def notify_success(self, message: str) -> None:
        """Display a success message."""
        self.console.print(f"[green]{message}[/green]")

    def show_stats(self, stats: dict) -> None:
        """Display storage statistics."""
        table = Table(
            title="[bold]Job Database Statistics[/bold]",
            show_header=True,
            header_style="bold cyan",
        )

        table.add_column("Company", style="white")
        table.add_column("Jobs", style="green", justify="right")

        for company, count in sorted(stats.get("by_company", {}).items()):
            table.add_row(company, str(count))

        table.add_row("[bold]Total[/bold]", f"[bold]{stats.get('total', 0)}[/bold]")

        self.console.print()
        self.console.print(table)
        self.console.print()
