import re
from typing import List, Pattern

def get_kafka_patterns() -> List[Pattern]:
    """Return compiled regex patterns for finding Kafka-related code."""
    return [
        re.compile(r'@KafkaListener\(.*?\)'),
        re.compile(r'@SendTo\(.*?\)'),
        re.compile(r'KafkaTemplate<.*?>'),
        re.compile(r'new KafkaConsumer\(.*?\)'),
        re.compile(r'new KafkaProducer\(.*?\)'),
        re.compile(r'from kafka import KafkaConsumer, KafkaProducer'),
        re.compile(r'using Kafka\.Clients'),
        re.compile(r'kafka\.clients\.consumer'),
        re.compile(r'kafka\.clients\.producer')
    ]