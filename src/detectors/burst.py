import pandas as pd
import numpy as np
from .base import Detector
from ..models.result import RepetitionBurst


class BurstDetector(Detector):
    def __init__(self, min_repeats=5, window_seconds=10):
        self.min_repeats = min_repeats
        self.window_seconds = window_seconds

    def detect(self, df, **kwargs):
        if df['timestamp'].isna().all():
            return []
        df_sorted = df.sort_values('timestamp').reset_index(drop=True)
        template_map = df[['event_id', 'template']].drop_duplicates()
        template_map = template_map.set_index('event_id')['template'].to_dict()
        bursts = []
        seen = set()
        if df_sorted.empty:
            return []
        window_start = df_sorted['timestamp'].iloc[0]
        for i, row in df_sorted.iterrows():
            cutoff = row['timestamp'] - pd.Timedelta(seconds=self.window_seconds)
            window_start = max(window_start, cutoff)
            mask = (df_sorted['timestamp'] >= window_start) & (df_sorted['timestamp'] <= row['timestamp'])
            window = df_sorted[mask]
            event_counts = window.groupby('event_id').size()
            for eid, cnt in event_counts.items():
                if cnt >= self.min_repeats:
                    key = (eid, row['timestamp'])
                    if key not in seen:
                        seen.add(key)
                        bursts.append(RepetitionBurst(
                            timestamp=row['timestamp'],
                            event_id=int(eid),
                            template=template_map.get(eid, ''),
                            count_in_window=int(cnt),
                            window_seconds=self.window_seconds,
                        ))
        return sorted(bursts, key=lambda b: b.timestamp)
