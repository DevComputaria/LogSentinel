import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
import pandas as pd
import numpy as np
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

def generate_html(df, template_stats, time_series, anomalies, bursts, semantic_anomalies,
                  level_dist, cluster_summaries, summary, source):
    fig = make_subplots(
        rows=4, cols=2,
        subplot_titles=(
            'Event Timeline (per 5min)',
            'Level Distribution',
            'Top 10 Events by Frequency',
            'Hourly Distribution',
            'Temporal Anomaly Z-Score',
            'Component Distribution',
            'Semantic Clusters',
            'Template Event Count (log scale)'
        ),
        vertical_spacing=0.08,
        horizontal_spacing=0.1,
    )

    if not time_series.empty:
        fig.add_trace(
            go.Scatter(x=time_series['timestamp'], y=time_series['total'],
                       mode='lines', name='Total Events',
                       line=dict(color='#636efa', width=1.5)),
            row=1, col=1
        )
        if 'error_count' in time_series.columns:
            fig.add_trace(
                go.Scatter(x=time_series['timestamp'], y=time_series['error_count'],
                           mode='lines', name='Errors',
                           line=dict(color='#ef553b', width=1)),
                row=1, col=1
            )

    colors_level = {'Info': '#636efa', 'Warning': '#ffa15a', 'Error': '#ef553b'}
    for _, row in level_dist.iterrows():
        fig.add_trace(
            go.Bar(x=[row['level']], y=[row['count']],
                   name=row['level'],
                   marker_color=colors_level.get(row['level'], '#636efa'),
                   showlegend=False),
            row=1, col=2
        )

    top10 = template_stats.head(10)
    fig.add_trace(
        go.Bar(x=top10['template'].str[:50], y=top10['count'],
               name='Frequency', marker_color='#636efa',
               text=top10['frequency_pct'].round(1),
               textposition='outside'),
        row=2, col=1
    )

    if not df['timestamp'].isna().all():
        hourly = df.groupby('hour').size().reset_index(name='count')
        fig.add_trace(
            go.Bar(x=hourly['hour'], y=hourly['count'],
                   name='Hourly', marker_color='#00cc96',
                   showlegend=False),
            row=2, col=2
        )

    if not anomalies.empty:
        fig.add_trace(
            go.Scatter(x=anomalies['timestamp'], y=anomalies['count_zscore'],
                       mode='markers', name='Anomalies',
                       marker=dict(color='#ef553b', size=6),
                       text=anomalies['anomaly_type']),
            row=3, col=1
        )

    comp_dist = df['component'].value_counts().head(10).reset_index()
    comp_dist.columns = ['component', 'count']
    fig.add_trace(
        go.Bar(x=comp_dist['component'], y=comp_dist['count'],
               name='Components', marker_color='#ab63fa',
               showlegend=False),
        row=3, col=2
    )

    if cluster_summaries:
        cluster_sizes = [c['size'] for c in cluster_summaries]
        cluster_names = [f"C{c['cluster_id']}: {c['sample'][:30]}" for c in cluster_summaries]
        fig.add_trace(
            go.Bar(x=cluster_names, y=cluster_sizes,
                   name='Clusters', marker_color='#ffa15a',
                   showlegend=False),
            row=4, col=1
        )

    event_counts = template_stats['count'].head(20).values
    fig.add_trace(
        go.Bar(x=list(range(len(event_counts))), y=event_counts,
               name='Event Counts', marker_color='#19d3f3',
               showlegend=False),
        row=4, col=2
    )
    fig.update_yaxes(type="log", row=4, col=2)

    fig.update_layout(
        height=1000,
        title_text=f'Log Analysis Dashboard — {source}',
        template='plotly_white',
        showlegend=True,
        hovermode='x unified',
        font=dict(size=10),
    )
    fig.update_xaxes(tickangle=45)

    html = f"""
    <html><head><meta charset="utf-8"/>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #f0f2f5; color: #1a1a2e; padding: 24px; }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        h1 {{ font-size: 26px; font-weight: 600; color: #1a1a2e; margin-bottom: 20px; }}
        .cards {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 24px; }}
        .card {{ background: #fff; padding: 18px 24px; border-radius: 10px;
                 box-shadow: 0 1px 3px rgba(0,0,0,0.08); min-width: 140px; text-align: center;
                 flex: 1; }}
        .card-value {{ font-size: 28px; font-weight: 700; }}
        .card-label {{ font-size: 12px; color: #666; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; }}
        .card.total .card-value {{ color: #636efa; }}
        .card.errors .card-value {{ color: #ef553b; }}
        .card.warnings .card-value {{ color: #ffa15a; }}
        .card.anomalies .card-value {{ color: #ab63fa; }}
        .card.coverage .card-value {{ color: #00cc96; }}
        .card.events .card-value {{ color: #636efa; }}
        .chart {{ background: #fff; border-radius: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);
                  padding: 8px; margin-bottom: 16px; }}
    </style>
    </head><body>
    <div class="container">
    <h1>Log Analysis — {source}</h1>
    <div class="cards">
        <div class="card total"><div class="card-value">{summary['total_lines']:,}</div><div class="card-label">Total Lines</div></div>
        <div class="card events"><div class="card-value">{summary['unique_events']}</div><div class="card-label">Unique Events</div></div>
        <div class="card errors"><div class="card-value">{summary['error_count']:,} ({summary['error_pct']}%)</div><div class="card-label">Errors</div></div>
        <div class="card warnings"><div class="card-value">{summary['warning_count']:,}</div><div class="card-label">Warnings</div></div>
        <div class="card coverage"><div class="card-value">{summary['top10_coverage']}%</div><div class="card-label">Top-10 Coverage</div></div>
        <div class="card anomalies"><div class="card-value">{len(anomalies) if not anomalies.empty else 0}</div><div class="card-label">Anomaly Windows</div></div>
    </div>
    <div class="chart">
    """
    html += fig.to_html(include_plotlyjs=False, full_html=False)
    html += "</div></body></html>"
    return html

