import pytest
from src.analyzers.java_analyzer import JavaKafkaAnalyzer, KafkaTopic

@pytest.fixture
def analyzer():
    return JavaKafkaAnalyzer()

def test_plain_kafka_producer(analyzer):
    content = '''
    public class OrderProducer {
        public void sendOrder(String orderId) {
            ProducerRecord<String, String> record = new ProducerRecord<>("orders", orderId, "order-data");
            producer.send(record);
        }
    }
    '''
    
    topics = analyzer.analyze_file('OrderProducer.java', content)
    assert len(topics) == 1
    assert topics[0].name == 'orders'
    assert topics[0].type == 'producer'
    assert topics[0].pattern_type == 'plain'

def test_plain_kafka_consumer(analyzer):
    content = '''
    public class OrderConsumer {
        public void consume() {
            consumer.subscribe(Arrays.asList("orders"));
        }
    }
    '''
    
    topics = analyzer.analyze_file('OrderConsumer.java', content)
    assert len(topics) == 1
    assert topics[0].name == 'orders'
    assert topics[0].type == 'consumer'
    assert topics[0].pattern_type == 'plain'

def test_spring_kafka_annotations(analyzer):
    content = '''
    @Service
    public class KafkaService {
        @KafkaListener(topics = "orders")
        @SendTo("processed-orders")
        public void processMessage(String message) {
            return "processed";
        }
    }
    '''
    
    topics = analyzer.analyze_file('KafkaService.java', content)
    assert len(topics) == 2
    assert any(t.name == 'orders' and t.type == 'consumer' for t in topics)
    assert any(t.name == 'processed-orders' and t.type == 'producer' for t in topics)

def test_spring_cloud_stream_annotations(analyzer):
    content = '''
    @EnableBinding(Processor.class)
    public class OrderProcessor {
        @StreamListener("orders")
        @SendTo("processed-orders")
        public ProcessedOrder processOrder(Order order) {
            return new ProcessedOrder(order.getId());
        }
    }
    '''
    
    topics = analyzer.analyze_file('OrderProcessor.java', content)
    assert len(topics) == 2
    assert any(t.name == 'orders' and t.type == 'consumer' for t in topics)
    assert any(t.name == 'processed-orders' and t.type == 'producer' for t in topics)

def test_topic_constants(analyzer):
    content = '''
    public class KafkaConfig {
        private static final String ORDER_TOPIC = "orders";
        private static final String PROCESSED_TOPIC = "processed-orders";
        
        public void process() {
            producer.send(ORDER_TOPIC, "data");
            consumer.subscribe(Arrays.asList(PROCESSED_TOPIC));
        }
    }
    '''
    
    topics = analyzer.analyze_file('KafkaConfig.java', content)
    assert len(topics) == 2
    assert any(t.name == 'orders' and t.type == 'producer' for t in topics)
    assert any(t.name == 'processed-orders' and t.type == 'consumer' for t in topics)

def test_spring_config_topics(analyzer):
    content = '''
    @Configuration
    public class KafkaConfig {
        @Value("${kafka.order.topic}")
        private String orderTopic;
        
        @KafkaListener(topics = "${kafka.order.topic}")
        public void process(String message) {
            kafkaTemplate.send(orderTopic, "processed");
        }
    }
    '''
    
    topics = analyzer.analyze_file('KafkaConfig.java', content)
    assert len(topics) == 2

def test_multi_topic_declaration(analyzer):
    content = '''
    @Service
    public class MultiTopicService {
        @KafkaListener(topics = {"orders", "returns"})
        public void processMessages(String message) {
            // Process
        }
    }
    '''
    
    topics = analyzer.analyze_file('MultiTopicService.java', content)
    assert len(topics) == 2
    assert any(t.name == 'orders' and t.type == 'consumer' for t in topics)
    assert any(t.name == 'returns' and t.type == 'consumer' for t in topics)

def test_topic_dependencies(analyzer):
    topics = [
        KafkaTopic('orders', 'consumer', {'file': 'service1.java', 'line': 1}, 'plain'),
        KafkaTopic('processed', 'producer', {'file': 'service1.java', 'line': 2}, 'plain'),
        KafkaTopic('processed', 'consumer', {'file': 'service2.java', 'line': 1}, 'plain'),
        KafkaTopic('notifications', 'producer', {'file': 'service2.java', 'line': 2}, 'plain'),
    ]
    
    dependencies = analyzer.get_topic_dependencies(topics)
    assert 'orders' in dependencies
    assert 'processed' in dependencies
    assert dependencies['orders'] == ['processed']
    assert dependencies['processed'] == ['notifications']