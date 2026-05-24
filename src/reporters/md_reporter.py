from .base import ReportBuilder
from ..models.result import AnalysisResult


class MdReportBuilder(ReportBuilder):
    def build(self, result):
        s = result.summary
        lines = [f"# Log Analysis Report — {result.source}", ""]
        lines.append(f"- **Total lines:** {s.total_lines:,}")
        lines.append(f"- **Unique events:** {s.unique_events}")
        lines.append(f"- **Errors:** {s.error_count} ({s.error_pct}%)")
        lines.append(f"- **Warnings:** {s.warning_count}")
        lines.append(f"- **Top-10 coverage:** {s.top10_coverage}%")
        lines.append(f"- **Anomaly windows:** {s.n_anomaly_windows}")
        lines.append(f"- **Repetition bursts:** {s.n_bursts}")
        lines.append(f"- **Semantic anomaly templates:** {s.n_semantic_anomalies}")
        lines.append("")

        lines.append("## Level Distribution")
        lines.append("")
        lines.append("| Level | Count | % |")
        lines.append("|---|---|---|")
        for _, row in result.level_dist.iterrows():
            lines.append(f"| {row['level']} | {int(row['count']):,} | {row['percentage']:.1f}% |")
        lines.append("")

        lines.append("## Top 10 Events")
        lines.append("")
        lines.append("| # | Template | Count | % |")
        lines.append("|---|---|---|---|")
        for i, ts in enumerate(result.template_stats[:10], 1):
            t = ts['template'][:60]
            lines.append(f"| {i} | {t} | {ts['count']:,} | {ts['frequency_pct']:.1f}% |")
        lines.append("")

        lines.append("## Temporal Anomaly Windows")
        lines.append("")
        if result.anomaly_windows:
            lines.append(f"**{len(result.anomaly_windows)}** anomalous windows detected. Top 10:")
            lines.append("")
            lines.append("| Timestamp | Count | Z-Score | Interpretation |")
            lines.append("|---|---|---|---|")
            for aw in result.anomaly_windows[:10]:
                lines.append(f"| {str(aw.timestamp)[:19]} | {aw.count} | {aw.count_zscore:.1f} | {aw.interpretation} |")
        else:
            lines.append("No temporal anomalies detected.")
        lines.append("")

        lines.append("## Repetition Bursts")
        lines.append("")
        if result.bursts:
            w = result.bursts[0].window_seconds
            lines.append(f"**{len(result.bursts)}** repetition bursts ({w}s windows). Top 10:")
            lines.append("")
            lines.append("| Timestamp | Event | Repeats |")
            lines.append("|---|---|---|")
            for b in result.bursts[:10]:
                tmpl = b.template[:50]
                lines.append(f"| {str(b.timestamp)[:19]} | {tmpl} | {b.count_in_window}x |")
        else:
            lines.append("No repetition bursts detected.")
        lines.append("")

        lines.append("## Semantic Anomalies")
        lines.append("")
        if result.semantic_anomalies:
            lines.append(f"**{len(result.semantic_anomalies)}** semantically anomalous templates. Top 10:")
            lines.append("")
            lines.append("| Template | Distance | Severity |")
            lines.append("|---|---|---|")
            for sa in result.semantic_anomalies[:10]:
                lines.append(f"| {sa.template[:60]} | {sa.distance:.3f} | {sa.severity} |")
        else:
            lines.append("No semantic anomalies detected.")
        lines.append("")

        lines.append("## Semantic Clusters")
        lines.append("")
        for cs in result.cluster_summaries[:5]:
            lines.append(f"- **Cluster {cs.cluster_id}**: {cs.size} templates ({cs.percentage:.1f}%) — {cs.sample[:50]}")
        lines.append("")

        return "\n".join(lines)

    def render(self, result, output_path):
        content = self.build(result)
        with open(output_path, 'w') as f:
            f.write(content)
