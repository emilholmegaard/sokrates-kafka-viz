from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import javalang
import pytest
import responses

from kafka_viz.analyzers.avro_analyzer import AvroAnalyzer
from kafka_viz.models.schema import AvroSchema


@pytest.fixture
def avro_analyzer():
    analyzer = AvroAnalyzer()
    # Update pattern to handle both full and short form
    analyzer.patterns["avro_annotation"] = (
        r"@(?:org\.apache\.avro\.specific\.)?AvroGenerated"
    )
    return analyzer


@pytest.fixture
def sample_avsc_content() -> dict[str, Any]:
    return {
        "type": "record",
        "name": "UserEvent",
        "namespace": "com.example.events",
        "fields": [
            {"name": "id", "type": "string"},
            {"name": "timestamp", "type": "long"},
            {"name": "data", "type": ["null", "string"]},
            {"name": "tags", "type": {"type": "array", "items": "string"}},
            {
                "name": "metadata",
                "type": {
                    "type": "record",
                    "name": "Metadata",
                    "fields": [
                        {"name": "source", "type": "string"},
                        {"name": "version", "type": "int"},
                    ],
                },
            },
        ],
    }


def test_parse_avsc_file(
    tmp_path: Path, avro_analyzer: AvroAnalyzer, sample_avsc_content
) -> None:
    """Test parsing of .avsc file with various field types"""
    # Create a temporary .avsc file
    avsc_file = tmp_path / "user_event.avsc"
    avsc_file.write_text(json.dumps(sample_avsc_content))

    # Parse the schema
    schema = avro_analyzer.parse_avsc_file(avsc_file)

    # Verify basic schema properties
    assert schema is not None
    assert schema.name == "UserEvent"
    assert schema.namespace == "com.example.events"
    assert schema.file_path == avsc_file

    # Verify field types are normalized correctly
    assert schema.fields["id"] == "string"
    assert schema.fields["timestamp"] == "long"
    assert schema.fields["data"] == "string"  # Union type normalized to non-null type
    assert schema.fields["tags"] == "array(string)"
    assert schema.fields["metadata"] == "Metadata"


def test_analyze_jvm_source(tmp_path: Path, avro_analyzer: AvroAnalyzer) -> None:
    """Test analyzing Java source with @AvroGenerated annotation"""
    java_content = """
package com.example.events;

import org.apache.avro.specific.AvroGenerated;

@org.apache.avro.specific.AvroGenerated
public class UserEvent {
    private String id;
    private long timestamp;
    private String data;

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public long getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(long timestamp) {
        this.timestamp = timestamp;
    }

    public String getData() {
        return data;
    }

    public void setData(String data) {
        this.data = data;
    }
}
"""

    java_file = tmp_path / "UserEvent.java"
    java_file.write_text(java_content)

    # Debug the content of the patterns
    print("\nPatterns:", avro_analyzer.patterns)

    # Debug the file content
    print("\nFile content:", java_file.read_text())

    # Initialize schema
    schema = None

    # Add debugging to track each step
    try:
        tree = javalang.parse.parse(java_file.read_text())
        print("\nTree parsed successfully")
        print("Package:", tree.package.name if tree.package else None)
        print("Imports:", [imp.path for imp in tree.imports])
        print("Types:", [t.name for t in tree.types])
        for type_decl in tree.types:
            print(f"\nClass: {type_decl.name}")
            print("Annotations:", [anno.name for anno in type_decl.annotations])
            # Fix field printing - access declarators
            fields = []
            for field in type_decl.fields:
                for declarator in field.declarators:
                    fields.append((field.type.name, declarator.name))
            print("Fields:", fields)

        # Let's check the analyze_jvm_source method step by step
        schema = avro_analyzer.analyze_jvm_source(java_file)

    except Exception as e:
        print(f"\nError during parsing: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback

        print(traceback.format_exc())

    assert schema is not None
    assert schema.name == "UserEvent"
    assert schema.namespace == "com.example.events"
    assert schema.fields["id"] == "string"
    assert schema.fields["timestamp"] == "long"
    assert schema.fields["data"] == "string"


def test_normalize_field_types(avro_analyzer: AvroAnalyzer) -> None:
    """Test normalization of various Avro field types"""
    # Test primitive type
    assert avro_analyzer._normalize_field_type("string") == "string"

    # Test union type
    union_type = ["null", "string", "int"]
    assert avro_analyzer._normalize_field_type(union_type) == "union(string,int)"

    # Test array type
    array_type = {"type": "array", "items": "string"}
    assert avro_analyzer._normalize_field_type(array_type) == "array(string)"

    # Test record type
    record_type = {
        "type": "record",
        "name": "Metadata",
        "fields": [{"name": "version", "type": "int"}],
    }
    assert avro_analyzer._normalize_field_type(record_type) == "Metadata"


@responses.activate
def test_find_schema_registry_refs(tmp_path: Path, avro_analyzer: AvroAnalyzer) -> None:
    """Test finding Schema Registry references in code"""
    # Mock the schema registry responses
    sample_schema = {
        "schema": json.dumps(
            {
                "type": "record",
                "name": "UserEvent",
                "namespace": "com.example.events",
                "fields": [
                    {"name": "id", "type": "string"},
                    {"name": "timestamp", "type": "long"},
                ],
            }
        )
    }

    responses.add(
        responses.GET,
        "http://localhost:8081/subjects/user-event-value/versions/latest",
        json=sample_schema,
        status=200,
    )
    responses.add(
        responses.GET,
        "http://localhost:8081/subjects/order-event-value/versions/latest",
        json=sample_schema,
        status=200,
    )
    responses.add(
        responses.GET,
        "http://schema-registry:8081/subjects/payment-event/versions/1",
        json=sample_schema,
        status=200,
    )

    java_content = """
    public class SchemaRegistryTest {
        void test() {
            schemaRegistry.getSchema("user-event-value");
            schemaRegistry.registerSchema("order-event-value");
            String schemaUrl = "http://schema-registry:8081/subjects/payment-event/versions/1";
        }
    }
    """

    java_file = tmp_path / "SchemaRegistryTest.java"
    java_file.write_text(java_content)

    registry_refs = avro_analyzer.find_schema_registry_refs(tmp_path)

    # Verify that schemas were found and processed
    assert len(registry_refs) > 0

    # Check that at least one schema was properly parsed
    schema = next(iter(registry_refs.values()))
    assert isinstance(schema, AvroSchema)
    assert schema.name == "UserEvent"
    assert "id" in schema.fields
    assert "timestamp" in schema.fields


def test_error_handling(tmp_path: Path, avro_analyzer: AvroAnalyzer) -> None:
    """Test error handling for invalid schemas and files"""
    # Test invalid AVSC file
    invalid_avsc = tmp_path / "invalid.avsc"
    invalid_avsc.write_text("invalid json")

    schema = avro_analyzer.parse_avsc_file(invalid_avsc)
    assert schema is None

    # Test invalid Java file
    invalid_java = tmp_path / "Invalid.java"
    invalid_java.write_text("invalid java code")

    schema = avro_analyzer.analyze_jvm_source(invalid_java)
    assert schema is None

    # Test non-record AVSC file
    non_record_avsc = tmp_path / "enum.avsc"
    enum_schema = {"type": "enum", "name": "Status", "symbols": ["ACTIVE", "INACTIVE"]}
    non_record_avsc.write_text(json.dumps(enum_schema))

    schema = avro_analyzer.parse_avsc_file(non_record_avsc)
    assert schema is None
