from abc import ABC, abstractmethod
import pandas as pd


class LogParser(ABC):
    @abstractmethod
    def parse(self, path: str) -> pd.DataFrame:
        ...
