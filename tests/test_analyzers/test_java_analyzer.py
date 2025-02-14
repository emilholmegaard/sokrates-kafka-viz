"""Tests for the Java-specific Kafka analyzer."""

from pathlib import Path

import pytest

from kafka_viz.analyzers.java_analyzer import JavaAnalyzer
from kafka_viz.models import Service


@pytest.fixture
def analyzer() -> JavaAnalyzer:
    return JavaAnalyzer()


@pytest.fixture
def test_service():
    return Service(name="test-service", root_path=Path("/tmp/test"))


def test_can_analyze(analyzer) -> None:
    """Test file extension detection."""
    assert analyzer.can_analyze(Path("test.java"))
    assert not analyzer.can_analyze(Path("test.py"))
    assert not analyzer.can_analyze(Path("test.cs"))


def test_plain_kafka_producer(analyzer, test_service, tmp_path) -> None:
    """Test detection of plain Kafka producer patterns."""
    content = """
    public class OrderProducer {
        public void sendOrder(String orderId) {
            ProducerRecord<String, String> record = new ProducerRecord<>(
                "orders", orderId, "order-data"
            );
            producer.send(record);
        }
    }
    """

    file_path = tmp_path / "OrderProducer.java"
    file_path.write_text(content)
    test_service.root_path = tmp_path

    analysis_result = analyzer.analyze(file_path, test_service)
    assert analysis_result.topics is not None
    assert "orders" in analysis_result.topics
    assert test_service.name in analysis_result.topics["orders"].producers
    assert not analysis_result.topics["orders"].consumers


def test_plain_kafka_consumer(analyzer, test_service, tmp_path) -> None:
    """Test detection of plain Kafka consumer patterns."""
    content = """
    public class OrderConsumer {
        public void consume() {
            consumer.subscribe(Arrays.asList("orders"));
        }
    }
    """

    file_path = tmp_path / "OrderConsumer.java"
    file_path.write_text(content)
    test_service.root_path = tmp_path

    analysis_result = analyzer.analyze(file_path, test_service)
    assert analysis_result.topics is not None
    assert "orders" in analysis_result.topics
    assert test_service.name in analysis_result.topics["orders"].consumers
    assert not analysis_result.topics["orders"].producers


def test_spring_kafka_annotations(analyzer, test_service, tmp_path) -> None:
    """Test detection of Spring Kafka annotations."""
    content = """
    @Service
    public class KafkaService {
        @KafkaListener(topics = "orders")
        @SendTo("processed-orders")
        public void processMessage(String message) {
            return "processed";
        }
    }
    """

    file_path = tmp_path / "KafkaService.java"
    file_path.write_text(content)
    test_service.root_path = tmp_path

    analysis_result = analyzer.analyze(file_path, test_service)
    assert analysis_result.topics is not None
    assert "orders" in analysis_result.topics
    assert "processed-orders" in analysis_result.topics
    assert test_service.name in analysis_result.topics["orders"].consumers
    assert test_service.name in analysis_result.topics["processed-orders"].producers


def test_spring_cloud_stream_annotations(analyzer, test_service, tmp_path) -> None:
    """Test detection of Spring Cloud Stream annotations."""
    content = """
    @EnableBinding(Processor.class)
    public class OrderProcessor {
        @StreamListener("orders")
        @SendTo("processed-orders")
        public ProcessedOrder processOrder(Order order) {
            return new ProcessedOrder(order.getId());
        }
    }
    """

    file_path = tmp_path / "OrderProcessor.java"
    file_path.write_text(content)
    test_service.root_path = tmp_path

    analysis_result = analyzer.analyze(file_path, test_service)
    assert analysis_result.topics is not None
    assert "orders" in analysis_result.topics
    assert "processed-orders" in analysis_result.topics
    assert test_service.name in analysis_result.topics["orders"].consumers
    assert test_service.name in analysis_result.topics["processed-orders"].producers


def test_topic_constants(analyzer, test_service, tmp_path) -> None:
    """Test detection of topic constants and variables."""
    content = """
    public class KafkaConfig {
        private static final String ORDER_TOPIC = "orders";
        private static final String PROCESSED_TOPIC = "processed-orders";
        public void process() {
            producer.send(ORDER_TOPIC, "data");
            consumer.subscribe(Arrays.asList(PROCESSED_TOPIC));
        }
    }
    """

    file_path = tmp_path / "KafkaConfig.java"
    file_path.write_text(content)
    test_service.root_path = tmp_path

    analysis_result = analyzer.analyze(file_path, test_service)
    assert analysis_result.topics is not None
    assert "orders" in analysis_result.topics
    assert "processed-orders" in analysis_result.topics
    assert test_service.name in analysis_result.topics["orders"].producers
    assert test_service.name in analysis_result.topics["processed-orders"].consumers


def test_spring_config_topics(analyzer, test_service, tmp_path) -> None:
    """Test detection of Spring configuration properties."""
    content = """
    @Configuration
    public class KafkaConfig {
        @Value("${kafka.order.topic}")
        private String orderTopic;
        @KafkaListener(topics = "${kafka.order.topic}")
        public void process(String message) {
            kafkaTemplate.send(orderTopic, "processed");
        }
    }
    """

    file_path = tmp_path / "KafkaConfig.java"
    file_path.write_text(content)
    test_service.root_path = tmp_path

    # Spring config topics need special handling as they're resolved at runtime
    analysis_result = analyzer.analyze(file_path, test_service)
    assert analysis_result.topics is not None
    assert len(analysis_result.topics) > 0


def test_multi_topic_declaration(analyzer, test_service, tmp_path) -> None:
    """Test detection of multi-topic declarations."""
    content = """
    @Service
    public class MultiTopicService {
        @KafkaListener(topics = {"orders", "returns"})
        public void processMessages(String message) {
            // Process
        }
    }
    """

    file_path = tmp_path / "MultiTopicService.java"
    file_path.write_text(content)
    test_service.root_path = tmp_path

    analysis_result = analyzer.analyze(file_path, test_service)
    assert analysis_result.topics is not None
    assert "orders" in analysis_result.topics
    assert "returns" in analysis_result.topics
    assert test_service.name in analysis_result.topics["orders"].consumers
    assert test_service.name in analysis_result.topics["returns"].consumers
