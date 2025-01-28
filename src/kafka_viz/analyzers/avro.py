from typing import Dict, Any
import json
import avro.schema
from avro.datafile import DataFileReader
from avro.io import DatumReader

def parse_avro_schema(schema_path: str) -> Dict[str, Any]:
    """Parse an Avro schema file and return its structure."""
    with open(schema_path, 'r') as f:
        schema_json = json.load(f)
    return avro.schema.parse(json.dumps(schema_json))

def read_avro_data(data_path: str) -> list:
    """Read data from an Avro file."""
    reader = DataFileReader(open(data_path, 'rb'), DatumReader())
    return [record for record in reader]