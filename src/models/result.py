from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import pandas as pd


@dataclass
class LogEntry:
    timestamp: Optional[datetime]
    level: str
    component: str
    message_raw: str
    pid: str
    source: str
    line: int
    event_id: int = 0
    template: str = ''
    hour: int = 0
    day_of_week: int = 0
    window_id: int = 0


@dataclass
class TemplateStats:
    event_id: int
    template: str
    count: int
    frequency_pct: float
    first_seen: Optional[datetime]
    last_seen: Optional[datetime]
    unique_messages: int
    components: str
    duration_seconds: float = 0
    rate_per_hour: float = 0


@dataclass
class AnomalyWindow:
    timestamp: datetime
    count: int
    count_zscore: float
    unique_zscore: float
    global_zscore: float
    anomaly_type: str
    top_events: list = field(default_factory=list)
    interpretation: str = ''


@dataclass
class RepetitionBurst:
    timestamp: datetime
    event_id: int
    template: str = ''
    count_in_window: int = 0
    window_seconds: int = 10


@dataclass
class SemanticAnomaly:
    template_idx: int
    template: str
    distance: float
    severity: str


@dataclass
class ClusterSummary:
    cluster_id: int
    size: int
    percentage: float
    templates: list = field(default_factory=list)
    sample: str = ''


@dataclass
class Summary:
    total_lines: int
    unique_events: int
    top_event: str = ''
    top_event_count: int = 0
    top_event_pct: float = 0
    error_count: int = 0
    error_pct: float = 0
    warning_count: int = 0
    top10_coverage: float = 0
    rare_events_count: int = 0
    n_anomaly_windows: int = 0
    n_bursts: int = 0
    n_semantic_anomalies: int = 0


@dataclass
class AnalysisResult:
    source: str
    entries: pd.DataFrame = field(default_factory=pd.DataFrame)
    template_stats: list = field(default_factory=list)
    time_series: pd.DataFrame = field(default_factory=pd.DataFrame)
    anomaly_windows: list = field(default_factory=list)
    bursts: list = field(default_factory=list)
    semantic_anomalies: list = field(default_factory=list)
    level_dist: pd.DataFrame = field(default_factory=pd.DataFrame)
    cluster_summaries: list = field(default_factory=list)
    summary: Summary = field(default_factory=Summary)
