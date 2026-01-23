"""Job scrapers for various company career pages."""

from .base import BaseScraper
from .google import GoogleScraper
from .stripe import StripeScraper
from .paypal import PayPalScraper
from .uber import UberScraper
from .ramp import RampScraper

__all__ = [
    "BaseScraper",
    "GoogleScraper",
    "StripeScraper",
    "PayPalScraper",
    "UberScraper",
    "RampScraper",
]

SCRAPERS = {
    "google": GoogleScraper,
    "stripe": StripeScraper,
    "paypal": PayPalScraper,
    "uber": UberScraper,
    "ramp": RampScraper,
}
