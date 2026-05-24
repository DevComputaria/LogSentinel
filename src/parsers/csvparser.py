import pandas as pd
from .base import LogParser
from .linux import LinuxLogParser


class CsvLogParser(LogParser):
    def parse(self, path):
        df = pd.read_csv(path, encoding='utf-8')
        df.columns = [c.strip().lower() for c in df.columns]
        return self._build_dataframe(df)

    def _build_dataframe(self, df):
        if 'month' in df.columns and 'date' in df.columns and 'time' in df.columns:
            df['timestamp'] = pd.to_datetime(
                df['month'].astype(str) + ' ' +
                df['date'].astype(str) + ' ' +
                df['time'].astype(str),
                errors='coerce'
            )
        elif 'date' in df.columns and 'time' in df.columns:
            df['timestamp'] = pd.to_datetime(
                df['date'].astype(str) + ' ' + df['time'].astype(str), errors='coerce'
            )
        elif 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        elif 'time' in df.columns:
            df['timestamp'] = pd.to_datetime(df['time'], errors='coerce')
        else:
            df['timestamp'] = pd.NaT

        rename_map = {
            'content': 'message_raw', 'message': 'message_raw',
            'component': 'component', 'eventid': 'event_id_csv',
            'eventtemplate': 'event_template_csv',
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

        if 'level' not in df.columns:
            df['level'] = 'Info'
        if 'level' in df.columns and 'message_raw' in df.columns:
            known_levels = {'info', 'warning', 'error', 'debug', 'trace', 'fatal', 'critical'}
            sample = str(df['level'].dropna().iloc[0]).lower() if not df['level'].dropna().empty else ''
            if sample not in known_levels:
                df['level'] = df['message_raw'].apply(
                    lambda m: LinuxLogParser._infer_level(str(m)))

        if 'component' not in df.columns:
            df['component'] = ''
        if 'message_raw' not in df.columns:
            df['message_raw'] = ''
        if 'pid' not in df.columns:
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
