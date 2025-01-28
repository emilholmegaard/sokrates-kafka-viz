# base.py
from abc import ABC, abstractmethod

class BaseGenerator(ABC):
    @abstractmethod
    def generate_html(self, data: dict) -> str:
        pass