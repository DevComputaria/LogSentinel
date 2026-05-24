from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from .base import ReportBuilder
from ..models.result import AnalysisResult


class CliReportBuilder(ReportBuilder):
    def build(self, result):
        console = Console()
        s = result.summary
        lines = []

        console.print(Panel(f"[bold blue]Log Analysis Report — {result.source}[/]", expand=False))
        console.print(f"[bold]Total Lines:[/] {s.total_lines:,} | "
                      f"[bold]Events:[/] {s.unique_events} | "
                      f"[red]Errors:[/] {s.error_count} ({s.error_pct}%) | "
                      f"[yellow]Warnings:[/] {s.warning_count}")
        print()

        table = Table(title="Level Distribution", box=box.SIMPLE)
        table.add_column("Level", style="bold")
        table.add_column("Count", justify="right")
        table.add_column("%", justify="right")
        for _, row in result.level_dist.iterrows():
            style = {'Error': 'red', 'Warning': 'yellow', 'Info': 'blue'}.get(row['level'], '')
            table.add_row(row['level'], str(int(row['count'])), f"{row['percentage']:.1f}%", style=style)
        console.print(table)
        print()

        table2 = Table(title=f"Top 10 Events ({s.top10_coverage}% of total)", box=box.SIMPLE)
        table2.add_column("#", justify="right")
        table2.add_column("Event Template", style="bold", width=60)
        table2.add_column("Count", justify="right")
        table2.add_column("%", justify="right")
        for i, ts in enumerate(result.template_stats[:10], 1):
            t = (ts['template'][:60] + '..') if len(ts['template']) > 60 else ts['template']
            table2.add_row(str(i), t, f"{ts['count']:,}", f"{ts['frequency_pct']:.1f}%")
        console.print(table2)
        print()

        if result.anomaly_windows:
            console.print(f"[red]Temporal Anomalies: {len(result.anomaly_windows)} windows[/]")
            table3 = Table(box=box.SIMPLE)
            table3.add_column("Timestamp", width=18)
            table3.add_column("Count", justify="right")
            table3.add_column("Z-Score", justify="right")
            table3.add_column("Interpretation", width=60)
            for aw in result.anomaly_windows[:10]:
                table3.add_row(
                    str(aw.timestamp)[:19], str(aw.count),
                    f"{aw.count_zscore:.1f}", aw.interpretation
                )
            console.print(table3)
            print()

        if result.bursts:
            console.print(f"[yellow]Repetition Bursts: {len(result.bursts)} detected[/]")
            table4 = Table(box=box.SIMPLE)
            table4.add_column("Timestamp", width=18)
            table4.add_column("Template", width=50)
            table4.add_column(f"Repeats/{result.bursts[0].window_seconds}s", justify="right")
            for b in result.bursts[:10]:
                tmpl = b.template[:50] + '..' if len(b.template) > 50 else b.template
                table4.add_row(str(b.timestamp)[:19], tmpl, str(b.count_in_window))
            console.print(table4)
            print()

        if result.semantic_anomalies:
            console.print(f"[red]Semantic Anomalies: {len(result.semantic_anomalies)} templates[/]")
            table5 = Table(box=box.SIMPLE)
            table5.add_column("Template", width=60)
            table5.add_column("Dist.", justify="right")
            table5.add_column("Sev.")
            for sa in result.semantic_anomalies[:10]:
                t = sa.template[:60] + '..' if len(sa.template) > 60 else sa.template
                table5.add_row(t, f"{sa.distance:.2f}", sa.severity[0].upper())
            console.print(table5)
            print()

        return ''

    def render(self, result, output_path):
        self.build(result)
