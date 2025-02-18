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

    application_properties = """auth-service.url=http://auth-service:8080
database-service.url=http://database-service:8080"""

    def mock_exists(self):
        return self.name in ["pom.xml", "application.properties"]

    def mock_read_text(self):
        if self.name == "pom.xml":
            return pom_content
        if self.name == "application.properties":
            return application_properties
        return ""

    monkeypatch.setattr(Path, "exists", mock_exists)
    monkeypatch.setattr(Path, "read_text", mock_read_text)

    service_analyzer._analyze_java_service(mock_service, mock_result)

    assert len(mock_result.service_relationships) == 2
    relationships = {r.target for r in mock_result.service_relationships}
    assert "auth-service" in relationships
    assert "database-service" in relationships
    assert all(r.type == "spring-cloud" for r in mock_result.service_relationships)

def test_analyze_java_service_no_spring_cloud(service_analyzer, mock_service, mock_result, monkeypatch):
    pom_content = """<?xml version="1.0" encoding="UTF-8"?>
    <project xmlns="http://maven.apache.org/POM/4.0.0">
        <dependencies>
            <dependency>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-starter-web</artifactId>
            </dependency>
        </dependencies>
    </project>"""

    def mock_exists(self):
        return True

    def mock_read_text(self):
        return pom_content

    monkeypatch.setattr(Path, "exists", mock_exists)
    monkeypatch.setattr(Path, "read_text", mock_read_text)

    service_analyzer._analyze_java_service(mock_service, mock_result)
    assert len(mock_result.service_relationships) == 0

def test_analyze_java_service_no_config_files(service_analyzer, mock_service, mock_result, monkeypatch):
    pom_content = """<?xml version="1.0" encoding="UTF-8"?>
    <project xmlns="http://maven.apache.org/POM/4.0.0">
        <dependencies>
            <dependency>
                <groupId>org.springframework.cloud</groupId>
                <artifactId>spring-cloud-starter</artifactId>
            </dependency>
        </dependencies>
    </project>"""

    def mock_exists(self):
        if self.name == "pom.xml":
            return True
        return False

    def mock_read_text(self):
        return pom_content

    monkeypatch.setattr(Path, "exists", mock_exists)
    monkeypatch.setattr(Path, "read_text", mock_read_text)

    service_analyzer._analyze_java_service(mock_service, mock_result)
    assert len(mock_result.service_relationships) == 0