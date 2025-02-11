from pathlib import Path

import pytest

from kafka_viz.analyzers.spring_analyzer import SpringCloudStreamAnalyzer
from kafka_viz.models.service import Service


@pytest.fixture
def spring_analyzer() -> SpringCloudStreamAnalyzer:
    return SpringCloudStreamAnalyzer()


@pytest.fixture
def sample_service() -> Service:
    return Service(
        name="test-service",
        root_path=Path("/fake/path"),
        language="java",
        build_file=Path("/fake/path/pom.xml"),
    )


def test_can_analyze_spring_boot_application(spring_analyzer, tmp_path):
    java_file = tmp_path / "Application.java"
    java_file.write_text(
        """
    @SpringBootApplication
    public class Application {
        public static void main(String[] args) {
            SpringApplication.run(Application.class, args);
        }
    }
    """
    )
    assert spring_analyzer.can_analyze(java_file)


def test_can_analyze_spring_cloud_stream(spring_analyzer, tmp_path):
    java_file = tmp_path / "MessageProcessor.java"
    java_file.write_text(
        """
    @StreamListener("input-channel")
    public void processMessage(Message message) {
        // Process message
    }
    """
    )
    assert spring_analyzer.can_analyze(java_file)


def test_can_analyze_rest_controller(spring_analyzer, tmp_path):
    java_file = tmp_path / "UserController.java"
    java_file.write_text(
        """
    @RestController
    @RequestMapping("/api/users")
    public class UserController {
        @GetMapping("/{id}")
        public User getUser(@PathVariable Long id) {
            return userService.findById(id);
        }
    }
    """
    )
    assert spring_analyzer.can_analyze(java_file)


def test_analyze_spring_cloud_stream_bindings(
    spring_analyzer, sample_service, tmp_path
):
    source_dir = tmp_path / "src/main/java"
    source_dir.mkdir(parents=True)

    java_file = source_dir / "MessageProcessor.java"
    java_file.write_text(
        """
    @StreamListener("input-channel")
    public void processMessage(Message message) {
        // Process message
    }   
    @ServiceActivator(outputChannel = "output-channel")
    public void sendMessage(Message message) {
        // Send message
    }
    """
    )

    config_dir = tmp_path / "src/main/resources"
    config_dir.mkdir(parents=True)

    properties_file = config_dir / "application.properties"
    properties_file.write_text(
        """
    spring.cloud.stream.bindings.input-channel.destination=incoming-topic
    spring.cloud.stream.bindings.output-channel.destination=outgoing-topic
    """
    )

    # Update service root path to temporary directory
    sample_service.root_path = tmp_path

    # Analyze the files
    topics = spring_analyzer.analyze(java_file, sample_service)

    assert len(topics) == 2
    assert "output-channel" in topics
    assert "input-channel" in topics
    print(sample_service.name)
    print(topics)

    assert sample_service.name in topics["output-channel"].producers
    assert sample_service.name in topics["input-channel"].consumers


def test_analyze_kafka_listeners(spring_analyzer, sample_service, tmp_path):
    java_file = tmp_path / "KafkaConsumer.java"
    java_file.write_text(
        """
    @KafkaListener(topics = "user-events")
    public void handleUserEvent(UserEvent event) {
        // Handle event
    }
    """
    )

    topics = spring_analyzer.analyze(java_file, sample_service)

    assert len(topics) == 1
    assert "user-events" in topics
    assert sample_service.name in topics["user-events"].consumers
