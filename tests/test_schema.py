"""Tests for schema models."""
import pytest
from pathlib import Path
from kafka_viz.models.schema import Schema, AvroSchema, DTOSchema, KafkaTopic

def test_kafka_topic():
    """Test KafkaTopic creation and modification."""
    topic = KafkaTopic(name="test-topic")
    assert topic.name == "test-topic"
    assert topic.producers == set()
    assert topic.consumers == set()

    topic.producers.add("producer1")
    topic.consumers.add("consumer1")
    assert "producer1" in topic.producers
    assert "consumer1" in topic.consumers

def test_schema():
    """Test Schema creation."""
    schema = Schema(
        name="TestSchema",
        file_path=Path("/test/path"),
        fields={"field1": "string"}
    )
    assert schema.name == "TestSchema"
    assert schema.file_path == Path("/test/path")
    assert schema.fields == {"field1": "string"}

def test_avro_schema():
    """Test AvroSchema creation."""
    schema = AvroSchema(
        name="TestAvroSchema",
        file_path=Path("/test/path"),
        namespace="com.test"
    )
    assert schema.name == "TestAvroSchema"
    assert schema.file_path == Path("/test/path")
    assert schema.namespace == "com.test"
    assert schema.type_name == "record"
    assert schema.fields == {}

def test_dto_schema():
    """Test DTOSchema creation."""
    schema = DTOSchema(
        name="TestDTOSchema",
        file_path=Path("/test/path"),
        language="java",
        serialization_format="JSON",
        service_name="TestService"
    )
    assert schema.name == "TestDTOSchema"
    assert schema.file_path == Path("/test/path")
    assert schema.language == "java"
    assert schema.serialization_format == "JSON"
    assert schema.service_name == "TestService"
    assert schema.fields == {}