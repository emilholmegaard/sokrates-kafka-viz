from pathlib import Path

import pytest

from kafka_viz.analyzers.analyzer_manager import AnalyzerManager
from kafka_viz.models.service import Service
from kafka_viz.models.service_collection import ServiceCollection


class TestAnalyzerManager:
    @pytest.fixture
    def analyzer_manager(self) -> AnalyzerManager:
        return AnalyzerManager()

    @pytest.fixture
    def mock_service(self):
        return Service(name="mock", root_path=Path("/mock/path"), language="java")

    def test_discover_services_java(self, analyzer_manager, tmp_path) -> None:
        # Create mock Java service structure
        services = ServiceCollection()
        service_dir = tmp_path / "services" / "java-service"
        service_dir.mkdir(parents=True)

        # Create pom.xml
        pom_content = """<?xml version="1.0" encoding="UTF-8"?>
        <project xmlns="http://maven.apache.org/POM/4.0.0">
            <artifactId>foo service</artifactId>
        </project>
        """
        (service_dir / "pom.xml").write_text(pom_content)

        # Create Java source file
        src_dir = service_dir / "src" / "main" / "java"
        src_dir.mkdir(parents=True)
        java_file = src_dir / "Service.java"
        java_file.write_text(
            """
        package com.example;
        @EnableBinding
        public class Service {
        }
        """
        )

        # Find services
        services = analyzer_manager.discover_services(tmp_path)

        assert len(services) == 1
        service = services.get_service("java-service")
        assert isinstance(service, Service)
        assert service.name == "java-service"
        assert service.language == "java"
        assert len(service.source_files) == 1

    def test_discover_services_python(
        self, analyzer_manager: AnalyzerManager, tmp_path: Path
    ) -> None:
        """Test Python service discovery with Poetry project structure."""
        # Create mock Python service structure
        service_dir = tmp_path / "python-service"  # Remove "services" subdirectory
        service_dir.mkdir(parents=True)

        # Create setup.py (since analyzer_manager likely looks for this)
        setup_content = """
from setuptools import setup

setup(
    name="python-service",
    version="0.1.0",
    packages=["python_service"],
    install_requires=[
        "kafka-python>=2.0.2",
    ],
)
"""
        (service_dir / "setup.py").write_text(setup_content)

        # Create Python package structure
        src_dir = service_dir / "python_service"
        src_dir.mkdir()
        (src_dir / "__init__.py").touch()

        # Create Python source file with Kafka usage
        py_file = src_dir / "consumer.py"
        py_file.write_text(
            """
from kafka import KafkaConsumer
consumer = KafkaConsumer('test-topic')
    """.strip()
        )

        # Find services
        services = analyzer_manager.discover_services(tmp_path)

        # Assert service was discovered
        assert len(services) == 1
        service = services.get_service("python-service")
        assert isinstance(service, Service)
        assert service.name == "python-service"
        assert service.language == "python"

    def test_analyze_schemas(self, analyzer_manager, mock_service, tmp_path) -> None:
        # Create mock Avro schema file
        schema_dir = tmp_path / "schemas"
        schema_dir.mkdir()
        schema_file = schema_dir / "test.avsc"
        schema_file.write_text(
            """
        {
            "type": "record",
            "name": "TestRecord",
            "namespace": "com.test",
            "fields": [
                {"name": "field1", "type": "string"}
            ]
        }
        """
        )

        mock_service.root_path = schema_dir
        analyzer_manager.analyze_schemas(mock_service)
        assert len(mock_service.schemas) > 0

    def test_analyze_file(self, analyzer_manager, mock_service, tmp_path) -> None:
        # Create mock Java file with Kafka annotations
        test_file = tmp_path / "TestConsumer.java"
        test_file.write_text(
            """
        @KafkaListener(topics = "test-topic")
        public void consume(String message) {
        }
        """
        )

        topics = analyzer_manager.analyze_file(test_file, mock_service)
        assert topics is not None
        assert "test-topic" in topics

    def test_generate_output(self, analyzer_manager) -> None:
        services = ServiceCollection()
        service = Service(root_path=Path("/test"), name="java")

        # First add the topic as a string
        service.add_topic("test-topic")

        # Then get and update the topic
        topic = service.topics["test-topic"]
        location_producer = {"file": "TestProducer.java", "line": "1"}
        topic.add_producer_location("TestProducer", location_producer)
        location_consumer = {"file": "TestConsumer.java", "line": "1"}
        topic.add_consumer_location("TestConsumer", location_consumer)

        services.add_service(service)

        output = analyzer_manager.generate_output(services)
        assert "services" in output
        assert len(output["services"]) == 1

    def test_save_output(self, analyzer_manager, tmp_path) -> None:
        services = ServiceCollection()
        output_file = tmp_path / "output.json"
        analyzer_manager.save_output(services, output_file)
        assert output_file.exists()

    def test_error_handling(self, analyzer_manager, mock_service, tmp_path) -> None:
        # Test with invalid file
        invalid_file = tmp_path / "invalid.txt"
        invalid_file.write_text("invalid content")

        # Should not raise exception
        analysis_result = analyzer_manager.analyze_file(invalid_file, mock_service)
        assert analysis_result is None
