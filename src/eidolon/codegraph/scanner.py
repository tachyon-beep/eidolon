from __future__ import annotations

import ast
import hashlib
import json
import statistics
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional, Sequence

import psutil


EXCLUDED_DIRS: tuple[str, ...] = (".git", ".hg", ".svn", "__pycache__", ".venv", "env", "venv")


@dataclass(slots=True)
class FileMetrics:
    path: str
    sha256: str
    size_bytes: int
    sloc: int
    class_count: int
    function_count: int
    import_count: int
    parse_ms: float


@dataclass(slots=True)
class ScanReport:
    repo_root: str
    files_processed: int
    duration_seconds: float
    files_per_second: float
    avg_parse_ms: float
    p95_parse_ms: float
    total_bytes: int
    avg_sloc: float
    rss_peak_bytes: int
    io_read_mb: float
    io_write_mb: float
    parse_errors: int
    skipped_files: int
    timestamp: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


class CodeGraphScanner:
    """Prototype scanner that measures throughput and collects lightweight metrics."""

    def __init__(
        self,
        repo_root: Path,
        *,
        exclude_dirs: Sequence[str] | None = None,
        follow_symlinks: bool = False,
    ) -> None:
        self.repo_root = repo_root
        self.exclude_dirs = set(exclude_dirs or ()).union(EXCLUDED_DIRS)
        self.follow_symlinks = follow_symlinks

    def iter_python_files(self) -> Iterable[Path]:
        for path in self.repo_root.rglob("*.py"):
            if not self.follow_symlinks and path.is_symlink():
                continue
            if any(part in self.exclude_dirs for part in path.parts):
                continue
            yield path

    def scan(self, *, records_path: Optional[Path] = None) -> ScanReport:
        python_files = list(self.iter_python_files())
        if not python_files:
            raise FileNotFoundError(
                f"No Python files found under {self.repo_root}. Did you point the scanner at the repo root?"
            )

        process = psutil.Process()
        peak_rss = process.memory_info().rss
        disk_start = psutil.disk_io_counters()

        parse_durations_ms: list[float] = []
        total_sloc = 0
        total_bytes = 0
        parse_errors = 0

        record_file_handle = records_path.open("w", encoding="utf-8") if records_path else None

        start_time = time.perf_counter()
        for path in python_files:
            file_metrics = self._scan_file(path)
            if file_metrics is None:
                parse_errors += 1
                continue

            total_sloc += file_metrics.sloc
            total_bytes += file_metrics.size_bytes
            parse_durations_ms.append(file_metrics.parse_ms)

            if record_file_handle:
                record_file_handle.write(json.dumps(asdict(file_metrics)) + "\n")

            rss = process.memory_info().rss
            if rss > peak_rss:
                peak_rss = rss

        duration = time.perf_counter() - start_time

        if record_file_handle:
            record_file_handle.close()

        disk_end = psutil.disk_io_counters()
        read_mb, write_mb = _diff_disk_counters(disk_start, disk_end)

        files_processed = len(parse_durations_ms)
        avg_parse_ms = statistics.fmean(parse_durations_ms) if parse_durations_ms else 0.0
        p95_parse_ms = _percentile(parse_durations_ms, 0.95)
        avg_sloc = (total_sloc / files_processed) if files_processed else 0.0

        skipped_files = len(python_files) - files_processed - parse_errors

        report = ScanReport(
            repo_root=str(self.repo_root),
            files_processed=files_processed,
            duration_seconds=duration,
            files_per_second=(files_processed / duration) if duration else 0.0,
            avg_parse_ms=avg_parse_ms,
            p95_parse_ms=p95_parse_ms,
            total_bytes=total_bytes,
            avg_sloc=avg_sloc,
            rss_peak_bytes=peak_rss,
            io_read_mb=read_mb,
            io_write_mb=write_mb,
            parse_errors=parse_errors,
            skipped_files=skipped_files,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        return report

    def _scan_file(self, path: Path) -> Optional[FileMetrics]:
        try:
            raw = path.read_bytes()
        except OSError:
            return None

        size_bytes = len(raw)
        sha256 = hashlib.sha256(raw).hexdigest()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("utf-8", errors="ignore")

        t0 = time.perf_counter()
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError:
            return None
        parse_ms = (time.perf_counter() - t0) * 1000

        sloc = sum(1 for line in text.splitlines() if line.strip())
        class_count = 0
        function_count = 0
        import_count = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_count += 1
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_count += 1
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                import_count += 1

        return FileMetrics(
            path=str(path.relative_to(self.repo_root)),
            sha256=sha256,
            size_bytes=size_bytes,
            sloc=sloc,
            class_count=class_count,
            function_count=function_count,
            import_count=import_count,
            parse_ms=parse_ms,
        )


def _percentile(values: Sequence[float], percentile: float) -> float:
    if not values:
        return 0.0
    percentile = max(0.0, min(1.0, percentile))
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * percentile
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[int(k)]
    d0 = sorted_vals[f] * (c - k)
    d1 = sorted_vals[c] * (k - f)
    return d0 + d1


def _diff_disk_counters(
    start: Optional[psutil._common.sdiskio],
    end: Optional[psutil._common.sdiskio],
) -> tuple[float, float]:
    if not start or not end:
        return 0.0, 0.0
    read_bytes = max(0, end.read_bytes - start.read_bytes)
    write_bytes = max(0, end.write_bytes - start.write_bytes)
    mb = 1024 * 1024
    return read_bytes / mb, write_bytes / mb
