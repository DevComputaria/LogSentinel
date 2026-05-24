import numpy as np
import pandas as pd

def extract_temporal_features(df, window_min=5):
    if df['timestamp'].isna().all():
        df['hour'] = 0
        df['day_of_week'] = 0
        df['window_id'] = 0
        return df

    df = df.copy()
    df['hour'] = df['timestamp'].dt.hour.fillna(0).astype(int)
    df['day_of_week'] = df['timestamp'].dt.dayofweek.fillna(0).astype(int)
    df['window_id'] = (
        df['timestamp'].dt.floor(f'{window_min}min')
        .rank(method='dense').fillna(0).astype(int)
    )
    return df

def compute_template_features(df):
    template_map = df.groupby('event_id')['template'].first()
    stats = df.groupby('event_id').agg(
        count=('message_raw', 'count'),
        first_seen=('timestamp', 'min'),
        last_seen=('timestamp', 'max'),
        unique_messages=('message_raw', 'nunique'),
        components=('component', lambda x: x.mode().iloc[0] if not x.mode().empty else '')
    ).reset_index()
    stats['template'] = stats['event_id'].map(template_map).fillna('')
    stats['duration'] = (
        (stats['last_seen'] - stats['first_seen']).dt.total_seconds().fillna(0)
    )
    stats['rate_per_hour'] = stats['count'] / (stats['duration'] / 3600 + 1)
    stats['frequency_pct'] = stats['count'] / stats['count'].sum() * 100
    return stats.sort_values('count', ascending=False)

def compute_time_series(df, freq='5min'):
    if df['timestamp'].isna().all():
        return pd.DataFrame()
    ts = (
        df.set_index('timestamp')
        .resample(freq)
        .agg(
            total=('message_raw', 'count'),
            unique_templates=('event_id', 'nunique'),
            error_count=('level', lambda x: (x == 'Error').sum()),
            warning_count=('level', lambda x: (x == 'Warning').sum()),
        )
        .fillna(0)
        .reset_index()
    )
    return ts

def compute_bursts(df, window_min=5, std_threshold=3):
    if df['timestamp'].isna().all():
        return pd.DataFrame()
    ts = (
        df.set_index('timestamp')
        .resample(f'{window_min}min')
        .size()
        .to_frame('count')
    )
    ts['ma'] = ts['count'].rolling(window=10, min_periods=1).mean()
    ts['std'] = ts['count'].rolling(window=10, min_periods=1).std().fillna(0)
    ts['zscore'] = ((ts['count'] - ts['ma']) / (ts['std'] + 1e-8))
    bursts = ts[ts['zscore'] > std_threshold].copy()
    return bursts.reset_index()
