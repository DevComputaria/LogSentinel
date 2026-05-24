from abc import ABC, abstractmethod
from typing import Any


class Detector(ABC):
    @abstractmethod
    def detect(self, df, **kwargs) -> Any:
        ...
