import pytest
from pathlib import Path
from kafka_viz.analyzers.analyzer_manager import AnalyzerManager
from kafka_viz.models.service import Service
from kafka_viz.models.schema import KafkaTopic
from kafka_viz.models.service_collection import ServiceCollection

class TestAnalyzerManager:
    @pytest.fixture
    def analyzer_manager(self):
        return AnalyzerManager()
    
    @pytest.fixture
    def mock_service(self):
        return Service(Path("/mock/path"), "java")
    
    def test_discover_services(self, analyzer_manager, tmp_path):
        # Create a mock service directory structure
        service_dir = tmp_path / "service1"
        service_dir.mkdir()
        (service_dir / "pom.xml").touch()
        
        services = analyzer_manager.discover_services(tmp_path)
        assert isinstance(services, ServiceCollection)
        assert len(services.services) == 1
    
    def test_analyze_schemas(self, analyzer_manager, mock_service, tmp_path):
        # Create mock Avro schema file
        schema_dir = tmp_path / "schemas"
        schema_dir.mkdir()
        schema_file = schema_dir / "test.avsc"
        schema_file.write_text('''
        {
            "type": "record",
            "name": "TestRecord",
            "namespace": "com.test",
            "fields": [
                {"name": "field1", "type": "string"}
            ]
        }
        ''')
        
        mock_service.root_path = schema_dir
        analyzer_manager.analyze_schemas(mock_service)
        assert len(mock_service.schemas) > 0
    
    def test_analyze_file(self, analyzer_manager, mock_service, tmp_path):
        # Create mock Java file with Kafka annotations
        test_file = tmp_path / "TestConsumer.java"
        test_file.write_text('''
        @KafkaListener(topics = "test-topic")
        public void consume(String message) {
        }
        ''')
        
        topics = analyzer_manager.analyze_file(test_file, mock_service)
        assert topics is not None
        assert "test-topic" in topics
    
    def test_generate_output(self, analyzer_manager):
        services = ServiceCollection()
        service = Service(Path("/test"), "java")
        topic = KafkaTopic("test-topic")
        topic.add_producer("TestProducer")
        topic.add_consumer("TestConsumer")
        service.add_topic(topic)
        services.add_service(service)
        
        output = analyzer_manager.generate_output(services)
        assert "services" in output
        assert len(output["services"]) == 1
    
    def test_save_output(self, analyzer_manager, tmp_path):
        services = ServiceCollection()
        output_file = tmp_path / "output.json"
        analyzer_manager.save_output(services, output_file)
        assert output_file.exists()
        
    def test_error_handling(self, analyzer_manager, mock_service, tmp_path):
        # Test with invalid file
        invalid_file = tmp_path / "invalid.txt"
        invalid_file.write_text("invalid content")
        
        # Should not raise exception
        topics = analyzer_manager.analyze_file(invalid_file, mock_service)
        assert topics is None
