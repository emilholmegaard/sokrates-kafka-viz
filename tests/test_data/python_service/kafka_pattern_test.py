from kafka import KafkaProducer, KafkaConsumer
from confluent_kafka import Producer, Consumer
from typing import Dict
import json

# Constants and configuration
TOPIC = "constant-topic"
topic = "variable-topic"

producer_config = {
    "topic": "config-topic",
    "bootstrap.servers": "localhost:9092"
}

consumer_config = {
    "topic": "consumer-topic",
    "group.id": "test-group"
}

class KafkaPatternTest:
    def __init__(self):
        self.producer = KafkaProducer(bootstrap_servers="localhost:9092")
        self.consumer = KafkaConsumer(bootstrap_servers="localhost:9092")
        
        self.producer_config = ProducerConfig()
        self.producer_config.topic = "producer-config-topic"
        
        self.consumer_config = ConsumerConfig()
        self.consumer_config.topic = "consumer-config-topic"

    # Producer patterns
    def test_producers(self):
        # Direct producer methods
        self.producer.send("direct-topic", b"message")
        self.producer.produce("produce-topic", b"message")
        
        # Confluent producer
        conf_producer = Producer({"bootstrap.servers": "localhost:9092"})
        conf_producer.produce("confluent-topic", b"message")

    # Consumer patterns
    @kafka_listener(topic="decorator-topic")
    def listen_decorator(self, message):
        pass
        
    @consumer(topic="consumer-decorator-topic")
    def consumer_decorator(self, message):
        pass

    def test_consumers(self):
        # Direct consumer methods
        self.consumer.subscribe(["subscribe-topic"])
        self.consumer.subscribe({"pattern-topic.*"})
        
        # Confluent consumer
        conf_consumer = Consumer({"bootstrap.servers": "localhost:9092"})
        conf_consumer.subscribe(["confluent-topic"])

class ProducerConfig:
    def __init__(self):
        self.topic = "producer-init-topic"
        
class ConsumerConfig:
    def __init__(self):
        self.topic = "consumer-init-topic"
