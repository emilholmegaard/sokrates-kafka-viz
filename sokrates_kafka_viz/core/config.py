from pathlib import Path
from typing import Dict, Any, Optional
import yaml

class AnalyzerConfig:
    def __init__(self, enabled: bool = True, **kwargs):
        self.enabled = enabled
        self.__dict__.update(kwargs)

class Config:
    def __init__(self, config_dict: Dict[str, Any]):
        self.analyzers = {}
        self.output = config_dict.get('output', {})
        
        analyzer_configs = config_dict.get('analyzers', {})
        for name, config in analyzer_configs.items():
            self.analyzers[name] = AnalyzerConfig(**config)
    
    @classmethod
    def from_file(cls, path: Path) -> 'Config':
        with open(path) as f:
            config_dict = yaml.safe_load(f)
        return cls(config_dict)

    def get_analyzer_config(self, name: str) -> Optional[AnalyzerConfig]:
        return self.analyzers.get(name)