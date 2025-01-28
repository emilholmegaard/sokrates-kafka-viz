"""Dependency injection container for Sokrates."""

from typing import Dict, Type, Any
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class Container:
    """A simple dependency injection container."""
    
    _instances: Dict[Type, Any] = field(default_factory=dict)
    _factories: Dict[Type, Any] = field(default_factory=dict)
    
    def register(self, interface: Type, implementation: Type) -> None:
        """Register an implementation for an interface."""
        self._factories[interface] = implementation
    
    def register_instance(self, interface: Type, instance: Any) -> None:
        """Register a pre-created instance."""
        self._instances[interface] = instance
    
    def resolve(self, interface: Type) -> Any:
        """Resolve an implementation for an interface."""
        # Return existing instance if available
        if interface in self._instances:
            return self._instances[interface]
        
        # Create new instance if factory exists
        if interface in self._factories:
            instance = self._create_instance(self._factories[interface])
            self._instances[interface] = instance
            return instance
        
        raise ValueError(f"No implementation registered for {interface}")
    
    def _create_instance(self, cls: Type) -> Any:
        """Create a new instance with dependencies injected."""
        import inspect
        
        # Get constructor parameters
        sig = inspect.signature(cls.__init__)
        params = {}
        
        # Resolve dependencies for each parameter
        for name, param in sig.parameters.items():
            if name == 'self':
                continue
            
            # Get the parameter type
            param_type = param.annotation
            if param_type == inspect.Parameter.empty:
                raise ValueError(f"Missing type annotation for parameter {name} in {cls}")
            
            # Resolve the dependency
            params[name] = self.resolve(param_type)
        
        return cls(**params)

# Create global container instance
container = Container()

# Interface definitions
class ILanguageDetector:
    """Interface for language detection."""
    def detect_language(self, file_path: Path) -> str:
        """Detect the programming language of a file."""
        raise NotImplementedError

class IFileAnalyzer:
    """Interface for analyzing source code files."""
    def can_handle(self, file_path: Path) -> bool:
        """Check if this analyzer can handle the given file."""
        raise NotImplementedError
    
    def analyze(self, file_path: Path, **kwargs) -> Any:
        """Analyze the file and return results."""
        raise NotImplementedError

class ISchemaAnalyzer:
    """Interface for analyzing message schemas."""
    def analyze_schema(self, content: str, schema_type: str) -> Dict:
        """Analyze a message schema and return its structure."""
        raise NotImplementedError

class IVisualizationGenerator:
    """Interface for generating visualizations."""
    def generate(self, analysis_result: Any, **kwargs) -> str:
        """Generate a visualization from analysis results."""
        raise NotImplementedError