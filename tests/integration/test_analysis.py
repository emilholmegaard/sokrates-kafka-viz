import pytest
from pathlib import Path

def create_test_services(tmp_path):
    """Create test service directories with sample code."""
    services_dir = tmp_path / "services"
    services_dir.mkdir()
    
    # Create Java service
    java_service = services_dir / "order-service"
    java_service.mkdir()
    (java_service / "src" / "main" / "java").mkdir(parents=True)
    with open(java_service / "src" / "main" / "java" / "OrderService.java", "w") as f:
        f.write("""
        @KafkaListener(topics = "orders")
        public void processOrder(OrderEvent event) {
            // Process order
            template.send("notifications", new NotificationEvent());
        }
        """)
    
    return services_dir

def test_end_to_end_analysis(tmp_path):
    """Test complete analysis process."""
    # Create test services
    services_dir = create_test_services(tmp_path)
    
    # Run analysis
    result = run_cli_analysis(services_dir)
    
    # Verify output
    assert result.exit_code == 0
    validate_analysis_output(result.output_file)
    
def test_kafka_analyzer_java():
    """Test Kafka pattern detection in Java code."""
    service = create_java_service(
        '''
        @KafkaListener(topics = "orders")
        public void processOrder(OrderEvent event) {
            // Process order
            template.send("notifications", new NotificationEvent());
        }
        '''
    )
    
    analyzer = KafkaAnalyzer()
    analyzer.analyze_service(service)
    
    assert "orders" in service.topics
    assert "notifications" in service.topics
    assert service.name in service.topics["orders"].consumers
    assert service.name in service.topics["notifications"].producers