import pandas as pd
import numpy as np
from .base import Detector
from ..models.result import AnomalyWindow


class TemporalAnomalyDetector(Detector):
    def __init__(self, window_min=5, std_threshold=2.5):
        self.window_min = window_min
        self.std_threshold = std_threshold

    def detect(self, df, **kwargs):
        if df['timestamp'].isna().all():
            return []
        ts = (
            df.set_index('timestamp')
            .resample(f'{self.window_min}min')
            .agg(count=('message_raw', 'count'),
                 n_unique=('event_id', 'nunique'))
            .fillna(0)
        )
        if len(ts) < 5:
            return []
        rolling_w = min(10, max(3, len(ts) // 5))
        ts['count_ma'] = ts['count'].rolling(rolling_w, min_periods=1).mean()
        ts['count_std'] = ts['count'].rolling(rolling_w, min_periods=1).std().fillna(0)
        ts['count_zscore'] = (ts['count'] - ts['count_ma']) / (ts['count_std'] + 1e-8)
        ts['unique_ma'] = ts['n_unique'].rolling(rolling_w, min_periods=1).mean()
        ts['unique_std'] = ts['n_unique'].rolling(rolling_w, min_periods=1).std().fillna(0)
        ts['unique_zscore'] = (ts['n_unique'] - ts['unique_ma']) / (ts['unique_std'] + 1e-8)
        global_mean = ts['count'].mean()
        global_std = ts['count'].std()
        ts['global_zscore'] = ((ts['count'] - global_mean) / (global_std + 1e-8))
        is_anomaly = (
            (ts['count_zscore'].abs() > self.std_threshold) |
            (ts['unique_zscore'].abs() > self.std_threshold) |
            (ts['global_zscore'].abs() > self.std_threshold * 1.5)
        )
        results = []
        for ts_val, row in ts[is_anomaly].iterrows():
            window_start = ts_val
            window_end = ts_val + pd.Timedelta(minutes=self.window_min)
            window_df = df[(df['timestamp'] >= window_start) & (df['timestamp'] < window_end)]
            top_events = (
                window_df.groupby('event_id').size()
                .sort_values(ascending=False).head(3).to_dict()
            )
            event_templates = window_df[['event_id', 'template']].drop_duplicates()
            top_with_templates = {}
            for eid, cnt in top_events.items():
                tmpl = event_templates[event_templates['event_id'] == eid]['template'].values
                label = (tmpl[0][:40] if len(tmpl) > 0 else f'event_{eid}')
                top_with_templates[eid] = {'count': int(cnt), 'template': label}

            atype = self._classify(row)
            interpretation = self._interpret(atype, int(row['count']), top_with_templates)

            results.append(AnomalyWindow(
                timestamp=ts_val,
                count=int(row['count']),
                count_zscore=float(row['count_zscore']),
                unique_zscore=float(row['unique_zscore']),
                global_zscore=float(row['global_zscore']),
                anomaly_type=atype,
                top_events=list(top_with_templates.values()),
                interpretation=interpretation,
            ))
        return results

    def _classify(self, row):
        types = []
        for col, prefix in [('count_zscore', 'volume'), ('unique_zscore', 'diversity'), ('global_zscore', 'global')]:
            val = row.get(col, 0)
            if val > self.std_threshold:
                types.append(f'{prefix}_burst')
            elif val < -self.std_threshold:
                types.append(f'{prefix}_drop')
        return '+'.join(types) if types else 'unknown'

    @staticmethod
    def _interpret(atype, count, top_events):
        parts = []
        if 'volume_burst' in atype:
            parts.append(f'volume burst ({count} events in 5min)')
        if 'diversity_burst' in atype:
            parts.append('event diversity spike')
        if 'global_burst' in atype:
            parts.append('global outlier')
        if 'drop' in atype:
            parts.append('activity drop')
        desc = ' + '.join(parts) if parts else 'anomalous pattern'

        top_info = ''
        if top_events:
            top_list = list(top_events.values())[:2]
            top_info = '. Top: ' + ', '.join(
                f'"{e["template"]}" ({e["count"]}x)' for e in top_list
            )
        return desc + top_info
