from pathlib import Path

import pytest

from kafka_viz.analyzers.service_analyzer import ServiceAnalyzer
from kafka_viz.models.service import Service
from kafka_viz.models.service_registry import AnalysisResult


@pytest.fixture
def service_analyzer():
    return ServiceAnalyzer()


@pytest.fixture
def mock_service():
    return Service(name="test-service", root_path=Path("/mock/path"))


@pytest.fixture
def mock_result(mock_service):
    return AnalysisResult(affected_service=mock_service.name)


@pytest.fixture
def requirements_content():
    return """flask>=2.0.0
auth-service-client>=1.0.0
database-api~=2.1.0
pytest>=6.0.0"""


def test_analyze_python_service(
    service_analyzer, mock_service, mock_result, requirements_content, monkeypatch
):
    """Test Python service dependency analysis."""
    monkeypatch.setattr(Path, "exists", lambda _: True)
    monkeypatch.setattr(Path, "read_text", lambda _: requirements_content)

    service_analyzer._analyze_python_service(mock_service, mock_result)

    # Verify relationships were created
    assert (
        len(mock_result.service_relationships) == 2
    )  # auth-service-client and database-api
    relationships = {r.target: r for r in mock_result.service_relationships}
    assert "auth-service-client" in relationships
    assert "database-api" in relationships
    assert all(r.type == "python-dependency" for r in mock_result.service_relationships)


@pytest.fixture
def requirements_content_with_spaces():
    return """
    flask>=2.0.0
auth-service-client >= 1.0.0
  database-api ~= 2.1.0
pytest>=6.0.0
"""


def test_analyze_python_service_with_spaces(
    service_analyzer,
    mock_service,
    mock_result,
    requirements_content_with_spaces,
    monkeypatch,
):
    """Test Python service dependency analysis with various spacing."""
    monkeypatch.setattr(Path, "exists", lambda _: True)
    monkeypatch.setattr(Path, "read_text", lambda _: requirements_content_with_spaces)

    service_analyzer._analyze_python_service(mock_service, mock_result)

    assert len(mock_result.service_relationships) == 2
    relationships = {r.target: r for r in mock_result.service_relationships}
    assert "auth-service-client" in relationships
    assert "database-api" in relationships


@pytest.fixture
def pom_content():
    return """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <dependencies>
        <dependency>
            <groupId>com.company</groupId>
            <artifactId>auth-client</artifactId>
            <version>1.0.0</version>
        </dependency>
        <dependency>
            <groupId>com.company</groupId>
            <artifactId>database-client</artifactId>
            <version>2.1.0</version>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
            <version>2.5.0</version>
        </dependency>
    </dependencies>
</project>"""


def test_analyze_java_service(
    service_analyzer, mock_service, mock_result, pom_content, monkeypatch
):
    """Test Java service dependency analysis."""
    monkeypatch.setattr(Path, "exists", lambda _: True)
    monkeypatch.setattr(Path, "read_text", lambda _: pom_content)

    service_analyzer._analyze_java_service(mock_service, mock_result)

    # Verify relationships were created
    assert (
        len(mock_result.service_relationships) == 2
    )  # auth-client and database-client
    relationships = {r.target: r for r in mock_result.service_relationships}
    assert "auth-client" in relationships
    assert "database-client" in relationships
    assert all(r.type == "java-dependency" for r in mock_result.service_relationships)
