"""Configuration management for Job Finder."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml


@dataclass
class WebhooksConfig:
    """Webhook configuration."""

    slack: Optional[str] = None
    discord: Optional[str] = None


@dataclass
class FiltersConfig:
    """Job filtering configuration."""

    keywords: List[str] = field(default_factory=list)
    locations: List[str] = field(default_factory=list)


@dataclass
class ScheduleConfig:
    """Scheduler configuration."""

    interval_hours: int = 6


@dataclass
class Config:
    """Main configuration class."""

    webhooks: WebhooksConfig = field(default_factory=WebhooksConfig)
    filters: FiltersConfig = field(default_factory=FiltersConfig)
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    db_path: str = "jobs.db"
    companies: List[str] = field(
        default_factory=lambda: [
            "google", "stripe", "paypal", "uber", "ramp",
            "openai", "anthropic", "datadog", "salesforce", "amazon",
        ]
    )

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Config":
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to config file. Defaults to config.yaml in current directory.

        Returns:
            Config instance.
        """
        if config_path is None:
            config_path = "config.yaml"

        path = Path(config_path)
        if not path.exists():
            return cls()

        with open(path) as f:
            data = yaml.safe_load(f) or {}

        # Parse webhooks
        webhooks_data = data.get("webhooks", {})
        webhooks = WebhooksConfig(
            slack=webhooks_data.get("slack") or os.environ.get("JOB_FINDER_SLACK_WEBHOOK"),
            discord=webhooks_data.get("discord") or os.environ.get("JOB_FINDER_DISCORD_WEBHOOK"),
        )

        # Parse filters
        filters_data = data.get("filters", {})
        filters = FiltersConfig(
            keywords=filters_data.get("keywords", []),
            locations=filters_data.get("locations", []),
        )

        # Parse schedule
        schedule_data = data.get("schedule", {})
        schedule = ScheduleConfig(
            interval_hours=schedule_data.get("interval_hours", 6),
        )

        # Parse other settings
        db_path = data.get("db_path", "jobs.db")
        companies = data.get("companies", [
            "google", "stripe", "paypal", "uber", "ramp",
            "openai", "anthropic", "datadog", "salesforce", "amazon",
        ])

        return cls(
            webhooks=webhooks,
            filters=filters,
            schedule=schedule,
            db_path=db_path,
            companies=companies,
        )

    def save(self, config_path: str = "config.yaml") -> None:
        """
        Save configuration to YAML file.

        Args:
            config_path: Path to config file.
        """
        data = {
            "webhooks": {
                "slack": self.webhooks.slack,
                "discord": self.webhooks.discord,
            },
            "filters": {
                "keywords": self.filters.keywords,
                "locations": self.filters.locations,
            },
            "schedule": {
                "interval_hours": self.schedule.interval_hours,
            },
            "db_path": self.db_path,
            "companies": self.companies,
        }

        with open(config_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def create_default_config(config_path: str = "config.yaml") -> None:
    """Create a default configuration file."""
    config = Config(
        filters=FiltersConfig(
            keywords=["engineer", "developer", "software"],
            locations=["remote", "new york"],
        ),
    )
    config.save(config_path)
