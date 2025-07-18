#!/usr/bin/env python3
"""
LeanVibe Agent Hive - Configuration Manager
Handles environment-specific configuration generation and validation
"""

import argparse
import json
import os
import sys
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import subprocess
from jinja2 import Template, Environment, FileSystemLoader
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class ConfigManager:
    """Configuration management for LeanVibe Agent Hive"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.environments_dir = self.config_dir / "environments"
        self.templates_dir = self.config_dir / "templates"
        self.output_dir = self.config_dir / "generated"
        
        # Ensure output directory exists
        self.output_dir.mkdir(exist_ok=True)
        
        # Setup Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    def load_base_config(self) -> Dict[str, Any]:
        """Load base configuration"""
        base_config_path = self.config_dir / "base.yaml"
        if not base_config_path.exists():
            raise FileNotFoundError(f"Base configuration not found: {base_config_path}")
        
        with open(base_config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def load_environment_config(self, environment: str) -> Dict[str, Any]:
        """Load environment-specific configuration"""
        env_config_path = self.environments_dir / f"{environment}.yaml"
        if not env_config_path.exists():
            raise FileNotFoundError(f"Environment configuration not found: {env_config_path}")
        
        with open(env_config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def merge_configs(self, base: Dict[str, Any], environment: Dict[str, Any]) -> Dict[str, Any]:
        """Merge base and environment configurations"""
        def deep_merge(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
            result = dict1.copy()
            for key, value in dict2.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result
        
        return deep_merge(base, environment)
    
    def get_merged_config(self, environment: str) -> Dict[str, Any]:
        """Get merged configuration for environment"""
        base_config = self.load_base_config()
        env_config = self.load_environment_config(environment)
        return self.merge_configs(base_config, env_config)
    
    def flatten_config(self, config: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """Flatten nested configuration for template variables"""
        flattened = {}
        
        for key, value in config.items():
            new_key = f"{prefix}_{key}".upper() if prefix else key.upper()
            
            if isinstance(value, dict):
                flattened.update(self.flatten_config(value, key))
            elif isinstance(value, list):
                flattened[new_key] = ",".join(str(v) for v in value)
            else:
                flattened[new_key] = str(value)
        
        return flattened
    
    def generate_docker_compose(self, environment: str) -> str:
        """Generate Docker Compose configuration"""
        config = self.get_merged_config(environment)
        template_vars = self.flatten_config(config)
        
        # Add environment-specific variables
        template_vars.update({
            "ENVIRONMENT": environment,
            "DOCKER_TARGET": "dev-server" if environment == "development" else "production",
            "DEVELOPMENT": environment == "development",
            "MONITORING": environment in ["staging", "production"],
            "RESOURCES": environment == "production",
        })
        
        template = self.jinja_env.get_template("docker-compose.yml.template")
        return template.render(**template_vars)
    
    def generate_k8s_configmap(self, environment: str) -> str:
        """Generate Kubernetes ConfigMap"""
        config = self.get_merged_config(environment)
        template_vars = self.flatten_config(config)
        
        # Add environment-specific variables
        template_vars.update({
            "ENVIRONMENT": environment,
            "ENVIRONMENT_SUFFIX": "dev" if environment == "development" else "",
        })
        
        template = self.jinja_env.get_template("k8s-configmap.yaml.template")
        return template.render(**template_vars)
    
    def validate_config(self, environment: str) -> bool:
        """Validate configuration for environment"""
        try:
            config = self.get_merged_config(environment)
            
            # Required sections
            required_sections = ["app", "server", "database", "cache", "security", "logging"]
            for section in required_sections:
                if section not in config:
                    logger.error(f"Missing required section: {section}")
                    return False
            
            # Required values
            required_values = [
                ("app.name", str),
                ("app.version", str),
                ("server.host", str),
                ("server.ports.main", int),
                ("database.type", str),
                ("cache.type", str),
            ]
            
            for path, expected_type in required_values:
                value = self._get_nested_value(config, path)
                if value is None:
                    logger.error(f"Missing required value: {path}")
                    return False
                if not isinstance(value, expected_type):
                    logger.error(f"Invalid type for {path}: expected {expected_type}, got {type(value)}")
                    return False
            
            logger.info(f"Configuration validation passed for environment: {environment}")
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False
    
    def _get_nested_value(self, config: Dict[str, Any], path: str) -> Any:
        """Get nested value from configuration using dot notation"""
        keys = path.split(".")
        value = config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value
    
    def export_config(self, environment: str, format: str = "yaml") -> str:
        """Export configuration in specified format"""
        config = self.get_merged_config(environment)
        
        if format == "yaml":
            return yaml.dump(config, default_flow_style=False, sort_keys=False)
        elif format == "json":
            return json.dumps(config, indent=2, sort_keys=False)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def list_environments(self) -> list:
        """List available environments"""
        environments = []
        for file_path in self.environments_dir.glob("*.yaml"):
            environments.append(file_path.stem)
        return sorted(environments)
    
    def generate_all(self, environment: str) -> Dict[str, str]:
        """Generate all configuration files for environment"""
        results = {}
        
        # Generate Docker Compose
        try:
            docker_compose = self.generate_docker_compose(environment)
            output_path = self.output_dir / f"docker-compose.{environment}.yml"
            with open(output_path, 'w') as f:
                f.write(docker_compose)
            results["docker_compose"] = str(output_path)
            logger.info(f"Generated Docker Compose: {output_path}")
        except Exception as e:
            logger.error(f"Failed to generate Docker Compose: {e}")
        
        # Generate Kubernetes ConfigMap
        try:
            k8s_configmap = self.generate_k8s_configmap(environment)
            output_path = self.output_dir / f"configmap.{environment}.yaml"
            with open(output_path, 'w') as f:
                f.write(k8s_configmap)
            results["k8s_configmap"] = str(output_path)
            logger.info(f"Generated Kubernetes ConfigMap: {output_path}")
        except Exception as e:
            logger.error(f"Failed to generate Kubernetes ConfigMap: {e}")
        
        # Export merged configuration
        try:
            config_yaml = self.export_config(environment, "yaml")
            output_path = self.output_dir / f"config.{environment}.yaml"
            with open(output_path, 'w') as f:
                f.write(config_yaml)
            results["config"] = str(output_path)
            logger.info(f"Generated merged configuration: {output_path}")
        except Exception as e:
            logger.error(f"Failed to generate merged configuration: {e}")
        
        return results

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="LeanVibe Agent Hive Configuration Manager"
    )
    parser.add_argument(
        "command",
        choices=["validate", "generate", "export", "list"],
        help="Command to execute"
    )
    parser.add_argument(
        "-e", "--environment",
        help="Target environment"
    )
    parser.add_argument(
        "-f", "--format",
        choices=["yaml", "json"],
        default="yaml",
        help="Output format for export"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file path"
    )
    parser.add_argument(
        "--config-dir",
        default="config",
        help="Configuration directory path"
    )
    
    args = parser.parse_args()
    
    try:
        manager = ConfigManager(args.config_dir)
        
        if args.command == "list":
            environments = manager.list_environments()
            print("Available environments:")
            for env in environments:
                print(f"  - {env}")
            return
        
        if not args.environment:
            logger.error("Environment is required for this command")
            sys.exit(1)
        
        if args.command == "validate":
            if manager.validate_config(args.environment):
                print(f"✅ Configuration validation passed for {args.environment}")
            else:
                print(f"❌ Configuration validation failed for {args.environment}")
                sys.exit(1)
        
        elif args.command == "generate":
            results = manager.generate_all(args.environment)
            print(f"Generated configuration files for {args.environment}:")
            for name, path in results.items():
                print(f"  - {name}: {path}")
        
        elif args.command == "export":
            config = manager.export_config(args.environment, args.format)
            if args.output:
                with open(args.output, 'w') as f:
                    f.write(config)
                print(f"Configuration exported to: {args.output}")
            else:
                print(config)
    
    except Exception as e:
        logger.error(f"Command failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()