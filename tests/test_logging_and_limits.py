import asyncio
from pathlib import Path

import pytest

from eidolon.logging_config import configure_logging, get_logger, bind_context, unbind_context, clear_context
from eidolon.resource_limits import ResourceValidator, ResourceLimits, ResourceLimitError, enforce_memory_limit


def test_logging_context_binding():
    configure_logging(log_level="INFO", json_logs=False)
    logger = get_logger("test")
    bind_context(session_id="abc")
    logger.info("message")
    unbind_context("session_id")
    clear_context()  # should not raise


def test_validate_file_size_and_module_counts(tmp_path, monkeypatch):
    small = tmp_path / "small.py"
    small.write_text("print('ok')\n")

    ResourceValidator.validate_file_size(str(small))  # should not raise
    ResourceValidator.validate_module_count(ResourceLimits.MAX_MODULES_PER_ANALYSIS - 1)
    ResourceValidator.validate_function_count(ResourceLimits.MAX_FUNCTIONS_PER_MODULE + 1, str(small))  # warns only

    monkeypatch.setattr(ResourceLimits, "MAX_FILE_SIZE_BYTES", 1)
    with pytest.raises(ResourceLimitError):
        ResourceValidator.validate_file_size(str(small))


def test_validate_cache_limits():
    with pytest.raises(ResourceLimitError):
        ResourceValidator.validate_cache_size(
            current_size_bytes=ResourceLimits.MAX_CACHE_SIZE_BYTES + 1,
            current_entries=10,
        )

    with pytest.raises(ResourceLimitError):
        ResourceValidator.validate_cache_size(
            current_size_bytes=10,
            current_entries=ResourceLimits.MAX_CACHE_ENTRIES + 1,
        )


def test_should_skip_large_file(tmp_path):
    tiny = tmp_path / "tiny.txt"
    tiny.write_text("x")
    assert ResourceValidator.should_skip_large_file(str(tiny)) is False
    assert ResourceValidator.should_skip_large_file("nonexistent.txt") is True


def test_memory_validation(monkeypatch):
    class FakeMemInfo:
        def __init__(self, rss):
            self.rss = rss

    class FakeProcess:
        def memory_info(self):
            return FakeMemInfo(rss=(ResourceLimits.MAX_MEMORY_PER_ANALYSIS_MB + 1) * 1024 * 1024)

    class FakeVMem:
        percent = ResourceLimits.MAX_MEMORY_PERCENT - 1

    monkeypatch.setattr("eidolon.resource_limits.psutil.Process", lambda: FakeProcess())
    monkeypatch.setattr("eidolon.resource_limits.psutil.virtual_memory", lambda: FakeVMem)

    with pytest.raises(ResourceLimitError):
        ResourceValidator.validate_memory_usage()

    # Now simulate healthy memory
    class HealthyProcess:
        def memory_info(self):
            return FakeMemInfo(rss=10 * 1024 * 1024)

    class HealthyVMem:
        percent = 10

    monkeypatch.setattr("eidolon.resource_limits.psutil.Process", lambda: HealthyProcess())
    monkeypatch.setattr("eidolon.resource_limits.psutil.virtual_memory", lambda: HealthyVMem)
    ResourceValidator.validate_memory_usage()  # should not raise


@pytest.mark.asyncio
async def test_enforce_memory_limit(monkeypatch):
    called = {"flag": False}

    @enforce_memory_limit
    async def sample():
        called["flag"] = True
        return "ok"

    monkeypatch.setattr(ResourceValidator, "validate_memory_usage", lambda: None)
    result = await sample()
    assert result == "ok"
    assert called["flag"] is True

    monkeypatch.setattr(ResourceValidator, "validate_memory_usage", lambda: (_ for _ in ()).throw(ResourceLimitError("fail")))
    with pytest.raises(ResourceLimitError):
        await sample()
