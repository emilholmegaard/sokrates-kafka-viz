from pathlib import Path
from kafka_viz.models.service import Service
from kafka_viz.analyzers.spring_analyzer import SpringCloudStreamAnalyzer

def test_spring_cloud_stream_analyzer(spring_service_dir):
    analyzer = SpringCloudStreamAnalyzer()
    service = Service(name='spring-service', path=spring_service_dir)
    
    # Test source file analysis
    processor_file = spring_service_dir / 'src/main/java/com/example/OrderProcessor.java'
    topics = analyzer.analyze(processor_file, service)
    
    assert topics is not None
    assert len(topics) > 0
    
    # Test config file analysis
    config_file = spring_service_dir / 'src/main/resources/application.yml'
    topics = analyzer.analyze(config_file, service)
    
    assert topics is not None
    assert 'orders' in topics
    assert 'processed-orders' in topics
    
    orders_topic = topics['orders']
    assert service.name in orders_topic.consumers
    
    processed_topic = topics['processed-orders']
    assert service.name in processed_topic.producers

def test_spring_analyzer_ignore_test_files(spring_service_dir):
    analyzer = SpringCloudStreamAnalyzer()
    service = Service(name='spring-service', path=spring_service_dir)
    
    test_file = Path('OrderProcessorTest.java')
    topics = analyzer.analyze(test_file, service)
    
    assert topics is None