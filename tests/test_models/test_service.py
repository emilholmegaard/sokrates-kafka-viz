from pathlib import Path
from kafka_viz.models.service import Service

def test_service_creation():
    path = Path('/test/service')
    service = Service(name='test-service', path=path)
    
    assert service.name == 'test-service'
    assert service.path == path
    assert service.kafka_topics == {}

def test_service_add_topic():
    service = Service(name='test-service', path=Path('/test'))
    
    service.add_topic('test-topic', producer=True)
    assert 'test-topic' in service.kafka_topics
    
    topic = service.kafka_topics['test-topic']
    assert service.name in topic.producers
    assert service.name not in topic.consumers

def test_service_equality():
    service1 = Service(name='test', path=Path('/test'))
    service2 = Service(name='test', path=Path('/test'))
    service3 = Service(name='other', path=Path('/test'))
    
    assert service1 == service2
    assert service1 != service3