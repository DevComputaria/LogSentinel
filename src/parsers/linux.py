import re
import pandas as pd
from datetime import datetime
from .base import LogParser

LINUX_LOG_RE = re.compile(
    r'^(?P<month>\w{3})\s+(?P<day>\d{1,2})\s'
    r'(?P<time>\d{2}:\d{2}:\d{2})\s'
    r'(?P<host>\S+)\s'
    r'(?P<program>[^\[:]+?)(?:\[(?P<pid>\d+)\])?:\s'
    r'(?P<message>.*)$'
)


class LinuxLogParser(LogParser):
    def parse(self, path):
        with open(path, 'r', errors='replace') as f:
            lines = f.readlines()
        return self._parse_lines(lines)

    def _parse_lines(self, lines):
        records = []
        current_year = datetime.now().year
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            m = LINUX_LOG_RE.match(line)
            if not m:
                records.append(self._unmatched(i, line))
                continue
            records.append(self._matched(m, i, current_year, line))
        return pd.DataFrame(records)

    def _unmatched(self, lineno, line):
        return {'timestamp': pd.NaT, 'level': 'Info', 'component': '',
                'message_raw': line, 'pid': '', 'source': 'linux', 'line': lineno}

    def _matched(self, m, lineno, year, line):
        month, day, time_str = m.group('month'), m.group('day'), m.group('time')
        try:
            dt = datetime.strptime(f'{month} {day} {time_str}', '%b %d %H:%M:%S')
            dt = dt.replace(year=year)
        except ValueError:
            dt = pd.NaT
        msg = m.group('message').strip()
        pid = m.group('pid') or ''
        program = m.group('program') or ''
        level = self._infer_level(msg, program)
        return {'timestamp': dt, 'level': level, 'component': program,
                'message_raw': msg, 'pid': pid, 'source': 'linux', 'line': lineno}

    @staticmethod
    def _infer_level(message, component=None):
        msg_upper = message.upper()
        if re.search(r'\b(ERROR|FAILED|FATAL|ALERT|CRITICAL)\b', msg_upper):
            return 'Error'
        if re.search(r'\b(WARN|WARNING)\b', msg_upper):
            return 'Warning'
        if re.search(r'(HRESULT\s*=\s*0x8[0-9a-fA-F]{7})', message):
            return 'Error'
        if re.search(r'\bError\b', message):
            return 'Error'
        if component and component.upper() in ('ERROR', 'WARNING', 'INFO'):
            return component.capitalize()
        return 'Info'
