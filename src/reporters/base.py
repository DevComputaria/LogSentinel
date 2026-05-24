from abc import ABC, abstractmethod
from ..models.result import AnalysisResult


class ReportBuilder(ABC):
    @abstractmethod
    def build(self, result: AnalysisResult) -> str:
        ...

    @abstractmethod
    def render(self, result: AnalysisResult, output_path: str):
        ...
