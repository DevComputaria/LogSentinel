from pathlib import Path
from .base import LogParser
from .linux import LinuxLogParser, LINUX_LOG_RE
from .windows import WindowsLogParser, WINDOWS_LOG_RE
from .csvparser import CsvLogParser


class ParserFactory:
    _parsers = {'.csv': CsvLogParser}

    @classmethod
    def register(cls, suffix, parser_cls):
        cls._parsers[suffix] = parser_cls

    @classmethod
    def create(cls, path):
        path = Path(path)
        suffix = path.suffix.lower()
        if suffix in cls._parsers:
            return cls._parsers[suffix]()

        with open(path, 'r', errors='replace') as f:
            lines = f.readlines()

        linux_hits = sum(1 for l in lines[:50] if LINUX_LOG_RE.match(l.strip()))
        windows_hits = sum(1 for l in lines[:50] if WINDOWS_LOG_RE.match(l.strip()))

        if linux_hits > windows_hits:
            return LinuxLogParser()
        if windows_hits > 0:
            return WindowsLogParser()

        sample = ''.join(lines[:30])
        if 'sshd' in sample or 'pam_unix' in sample or 'su(' in sample:
            return LinuxLogParser()
        if 'CBS' in sample or 'TrustedInstaller' in sample:
            return WindowsLogParser()

        return WindowsLogParser()
