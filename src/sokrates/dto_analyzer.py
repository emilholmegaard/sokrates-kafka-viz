"""DTO (Data Transfer Object) analyzer for different programming languages."""

import re
from dataclasses import dataclass
from typing import Dict, List, Set, Optional
from pathlib import Path

@dataclass
class DTOClass:
    """Represents a DTO class with its properties and relationships."""
    name: str
    properties: Dict[str, str]  # property_name -> type
    serialization_format: Optional[str] = None  # e.g., 'JSON', 'XML', etc.
    source_file: Optional[Path] = None
    service_name: Optional[str] = None

class DTOAnalyzer:
    """Analyzes source code to detect DTOs and their relationships."""

    # Language-specific DTO patterns
    DTO_PATTERNS = {
        'Java': [
            # Record pattern (Java 14+)
            r'record\s+(\w+)\s*\(([\s\S]*?)\)',
            # Class with @Data/@Value (Lombok)
            r'@(?:Data|Value)\s+class\s+(\w+)',
            # Traditional POJO
            r'class\s+(\w+)(?:\s+implements\s+Serializable)?'
        ],
        'C#': [
            # Record
            r'record\s+(\w+)\s*\(([\s\S]*?)\)',
            # Class with auto-properties
            r'class\s+(\w+)(?:\s*:\s*IDto)?'
        ],
        'Kotlin': [
            # Data class
            r'data\s+class\s+(\w+)\s*\(([\s\S]*?)\)'
        ],
        'TypeScript': [
            # Interface
            r'interface\s+(\w+)',
            # Type
            r'type\s+(\w+)\s*=\s*{[\s\S]*?}'
        ]
    }

    # Serialization annotations/decorators
    SERIALIZATION_MARKERS = {
        'Java': {
            'JSON': [r'@JsonSerialize', r'@JsonProperty', r'@JsonFormat'],
            'XML': [r'@XmlRootElement', r'@XmlElement', r'@XmlAttribute'],
            'AVRO': [r'@AvroSchema', r'@AvroRecord']
        },
        'C#': {
            'JSON': [r'\[JsonProperty', r'\[JsonSerializer'],
            'XML': [r'\[XmlRoot', r'\[XmlElement']
        }
    }

    def __init__(self):
        self.dtos: Dict[str, DTOClass] = {}
        self.service_relationships: Dict[str, Set[str]] = {}  # service -> set of DTOs used

    def analyze_file(self, file_path: Path, language: str, service_name: str) -> List[DTOClass]:
        """Analyze a single file for DTOs."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            return []

        dtos = []
        patterns = self.DTO_PATTERNS.get(language, [])
        
        for pattern in patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                dto_name = match.group(1)
                
                # Skip if it's clearly not a DTO
                if self._should_skip_class(dto_name, content):
                    continue

                properties = self._extract_properties(content, dto_name, language)
                serialization = self._detect_serialization(content, language)
                
                dto = DTOClass(
                    name=dto_name,
                    properties=properties,
                    serialization_format=serialization,
                    source_file=file_path,
                    service_name=service_name
                )
                
                dtos.append(dto)
                self.dtos[dto_name] = dto
                
                # Update service relationships
                if service_name not in self.service_relationships:
                    self.service_relationships[service_name] = set()
                self.service_relationships[service_name].add(dto_name)

        return dtos

    def _should_skip_class(self, class_name: str, content: str) -> bool:
        """Determine if a class should be skipped (not a DTO)."""
        # Skip if it contains business logic methods
        if re.search(rf'class\s+{class_name}[\s\S]*?{{\s*.*?(?:private|protected)\s+\w+\s+\w+\s*\(', content):
            return True
        
        # Skip if it's clearly a service/repository/controller
        skip_suffixes = ['Service', 'Repository', 'Controller', 'Manager', 'Handler']
        if any(class_name.endswith(suffix) for suffix in skip_suffixes):
            return True

        return False

    def _extract_properties(self, content: str, class_name: str, language: str) -> Dict[str, str]:
        """Extract properties and their types from a DTO class."""
        properties = {}
        
        if language == 'Java':
            # Handle Java record properties
            record_match = re.search(rf'record\s+{class_name}\s*\(([\s\S]*?)\)', content)
            if record_match:
                params = record_match.group(1).split(',')
                for param in params:
                    param = param.strip()
                    if param:
                        type_name = param.split()[0]
                        prop_name = param.split()[1]
                        properties[prop_name] = type_name
            else:
                # Handle regular class properties
                prop_pattern = r'(?:private|public)\s+(\w+(?:<[^>]+>)?)\s+(\w+)\s*;'
                for match in re.finditer(prop_pattern, content):
                    properties[match.group(2)] = match.group(1)

        elif language == 'C#':
            # Handle C# properties
            prop_pattern = r'public\s+(\w+(?:<[^>]+>)?)\s+(\w+)\s*{\s*get;\s*(?:set;)?\s*}'
            for match in re.finditer(prop_pattern, content):
                properties[match.group(2)] = match.group(1)

        elif language == 'Kotlin':
            # Handle Kotlin data class properties
            data_class_match = re.search(rf'data\s+class\s+{class_name}\s*\(([\s\S]*?)\)', content)
            if data_class_match:
                params = data_class_match.group(1).split(',')
                for param in params:
                    param = param.strip()
                    if param:
                        parts = param.split(':')
                        if len(parts) == 2:
                            prop_name = parts[0].strip()
                            type_name = parts[1].strip()
                            properties[prop_name] = type_name

        return properties

    def _detect_serialization(self, content: str, language: str) -> Optional[str]:
        """Detect the serialization format used by the DTO."""
        markers = self.SERIALIZATION_MARKERS.get(language, {})
        
        for format_name, patterns in markers.items():
            if any(re.search(pattern, content) for pattern in patterns):
                return format_name
                
        # Fallback: Check for common serialization libraries
        if language == 'Java':
            if 'com.fasterxml.jackson' in content:
                return 'JSON'
            elif 'javax.xml.bind' in content:
                return 'XML'
        elif language == 'C#':
            if 'System.Text.Json' in content:
                return 'JSON'
            elif 'System.Xml.Serialization' in content:
                return 'XML'

        return None

    def get_dto_relationships(self) -> Dict[str, Set[str]]:
        """Get relationships between services and DTOs."""
        return self.service_relationships

    def get_shared_dtos(self) -> Set[str]:
        """Get DTOs that are used by multiple services."""
        shared = set()
        dto_usage = {}
        
        for service, dtos in self.service_relationships.items():
            for dto in dtos:
                if dto not in dto_usage:
                    dto_usage[dto] = set()
                dto_usage[dto].add(service)
        
        return {dto for dto, services in dto_usage.items() if len(services) > 1}