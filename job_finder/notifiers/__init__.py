"""Notification handlers for job postings."""

from .terminal import TerminalNotifier
from .webhook import WebhookNotifier

__all__ = ["TerminalNotifier", "WebhookNotifier"]
