"""
Resource limits and validation for MONAD

Prevents resource exhaustion by enforcing limits on:
- File sizes
- Analysis depth (recursion, complexity)
- Memory usage
- Concurrent operations
- Request sizes

Protects against pathological inputs and DoS scenarios.
"""
from pathlib import Path
from typing import Optional
import psutil
from logging_config import get_logger

logger = get_logger(__name__)


class ResourceLimitError(Exception):
    """Raised when a resource limit is exceeded"""
    pass


class ResourceLimits:
    """Configuration for resource limits"""

    # File size limits
    MAX_FILE_SIZE_MB = 10
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

    # Analysis limits
    MAX_ANALYSIS_DEPTH = 100  # Max recursion/nesting depth
    MAX_FUNCTIONS_PER_MODULE = 500
    MAX_MODULES_PER_ANALYSIS = 1000
    MAX_LINES_PER_FUNCTION = 1000

    # Memory limits
    MAX_MEMORY_PERCENT = 80  # Stop if process uses >80% system memory
    MAX_MEMORY_PER_ANALYSIS_MB = 2048  # 2GB max per analysis

    # Cache limits
    MAX_CACHE_SIZE_GB = 50
    MAX_CACHE_SIZE_BYTES = MAX_CACHE_SIZE_GB * 1024 * 1024 * 1024
    MAX_CACHE_ENTRIES = 100000

    # API limits
    MAX_RESPONSE_TOKENS = 4096
    MAX_REQUEST_SIZE_MB = 50
    MAX_CONCURRENT_ANALYSES = 5
    MAX_CONCURRENT_AI_CALLS = 10

    # Database limits
    MAX_DB_SIZE_GB = 100
    MAX_CARDS_PER_ANALYSIS = 10000


