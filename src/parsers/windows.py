import re
import pandas as pd
from datetime import datetime
from .base import LogParser
from .linux import LinuxLogParser

WINDOWS_LOG_RE = re.compile(
    r'^(?P<date>\d{4}-\d{2}-\d{2})\s'
    r'(?P<time>\d{2}:\d{2}:\d{2})[,\d]*\s+'
    r'(?P<level>\w+)\s+'
    r'(?P<component>\S+)\s+'
    r'(?P<message>.*)$'
)


class WindowsLogParser(LogParser):
    def parse(self, path):
        with open(path, 'r', errors='replace') as f:
            lines = f.readlines()
        return self._parse_lines(lines)

    def _parse_lines(self, lines):
        records = []
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            m = WINDOWS_LOG_RE.match(line)
            if not m:
                records.append(self._unmatched(i, line))
                continue
            records.append(self._matched(m, i, line))
        return pd.DataFrame(records)

    def _unmatched(self, lineno, line):
        return {'timestamp': pd.NaT, 'level': 'Info', 'component': '',
                'message_raw': line, 'pid': '', 'source': 'windows', 'line': lineno}

    def _matched(self, m, lineno, line):
        date_str, time_str = m.group('date'), m.group('time')
        try:
            dt = datetime.strptime(f'{date_str} {time_str}', '%Y-%m-%d %H:%M:%S')
        except ValueError:
            dt = pd.NaT
        parsed_level = m.group('level') or 'Info'
        component = m.group('component') or ''
        msg = m.group('message').strip()
        inferred = LinuxLogParser._infer_level(msg, component)
        level = 'Error' if inferred == 'Error' else 'Warning' if inferred == 'Warning' else parsed_level
        return {'timestamp': dt, 'level': level, 'component': component,
                'message_raw': msg, 'pid': '', 'source': 'windows', 'line': lineno}
