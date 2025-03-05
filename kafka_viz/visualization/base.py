# base.py
from abc import ABC, abstractmethod
from pathlib import Path


class BaseGenerator(ABC):
    @abstractmethod
    def generate_html(self, data: dict) -> str:
        pass

    @abstractmethod
    def generate_output(self, data: dict, file_path: Path) -> None:
        pass
