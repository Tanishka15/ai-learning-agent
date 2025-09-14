"""
Configuration Management

Handles loading and managing configuration from YAML files and environment variables.
"""

import os
import logging
from typing import Any, Dict, Optional
from dataclasses import dataclass, field

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    from dotenv import load_dotenv
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False


@dataclass
class AgentConfig:
    """Agent configuration settings."""
    name: str = "AI Learning Agent"
    version: str = "1.0.0"
    max_concurrent_tasks: int = 5
    memory_limit_mb: int = 1024


@dataclass
class DataSourcesConfig:
    """Data sources configuration."""
    
    @dataclass
    class WebScrapingConfig:
        enabled: bool = True
        max_pages_per_search: int = 10
        timeout_seconds: int = 30
        user_agent: str = "AI-Learning-Agent/1.0"
        respect_robots_txt: bool = True
    
    @dataclass
    class APIsConfig:
        enabled: bool = True
        rate_limit_requests_per_minute: int = 60
        timeout_seconds: int = 30
    
    @dataclass
    class DatabasesConfig:
        enabled: bool = True
        connection_timeout: int = 10
    
    web_scraping: WebScrapingConfig = field(default_factory=WebScrapingConfig)
    apis: APIsConfig = field(default_factory=APIsConfig)
    databases: DatabasesConfig = field(default_factory=DatabasesConfig)


@dataclass
class AIModelsConfig:
    """AI models configuration."""
    primary_llm: str = "gpt-4"
    embedding_model: str = "text-embedding-ada-002"
    summarization_model: str = "gpt-3.5-turbo"


@dataclass
class KnowledgeConfig:
    """Knowledge processing configuration."""
    max_document_length: int = 10000
    chunk_size: int = 1000
    chunk_overlap: int = 200
    similarity_threshold: float = 0.7
    max_related_concepts: int = 20


@dataclass
class TeachingConfig:
    """Teaching configuration."""
    difficulty_levels: list = field(default_factory=lambda: ["beginner", "intermediate", "advanced"])
    default_difficulty: str = "beginner"
    quiz_questions_per_topic: int = 5
    explanation_style: str = "conversational"
    include_examples: bool = True
    adaptive_learning: bool = True


@dataclass
class ReasoningConfig:
    """Reasoning engine configuration."""
    planning_depth: int = 3
    max_reasoning_steps: int = 10
    confidence_threshold: float = 0.8
    backtrack_on_failure: bool = True


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    file: str = "logs/agent.log"
    max_file_size_mb: int = 100
    backup_count: int = 5


@dataclass
class APIKeysConfig:
    """API keys configuration."""
    openai: Optional[str] = None
    anthropic: Optional[str] = None
    google: Optional[str] = None
    wikipedia: Optional[str] = None


