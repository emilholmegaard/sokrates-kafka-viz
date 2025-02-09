"""Unit tests for service-level analyzers."""

from pathlib import Path

import pytest

from kafka_viz.analyzers.service_level_base import ServiceLevelAnalyzer
from kafka_viz.models.service import Service
from kafka_viz.models.service_collection import ServiceCollection


class MockServiceLevelAnalyzer(ServiceLevelAnalyzer):
    """Mock implementation of ServiceLevelAnalyzer for testing."""

    def __init__(self) -> None:
        self.analyze_called = False
        self.last_services = None

    def analyze_services(self, services: ServiceCollection) -> None:
        self.analyze_called = True
        self.last_services = services


def test_service_level_analyzer_interface() -> None:
    """Test that the base ServiceLevelAnalyzer interface works as expected."""
    analyzer = MockServiceLevelAnalyzer()
    services = ServiceCollection()

    # Add a test service
    service = Service(
        name="test-service", root_path=Path("/fake/path"), language="java"
    )
    services.add_service(service)

    # Run analysis
    analyzer.analyze_services(services)

    # Verify analyze_services was called with correct parameters
    assert analyzer.analyze_called
    assert analyzer.last_services == services

    # Check debug info format
    debug_info = analyzer.get_debug_info()
    assert isinstance(debug_info, dict)
    assert debug_info["analyzer"] == "MockServiceLevelAnalyzer"
    assert debug_info["type"] == "service-level"


def test_analyzer_inheritance() -> None:
    """Test that service-level analyzers properly inherit from base class."""
    from kafka_viz.analyzers.dependency_analyzer import DependencyAnalyzer

    # Check that DependencyAnalyzer is a ServiceLevelAnalyzer
    assert issubclass(DependencyAnalyzer, ServiceLevelAnalyzer)

    # Verify interface implementation
    analyzer = DependencyAnalyzer()
    assert hasattr(analyzer, "analyze_services")
    assert hasattr(analyzer, "get_debug_info")

    # Check debug info includes base class fields
    debug_info = analyzer.get_debug_info()
    assert "analyzer" in debug_info
    assert "type" in debug_info
    assert debug_info["type"] == "service-level"


def test_service_level_analyzer_with_empty_services() -> None:
    """Test that service-level analyzers handle empty service collections gracefully."""
    analyzer = MockServiceLevelAnalyzer()
    services = ServiceCollection()

    # Analysis should not raise exceptions with empty service collection
    analyzer.analyze_services(services)
    assert analyzer.analyze_called
    assert len(analyzer.last_services.services) == 0


def test_service_level_analyzer_error_handling() -> None:
    """Test error handling in service-level analyzers."""

    class ErrorAnalyzer(ServiceLevelAnalyzer):
        def analyze_services(self, services: ServiceCollection) -> None:
            raise ValueError("Test error")

    analyzer = ErrorAnalyzer()
    services = ServiceCollection()
    service = Service(
        name="test-service", root_path=Path("/fake/path"), language="java"
    )
    services.add_service(service)

    # Analysis should raise the error
    with pytest.raises(ValueError, match="Test error"):
        analyzer.analyze_services(services)


def test_analyzer_debug_info_override():
    """Test that analyzers can override and extend debug info."""

    class ExtendedDebugAnalyzer(ServiceLevelAnalyzer):
        def analyze_services(self, services: ServiceCollection) -> None:
            pass

        def get_debug_info(self) -> dict:
            base_info = super().get_debug_info()
            base_info.update({"custom_field": "custom_value", "another_field": 123})
            return base_info

    analyzer = ExtendedDebugAnalyzer()
    debug_info = analyzer.get_debug_info()

    # Check that both base and extended fields are present
    assert debug_info["analyzer"] == "ExtendedDebugAnalyzer"
    assert debug_info["type"] == "service-level"
    assert debug_info["custom_field"] == "custom_value"
    assert debug_info["another_field"] == 123
