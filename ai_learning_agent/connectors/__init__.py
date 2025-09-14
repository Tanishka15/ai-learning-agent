"""Connectors module for data source integration."""

from .web_scraper import WebScraper
from .api_client import APIClient
from .database import DatabaseConnector

__all__ = ["WebScraper", "APIClient", "DatabaseConnector"]