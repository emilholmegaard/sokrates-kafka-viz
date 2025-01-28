from dataclasses import dataclass
from typing import List, Optional
import yaml

@dataclass
class AnalyzerConfig:
    languages: List[str]
    exclude_patterns: List[str]
    max_depth: int
    
@dataclass
class Config:
    analyzer: AnalyzerConfig
    output_format: str
    log_level: str

def load_config(config_path: Optional[str] = None) -> Config:
    if not config_path:
        return Config(
            analyzer=AnalyzerConfig(
                languages=['java', 'python', 'csharp', 'javascript'],
                exclude_patterns=['**/node_modules/**', '**/.git/**'],
                max_depth=5
            ),
            output_format='html',
            log_level='INFO'
        )
    
    with open(config_path) as f:
        config_dict = yaml.safe_load(f)
        return Config(**config_dict)