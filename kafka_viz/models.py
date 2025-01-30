from enum import Enum
from typing import Set

class TopicType(Enum):
    PRODUCER = "producer"
    CONSUMER = "consumer"

class KafkaTopic:
    def __init__(self, name: str, type_: TopicType, services: Set[str] = None):
        self.name = name
        self.type = type_
        self.services = services or set()

    def __eq__(self, other):
        if not isinstance(other, KafkaTopic):
            return False
        return self.name == other.name and self.type == other.type

    def __hash__(self):
        return hash((self.name, self.type))

    def __repr__(self):
        return f"KafkaTopic(name='{self.name}', type={self.type}, services={self.services})"