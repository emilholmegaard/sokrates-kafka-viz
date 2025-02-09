import pytest
from pathlib import Path

from kafka_viz.analyzers.analyzer_manager import AnalyzerManager
from kafka_viz.models.service import Service
from kafka_viz.models.service_collection import ServiceCollection


def test_advanced_kafka_patterns_integration(test_data_dir) -> None:
    """Test that all advanced Kafka patterns are correctly detected using AnalyzerManager."""
    # Initialize the analyzer manager
    analyzer_manager = AnalyzerManager()
    
    # Create a service manually (since we're testing a specific directory)
    service_path = test_data_dir / "java" / "advanced"
    java_service = Service(name="java-service", path=service_path, language="java")
    
    # Create a service collection and add our service
    services = ServiceCollection()
    services.add_service(java_service)
    
    # Analyze schemas first (following the manager's intended order)
    analyzer_manager.analyze_schemas(java_service)
    
    # Analyze all files in the service
    for file_path in service_path.rglob("*"):
        if file_path.is_file():
            topics = analyzer_manager.analyze_file(file_path, java_service)
            if topics:
                java_service.topics.update(topics)

    # Check if all expected topics are found
    topic_names = {t.name for t in java_service.topics.values()}

    expected_topics = {
        "record-topic",
        "publish-topic",
        "${kafka.topic.name}",
        "topic1",
        "topic2",
        "topic3",
        "topic4",
        "topic5",
        "topic6",
        "${kafka.topics.custom}",
        "outputChannel",
        "inputChannel",
        "input",
        "output",
    }
    assert topic_names == expected_topics

    # Check topic producer roles
    producers = {topic_name for topic_name, topic in java_service.topics.items() if topic.producers}
    expected_producers = {
        "record-topic",
        "publish-topic",
        "${kafka.topic.name}",
        "outputChannel",
        "output",
    }
    assert producers == expected_producers

    # Check topic consumer roles
    consumers = {topic_name for topic_name, topic in java_service.topics.items() if topic.consumers}
    expected_consumers = {
        "topic1",
        "topic2",
        "topic3",
        "topic4",
        "topic5",
        "topic6",
        "${kafka.topics.custom}",
        "inputChannel",
        "input",
    }
    assert consumers == expected_consumers


def test_service_analysis_integration(test_data_dir) -> None:
    """Test the complete integration of AnalyzerManager with analyzing specific services."""
    analyzer_manager = AnalyzerManager()
    services = ServiceCollection()
    
    # Add Java service
    java_service_path = test_data_dir / "java" / "advanced"
    if java_service_path.exists():
        java_service = Service(name="java-service", path=java_service_path, language="java")
        services.add_service(java_service)
        
    # Add Spring service if it exists
    spring_service_path = test_data_dir / "spring_service"
    if spring_service_path.exists():
        spring_service = Service(name="spring-service", path=spring_service_path, language="java")
        services.add_service(spring_service)
        
    # Add Python service if it exists
    python_service_path = test_data_dir / "python_service"
    if python_service_path.exists():
        python_service = Service(name="python-service", path=python_service_path, language="python")
        services.add_service(python_service)
    
    # Verify that we found services
    assert len(services.services) > 0, "No test services were found"
    
    # For each service, analyze schemas and then analyze all files
    for service in services.services.values():
        analyzer_manager.analyze_schemas(service)
        
        for file_path in service.root_path.rglob("*"):
            if file_path.is_file():
                topics = analyzer_manager.analyze_file(file_path, service)
                if topics:
                    service.topics.update(topics)
    
    # Verify that at least one service has topics
    has_topics = any(len(service.topics) > 0 for service in services.services.values())
    assert has_topics, "No Kafka topics were found in any service"
    
    # If we have the Java service, verify its topics
    java_service = services.services.get("java-service")
    if java_service:
        assert len(java_service.topics) > 0, "No topics found in Java service"