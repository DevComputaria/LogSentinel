import pandas as pd
import numpy as np
from collections import Counter

def top_problems(df, template_stats, top_n=10):
    top = template_stats.head(top_n).copy()
    top['problem_ratio'] = top['count'] / len(df) * 100
    return top

def level_distribution(df):
    dist = df['level'].value_counts().reset_index()
    dist.columns = ['level', 'count']
    dist['percentage'] = dist['count'] / dist['count'].sum() * 100
    return dist

def component_distribution(df, top_n=15):
    dist = df['component'].value_counts().head(top_n).reset_index()
    dist.columns = ['component', 'count']
    dist['percentage'] = dist['count'] / dist['count'].sum() * 100
    return dist

def hourly_distribution(df):
    if df['timestamp'].isna().all():
        return pd.DataFrame()
    df = df.dropna(subset=['timestamp'])
    dist = df.groupby('hour').size().reset_index(name='count')
    dist['percentage'] = dist['count'] / dist['count'].sum() * 100
    return dist

def pattern_summary(df, template_stats):
    total = len(df)
    unique_events = template_stats.shape[0]
    top_event = template_stats.iloc[0] if not template_stats.empty else None
    error_count = int((df['level'] == 'Error').sum())
    warning_count = int((df['level'] == 'Warning').sum())
    error_pct = error_count / total * 100 if total else 0
    top_pct = top_event['frequency_pct'] if top_event is not None else 0

    coverage_10 = template_stats.head(10)['count'].sum() / total * 100 if total else 0
    n_rare = (template_stats['frequency_pct'] < 1).sum()

    return {
        'total_lines': total,
        'unique_events': unique_events,
        'top_event': top_event['template'] if top_event is not None else '',
        'top_event_count': int(top_event['count']) if top_event is not None else 0,
        'top_event_pct': round(top_pct, 1),
        'error_count': error_count,
        'error_pct': round(error_pct, 1),
        'warning_count': warning_count,
        'top10_coverage': round(coverage_10, 1),
        'rare_events_count': n_rare,
    }

def generate_summary_text(summary, template_stats, time_series, anomalies, bursts, semantic_anomalies, level_dist, cluster_summaries, source):
    header = f"# Log Analysis Report — {source}\n\n"
    header += f"**Total lines:** {summary['total_lines']} | "
    header += f"**Unique events:** {summary['unique_events']} | "
    header += f"**Errors:** {summary['error_count']} ({summary['error_pct']}%) | "
    header += f"**Warnings:** {summary['warning_count']}\n\n"

    dist_section = "## Level Distribution\n\n"
    for _, row in level_dist.iterrows():
        dist_section += f"- **{row['level']}**: {int(row['count'])} ({row['percentage']:.1f}%)\n"
    dist_section += "\n"

    top_section = f"## Top 10 Most Frequent Events\n\n"
    top_section += "| # | Event | Count | % Total | First Seen | Last Seen |\n"
    top_section += "|---|---|---|---|---|---|\n"
    for i, (_, row) in enumerate(template_stats.head(10).iterrows(), 1):
        first = str(row['first_seen'])[:19] if pd.notna(row['first_seen']) else '-'
        last = str(row['last_seen'])[:19] if pd.notna(row['last_seen']) else '-'
        top_section += f"| {i} | {row['template'][:80]} | {int(row['count'])} | {row['frequency_pct']:.1f}% | {first} | {last} |\n"
    top_section += "\n"

    cluster_section = "## Semantic Clusters\n\n"
    for cs in cluster_summaries[:5]:
        cluster_section += f"- **Cluster {cs['cluster_id']}** ({cs['size']} templates, {cs['percentage']:.1f}%): {cs['sample'][:80]}\n"
    cluster_section += "\n"

    anomaly_section = "## Temporal Anomalies (Bursts)\n\n"
    if not anomalies.empty:
        anomaly_section += f"Detected **{len(anomalies)}** anomalous windows:\n\n"
        for _, row in anomalies.head(10).iterrows():
            ts = str(row['timestamp'])[:19]
            anomaly_section += f"- **{ts}**: count={int(row['count'])}, z-score={row['count_zscore']:.1f}, type={row['anomaly_type']}\n"
    else:
        anomaly_section += "No significant temporal anomalies detected.\n"
    anomaly_section += "\n"

    burst_section = "## Repetition Bursts\n\n"
    if not bursts.empty:
        burst_section += f"Detected **{len(bursts)}** repetition bursts:\n\n"
        for _, row in bursts.head(10).iterrows():
            ts = str(row['timestamp'])[:19]
            burst_section += f"- **{ts}**: `{row['event_id']}` repeated {int(row['count_in_window'])}x in {int(row['window_seconds'])}s\n"
    else:
        burst_section += "No repetition bursts detected.\n"
    burst_section += "\n"

    sem_section = "## Semantic Anomalies\n\n"
    if semantic_anomalies:
        sem_section += f"Detected **{len(semantic_anomalies)}** semantically anomalous templates:\n\n"
        for sa in semantic_anomalies[:10]:
            sem_section += f"- **{sa['template'][:100]}** (distance={sa['distance']:.3f}, severity={sa['severity']})\n"
    else:
        sem_section += "No semantic anomalies detected.\n"
    sem_section += "\n"

    return header + dist_section + top_section + cluster_section + anomaly_section + burst_section + sem_section
