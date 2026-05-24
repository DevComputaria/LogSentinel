from .base import ReportBuilder
from ..models.result import AnalysisResult
import plotly.graph_objects as go
from plotly.subplots import make_subplots


class HtmlReportBuilder(ReportBuilder):
    def build(self, result):
        fig = make_subplots(
            rows=4, cols=2,
            subplot_titles=(
                'Event Timeline', 'Level Distribution',
                'Top 10 Events', 'Hourly Distribution',
                'Anomaly Z-Scores', 'Component Distribution',
                'Semantic Clusters', 'Event Counts (log scale)'
            ),
            vertical_spacing=0.08, horizontal_spacing=0.1,
        )

        ts = result.time_series
        if not ts.empty:
            fig.add_trace(go.Scatter(x=ts['timestamp'], y=ts['total'], mode='lines',
                          name='Total', line=dict(color='#636efa')), row=1, col=1)
            if 'error_count' in ts.columns:
                fig.add_trace(go.Scatter(x=ts['timestamp'], y=ts['error_count'], mode='lines',
                              name='Errors', line=dict(color='#ef553b')), row=1, col=1)

        colors = {'Info': '#636efa', 'Warning': '#ffa15a', 'Error': '#ef553b'}
        for _, row in result.level_dist.iterrows():
            fig.add_trace(go.Bar(x=[row['level']], y=[row['count']], name=row['level'],
                          marker_color=colors.get(row['level'], '#636efa'), showlegend=False),
                          row=1, col=2)

        top10 = result.template_stats[:10]
        fig.add_trace(go.Bar(x=[t['template'][:40] for t in top10], y=[t['count'] for t in top10],
                      name='Top 10', marker_color='#636efa'), row=2, col=1)

        df = result.entries
        if not df['timestamp'].isna().all():
            hourly = df.groupby('hour').size().reset_index(name='count')
            fig.add_trace(go.Bar(x=hourly['hour'], y=hourly['count'], name='Hourly',
                          marker_color='#00cc96', showlegend=False), row=2, col=2)

        if result.anomaly_windows:
            aw = result.anomaly_windows
            fig.add_trace(go.Scatter(x=[a.timestamp for a in aw], y=[a.count_zscore for a in aw],
                          mode='markers', name='Anomalies',
                          marker=dict(color='#ef553b', size=6),
                          text=[a.interpretation for a in aw]), row=3, col=1)

        comp_dist = df['component'].value_counts().head(10).reset_index()
        comp_dist.columns = ['component', 'count']
        fig.add_trace(go.Bar(x=comp_dist['component'], y=comp_dist['count'],
                      name='Components', marker_color='#ab63fa', showlegend=False), row=3, col=2)

        if result.cluster_summaries:
            sizes = [c.size for c in result.cluster_summaries]
            names = [f"C{c.cluster_id}" for c in result.cluster_summaries]
            fig.add_trace(go.Bar(x=names, y=sizes, name='Clusters',
                          marker_color='#ffa15a', showlegend=False), row=4, col=1)

        event_counts = [t['count'] for t in result.template_stats[:20]]
        fig.add_trace(go.Bar(x=list(range(len(event_counts))), y=event_counts,
                      name='Counts', marker_color='#19d3f3', showlegend=False), row=4, col=2)
        fig.update_yaxes(type="log", row=4, col=2)

        fig.update_layout(height=1000,
                          title_text=f'Log Analysis Dashboard — {result.source}',
                          template='plotly_white', font=dict(size=10))
        fig.update_xaxes(tickangle=45)

        s = result.summary
        cards_rows = []
        metrics = [
            ('total', s.total_lines, 'Total Lines'),
            ('events', s.unique_events, 'Unique Events'),
            ('errors', f'{s.error_count} ({s.error_pct}%)', 'Errors'),
            ('warnings', s.warning_count, 'Warnings'),
            ('coverage', f'{s.top10_coverage}%', 'Top-10 Coverage'),
            ('anomalies', s.n_anomaly_windows, 'Anomaly Windows'),
        ]
        for cls, val, label in metrics:
            if isinstance(val, int):
                val_str = f'{val:,}'
            else:
                val_str = str(val)
            cards_rows.append(
                f'<div class="card {cls}"><div class="card-value">{val_str}</div>'
                f'<div class="card-label">{label}</div></div>'
            )

        anomaly_rows = ''
        if result.anomaly_windows:
            anomaly_rows = '<h2>Anomaly Windows Detail</h2><table><tr><th>Timestamp</th><th>Count</th><th>Z-Score</th><th>Interpretation</th></tr>'
            for aw in result.anomaly_windows[:20]:
                anomaly_rows += f'<tr><td>{str(aw.timestamp)[:19]}</td><td>{aw.count}</td><td>{aw.count_zscore:.1f}</td><td>{aw.interpretation}</td></tr>'
            anomaly_rows += '</table>'

        html = f'''
        <html><head><meta charset="utf-8"/>
        <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
        <style>
            * {{ margin:0; padding:0; box-sizing:border-box; }}
            body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
                    background:#f0f2f5; color:#1a1a2e; padding:24px; }}
            .container {{ max-width:1400px; margin:0 auto; }}
            h1 {{ font-size:26px; font-weight:600; margin-bottom:20px; }}
            h2 {{ font-size:18px; font-weight:600; margin:24px 0 12px; }}
            .cards {{ display:flex; gap:16px; flex-wrap:wrap; margin-bottom:24px; }}
            .card {{ background:#fff; padding:18px 24px; border-radius:10px;
                     box-shadow:0 1px 3px rgba(0,0,0,0.08); min-width:140px; text-align:center; flex:1; }}
            .card-value {{ font-size:28px; font-weight:700; }}
            .card-label {{ font-size:12px; color:#666; margin-top:4px; text-transform:uppercase; letter-spacing:.5px; }}
            .card.total .card-value {{ color:#636efa; }}
            .card.errors .card-value {{ color:#ef553b; }}
            .card.warnings .card-value {{ color:#ffa15a; }}
            .card.anomalies .card-value {{ color:#ab63fa; }}
            .card.coverage .card-value {{ color:#00cc96; }}
            .card.events .card-value {{ color:#636efa; }}
            .chart {{ background:#fff; border-radius:10px; box-shadow:0 1px 3px rgba(0,0,0,0.08); padding:8px; margin-bottom:16px; }}
            table {{ width:100%; border-collapse:collapse; background:#fff; border-radius:10px; overflow:hidden;
                     box-shadow:0 1px 3px rgba(0,0,0,0.08); margin-bottom:24px; }}
            th {{ background:#636efa; color:#fff; padding:10px 14px; text-align:left; font-size:13px; }}
            td {{ padding:8px 14px; border-bottom:1px solid #eee; font-size:13px; }}
            tr:hover td {{ background:#f5f5ff; }}
        </style>
        </head><body>
        <div class="container">
        <h1>Log Analysis — {result.source}</h1>
        <div class="cards">{"".join(cards_rows)}</div>
        {anomaly_rows}
        <div class="chart">
        '''
        html += fig.to_html(include_plotlyjs=False, full_html=False)
        html += '</div></div></body></html>'
        return html

    def render(self, result, output_path):
        content = self.build(result)
        with open(output_path, 'w') as f:
            f.write(content)
