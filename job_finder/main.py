"""Main entry point for Job Finder."""

import argparse
import logging
import sys
import time
from typing import List

import schedule

from .config import Config, create_default_config
from .models import Job
from .notifiers import TerminalNotifier, WebhookNotifier
from .scrapers import SCRAPERS
from .storage import JobStorage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def fetch_all_jobs(config: Config) -> List[Job]:
    """
    Fetch jobs from all configured companies.

    Args:
        config: Application configuration.

    Returns:
        List of all fetched jobs.
    """
    all_jobs = []

    for company_name in config.companies:
        scraper_class = SCRAPERS.get(company_name.lower())
        if not scraper_class:
            logger.warning(f"Unknown company: {company_name}")
            continue

        scraper = scraper_class()
        logger.info(f"Fetching jobs from {company_name}...")

        try:
            jobs = scraper.fetch_jobs()
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"Error fetching jobs from {company_name}: {e}")

    return all_jobs


def filter_jobs(jobs: List[Job], config: Config) -> List[Job]:
    """
    Filter jobs based on configuration.

    Args:
        jobs: List of jobs to filter.
        config: Application configuration.

    Returns:
        Filtered list of jobs.
    """
    filtered = []

    for job in jobs:
        # Check keyword filter
        if config.filters.keywords:
            if not job.matches_keywords(config.filters.keywords):
                continue

        # Check location filter
        if config.filters.locations:
            if not job.matches_locations(config.filters.locations):
                continue

        filtered.append(job)

    return filtered


def run_job_check(config: Config, storage: JobStorage, terminal: TerminalNotifier, webhook: WebhookNotifier) -> None:
    """Run a single job check cycle."""
    terminal.notify_info("Fetching jobs from all companies...")

    # Fetch all jobs
    all_jobs = fetch_all_jobs(config)
    terminal.notify_info(f"Fetched {len(all_jobs)} total jobs")

    # Filter jobs
    filtered_jobs = filter_jobs(all_jobs, config)
    terminal.notify_info(f"After filtering: {len(filtered_jobs)} jobs match criteria")

    # Find new jobs
    new_jobs = storage.find_new_jobs(filtered_jobs)

    if new_jobs:
        # Store new jobs
        storage.add_jobs(new_jobs)

        # Notify via terminal
        terminal.notify(new_jobs)

        # Notify via webhooks
        if config.webhooks.slack or config.webhooks.discord:
            webhook.notify(new_jobs)
    else:
        terminal.notify_info("No new jobs found")


def cmd_run(args: argparse.Namespace) -> int:
    """Run a single job check."""
    config = Config.load(args.config)
    storage = JobStorage(config.db_path)
    terminal = TerminalNotifier()
    webhook = WebhookNotifier(
        slack_webhook=config.webhooks.slack,
        discord_webhook=config.webhooks.discord,
    )

    run_job_check(config, storage, terminal, webhook)
    return 0


def cmd_schedule(args: argparse.Namespace) -> int:
    """Run scheduled job checks."""
    config = Config.load(args.config)
    storage = JobStorage(config.db_path)
    terminal = TerminalNotifier()
    webhook = WebhookNotifier(
        slack_webhook=config.webhooks.slack,
        discord_webhook=config.webhooks.discord,
    )

    interval = args.interval or config.schedule.interval_hours

    terminal.notify_success(f"Starting scheduler (checking every {interval} hours)")
    terminal.notify_info("Press Ctrl+C to stop")

    # Run immediately on start
    run_job_check(config, storage, terminal, webhook)

    # Schedule periodic runs
    schedule.every(interval).hours.do(
        run_job_check, config, storage, terminal, webhook
    )

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        terminal.notify_info("\nScheduler stopped")

    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    """Show database statistics."""
    config = Config.load(args.config)
    storage = JobStorage(config.db_path)
    terminal = TerminalNotifier()

    stats = storage.get_stats()
    terminal.show_stats(stats)
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """List stored jobs."""
    config = Config.load(args.config)
    storage = JobStorage(config.db_path)
    terminal = TerminalNotifier()

    jobs = storage.get_all_jobs(company=args.company)

    if args.limit:
        jobs = jobs[: args.limit]

    terminal.notify(jobs, title="Stored Jobs")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    """Initialize configuration file."""
    terminal = TerminalNotifier()

    config_path = args.config or "config.yaml"
    create_default_config(config_path)

    terminal.notify_success(f"Created default configuration at {config_path}")
    terminal.notify_info("Edit the file to customize webhooks and filters")
    return 0


def cmd_test_webhooks(args: argparse.Namespace) -> int:
    """Test webhook connections."""
    config = Config.load(args.config)
    terminal = TerminalNotifier()

    if not config.webhooks.slack and not config.webhooks.discord:
        terminal.notify_error("No webhooks configured. Add webhooks to config.yaml")
        return 1

    webhook = WebhookNotifier(
        slack_webhook=config.webhooks.slack,
        discord_webhook=config.webhooks.discord,
    )

    terminal.notify_info("Testing webhook connections...")
    results = webhook.test_connection()

    for platform, success in results.items():
        if success:
            terminal.notify_success(f"{platform.capitalize()}: Connected successfully")
        else:
            terminal.notify_error(f"{platform.capitalize()}: Connection failed")

    return 0 if all(results.values()) else 1


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Job Finder - Monitor career pages for new job postings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-c", "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run a single job check")
    run_parser.set_defaults(func=cmd_run)

    # Schedule command
    schedule_parser = subparsers.add_parser("schedule", help="Run scheduled job checks")
    schedule_parser.add_argument(
        "-i", "--interval",
        type=int,
        help="Check interval in hours (overrides config)",
    )
    schedule_parser.set_defaults(func=cmd_schedule)

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show database statistics")
    stats_parser.set_defaults(func=cmd_stats)

    # List command
    list_parser = subparsers.add_parser("list", help="List stored jobs")
    list_parser.add_argument(
        "--company",
        help="Filter by company name",
    )
    list_parser.add_argument(
        "-n", "--limit",
        type=int,
        help="Limit number of jobs shown",
    )
    list_parser.set_defaults(func=cmd_list)

    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize configuration file")
    init_parser.set_defaults(func=cmd_init)

    # Test webhooks command
    test_parser = subparsers.add_parser("test-webhooks", help="Test webhook connections")
    test_parser.set_defaults(func=cmd_test_webhooks)

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not args.command:
        # Default to run if no command specified
        args.func = cmd_run

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
