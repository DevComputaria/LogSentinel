import re
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

LINUX_LOG_RE = re.compile(
    r'^(?P<month>\w{3})\s+(?P<day>\d{1,2})\s'
    r'(?P<time>\d{2}:\d{2}:\d{2})\s'
    r'(?P<host>\S+)\s'
    r'(?P<program>[^\[:]+?)(?:\[(?P<pid>\d+)\])?:\s'
    r'(?P<message>.*)$'
)

WINDOWS_LOG_RE = re.compile(
    r'^(?P<date>\d{4}-\d{2}-\d{2})\s'
    r'(?P<time>\d{2}:\d{2}:\d{2})[,\d]*\s+'
    r'(?P<level>\w+)\s+'
    r'(?P<component>\S+)\s+'
    r'(?P<message>.*)$'
)

def detect_format(lines):
    if not lines:
        return 'unknown'
    linux_score = 0
    windows_score = 0
    for line in lines[:50]:
        line = line.strip()
        if not line:
            continue
        if LINUX_LOG_RE.match(line):
            linux_score += 1
        elif WINDOWS_LOG_RE.match(line):
            windows_score += 1
    if linux_score > windows_score:
        return 'linux'
    elif windows_score > linux_score:
        return 'windows'
    sample = ''.join(lines[:20])
    if ',' in sample and re.search(r'\d{4}-\d{2}-\d{2}', sample):
        return 'windows'
    if re.search(r'^\w{3}\s+\d{1,2}\s\d{2}:\d{2}:\d{2}\s\S+\s', sample, re.MULTILINE):
        return 'linux'
    return 'unknown'

def infer_level(message, component=None):
    msg_upper = message.upper()
    if re.search(r'\b(ERROR|FAILED|FATAL|ALERT|CRITICAL|E_FAIL)\b', msg_upper):
        return 'Error'
    if re.search(r'\b(WARN|WARNING)\b', msg_upper):
        return 'Warning'
    if re.search(r'\b(INFO|INFORMATION)\b', msg_upper):
        return 'Info'
    if re.search(r'(HRESULT\s*=\s*0x8[0-9a-fA-F]{7})', message):
        return 'Error'
    if re.search(r'\b(Warning|Error)\b', message):
        return 'Error' if re.search(r'\bError\b', message) else 'Warning'
    if component and component.upper() in ('ERROR', 'WARNING', 'INFO'):
        return component.capitalize()
    return 'Info'

def parse_linux(lines):
    records = []
    current_year = datetime.now().year
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        m = LINUX_LOG_RE.match(line)
        if not m:
            records.append({
                'timestamp': pd.NaT, 'level': 'Info', 'component': '',
                'message_raw': line, 'pid': '', 'source': 'linux', 'line': i
            })
            continue
        month, day, time_str = m.group('month'), m.group('day'), m.group('time')
        try:
            dt = datetime.strptime(f'{month} {day} {time_str}', '%b %d %H:%M:%S')
            dt = dt.replace(year=current_year)
        except ValueError:
            dt = pd.NaT
        msg = m.group('message').strip()
        pid = m.group('pid') or ''
        program = m.group('program') or ''
        level = infer_level(msg, program)
        records.append({
            'timestamp': dt, 'level': level, 'component': program,
            'message_raw': msg, 'pid': pid, 'source': 'linux', 'line': i
        })
    return pd.DataFrame(records)

def parse_windows(lines):
    records = []
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        m = WINDOWS_LOG_RE.match(line)
        if not m:
            records.append({
                'timestamp': pd.NaT, 'level': 'Info', 'component': '',
                'message_raw': line, 'pid': '', 'source': 'windows', 'line': i
            })
            continue
        date_str, time_str = m.group('date'), m.group('time')
        try:
            dt = datetime.strptime(f'{date_str} {time_str}', '%Y-%m-%d %H:%M:%S')
        except ValueError:
            dt = pd.NaT
        parsed_level = m.group('level') or 'Info'
        component = m.group('component') or ''
        msg = m.group('message').strip()
        inferred = infer_level(msg, component)
        level = 'Error' if inferred == 'Error' else 'Warning' if inferred == 'Warning' else parsed_level
        records.append({
            'timestamp': dt, 'level': level, 'component': component,
            'message_raw': msg, 'pid': '', 'source': 'windows', 'line': i
        })
    return pd.DataFrame(records)

def parse_csv(path):
    try:
        df = pd.read_csv(path, encoding='utf-8')
        df.columns = [c.strip().lower() for c in df.columns]

        if 'month' in df.columns and 'date' in df.columns and 'time' in df.columns:
            df['timestamp'] = pd.to_datetime(
                df['month'].astype(str) + ' ' +
                df['date'].astype(str) + ' ' +
                df['time'].astype(str),
                errors='coerce'
            )
        elif 'date' in df.columns and 'time' in df.columns:
            df['timestamp'] = pd.to_datetime(
                df['date'].astype(str) + ' ' + df['time'].astype(str),
                errors='coerce'
            )
        elif 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        elif 'time' in df.columns:
            df['timestamp'] = pd.to_datetime(df['time'], errors='coerce')
        else:
            df['timestamp'] = pd.NaT

        rename_map = {
            'content': 'message_raw',
            'message': 'message_raw',
            'component': 'component',
            'eventid': 'event_id_csv',
            'eventtemplate': 'event_template_csv',
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

        if 'level' not in df.columns:
            df['level'] = 'Info'
        if 'level' in df.columns and 'message_raw' in df.columns:
            known_levels = {'info', 'warning', 'error', 'debug', 'trace', 'fatal', 'critical'}
            sample_level = str(df['level'].dropna().iloc[0]).lower() if not df['level'].dropna().empty else ''
            if sample_level not in known_levels:
                df['level'] = df['message_raw'].apply(lambda m: infer_level(str(m)))
        if 'component' not in df.columns:
            df['component'] = ''
        if 'message_raw' not in df.columns:
            df['message_raw'] = ''
        if 'pid' not in df.columns and 'pid' in df.columns:
            pass
        elif 'pid' not in df.columns:
            df['pid'] = ''
        df['source'] = 'csv'
        if 'line' not in df.columns and 'lineid' in df.columns:
            df['line'] = df['lineid']
        elif 'line' not in df.columns:
            df['line'] = range(1, len(df) + 1)
        cols = ['timestamp', 'level', 'component', 'message_raw', 'pid', 'source', 'line']
        for c in cols:
            if c not in df.columns:
                df[c] = ''
        return df[cols]
    except Exception as e:
        return None

def parse(path):
    path = Path(path)
    if path.suffix == '.csv':
        df = parse_csv(path)
        if df is not None and not df.empty:
            return df
    raw_lines = []
    try:
        with open(path, 'r', errors='replace') as f:
            raw_lines = f.readlines()
    except Exception as e:
        raise ValueError(f'Failed to read {path}: {e}')
    fmt = detect_format(raw_lines)
    if fmt == 'linux':
        df = parse_linux(raw_lines)
    elif fmt == 'windows':
        df = parse_windows(raw_lines)
    else:
        raise ValueError(f'Unknown log format for {path}')
    return df
