"""Job scrapers for various company career pages."""

from .base import BaseScraper
from .google import GoogleScraper
from .stripe import StripeScraper
from .paypal import PayPalScraper
from .uber import UberScraper
from .ramp import RampScraper
from .openai import OpenAIScraper
from .anthropic import AnthropicScraper
from .datadog import DatadogScraper
from .salesforce import SalesforceScraper
from .amazon import AmazonScraper

__all__ = [
    "BaseScraper",
    "GoogleScraper",
    "StripeScraper",
    "PayPalScraper",
    "UberScraper",
    "RampScraper",
    "OpenAIScraper",
    "AnthropicScraper",
    "DatadogScraper",
    "SalesforceScraper",
    "AmazonScraper",
]

SCRAPERS = {
    "google": GoogleScraper,
    "stripe": StripeScraper,
    "paypal": PayPalScraper,
    "uber": UberScraper,
    "ramp": RampScraper,
    "openai": OpenAIScraper,
    "anthropic": AnthropicScraper,
    "datadog": DatadogScraper,
    "salesforce": SalesforceScraper,
    "amazon": AmazonScraper,
}
