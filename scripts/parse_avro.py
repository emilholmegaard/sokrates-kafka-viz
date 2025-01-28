import json
from typing import Dict, Any

class AvroSchemaParser:
    def __init__(self):
        self.parsed_schemas = {}

    def parse_schema(self, content: str) -> Dict[str, Any]:
        """Parse an Avro schema file and return its structure."""
        try:
            schema = json.loads(content)
            if isinstance(schema, dict):
                self.parsed_schemas[schema.get('name')] = schema
                return schema
            return {}
        except json.JSONDecodeError:
            print(f"Error parsing Avro schema: Invalid JSON")
            return {}

    def get_schema_references(self, schema: Dict[str, Any]) -> set:
        """Extract references to other schemas from a given schema."""
        references = set()
        
        def extract_refs(obj):
            if isinstance(obj, dict):
                if 'type' in obj and isinstance(obj['type'], str):
                    if obj['type'] not in ['record', 'enum', 'fixed', 'string', 
                                         'int', 'long', 'float', 'double', 
                                         'boolean', 'null', 'bytes']:
                        references.add(obj['type'])
                for value in obj.values():
                    extract_refs(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_refs(item)

        extract_refs(schema)
        return references