class Config:
    """
    Main configuration class that loads and manages all configuration settings.
    
    Supports loading from:
    - YAML configuration files
    - Environment variables
    - Default values
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize configuration.
        
        Args:
            config_path: Path to YAML configuration file
        """
        self.config_path = config_path
        self.logger = logging.getLogger("config")
        
        # Load environment variables
        if HAS_DOTENV:
            load_dotenv()
        
        # Initialize configuration objects
        self.agent = AgentConfig()
        self.data_sources = DataSourcesConfig()
        self.ai_models = AIModelsConfig()
        self.knowledge = KnowledgeConfig()
        self.teaching = TeachingConfig()
        self.reasoning = ReasoningConfig()
        self.logging = LoggingConfig()
        self.api_keys = APIKeysConfig()
        
        # Load configuration
        self._load_config()
        self._load_environment_variables()
        
        self.logger.info(f"Configuration loaded from {config_path}")
    
    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        if not os.path.exists(self.config_path):
            self.logger.warning(f"Configuration file {self.config_path} not found, using defaults")
            return
        
        if not HAS_YAML:
            self.logger.warning("PyYAML not available, cannot load YAML configuration")
            return
        
        try:
            with open(self.config_path, 'r') as file:
                config_data = yaml.safe_load(file)
            
            if not config_data:
                return
            
            # Update agent config
            if 'agent' in config_data:
                self._update_dataclass_from_dict(self.agent, config_data['agent'])
            
            # Update data sources config
            if 'data_sources' in config_data:
                ds_config = config_data['data_sources']
                
                if 'web_scraping' in ds_config:
                    self._update_dataclass_from_dict(self.data_sources.web_scraping, ds_config['web_scraping'])
                
                if 'apis' in ds_config:
                    self._update_dataclass_from_dict(self.data_sources.apis, ds_config['apis'])
                
                if 'databases' in ds_config:
                    self._update_dataclass_from_dict(self.data_sources.databases, ds_config['databases'])
            
            # Update AI models config
            if 'ai_models' in config_data:
                self._update_dataclass_from_dict(self.ai_models, config_data['ai_models'])
            
            # Update knowledge config
            if 'knowledge' in config_data:
                self._update_dataclass_from_dict(self.knowledge, config_data['knowledge'])
            
            # Update teaching config
            if 'teaching' in config_data:
                self._update_dataclass_from_dict(self.teaching, config_data['teaching'])
            
            # Update reasoning config
            if 'reasoning' in config_data:
                self._update_dataclass_from_dict(self.reasoning, config_data['reasoning'])
            
            # Update logging config
            if 'logging' in config_data:
                self._update_dataclass_from_dict(self.logging, config_data['logging'])
            
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
    
    def _load_environment_variables(self) -> None:
        """Load API keys and sensitive data from environment variables."""
        self.api_keys.openai = os.getenv('OPENAI_API_KEY')
        self.api_keys.anthropic = os.getenv('ANTHROPIC_API_KEY')
        self.api_keys.google = os.getenv('GOOGLE_API_KEY')
        self.api_keys.wikipedia = os.getenv('WIKIPEDIA_API_KEY')
        
        # Override config with environment variables if present
        if os.getenv('DEBUG'):
            self.logging.level = 'DEBUG'
        
        if os.getenv('LOG_LEVEL'):
            self.logging.level = os.getenv('LOG_LEVEL')
    
    def _update_dataclass_from_dict(self, obj: Any, data: Dict[str, Any]) -> None:
        """Update a dataclass object with values from a dictionary."""
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
            else:
                self.logger.warning(f"Unknown configuration key: {key}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.
        
        Args:
            key: Configuration key in dot notation (e.g., 'agent.name')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        try:
            parts = key.split('.')
            obj = self
            
            for part in parts:
                obj = getattr(obj, part)
            
            return obj
        except AttributeError:
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value using dot notation.
        
        Args:
            key: Configuration key in dot notation
            value: Value to set
        """
        try:
            parts = key.split('.')
            obj = self
            
            for part in parts[:-1]:
                obj = getattr(obj, part)
            
            setattr(obj, parts[-1], value)
        except AttributeError:
            self.logger.error(f"Cannot set configuration key: {key}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'agent': self._dataclass_to_dict(self.agent),
            'data_sources': {
                'web_scraping': self._dataclass_to_dict(self.data_sources.web_scraping),
                'apis': self._dataclass_to_dict(self.data_sources.apis),
                'databases': self._dataclass_to_dict(self.data_sources.databases)
            },
            'ai_models': self._dataclass_to_dict(self.ai_models),
            'knowledge': self._dataclass_to_dict(self.knowledge),
            'teaching': self._dataclass_to_dict(self.teaching),
            'reasoning': self._dataclass_to_dict(self.reasoning),
            'logging': self._dataclass_to_dict(self.logging),
            'api_keys': self._dataclass_to_dict(self.api_keys, hide_sensitive=True)
        }
    
    def _dataclass_to_dict(self, obj: Any, hide_sensitive: bool = False) -> Dict[str, Any]:
        """Convert a dataclass to dictionary."""
        result = {}
        
        for field_name in obj.__dataclass_fields__:
            value = getattr(obj, field_name)
            
            if hide_sensitive and field_name in ['openai', 'anthropic', 'google', 'wikipedia']:
                result[field_name] = "***" if value else None
            else:
                result[field_name] = value
        
        return result
    
    def save(self, path: Optional[str] = None) -> None:
        """
        Save current configuration to YAML file.
        
        Args:
            path: Path to save configuration, defaults to original config path
        """
        if not HAS_YAML:
            self.logger.error("PyYAML not available, cannot save configuration")
            return
        
        save_path = path or self.config_path
        
        try:
            config_dict = self.to_dict()
            
            with open(save_path, 'w') as file:
                yaml.dump(config_dict, file, default_flow_style=False, indent=2)
            
            self.logger.info(f"Configuration saved to {save_path}")
        
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
    
    def validate(self) -> bool:
        """
        Validate configuration settings.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        valid = True
        
        # Validate numeric ranges
        if self.agent.max_concurrent_tasks <= 0:
            self.logger.error("max_concurrent_tasks must be positive")
            valid = False
        
        if self.knowledge.similarity_threshold < 0 or self.knowledge.similarity_threshold > 1:
            self.logger.error("similarity_threshold must be between 0 and 1")
            valid = False
        
        if self.reasoning.confidence_threshold < 0 or self.reasoning.confidence_threshold > 1:
            self.logger.error("confidence_threshold must be between 0 and 1")
            valid = False
        
        # Validate difficulty levels
        valid_difficulties = ["beginner", "intermediate", "advanced"]
        if self.teaching.default_difficulty not in valid_difficulties:
            self.logger.error(f"default_difficulty must be one of {valid_difficulties}")
            valid = False
        
        # Validate logging level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.logging.level.upper() not in valid_log_levels:
            self.logger.error(f"logging level must be one of {valid_log_levels}")
            valid = False
        
        return valid
    
    def __repr__(self) -> str:
        return f"Config(agent={self.agent.name}, version={self.agent.version})"