def generate_md(summary, template_stats, time_series, anomalies, bursts, semantic_anomalies,
                 level_dist, cluster_summaries, source, df):
    return _generate_md_inline(
        summary, template_stats, time_series, anomalies, bursts,
        semantic_anomalies, level_dist, cluster_summaries, source
    )

def _generate_md_inline(summary, template_stats, time_series, anomalies, bursts,
                         semantic_anomalies, level_dist, cluster_summaries, source):
    lines = [f"# Log Analysis Report — {source}", ""]
    lines.append(f"- **Total lines:** {summary['total_lines']:,}")
    lines.append(f"- **Unique events:** {summary['unique_events']}")
    lines.append(f"- **Errors:** {summary['error_count']} ({summary['error_pct']}%)")
    lines.append(f"- **Warnings:** {summary['warning_count']}")
    lines.append(f"- **Top-10 coverage:** {summary['top10_coverage']}%")
    lines.append("")
    lines.append("## Level Distribution")
    lines.append("")
    lines.append("| Level | Count | % |")
    lines.append("|---|---|---|")
    for _, row in level_dist.iterrows():
        lines.append(f"| {row['level']} | {int(row['count']):,} | {row['percentage']:.1f}% |")
    lines.append("")
    lines.append("## Top 10 Events")
    lines.append("")
    lines.append("| # | Template | Count | % |")
    lines.append("|---|---|---|---|")
    for i, (_, row) in enumerate(template_stats.head(10).iterrows(), 1):
        t = row['template'][:60]
        lines.append(f"| {i} | {t} | {int(row['count']):,} | {row['frequency_pct']:.1f}% |")
    lines.append("")
    lines.append("## Temporal Anomalies")
    lines.append("")
    if not anomalies.empty:
        lines.append(f"Detected **{len(anomalies)}** anomalous windows. Top 10:")
        lines.append("")
        lines.append("| Timestamp | Count | Z-Score | Type |")
        lines.append("|---|---|---|---|")
        for _, row in anomalies.head(10).iterrows():
            lines.append(f"| {str(row['timestamp'])[:19]} | {int(row['count']):,} | "
                         f"{row['count_zscore']:.1f} | {row['anomaly_type']} |")
    else:
        lines.append("No significant temporal anomalies detected.")
    lines.append("")
    lines.append("## Repetition Bursts")
    lines.append("")
    if not bursts.empty:
        w = int(bursts['window_seconds'].iloc[0]) if not bursts.empty else 10
        lines.append(f"Detected **{len(bursts)}** repetition bursts ({w}s windows). Top 10:")
        lines.append("")
        lines.append("| Timestamp | Event ID | Repeats |")
        lines.append("|---|---|---|")
        for _, row in bursts.head(10).iterrows():
            lines.append(f"| {str(row['timestamp'])[:19]} | {row['event_id']} | "
                         f"{int(row['count_in_window'])}x |")
    else:
        lines.append("No repetition bursts detected.")
    lines.append("")
    lines.append("## Semantic Anomalies")
    lines.append("")
    if semantic_anomalies:
        lines.append(f"Detected **{len(semantic_anomalies)}** semantically anomalous templates. Top 10:")
        lines.append("")
        lines.append("| Template | Distance | Severity |")
        lines.append("|---|---|---|")
        for sa in semantic_anomalies[:10]:
            lines.append(f"| {sa['template'][:60]} | {sa['distance']:.3f} | {sa['severity']} |")
    else:
        lines.append("No semantic anomalies detected.")
    lines.append("")
    lines.append("## Semantic Clusters")
    lines.append("")
    for cs in cluster_summaries[:5]:
        lines.append(f"- **Cluster {cs['cluster_id']}**: {cs['size']} templates ({cs['percentage']:.1f}%) — "
                     f"{cs['sample'][:50]}")
    return "\n".join(lines)

