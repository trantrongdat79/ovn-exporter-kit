"""
Farm assignment logic based on hostname patterns.

Resolves farm identifiers from hostnames using configurable pattern matching rules.
"""

import os
from typing import List, Dict, Optional
import yaml
from common.logger import MyLogger


class FarmResolver:
    """
    Resolves farm identifiers from hostnames using pattern matching.
    
    Patterns are loaded from YAML configuration and matched sequentially.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize farm resolver with configuration.
        
        Args:
            config_path: Path to farm_rules.yaml configuration file.
        """
        self.logger = MyLogger(
            'raw_to_json-farm-resolver',
            'logs/raw_to_json/farm-resolver.log',
            level=os.getenv('LOG_LEVEL', 'INFO')
        )
        
        # Use provided path, env var, or default
        if config_path is None:
            config_path = os.getenv('FARM_RULES_PATH', '/config/farm_rules.yaml')
        
        self.rules: List[Dict[str, str]] = []
        self.config_path = config_path
        self._load_rules()
    
    def _load_rules(self):
        """
        Load farm assignment rules from YAML file.
        
        Gracefully handles errors by logging and using empty rules.
        """
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                
            if not config or 'farm_rules' not in config:
                self.logger.log_with_context(
                    MyLogger.WARNING,
                    "No farm_rules found in configuration",
                    config_path=self.config_path
                )
                self.rules = []
                return
            
            self.rules = config['farm_rules']
            self.logger.log_with_context(
                MyLogger.INFO,
                "Farm rules loaded successfully",
                config_path=self.config_path,
                rule_count=len(self.rules)
            )
            
        except FileNotFoundError:
            self.logger.log_with_context(
                MyLogger.WARNING,
                "Farm rules configuration file not found",
                config_path=self.config_path
            )
            self.rules = []
            
        except yaml.YAMLError as e:
            self.logger.log_with_context(
                MyLogger.ERROR,
                "Failed to parse farm rules YAML",
                config_path=self.config_path,
                error=str(e)
            )
            self.rules = []
            
        except Exception as e:
            self.logger.log_with_context(
                MyLogger.ERROR,
                "Unexpected error loading farm rules",
                config_path=self.config_path,
                error=str(e)
            )
            self.rules = []
    
    def resolve(self, hostname: str) -> str:
        """
        Resolve farm identifier from hostname.
        
        Checks patterns sequentially and returns first match.
        Falls back to 'other' if no pattern matches.
        
        Args:
            hostname: Hostname to resolve
            
        Returns:
            Farm identifier string
        """
        # Handle None or empty hostname
        if not hostname:
            return "other"
        
        # Check each rule in order
        for rule in self.rules:
            pattern = rule.get('pattern', '')
            farm = rule.get('farm', 'other')
            
            # Special handling for 'default' pattern (always matches)
            if pattern == 'default':
                return farm
            
            # Check if pattern is in hostname (case-sensitive substring match)
            if pattern and pattern in hostname:
                self.logger.log_with_context(
                    MyLogger.DEBUG,
                    "Farm resolved",
                    hostname=hostname,
                    pattern=pattern,
                    farm=farm
                )
                return farm
        
        # No match found, return default
        self.logger.log_with_context(
            MyLogger.DEBUG,
            "No farm pattern matched, using default",
            hostname=hostname
        )
        return "other"
