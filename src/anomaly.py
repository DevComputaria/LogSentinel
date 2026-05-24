import numpy as np
import pandas as pd

def detect_temporal_anomalies(df, window_min=5, std_threshold=3):
    if df['timestamp'].isna().all():
        return pd.DataFrame()
    ts = (
        df.set_index('timestamp')
        .resample(f'{window_min}min')
        .agg(
            count=('message_raw', 'count'),
            n_unique=('event_id', 'nunique'),
        )
        .fillna(0)
    )
    if len(ts) < 5:
        return pd.DataFrame()
    rolling_w = min(10, max(3, len(ts) // 5))
    ts['count_ma'] = ts['count'].rolling(window=rolling_w, min_periods=1).mean()
    ts['count_std'] = ts['count'].rolling(window=rolling_w, min_periods=1).std().fillna(0)
    ts['count_zscore'] = (ts['count'] - ts['count_ma']) / (ts['count_std'] + 1e-8)

    ts['unique_ma'] = ts['n_unique'].rolling(window=rolling_w, min_periods=1).mean()
    ts['unique_std'] = ts['n_unique'].rolling(window=rolling_w, min_periods=1).std().fillna(0)
    ts['unique_zscore'] = (ts['n_unique'] - ts['unique_ma']) / (ts['unique_std'] + 1e-8)

    global_mean = ts['count'].mean()
    global_std = ts['count'].std()
    ts['global_zscore'] = ((ts['count'] - global_mean) / (global_std + 1e-8))

    is_anomaly = (
        (ts['count_zscore'].abs() > std_threshold) |
        (ts['unique_zscore'].abs() > std_threshold) |
        (ts['global_zscore'].abs() > std_threshold * 1.5)
    )
    anomalies = ts[is_anomaly].copy()
    anomalies['anomaly_type'] = anomalies.apply(
        lambda r: _classify_anomaly(r, std_threshold), axis=1
    )
    return anomalies.reset_index()

def _classify_anomaly(row, threshold):
    types = []
    for col, prefix in [('count_zscore', 'volume'), ('unique_zscore', 'diversity'), ('global_zscore', 'global')]:
        val = row.get(col, 0)
        if val > threshold:
            types.append(f'{prefix}_burst')
        elif val < -threshold:
            types.append(f'{prefix}_drop')
    return '+'.join(types) if types else 'unknown'

def detect_semantic_anomalies(embeddings, template_texts, distances, threshold=0.5):
    results = []
    for i, (dist, text) in enumerate(zip(distances, template_texts)):
        if dist > threshold and not np.isnan(dist):
            results.append({
                'template_idx': i,
                'template': text,
                'distance': float(dist),
                'severity': 'high' if dist > threshold * 1.5 else 'medium',
            })
    return sorted(results, key=lambda x: x['distance'], reverse=True)

def detect_repetition_bursts(df, min_repeats=5, window_seconds=10):
    if df['timestamp'].isna().all():
        return pd.DataFrame()
    df_sorted = df.sort_values('timestamp').reset_index(drop=True)
    bursts = []
    seen = set()
    window_start = df_sorted['timestamp'].iloc[0] if not df_sorted.empty else pd.Timestamp.min
    for i, row in df_sorted.iterrows():
        cutoff = row['timestamp'] - pd.Timedelta(seconds=window_seconds)
        window_start = max(window_start, cutoff)
        mask = (df_sorted['timestamp'] >= window_start) & (df_sorted['timestamp'] <= row['timestamp'])
        window = df_sorted[mask]
        event_counts = window.groupby('event_id').size()
        for eid, cnt in event_counts.items():
            if cnt >= min_repeats:
                key = (eid, row['timestamp'])
                if key not in seen:
                    seen.add(key)
                    bursts.append({
                        'timestamp': row['timestamp'],
                        'event_id': eid,
                        'count_in_window': int(cnt),
                        'window_seconds': window_seconds,
                    })
    if bursts:
        return pd.DataFrame(bursts).sort_values('timestamp')
    return pd.DataFrame()
