"""
Prometheus metrics for MONAD

Provides comprehensive metrics collection for monitoring system performance,
reliability, and resource usage. Integrates with Prometheus/Grafana for
dashboards and alerting.
"""
from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, REGISTRY
from prometheus_client import CONTENT_TYPE_LATEST
from typing import Dict, Any
import psutil
import time


# System Info
system_info = Info(
    'monad_system',
    'MONAD system information'
)

# Set system info on import
system_info.info({
    'version': '0.1.0',
    'python_version': f"{psutil.sys.version_info.major}.{psutil.sys.version_info.minor}.{psutil.sys.version_info.micro}"
})


# Analysis Metrics
analysis_total = Counter(
    'monad_analyses_total',
    'Total number of analyses started',
    ['mode', 'status']  # mode: full/incremental, status: success/failure/cancelled
)

analysis_duration_seconds = Histogram(
    'monad_analysis_duration_seconds',
    'Analysis duration in seconds',
    ['mode'],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600]
)

active_analyses = Gauge(
    'monad_active_analyses',
    'Number of currently running analyses'
)

modules_analyzed_total = Counter(
    'monad_modules_analyzed_total',
    'Total number of modules analyzed',
    ['mode']
)

functions_analyzed_total = Counter(
    'monad_functions_analyzed_total',
    'Total number of functions analyzed',
    ['mode']
)


# AI API Metrics
ai_api_calls_total = Counter(
    'monad_ai_api_calls_total',
    'Total AI API calls',
    ['status', 'model']  # status: success/error/timeout/rate_limited
)

ai_api_tokens_total = Counter(
    'monad_ai_api_tokens_total',
    'Total tokens consumed',
    ['direction', 'model']  # direction: input/output
)

ai_api_latency_seconds = Histogram(
    'monad_ai_api_latency_seconds',
    'AI API call latency in seconds',
    ['model'],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60, 90, 120]
)

ai_api_rate_limit_waits_total = Counter(
    'monad_ai_api_rate_limit_waits_total',
    'Number of times rate limiter caused a wait'
)

ai_api_rate_limit_wait_seconds = Histogram(
    'monad_ai_api_rate_limit_wait_seconds',
    'Time spent waiting for rate limiter',
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60]
)


# Circuit Breaker Metrics
circuit_breaker_state = Gauge(
    'monad_circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=half_open, 2=open)',
    ['name']
)

circuit_breaker_failures_total = Counter(
    'monad_circuit_breaker_failures_total',
    'Total circuit breaker failures',
    ['name']
)

circuit_breaker_successes_total = Counter(
    'monad_circuit_breaker_successes_total',
    'Total circuit breaker successes',
    ['name']
)

circuit_breaker_state_changes_total = Counter(
    'monad_circuit_breaker_state_changes_total',
    'Circuit breaker state changes',
    ['name', 'from_state', 'to_state']
)


# Retry Metrics
retry_attempts_total = Counter(
    'monad_retry_attempts_total',
    'Total retry attempts',
    ['operation', 'attempt']  # attempt: 1, 2, 3
)

retry_exhausted_total = Counter(
    'monad_retry_exhausted_total',
    'Total times all retries were exhausted',
    ['operation']
)


# Cache Metrics
cache_operations_total = Counter(
    'monad_cache_operations_total',
    'Total cache operations',
    ['operation', 'result']  # operation: get/set/invalidate, result: hit/miss/error
)

cache_size_bytes = Gauge(
    'monad_cache_size_bytes',
    'Current cache size in bytes'
)

cache_entries_total = Gauge(
    'monad_cache_entries_total',
    'Number of entries in cache'
)

cache_hit_rate_percent = Gauge(
    'monad_cache_hit_rate_percent',
    'Cache hit rate as percentage'
)

cache_evictions_total = Counter(
    'monad_cache_evictions_total',
    'Total number of cache evictions',
    ['reason']  # reason: size/age/manual
)


# Database Metrics
db_queries_total = Counter(
    'monad_db_queries_total',
    'Total database queries',
    ['operation', 'table']  # operation: select/insert/update/delete
)

db_query_duration_seconds = Histogram(
    'monad_db_query_duration_seconds',
    'Database query duration in seconds',
    ['operation', 'table'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5]
)

db_connections_active = Gauge(
    'monad_db_connections_active',
    'Number of active database connections'
)

db_connection_errors_total = Counter(
    'monad_db_connection_errors_total',
    'Total database connection errors'
)


# WebSocket Metrics
websocket_connections_active = Gauge(
    'monad_websocket_connections_active',
    'Number of active WebSocket connections'
)

websocket_messages_total = Counter(
    'monad_websocket_messages_total',
    'Total WebSocket messages',
    ['direction', 'type']  # direction: sent/received, type: progress/error/complete
)

websocket_connection_errors_total = Counter(
    'monad_websocket_connection_errors_total',
    'Total WebSocket connection errors',
    ['reason']
)


