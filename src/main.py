#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.analyzer import LogAnalyzer
from src.reporters.cli_reporter import CliReportBuilder
from src.reporters.html_reporter import HtmlReportBuilder
from src.reporters.md_reporter import MdReportBuilder


def main():
    parser = argparse.ArgumentParser(
        description='LogSentinel — ML-powered log analysis tool'
    )
    parser.add_argument('log', type=str, help='Path to log file')
    parser.add_argument('--output', '-o', type=str, default='output',
                        help='Output directory (default: output)')
    parser.add_argument('--format', '-f', type=str, nargs='+',
                        choices=['html', 'md', 'cli', 'all'],
                        default=['cli'], help='Output format(s)')
    parser.add_argument('--no-embeddings', action='store_true',
                        help='Skip embedding computation (faster)')
    args = parser.parse_args()

    log_path = Path(args.log)
    if not log_path.exists():
        print(f'Error: {log_path} not found', file=sys.stderr)
        sys.exit(1)

    print(f'Analyzing {log_path}...')
    analyzer = LogAnalyzer()
    result = analyzer.analyze(str(log_path), no_embeddings=args.no_embeddings)
    print('Done.')

    formats = set()
    for f in args.format:
        if f == 'all':
            formats.update(['html', 'md', 'cli'])
        else:
            formats.add(f)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    builders = {
        'cli': (CliReportBuilder(), None),
        'md': (MdReportBuilder(), output_dir / f'{log_path.stem}_report.md'),
        'html': (HtmlReportBuilder(), output_dir / f'{log_path.stem}_dashboard.html'),
    }

    for fmt in formats:
        if fmt not in builders:
            continue
        builder, out_path = builders[fmt]
        if out_path:
            builder.render(result, str(out_path))
            print(f'  {fmt} report saved: {out_path}')
        else:
            builder.render(result, None)


if __name__ == '__main__':
    main()