def _shorten_type(t):
    return (t.replace('_burst', '')
            .replace('_drop', '\u2193')
            .replace('+', '/'))[:20]

def generate_cli(df, template_stats, anomalies, bursts, semantic_anomalies,
                  level_dist, cluster_summaries, summary, source):
    console = Console()

    console.print(Panel(f"[bold blue]Log Analysis Report — {source}[/]", expand=False))
    console.print(f"[bold]Total Lines:[/] {summary['total_lines']:,} | "
                  f"[bold]Events:[/] {summary['unique_events']} | "
                  f"[red]Errors:[/] {summary['error_count']} ({summary['error_pct']}%) | "
                  f"[yellow]Warnings:[/] {summary['warning_count']}")
    print()

    table = Table(title="Level Distribution", box=box.SIMPLE)
    table.add_column("Level", style="bold")
    table.add_column("Count", justify="right")
    table.add_column("%", justify="right")
    for _, row in level_dist.iterrows():
        style = {'Error': 'red', 'Warning': 'yellow', 'Info': 'blue'}.get(row['level'], '')
        table.add_row(row['level'], str(int(row['count'])), f"{row['percentage']:.1f}%",
                      style=style)
    console.print(table)
    print()

    table2 = Table(title=f"Top 10 Events ({summary['top10_coverage']}% of total)", box=box.SIMPLE)
    table2.add_column("#", justify="right")
    table2.add_column("Event Template", style="bold", width=60)
    table2.add_column("Count", justify="right")
    table2.add_column("%", justify="right")
    for i, (_, row) in enumerate(template_stats.head(10).iterrows(), 1):
        t = row['template'][:60] + '..' if len(row['template']) > 60 else row['template']
        table2.add_row(str(i), t, f"{int(row['count']):,}",
                       f"{row['frequency_pct']:.1f}%")
    console.print(table2)
    print()

    if not anomalies.empty:
        console.print(f"[red]Temporal Anomalies: {len(anomalies)} windows[/]")
        table3 = Table(box=box.SIMPLE)
        table3.add_column("Timestamp", width=18)
        table3.add_column("Count", justify="right")
        table3.add_column("Z-Score", justify="right")
        table3.add_column("Type", width=18)
        for _, row in anomalies.head(10).iterrows():
            table3.add_row(str(row['timestamp'])[:19], str(int(row['count'])),
                          f"{row['count_zscore']:.1f}", _shorten_type(row['anomaly_type']))
        console.print(table3)
        print()

    if not bursts.empty:
        console.print(f"[yellow]Repetition Bursts: {len(bursts)} detected[/]")
        table4 = Table(box=box.SIMPLE)
        table4.add_column("Timestamp", width=18)
        table4.add_column("Event ID")
        table4.add_column("Repeats/{}s".format(
            int(bursts['window_seconds'].iloc[0]) if not bursts.empty else 10),
            justify="right")
        for _, row in bursts.head(10).iterrows():
            table4.add_row(str(row['timestamp'])[:19], str(row['event_id']),
                          str(int(row['count_in_window'])))
        console.print(table4)
        print()

    if semantic_anomalies:
        console.print(f"[red]Semantic Anomalies: {len(semantic_anomalies)} templates[/]")
        table5 = Table(box=box.SIMPLE)
        table5.add_column("Template", width=60)
        table5.add_column("Dist.", justify="right")
        table5.add_column("Sev.")
        for sa in semantic_anomalies[:10]:
            t = sa['template'][:60] + '..' if len(sa['template']) > 60 else sa['template']
            table5.add_row(t, f"{sa['distance']:.2f}", sa['severity'][0].upper())
        console.print(table5)
        print()
