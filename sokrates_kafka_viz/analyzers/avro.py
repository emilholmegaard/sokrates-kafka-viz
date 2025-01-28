"""Analyzer for detecting and parsing Avro schemas."""
from typing import Dict, List, Optional, Set, Any
from pathlib import Path
import json
import re
import ast
import javalang
from urllib.parse import urlparse
import aiohttp
import logging

from ..core.analyzer import BaseAnalyzer
from ..core.config import Config
from ..core.errors import AnalyzerError
from ..models.schema import AvroSchema

logger = logging.getLogger(__name__)

class AvroAnalyzer(BaseAnalyzer):
    """Analyzer for Avro schemas and related code."""
    
    def __init__(self):
        """Initialize Avro analyzer with detection patterns."""
        self.patterns = {
            'avro_annotation': r'@org\.apache\.avro\.specific\.AvroGenerated',
            'schema_registry': r'schemaRegistry\.(?:get|register)Schema\(["\']([^"\']+)["\']\)',
            'schema_reference': r'Schema\.Parser\(\)\.parse\(["\']([^"\']+)["\']\)',
            'confluent_registry': r'http[s]?://[^/]+/subjects/[^/]+/versions/\d+'
        }
        
    async def analyze(self, config: Config) -> Dict[str, Any]:
        """Analyze configured directories for Avro schemas.
        
        Args:
            config: Analysis configuration
            
        Returns:
            Dictionary containing discovered schemas and analysis results
        """
        try:
            analyzer_config = config.get_analyzer_config('avro')
            if not analyzer_config:
                raise AnalyzerError('Avro analyzer configuration not found')
                
            # Get services from configuration
            services = self._get_services_from_config(config)
            schemas: Dict[str, AvroSchema] = {}
            
            # Process each service
            for service in services.values():
                service_schemas = await self._analyze_service(service, analyzer_config)
                schemas.update(service_schemas)
                
            # Fetch schemas from registry if configured
            if hasattr(analyzer_config, 'schema_registry'):
                registry_schemas = await self._fetch_registry_schemas(
                    analyzer_config.schema_registry,
                    analyzer_config.timeout_seconds
                )
                schemas.update(registry_schemas)
                
            return {
                'schemas': schemas,
                'total_count': len(schemas),
                'by_namespace': self._group_by_namespace(schemas)
            }
            
        except Exception as e:
            raise AnalyzerError(f'Avro analysis failed: {str(e)}') from e
    
    async def _analyze_service(self, service: Path, config: Any) -> Dict[str, AvroSchema]:
        """Analyze a service directory for Avro schemas."""
        schemas: Dict[str, AvroSchema] = {}
        
        try:
            # Find .avsc files
            for avsc_file in service.root_path.rglob('*.avsc'):
                schema = self._parse_avsc_file(avsc_file)
                if schema:
                    schemas[schema.name] = schema
            
            # Find Java/Kotlin/Scala files with @AvroGenerated
            for ext in ['.java', '.kt', '.scala']:
                for source_file in service.root_path.rglob(f'*{ext}'):
                    schema = self._analyze_jvm_source(source_file)
                    if schema:
                        schemas[schema.name] = schema
                        
            # Find schema registry references
            registry_refs = self._find_schema_registry_refs(service.root_path)
            if registry_refs and hasattr(config, 'schema_registry'):
                registry_schemas = await self._fetch_registry_schemas(
                    config.schema_registry,
                    getattr(config, 'timeout_seconds', 30),
                    registry_refs
                )
                schemas.update(registry_schemas)
                
        except Exception as e:
            logger.warning(f'Error analyzing service {service.name}: {e}')
            
        return schemas
        
    def _parse_avsc_file(self, file_path: Path) -> Optional[AvroSchema]:
        """Parse an Avro schema file (.avsc)."""
        try:
            with open(file_path) as f:
                schema_json = json.load(f)
                
            if schema_json.get('type') != 'record':
                return None
                
            fields = {}
            for field in schema_json.get('fields', []):
                field_name = field.get('name')
                field_type = self._normalize_field_type(field.get('type'))
                if field_name and field_type:
                    fields[field_name] = field_type
                    
            return AvroSchema(
                name=schema_json.get('name'),
                namespace=schema_json.get('namespace', ''),
                file_path=file_path,
                fields=fields
            )
            
        except Exception as e:
            logger.error(f"Error parsing Avro schema {file_path}: {e}")
            return None
            
    def _analyze_jvm_source(self, file_path: Path) -> Optional[AvroSchema]:
        """Analyze Java/Kotlin/Scala source file for Avro classes."""
        try:
            with open(file_path) as f:
                content = f.read()
                
            # Check for @AvroGenerated annotation
            if not re.search(self.patterns['avro_annotation'], content):
                return None
                
            # Parse Java source
            tree = javalang.parse.parse(content)
            
            # Find class with @AvroGenerated
            for class_decl in tree.types:
                if any(anno.name == 'AvroGenerated' for anno in class_decl.annotations):
                    fields = {}
                    for field in class_decl.fields:
                        field_type = self._get_java_field_type(field)
                        fields[field.name] = field_type
                        
                    return AvroSchema(
                        name=class_decl.name,
                        namespace=tree.package.name if tree.package else '',
                        file_path=file_path,
                        fields=fields
                    )
                    
        except Exception as e:
            logger.error(f"Error analyzing source file {file_path}: {e}")
            return None
            
        return None
        
    def _find_schema_registry_refs(self, directory: Path) -> Set[str]:
        """Find references to Schema Registry."""
        registry_refs: Set[str] = set()
        
        try:
            # Find Schema Registry URLs in code
            for ext in ['.java', '.kt', '.scala', '.py', '.js', '.ts']:
                for source_file in directory.rglob(f'*{ext}'):
                    with open(source_file) as f:
                        content = f.read()
                        
                    # Find registry URLs
                    for match in re.finditer(self.patterns['confluent_registry'], content):
                        registry_refs.add(match.group(0))
                        
                    # Find schema references
                    for match in re.finditer(self.patterns['schema_registry'], content):
                        subject = match.group(1)
                        if '/' not in subject:  # Skip full URLs
                            registry_refs.add(subject)
                            
        except Exception as e:
            logger.warning(f'Error searching for registry references: {e}')
            
        return registry_refs
        
    async def _fetch_registry_schemas(
        self,
        registry_url: str,
        timeout: int,
        subjects: Optional[Set[str]] = None
    ) -> Dict[str, AvroSchema]:
        """Fetch schemas from Schema Registry."""
        schemas = {}
        
        try:
            async with aiohttp.ClientSession() as session:
                if not subjects:
                    # Fetch all subjects
                    async with session.get(
                        f'{registry_url}/subjects',
                        timeout=timeout
                    ) as response:
                        if response.status == 200:
                            subjects = set(await response.json())
                        else:
                            logger.error(
                                f'Failed to fetch subjects: {response.status}'
                            )
                            return {}
                
                # Fetch each schema
                for subject in subjects:
                    try:
                        schema = await self._fetch_schema(
                            session, registry_url, subject, timeout
                        )
                        if schema:
                            schemas[schema.name] = schema
                    except Exception as e:
                        logger.warning(f'Error fetching schema for {subject}: {e}')
                        
        except Exception as e:
            logger.error(f'Error connecting to schema registry: {e}')
            
        return schemas
        
    async def _fetch_schema(
        self,
        session: aiohttp.ClientSession,
        registry_url: str,
        subject: str,
        timeout: int
    ) -> Optional[AvroSchema]:
        """Fetch and parse a single schema from the registry."""
        try:
            url = f'{registry_url}/subjects/{subject}/versions/latest'
            async with session.get(url, timeout=timeout) as response:
                if response.status != 200:
                    logger.warning(f'Failed to fetch schema for {subject}')
                    return None
                    
                data = await response.json()
                schema_json = json.loads(data['schema'])
                
                if schema_json.get('type') != 'record':
                    return None
                    
                fields = {}
                for field in schema_json.get('fields', []):
                    field_name = field.get('name')
                    field_type = self._normalize_field_type(field.get('type'))
                    if field_name and field_type:
                        fields[field_name] = field_type
                        
                return AvroSchema(
                    name=schema_json.get('name'),
                    namespace=schema_json.get('namespace', ''),
                    file_path=Path(urlparse(url).path),
                    fields=fields
                )
                
        except Exception as e:
            logger.error(f'Error fetching schema from registry {subject}: {e}')
            return None
            
    def _normalize_field_type(self, field_type) -> str:
        """Normalize Avro field type to consistent string representation."""
        if isinstance(field_type, str):
            return field_type
            
        if isinstance(field_type, list):
            # Handle union types
            non_null_types = [t for t in field_type if t != 'null']
            if len(non_null_types) == 1:
                return non_null_types[0]
            return f"union({','.join(non_null_types)})"
            
        if isinstance(field_type, dict):
            if field_type.get('type') == 'array':
                item_type = self._normalize_field_type(field_type.get('items'))
                return f"array({item_type})"
            if field_type.get('type') == 'record':
                return field_type.get('name', 'record')
                
        return str(field_type)
        
    def _get_java_field_type(self, field) -> str:
        """Get field type from Java AST field node."""
        # Handle primitive types
        if hasattr(field.type, 'name'):
            type_name = field.type.name
            if type_name in ['int', 'long', 'float', 'double', 'boolean', 'String']:
                return type_name.lower()
                
        # Handle arrays
        if hasattr(field.type, 'dimensions') and field.type.dimensions:
            base_type = self._get_java_field_type(field.type)
            return f"array({base_type})"
            
        # Handle generic types
        if hasattr(field.type, 'arguments'):
            base_type = field.type.name
            if field.type.arguments:
                arg_types = [self._get_java_field_type(arg) for arg in field.type.arguments]
                return f"{base_type}<{','.join(arg_types)}>"
                
        return 'object'
        
    def _group_by_namespace(self, schemas: Dict[str, AvroSchema]) -> Dict[str, List[str]]:
        """Group schemas by namespace."""
        by_namespace = {}
        for schema in schemas.values():
            namespace = schema.namespace or 'default'
            if namespace not in by_namespace:
                by_namespace[namespace] = []
            by_namespace[namespace].append(schema.name)
        return by_namespace