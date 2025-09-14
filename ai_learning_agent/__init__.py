"""AI Learning Agent Package

An intelligent agent that connects to various data sources, 
researches topics autonomously, and provides interactive teaching experiences.
"""

__version__ = "1.0.0"
__author__ = "AI Learning Agent Team"

from .core.agent import Agent
from .teacher.tutor import Tutor
from .connectors.web_scraper import WebScraper
from .processors.knowledge_graph import KnowledgeGraph

__all__ = ["Agent", "Tutor", "WebScraper", "KnowledgeGraph"]