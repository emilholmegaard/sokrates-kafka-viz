import pytest
from pathlib import Path
from kafka_viz.models.service import Service
from kafka_viz.models.service_registry import AnalysisResult
from kafka_viz.analyzers.service_analyzer import ServiceAnalyzer

@pytest.fixture
def service_analyzer():
    return ServiceAnalyzer()

@pytest.fixture
def mock_service():
    return Service(name="test-service", root_path=Path("/mock/path"))

@pytest.fixture
def mock_result():
    return AnalysisResult(affected_service="test-service")

def test_analyze_java_service(
    service_analyzer, mock_service, mock_result, monkeypatch
):
    """Test Java service dependency analysis."""
    pom_content = """<?xml version="1.0" encoding="UTF-8"?>
    <project xmlns="http://maven.apache.org/POM/4.0.0">
        <dependencies>
            <dependency>
                <groupId>org.springframework.cloud</groupId>
                <artifactId>spring-cloud-starter</artifactId>
            </dependency>
        </dependencies>
    </project>"""

    application_properties = """
    auth-service.url=http://auth-service:8080
    database-service.url=http://database-service:8080
    """

    # Mock file existence and content reading
    read_counts = {"pom.xml": 0}
    def mock_read_text(self):
        if self.name == "pom.xml":
            read_counts["pom.xml"] += 1
            return pom_content
        return application_properties

    monkeypatch.setattr(Path, "exists", lambda _: True)
    monkeypatch.setattr(Path, "read_text", mock_read_text)

    service_analyzer._analyze_java_service(mock_service, mock_result)

    # Verify relationships were created
    assert len(mock_result.service_relationships) == 2
    relationships = {r.target: r for r in mock_result.service_relationships}
    assert "auth-service" in relationships
    assert "database-service" in relationships
    assert all(r.type == "spring-cloud" for r in mock_result.service_relationships)