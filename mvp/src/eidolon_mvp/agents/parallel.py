"""Parallel execution of agents with rate limiting and error isolation."""

import asyncio
from typing import Any, Callable, TypeVar

T = TypeVar("T")


class ParallelExecutor:
    """Executes multiple agents in parallel with rate limiting."""

    def __init__(self, max_concurrent: int = 10, rate_limit_delay: float = 0.1):
        """Initialize executor.

        Args:
            max_concurrent: Maximum concurrent operations
            rate_limit_delay: Delay between starting operations (seconds)
        """
        self.max_concurrent = max_concurrent
        self.rate_limit_delay = rate_limit_delay
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def execute_all(
        self,
        agents: list[Any],
        operation: Callable[[Any], Any],
        on_progress: Callable[[int, int], None] | None = None,
    ) -> list[tuple[Any, Any | Exception]]:
        """Execute operation on all agents in parallel.

        Args:
            agents: List of agents to process
            operation: Async operation to perform (e.g., agent.analyze)
            on_progress: Optional callback(completed, total)

        Returns:
            List of (agent, result_or_exception) tuples
        """
        total = len(agents)
        completed = 0
        results = []

        async def execute_with_semaphore(agent):
            nonlocal completed

            async with self.semaphore:
                try:
                    # Rate limiting
                    if self.rate_limit_delay > 0:
                        await asyncio.sleep(self.rate_limit_delay)

                    # Execute operation
                    result = await operation(agent)

                    completed += 1
                    if on_progress:
                        on_progress(completed, total)

                    return (agent, result)

                except Exception as e:
                    # Isolate errors - one failure doesn't stop others
                    completed += 1
                    if on_progress:
                        on_progress(completed, total)

                    return (agent, e)

        # Run all in parallel
        tasks = [execute_with_semaphore(agent) for agent in agents]
        results = await asyncio.gather(*tasks)

        return results

    async def execute_batch(
        self,
        agents: list[Any],
        operation: Callable[[Any], Any],
        batch_size: int | None = None,
    ) -> list[list[tuple[Any, Any | Exception]]]:
        """Execute in batches (for very large sets).

        Args:
            agents: List of agents to process
            operation: Async operation to perform
            batch_size: Batch size (defaults to max_concurrent)

        Returns:
            List of result batches
        """
        if batch_size is None:
            batch_size = self.max_concurrent

        batches = []
        for i in range(0, len(agents), batch_size):
            batch = agents[i : i + batch_size]
            results = await self.execute_all(batch, operation)
            batches.append(results)

        return batches


class ProgressTracker:
    """Simple progress tracker for agent execution."""

    def __init__(self, total: int, verbose: bool = True):
        """Initialize tracker.

        Args:
            total: Total number of operations
            verbose: Whether to print progress
        """
        self.total = total
        self.completed = 0
        self.verbose = verbose
        self.errors = []

    def update(self, completed: int, total: int):
        """Update progress.

        Args:
            completed: Number completed
            total: Total number
        """
        self.completed = completed
        if self.verbose:
            pct = (completed / total * 100) if total > 0 else 0
            print(f"  Progress: {completed}/{total} ({pct:.0f}%)", end="\r")

    def record_error(self, agent_id: str, error: Exception):
        """Record an error.

        Args:
            agent_id: Agent that failed
            error: Exception that occurred
        """
        self.errors.append((agent_id, error))

    def finish(self):
        """Finish tracking."""
        if self.verbose:
            print()  # New line after progress
            if self.errors:
                print(f"⚠️  {len(self.errors)} agent(s) failed")