# Git Operations Metrics
git_operations_total = Counter(
    'monad_git_operations_total',
    'Total git operations',
    ['operation', 'status']  # operation: diff/status/commit, status: success/error/timeout
)

git_operation_duration_seconds = Histogram(
    'monad_git_operation_duration_seconds',
    'Git operation duration in seconds',
    ['operation'],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30]
)


# Card Metrics
cards_created_total = Counter(
    'monad_cards_created_total',
    'Total cards created',
    ['type', 'status']  # type: review/insight/warning, status: new/proposed/done
)

cards_active = Gauge(
    'monad_cards_active',
    'Number of active cards',
    ['type', 'status']
)


# Error Metrics
errors_total = Counter(
    'monad_errors_total',
    'Total errors',
    ['component', 'error_type']  # component: orchestrator/api/cache/db
)

unhandled_exceptions_total = Counter(
    'monad_unhandled_exceptions_total',
    'Total unhandled exceptions',
    ['component']
)


# Resource Usage Metrics
process_cpu_percent = Gauge(
    'monad_process_cpu_percent',
    'CPU usage percentage of MONAD process'
)

process_memory_bytes = Gauge(
    'monad_process_memory_bytes',
    'Memory usage in bytes of MONAD process',
    ['type']  # type: rss/vms/shared
)

process_open_files = Gauge(
    'monad_process_open_files',
    'Number of open file descriptors'
)

system_disk_usage_percent = Gauge(
    'monad_system_disk_usage_percent',
    'System disk usage percentage'
)

system_memory_usage_percent = Gauge(
    'monad_system_memory_usage_percent',
    'System memory usage percentage'
)


# HTTP Metrics
http_requests_total = Counter(
    'monad_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'monad_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10]
)

http_requests_in_progress = Gauge(
    'monad_http_requests_in_progress',
    'Number of HTTP requests currently being processed',
    ['method', 'endpoint']
)


def update_resource_metrics():
    """Update system resource usage metrics"""
    try:
        # Process metrics
        process = psutil.Process()

        process_cpu_percent.set(process.cpu_percent())

        memory_info = process.memory_info()
        process_memory_bytes.labels(type='rss').set(memory_info.rss)
        process_memory_bytes.labels(type='vms').set(memory_info.vms)

        try:
            process_open_files.set(len(process.open_files()))
        except (psutil.AccessDenied, AttributeError):
            pass  # Some systems don't allow this

        # System metrics
        disk_usage = psutil.disk_usage('/')
        system_disk_usage_percent.set(disk_usage.percent)

        memory = psutil.virtual_memory()
        system_memory_usage_percent.set(memory.percent)

    except Exception as e:
        # Don't fail if metrics collection fails
        pass


def get_metrics_response() -> tuple:
    """
    Get Prometheus metrics in wire format

    Returns:
        Tuple of (content, content_type) for HTTP response
    """
    # Update resource metrics before generating output
    update_resource_metrics()

    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST


# Convenience functions for common metric patterns

class MetricsContext:
    """Context manager for timing and recording metrics"""

    def __init__(self, histogram, labels: Dict[str, str] = None):
        self.histogram = histogram
        self.labels = labels or {}
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        if self.labels:
            self.histogram.labels(**self.labels).observe(duration)
        else:
            self.histogram.observe(duration)
        return False


def track_analysis(mode: str):
    """
    Context manager for tracking analysis metrics

    Usage:
        with track_analysis('incremental'):
            # perform analysis
            pass
    """
    class AnalysisTracker:
        def __init__(self, mode):
            self.mode = mode
            self.start_time = None

        def __enter__(self):
            active_analyses.inc()
            self.start_time = time.time()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            duration = time.time() - self.start_time
            active_analyses.dec()

            status = 'success' if exc_type is None else 'failure'
            analysis_total.labels(mode=self.mode, status=status).inc()
            analysis_duration_seconds.labels(mode=self.mode).observe(duration)

            return False

    return AnalysisTracker(mode)


def record_ai_call(model: str, input_tokens: int, output_tokens: int, duration: float, success: bool = True):
    """Record metrics for an AI API call"""
    status = 'success' if success else 'error'

    ai_api_calls_total.labels(status=status, model=model).inc()
    ai_api_tokens_total.labels(direction='input', model=model).inc(input_tokens)
    ai_api_tokens_total.labels(direction='output', model=model).inc(output_tokens)
    ai_api_latency_seconds.labels(model=model).observe(duration)


def record_cache_operation(operation: str, result: str):
    """Record cache operation"""
    cache_operations_total.labels(operation=operation, result=result).inc()


def record_db_query(operation: str, table: str, duration: float):
    """Record database query"""
    db_queries_total.labels(operation=operation, table=table).inc()
    db_query_duration_seconds.labels(operation=operation, table=table).observe(duration)
