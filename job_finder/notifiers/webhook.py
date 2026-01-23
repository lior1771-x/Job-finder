"""Webhook notifier for Slack and Discord."""

import logging
from typing import List, Optional

import requests

from ..models import Job

logger = logging.getLogger(__name__)


class WebhookNotifier:
    """Notifier that sends job postings to Slack/Discord webhooks."""

    def __init__(
        self,
        slack_webhook: Optional[str] = None,
        discord_webhook: Optional[str] = None,
    ):
        """
        Initialize webhook notifier.

        Args:
            slack_webhook: Slack incoming webhook URL.
            discord_webhook: Discord webhook URL.
        """
        self.slack_webhook = slack_webhook
        self.discord_webhook = discord_webhook

    def notify(self, jobs: List[Job]) -> bool:
        """
        Send job notifications to configured webhooks.

        Args:
            jobs: List of jobs to notify about.

        Returns:
            True if at least one notification was sent successfully.
        """
        if not jobs:
            return True

        success = False

        if self.slack_webhook:
            if self._send_slack(jobs):
                success = True

        if self.discord_webhook:
            if self._send_discord(jobs):
                success = True

        return success

    def _send_slack(self, jobs: List[Job]) -> bool:
        """Send notification to Slack."""
        try:
            # Group jobs by company
            jobs_by_company: dict[str, List[Job]] = {}
            for job in jobs:
                jobs_by_company.setdefault(job.company, []).append(job)

            # Build Slack message blocks
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🚀 {len(jobs)} New Job(s) Found!",
                        "emoji": True,
                    },
                },
                {"type": "divider"},
            ]

            for company, company_jobs in jobs_by_company.items():
                blocks.append(
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*{company}* ({len(company_jobs)} jobs)",
                        },
                    }
                )

                # Add up to 10 jobs per company to avoid message limits
                for job in company_jobs[:10]:
                    location_text = f" | 📍 {job.location}" if job.location else ""
                    dept_text = f" | 🏢 {job.department}" if job.department else ""

                    blocks.append(
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"• <{job.url}|{job.title}>{location_text}{dept_text}",
                            },
                        }
                    )

                if len(company_jobs) > 10:
                    blocks.append(
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"_...and {len(company_jobs) - 10} more_",
                            },
                        }
                    )

                blocks.append({"type": "divider"})

            payload = {"blocks": blocks}

            response = requests.post(
                self.slack_webhook,
                json=payload,
                timeout=30,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

            logger.info(f"Sent Slack notification for {len(jobs)} jobs")
            return True

        except requests.RequestException as e:
            logger.error(f"Error sending Slack notification: {e}")
            return False

    def _send_discord(self, jobs: List[Job]) -> bool:
        """Send notification to Discord."""
        try:
            # Group jobs by company
            jobs_by_company: dict[str, List[Job]] = {}
            for job in jobs:
                jobs_by_company.setdefault(job.company, []).append(job)

            # Build Discord embeds
            embeds = []

            for company, company_jobs in jobs_by_company.items():
                # Build job list for this company
                job_lines = []
                for job in company_jobs[:10]:
                    location = f" ({job.location})" if job.location else ""
                    job_lines.append(f"• [{job.title}]({job.url}){location}")

                if len(company_jobs) > 10:
                    job_lines.append(f"_...and {len(company_jobs) - 10} more_")

                embeds.append(
                    {
                        "title": f"{company} ({len(company_jobs)} jobs)",
                        "description": "\n".join(job_lines),
                        "color": 0x00FF00,  # Green
                    }
                )

            payload = {
                "content": f"🚀 **{len(jobs)} New Job(s) Found!**",
                "embeds": embeds[:10],  # Discord limits to 10 embeds
            }

            response = requests.post(
                self.discord_webhook,
                json=payload,
                timeout=30,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

            logger.info(f"Sent Discord notification for {len(jobs)} jobs")
            return True

        except requests.RequestException as e:
            logger.error(f"Error sending Discord notification: {e}")
            return False

    def test_connection(self) -> dict[str, bool]:
        """Test webhook connections."""
        results = {}

        if self.slack_webhook:
            try:
                response = requests.post(
                    self.slack_webhook,
                    json={"text": "🔔 Job Finder webhook test - connection successful!"},
                    timeout=10,
                )
                results["slack"] = response.status_code == 200
            except requests.RequestException:
                results["slack"] = False

        if self.discord_webhook:
            try:
                response = requests.post(
                    self.discord_webhook,
                    json={"content": "🔔 Job Finder webhook test - connection successful!"},
                    timeout=10,
                )
                results["discord"] = response.status_code == 204 or response.status_code == 200
            except requests.RequestException:
                results["discord"] = False

        return results
