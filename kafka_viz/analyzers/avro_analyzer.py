"""Analyzer for detecting and parsing Avro schemas."""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional, Set
from urllib.parse import urlparse

import javalang
import requests

from ..models.schema import AvroSchema

logger = logging.getLogger(__name__)


class AvroAnalyzer:
    """Analyzer for Avro schemas and related code."""

    def __init__(self) -> None:
        """Initialize Avro analyzer with detection patterns."""
        self.patterns = {
            "avro_annotation": r"@org\.apache\.avro\.specific\.AvroGenerated",
            "schema_registry": r'schemaRegistry\.(?:get|register)Schema\(["\']([^"\']+)["\']\)',
            "schema_reference": r'Schema\.Parser\(\)\.parse\(["\']([^"\']+)["\']\)',
            "confluent_registry": r"http[s]?://[^/]+/subjects/[^/]+/versions/\d+",
        }

    def analyze_directory(self, directory: Path) -> Dict[str, AvroSchema]:
        """Analyze directory for Avro schemas.

        Args:
            directory: Directory to analyze

        Returns:
            Dictionary mapping schema names to AvroSchema objects
        """
        schemas: Dict[str, AvroSchema] = {}

        # Find .avsc files
        for avsc_file in directory.rglob("*.avsc"):
            schema = self.parse_avsc_file(avsc_file)
            if schema is not None:
                logger.debug(
                    f"Found avro schema name: {schema.name} in file: {avsc_file}"
                )

            if schema is not None:
                schemas[schema.name] = schema

        # Find Java/Kotlin/Scala files with @AvroGenerated
        for ext in [".java", ".kt", ".scala"]:
            for source_file in directory.rglob(f"*{ext}"):
                schema = self.analyze_jvm_source(source_file)
                if schema is not None:
                    schemas[schema.name] = schema

        # Find schema registry references
        registry_schemas = self.find_schema_registry_refs(directory)
        schemas.update(registry_schemas)

        return schemas

    def parse_avsc_file(self, file_path: Path) -> Optional[AvroSchema]:
        """Parse an Avro schema file (.avsc).

        Args:
            file_path: Path to .avsc file

        Returns:
            AvroSchema object or None if parsing fails
        """
        try:
            with open(file_path) as f:
                schema_json = json.load(f)

            if schema_json.get("type") != "record":
                return None

            fields = {}
            for field in schema_json.get("fields", []):
                field_name = field.get("name")
                field_type = self._normalize_field_type(field.get("type"))
                if field_name and field_type:
                    fields[field_name] = field_type

            return AvroSchema(
                name=schema_json.get("name"),
                namespace=schema_json.get("namespace", ""),
                file_path=file_path,
                fields=fields,
            )

        except Exception as e:
            logger.error(f"Error parsing Avro schema {file_path}: {e}")
            print(f"Error parsing Avro schema {file_path}: {e}")
            return None

    def analyze_jvm_source(self, file_path: Path) -> Optional[AvroSchema]:
        """Analyze Java/Kotlin/Scala source file for Avro classes.

        Args:
            file_path: Path to source file

        Returns:
            AvroSchema object or None if no Avro class found
        """
        try:
            with open(file_path) as f:
                content = f.read()

            # Check for @AvroGenerated annotation
            if not re.search(self.patterns["avro_annotation"], content):
                return None

            # Parse Java source
            tree = javalang.parse.parse(content)

            # Find class with @AvroGenerated
            for class_decl in tree.types:
                if any(anno.name == "AvroGenerated" for anno in class_decl.annotations):
                    fields = {}
                    for field in class_decl.fields:
                        field_type = self._get_java_field_type(field)
                        fields[field.name] = field_type

                    return AvroSchema(
                        name=class_decl.name,
                        namespace=tree.package.name if tree.package else "",
                        file_path=file_path,
                        fields=fields,
                    )

        except Exception as e:
            logger.error(f"Error analyzing source file {file_path}: {e}")
            print(f"Error analyzing source file {file_path}: {e}")
            return None

        return None

    def find_schema_registry_refs(self, directory: Path) -> Dict[str, AvroSchema]:
        """Find references to Schema Registry and fetch schemas.

        Args:
            directory: Directory to search for references

        Returns:
            Dictionary mapping schema names to AvroSchema objects
        """
        schemas = {}
        registry_urls: Set[str] = set()

        # Find Schema Registry URLs in code
        for ext in [".java", ".kt", ".scala", ".py", ".js", ".ts"]:
            for source_file in directory.rglob(f"*{ext}"):
                with open(source_file) as f:
                    content = f.read()

                # Find registry URLs
                for match in re.finditer(self.patterns["confluent_registry"], content):
                    registry_urls.add(match.group(0))

                # Find schema references
                for match in re.finditer(self.patterns["schema_registry"], content):
                    subject = match.group(1)
                    if "/" not in subject:  # Skip full URLs
                        # Construct registry URL (this would come from config in practice)
                        registry_url = (
                            f"http://localhost:8081/subjects/{subject}/versions/latest"
                        )
                        registry_urls.add(registry_url)

        # Fetch schemas from registry
        for url in registry_urls:
            try:
                schema = self._fetch_schema_from_registry(url)
                if schema:
                    schemas[schema.name] = schema
            except Exception as e:
                logger.error(f"Error fetching schema from {url}: {e}")
                print(f"Error fetching schema from {url}: {e}")

        return schemas

    def _fetch_schema_from_registry(self, url: str) -> Optional[AvroSchema]:
        """Fetch schema from Schema Registry.

        Args:
            url: Schema Registry URL

        Returns:
            AvroSchema object or None if fetch fails
        """
        try:
            response = requests.get(
                url, headers={"Accept": "application/vnd.schemaregistry.v1+json"}
            )
            response.raise_for_status()

            data = response.json()
            schema_json = json.loads(data["schema"])

            if schema_json.get("type") != "record":
                return None

            fields = {}
            for field in schema_json.get("fields", []):
                field_name = field.get("name")
                field_type = self._normalize_field_type(field.get("type"))
                if field_name and field_type:
                    fields[field_name] = field_type

            return AvroSchema(
                name=schema_json.get("name"),
                namespace=schema_json.get("namespace", ""),
                file_path=Path(urlparse(url).path),
                fields=fields,
            )

        except Exception as e:
            print(f"Error fetching schema from registry {url}: {e}")
            return None

    def _normalize_field_type(self, field_type) -> str:
        """Normalize Avro field type to consistent string representation.

        Args:
            field_type: Raw field type from schema

        Returns:
            Normalized type string
        """
        if isinstance(field_type, str):
            return field_type

        if isinstance(field_type, list):
            # Handle union types
            non_null_types = [t for t in field_type if t != "null"]
            if len(non_null_types) == 1:
                return non_null_types[0]
            return f"union({','.join(non_null_types)})"

        if isinstance(field_type, dict):
            if field_type.get("type") == "array":
                item_type = self._normalize_field_type(field_type.get("items"))
                return f"array({item_type})"
            if field_type.get("type") == "record":
                return field_type.get("name", "record")

        return str(field_type)

    def _get_java_field_type(self, field) -> str:
        """Get field type from Java AST field node.

        Args:
            field: javalang Field node

        Returns:
            Field type string
        """
        # Handle primitive types
        if hasattr(field.type, "name"):
            type_name = field.type.name
            if type_name in ["int", "long", "float", "double", "boolean", "String"]:
                return type_name.lower()

        # Handle arrays
        if hasattr(field.type, "dimensions") and field.type.dimensions:
            base_type = self._get_java_field_type(field.type)
            return f"array({base_type})"

        # Handle generic types
        if hasattr(field.type, "arguments"):
            base_type = field.type.name
            if field.type.arguments:
                arg_types = [
                    self._get_java_field_type(arg) for arg in field.type.arguments
                ]
                return f"{base_type}<{','.join(arg_types)}>"

        return "object"

    def get_debug_info(self) -> Dict[str, Any]:
        """Get debug information about the Avro analysis."""
        return {
            "patterns": self.patterns,
            "schemas": list(self.analyze_directory(Path(".")).keys()),
        }