class ResourceValidator:
    """Validates resources against limits"""

    @staticmethod
    def validate_file_size(file_path: str) -> None:
        """
        Validate that file size is within limits

        Args:
            file_path: Path to file to validate

        Raises:
            ResourceLimitError: If file exceeds size limit
        """
        try:
            file_size = Path(file_path).stat().st_size
            size_mb = file_size / (1024 * 1024)

            if file_size > ResourceLimits.MAX_FILE_SIZE_BYTES:
                logger.error(
                    "file_too_large",
                    file=file_path,
                    size_mb=round(size_mb, 2),
                    limit_mb=ResourceLimits.MAX_FILE_SIZE_MB
                )
                raise ResourceLimitError(
                    f"File {file_path} ({size_mb:.1f}MB) exceeds maximum size "
                    f"of {ResourceLimits.MAX_FILE_SIZE_MB}MB"
                )

            logger.debug("file_size_validated", file=file_path, size_mb=round(size_mb, 2))

        except FileNotFoundError:
            raise ResourceLimitError(f"File not found: {file_path}")
        except OSError as e:
            raise ResourceLimitError(f"Error accessing file {file_path}: {str(e)}")

    @staticmethod
    def validate_module_count(count: int) -> None:
        """
        Validate module count against limits

        Args:
            count: Number of modules to analyze

        Raises:
            ResourceLimitError: If count exceeds limit
        """
        if count > ResourceLimits.MAX_MODULES_PER_ANALYSIS:
            logger.error(
                "too_many_modules",
                count=count,
                limit=ResourceLimits.MAX_MODULES_PER_ANALYSIS
            )
            raise ResourceLimitError(
                f"Analysis contains {count} modules, exceeding limit of "
                f"{ResourceLimits.MAX_MODULES_PER_ANALYSIS}. "
                f"Consider analyzing a subdirectory or using filters."
            )

        logger.debug("module_count_validated", count=count)

    @staticmethod
    def validate_function_count(count: int, module_path: str) -> None:
        """
        Validate function count per module

        Args:
            count: Number of functions in module
            module_path: Path to module

        Raises:
            ResourceLimitError: If count exceeds limit
        """
        if count > ResourceLimits.MAX_FUNCTIONS_PER_MODULE:
            logger.warning(
                "too_many_functions",
                module=module_path,
                count=count,
                limit=ResourceLimits.MAX_FUNCTIONS_PER_MODULE
            )
            # Don't raise error, just warn - large modules exist
            # But could skip detailed analysis of huge modules

    @staticmethod
    def validate_memory_usage() -> None:
        """
        Validate current memory usage

        Raises:
            ResourceLimitError: If memory usage exceeds limits
        """
        try:
            process = psutil.Process()
            process_memory_mb = process.memory_info().rss / (1024 * 1024)

            # Check process memory
            if process_memory_mb > ResourceLimits.MAX_MEMORY_PER_ANALYSIS_MB:
                logger.error(
                    "memory_limit_exceeded",
                    process_memory_mb=round(process_memory_mb, 2),
                    limit_mb=ResourceLimits.MAX_MEMORY_PER_ANALYSIS_MB
                )
                raise ResourceLimitError(
                    f"Process memory usage ({process_memory_mb:.0f}MB) exceeds limit "
                    f"of {ResourceLimits.MAX_MEMORY_PER_ANALYSIS_MB}MB"
                )

            # Check system memory
            system_memory = psutil.virtual_memory()
            if system_memory.percent > ResourceLimits.MAX_MEMORY_PERCENT:
                logger.error(
                    "system_memory_high",
                    percent=system_memory.percent,
                    limit=ResourceLimits.MAX_MEMORY_PERCENT
                )
                raise ResourceLimitError(
                    f"System memory usage ({system_memory.percent:.1f}%) exceeds limit "
                    f"of {ResourceLimits.MAX_MEMORY_PERCENT}%"
                )

        except psutil.Error as e:
            logger.warning("memory_check_failed", error=str(e))
            # Don't fail if we can't check memory

    @staticmethod
    def validate_cache_size(current_size_bytes: int, current_entries: int) -> None:
        """
        Validate cache size and entry count

        Args:
            current_size_bytes: Current cache size in bytes
            current_entries: Current number of entries

        Raises:
            ResourceLimitError: If cache exceeds limits
        """
        size_gb = current_size_bytes / (1024 ** 3)

        if current_size_bytes > ResourceLimits.MAX_CACHE_SIZE_BYTES:
            logger.warning(
                "cache_size_exceeded",
                size_gb=round(size_gb, 2),
                limit_gb=ResourceLimits.MAX_CACHE_SIZE_GB
            )
            raise ResourceLimitError(
                f"Cache size ({size_gb:.1f}GB) exceeds limit of {ResourceLimits.MAX_CACHE_SIZE_GB}GB. "
                f"Consider running cache pruning."
            )

        if current_entries > ResourceLimits.MAX_CACHE_ENTRIES:
            logger.warning(
                "cache_entries_exceeded",
                entries=current_entries,
                limit=ResourceLimits.MAX_CACHE_ENTRIES
            )
            raise ResourceLimitError(
                f"Cache entries ({current_entries}) exceeds limit of {ResourceLimits.MAX_CACHE_ENTRIES}. "
                f"Consider running cache pruning."
            )

    @staticmethod
    def should_skip_large_file(file_path: str, warn: bool = True) -> bool:
        """
        Check if file should be skipped due to size (non-throwing version)

        Args:
            file_path: Path to check
            warn: Whether to log a warning

        Returns:
            True if file should be skipped, False otherwise
        """
        try:
            file_size = Path(file_path).stat().st_size
            if file_size > ResourceLimits.MAX_FILE_SIZE_BYTES:
                if warn:
                    size_mb = file_size / (1024 * 1024)
                    logger.warning(
                        "skipping_large_file",
                        file=file_path,
                        size_mb=round(size_mb, 2),
                        limit_mb=ResourceLimits.MAX_FILE_SIZE_MB
                    )
                return True
            return False
        except (OSError, FileNotFoundError):
            return True  # Skip files we can't access

    @staticmethod
    def get_memory_stats() -> dict:
        """
        Get current memory statistics

        Returns:
            Dict with memory stats
        """
        try:
            process = psutil.Process()
            process_memory = process.memory_info()
            system_memory = psutil.virtual_memory()

            return {
                'process_memory_mb': process_memory.rss / (1024 * 1024),
                'process_memory_limit_mb': ResourceLimits.MAX_MEMORY_PER_ANALYSIS_MB,
                'system_memory_percent': system_memory.percent,
                'system_memory_limit_percent': ResourceLimits.MAX_MEMORY_PERCENT,
                'system_memory_available_mb': system_memory.available / (1024 * 1024)
            }
        except Exception as e:
            logger.warning("memory_stats_failed", error=str(e))
            return {}


# Convenience decorator for resource validation
def enforce_memory_limit(func):
    """
    Decorator to enforce memory limits before function execution

    Usage:
        @enforce_memory_limit
        async def analyze_codebase(path):
            ...
    """
    async def wrapper(*args, **kwargs):
        ResourceValidator.validate_memory_usage()
        return await func(*args, **kwargs)

    return wrapper
