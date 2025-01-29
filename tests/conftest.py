"""Test configuration and fixtures."""
import tempfile
from pathlib import Path

import pytest

from kafka_viz.models import Service

def create_test_services(base_path: Path) -> Path:
    """Create test service directories with sample code.
    
    Args:
        base_path: Base directory for test services
        
    Returns:
        Path: Path to services directory
    """
    services_dir = base_path / "services"
    services_dir.mkdir()
    
    # Create Java service
    java_service = services_dir / "order-service"
    java_service.mkdir(parents=True)
    java_src = java_service / "src" / "main" / "java"
    java_src.mkdir(parents=True)
    
    with open(java_src / "OrderService.java", "w") as f:
        f.write("""
        @Service
        public class OrderService {
            @KafkaListener(topics = "orders")
            public void processOrder(OrderEvent event) {
                // Process order
                template.send("notifications", new NotificationEvent());
            }
        }
        """)
    
    return services_dir

def create_java_service(content: str) -> Service:
    """Create a Java service with the given content.
    
    Args:
        content: Java source code content
        
    Returns:
        Service: Created service
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        service_dir = Path(tmpdir) / "test-service"
        java_src = service_dir / "src" / "main" / "java"
        java_src.mkdir(parents=True)
        
        with open(java_src / "TestService.java", "w") as f:
            f.write(content)
            
        return Service(name="test-service", path=service_dir, language="java")

def run_cli_analysis(services_dir: Path) -> Path:
    """Run CLI analysis on test services.
    
    Args:
        services_dir: Directory containing test services
        
    Returns:
        Path: Path to output file
    """
    output_file = services_dir.parent / "output.json"
    
    # TODO: Implement CLI runner
    # For now, just create a dummy output file
    with open(output_file, "w") as f:
        f.write("{}")
    
    return output_file

@pytest.fixture
def spring_service_dir() -> Path:
    """Fixture providing path to Spring service test data."""
    return Path(__file__).parent / "test_data" / "spring_service"

@pytest.fixture
def python_service_dir() -> Path:
    """Fixture providing path to Python service test data."""
    return Path(__file__).parent / "test_data" / "python_service"