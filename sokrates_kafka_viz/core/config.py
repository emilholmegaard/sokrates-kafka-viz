"""Configuration management for Sokrates Kafka Viz."""
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any

@dataclass
class SchemaConfig:
    """Schema analysis configuration."""
    enabled: bool = True
    detectors: List[str] = None  # None means all available
    schema_registry_url: Optional[str] = None
    cache_schemas: bool = True
    timeout_seconds: int = 30
    custom_formats: List[Dict[str, str]] = None

    @classmethod
    def from_dict(cls, data: dict) -> 'SchemaConfig':
        return cls(
            enabled=data.get('enabled', True),
            detectors=data.get('detectors'),
            schema_registry_url=data.get('schema_registry', {}).get('url'),
            cache_schemas=data.get('schema_registry', {}).get('cache_schemas', True),
            timeout_seconds=data.get('schema_registry', {}).get('timeout_seconds', 30),
            custom_formats=data.get('custom_formats')
        )

@dataclass
class StateConfig:
    """State persistence configuration."""
    enabled: bool = True
    persistence_dir: Path = Path('.kafka_viz_state')
    checkpoint_interval: int = 300  # seconds
    save_on_error: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> 'StateConfig':
        if not data:
            return cls()
        return cls(
            enabled=data.get('enabled', True),
            persistence_dir=Path(data.get('persistence_dir', '.kafka_viz_state')),
            checkpoint_interval=data.get('checkpoint_interval', 300),
            save_on_error=data.get('save_on_error', True)
        )

@dataclass
class Config:
    """Main configuration."""
    schema_config: SchemaConfig
    state_config: StateConfig
    output_path: Path
    kafka_config: Dict[str, Any]
    service_paths: List[Path]
    exclude_patterns: List[str]
    logging_config: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict) -> 'Config':
        analyzers = data.get('analyzers', {})
        return cls(
            schema_config=SchemaConfig.from_dict(analyzers.get('schemas', {})),
            state_config=StateConfig.from_dict(data.get('state', {})),
            output_path=Path(data.get('output', {}).get('path', './analysis_output')),
            kafka_config=analyzers.get('kafka', {}),
            service_paths=[Path(p) for p in analyzers.get('service', {}).get('paths', [])],
            exclude_patterns=analyzers.get('service', {}).get('exclude_patterns', []),
            logging_config=data.get('logging', {})
        )

    def validate(self) -> List[str]:
        """Validate configuration and return list of errors if any."""
        errors = []
        
        # Check paths exist
        for path in self.service_paths:
            if not path.exists():
                errors.append(f"Service path does not exist: {path}")
                
        # Validate schema registry URL if provided
        if (self.schema_config.schema_registry_url and 
            not self.schema_config.schema_registry_url.startswith(('http://', 'https://'))):
            errors.append("Invalid schema registry URL format")
            
        # Check custom format configurations
        if self.schema_config.custom_formats:
            for fmt in self.schema_config.custom_formats:
                if 'module' not in fmt or 'class' not in fmt:
                    errors.append("Custom format missing required 'module' or 'class' field")
                    
        # Validate Kafka config
        if not self.kafka_config.get('bootstrap_servers'):
            errors.append("Kafka bootstrap servers not configured")
            
        return errors