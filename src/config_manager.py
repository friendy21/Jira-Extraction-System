"""
Configuration Manager Module
Handles loading and accessing application configuration from YAML files and environment variables.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv


class ConfigManager:
    """Manages application configuration from YAML files and environment variables."""
    
    _instance = None
    _config: Dict = None
    _teams_mapping: Dict = None
    
    def __new__(cls):
        """Singleton pattern for configuration."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize configuration if not already loaded."""
        if self._config is None:
            self._load_configuration()
    
    def _load_configuration(self) -> None:
        """Load all configuration files."""
        # Load environment variables from .env file
        load_dotenv()
        
        # Determine config directory
        self._config_dir = self._find_config_dir()
        
        # Load main config
        config_path = self._config_dir / 'config.yaml'
        self._config = self._load_yaml_with_env(config_path)
        
        # Load teams mapping
        teams_path = self._config_dir / 'teams_mapping.yaml'
        self._teams_mapping = self._load_yaml_with_env(teams_path)
    
    def _find_config_dir(self) -> Path:
        """Find the configuration directory."""
        # Check for CONFIG_DIR environment variable
        env_config_dir = os.getenv('CONFIG_DIR')
        if env_config_dir:
            return Path(env_config_dir)
        
        # Default locations to check
        possible_paths = [
            Path(__file__).parent.parent.parent / 'config',  # Relative to src/
            Path.cwd() / 'config',  # Current working directory
            Path('/app/config'),  # Docker container
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        raise FileNotFoundError("Configuration directory not found")
    
    def _load_yaml_with_env(self, file_path: Path) -> Dict:
        """
        Load YAML file with environment variable substitution.
        
        Supports ${VAR_NAME} and ${VAR_NAME:-default} syntax.
        """
        if not file_path.exists():
            return {}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Substitute environment variables
        content = self._substitute_env_vars(content)
        
        return yaml.safe_load(content) or {}
    
    def _substitute_env_vars(self, content: str) -> str:
        """
        Substitute environment variables in string.
        
        Supports:
        - ${VAR_NAME} - Required variable
        - ${VAR_NAME:-default} - Variable with default value
        """
        # Pattern for ${VAR:-default} or ${VAR}
        pattern = r'\$\{([A-Z_][A-Z0-9_]*)(?::-([^}]*))?\}'
        
        def replacer(match):
            var_name = match.group(1)
            default_value = match.group(2)
            
            value = os.getenv(var_name)
            if value is not None:
                return value
            elif default_value is not None:
                return default_value
            else:
                return match.group(0)  # Return original if not found
        
        return re.sub(pattern, replacer, content)
    
    # ========================================
    # Configuration Getters
    # ========================================
    
    def get_jira_config(self) -> Dict:
        """Get Jira API configuration."""
        return self._config.get('jira', {})
    
    def get_database_config(self) -> Dict:
        """Get database configuration."""
        return self._config.get('database', {})
    
    def get_etl_config(self) -> Dict:
        """Get ETL configuration."""
        return self._config.get('etl', {})
    
    def get_reports_config(self) -> Dict:
        """Get reports configuration."""
        return self._config.get('reports', {})
    
    def get_logging_config(self) -> Dict:
        """Get logging configuration."""
        return self._config.get('logging', {})
    
    def get_scheduler_config(self) -> Dict:
        """Get scheduler configuration."""
        return self._config.get('scheduler', {})
    
    # ========================================
    # Team Mapping Getters
    # ========================================
    
    def get_organizations(self) -> List[Dict]:
        """Get all organizations."""
        return self._teams_mapping.get('organizations', [])
    
    def get_organization_by_code(self, code: str) -> Optional[Dict]:
        """Get organization by code."""
        for org in self.get_organizations():
            if org.get('code') == code:
                return org
        return None
    
    def get_all_teams(self) -> List[Dict]:
        """Get all teams across all organizations."""
        teams = []
        for org in self.get_organizations():
            org_name = org.get('name')
            for team in org.get('teams', []):
                team_copy = team.copy()
                team_copy['organization'] = org_name
                team_copy['org_code'] = org.get('code')
                teams.append(team_copy)
        return teams
    
    def get_team_by_code(self, code: str) -> Optional[Dict]:
        """Get team by code."""
        for team in self.get_all_teams():
            if team.get('code') == code:
                return team
        return None
    
    def get_teams_by_org(self, org_code: str) -> List[Dict]:
        """Get all teams for an organization."""
        org = self.get_organization_by_code(org_code)
        if org:
            return org.get('teams', [])
        return []
    
    def get_project_keys_for_team(self, team_code: str) -> List[str]:
        """Get Jira project keys for a team."""
        team = self.get_team_by_code(team_code)
        if team:
            return team.get('jira_project_keys', [])
        return []
    
    def get_all_project_keys(self) -> List[str]:
        """Get all Jira project keys across all teams."""
        keys = []
        for team in self.get_all_teams():
            keys.extend(team.get('jira_project_keys', []))
        return list(set(keys))
    
    # ========================================
    # JQL Template Getters
    # ========================================
    
    def get_jql_templates(self) -> Dict[str, str]:
        """Get JQL query templates."""
        return self._teams_mapping.get('jql_templates', {})
    
    def build_jql(self, template_name: str, **kwargs) -> str:
        """
        Build JQL query from template.
        
        Args:
            template_name: Name of the template
            **kwargs: Template variables
            
        Returns:
            Formatted JQL query
        """
        templates = self.get_jql_templates()
        template = templates.get(template_name, '')
        
        try:
            return template.format(**kwargs)
        except KeyError:
            return template
    
    # ========================================
    # Priority & Status Mappings
    # ========================================
    
    def get_priority_weights(self) -> Dict[str, int]:
        """Get priority name to weight mapping."""
        return self._teams_mapping.get('priority_weights', {})
    
    def get_status_categories(self) -> Dict[str, List[str]]:
        """Get status category mappings."""
        return self._teams_mapping.get('status_categories', {})
    
    def get_status_category(self, status_name: str) -> Optional[str]:
        """
        Get status category for a given status name.
        
        Args:
            status_name: Name of the status
            
        Returns:
            Category name ('to_do', 'in_progress', 'done') or None
        """
        categories = self.get_status_categories()
        for category, statuses in categories.items():
            if status_name in statuses:
                return category
        return None
    
    def reload(self) -> None:
        """Reload configuration from files."""
        self._config = None
        self._teams_mapping = None
        self._load_configuration()


# Convenience function
def get_config() -> ConfigManager:
    """Get the singleton configuration manager instance."""
    return ConfigManager()
