"""
Request context and cancellation support for Eidolon

Provides request lifecycle management, allowing graceful cancellation of
long-running analysis operations. Enables users to stop unwanted analyses
and reclaim resources.
"""
import asyncio
import uuid
from typing import Dict, Optional, Set
from datetime import datetime, timezone
from dataclasses import dataclass, field
from eidolon.logging_config import get_logger

logger = get_logger(__name__)


class AnalysisCancelledError(Exception):
    """Raised when an analysis is cancelled"""
    pass


@dataclass
class AnalysisContext:
    """
    Context for a running analysis

    Tracks cancellation state, background tasks, and metadata
    """
    session_id: str
    path: str
    mode: str  # 'full' or 'incremental'
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Cancellation
    cancelled: asyncio.Event = field(default_factory=asyncio.Event)
    cancel_reason: Optional[str] = None

    # Task tracking
    tasks: Set[asyncio.Task] = field(default_factory=set)

    # Metadata
    user_id: Optional[str] = None
    metadata: Dict = field(default_factory=dict)

    def cancel(self, reason: str = "User requested cancellation"):
        """
        Cancel this analysis

        Args:
            reason: Human-readable reason for cancellation
        """
        if self.cancelled.is_set():
            logger.warning("analysis_already_cancelled", session_id=self.session_id)
            return

        logger.info(
            "analysis_cancelling",
            session_id=self.session_id,
            reason=reason,
            elapsed_seconds=(datetime.now(timezone.utc) - self.started_at).total_seconds()
        )

        self.cancel_reason = reason
        self.cancelled.set()

        # Cancel all tracked tasks
        cancelled_count = 0
        for task in self.tasks:
            if not task.done():
                task.cancel()
                cancelled_count += 1

        logger.info(
            "analysis_tasks_cancelled",
            session_id=self.session_id,
            tasks_cancelled=cancelled_count,
            tasks_total=len(self.tasks)
        )

    async def check_cancelled(self):
        """
        Check if analysis has been cancelled

        Raises:
            AnalysisCancelledError: If cancelled
        """
        if self.cancelled.is_set():
            logger.debug("cancellation_check_triggered", session_id=self.session_id)
            raise AnalysisCancelledError(
                f"Analysis {self.session_id} was cancelled: {self.cancel_reason}"
            )

    def add_task(self, task: asyncio.Task):
        """Add a task to be tracked and cancelled if analysis is cancelled"""
        self.tasks.add(task)

        # Clean up when task completes
        def cleanup_task(t):
            self.tasks.discard(t)

        task.add_done_callback(cleanup_task)

    def is_cancelled(self) -> bool:
        """Check if cancelled without raising exception"""
        return self.cancelled.is_set()

    def get_status(self) -> Dict:
        """Get current status of analysis"""
        return {
            'session_id': self.session_id,
            'path': self.path,
            'mode': self.mode,
            'started_at': self.started_at.isoformat(),
            'elapsed_seconds': (datetime.now(timezone.utc) - self.started_at).total_seconds(),
            'cancelled': self.cancelled.is_set(),
            'cancel_reason': self.cancel_reason,
            'active_tasks': len([t for t in self.tasks if not t.done()]),
            'total_tasks': len(self.tasks)
        }


class AnalysisRegistry:
    """
    Global registry of active analyses

    Manages lifecycle of analysis contexts and provides lookup by session ID
    """

    def __init__(self):
        self._analyses: Dict[str, AnalysisContext] = {}
        self._lock = asyncio.Lock()

    async def create(
        self,
        path: str,
        mode: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> AnalysisContext:
        """
        Create and register a new analysis context

        Args:
            path: Path being analyzed
            mode: Analysis mode ('full' or 'incremental')
            session_id: Optional session ID (generated if not provided)
            user_id: Optional user ID

        Returns:
            AnalysisContext instance
        """
        if session_id is None:
            session_id = str(uuid.uuid4())

        async with self._lock:
            if session_id in self._analyses:
                logger.warning(
                    "session_id_collision",
                    session_id=session_id,
                    message="Session ID already exists, generating new one"
                )
                session_id = str(uuid.uuid4())

            context = AnalysisContext(
                session_id=session_id,
                path=path,
                mode=mode,
                user_id=user_id
            )

            self._analyses[session_id] = context

            logger.info(
                "analysis_registered",
                session_id=session_id,
                path=path,
                mode=mode,
                active_analyses=len(self._analyses)
            )

            return context

    async def get(self, session_id: str) -> Optional[AnalysisContext]:
        """Get analysis context by session ID"""
        async with self._lock:
            return self._analyses.get(session_id)

    async def cancel(self, session_id: str, reason: str = "User requested cancellation") -> bool:
        """
        Cancel an analysis by session ID

        Args:
            session_id: Session ID to cancel
            reason: Reason for cancellation

        Returns:
            True if cancelled, False if not found
        """
        async with self._lock:
            context = self._analyses.get(session_id)
            if context:
                context.cancel(reason)
                return True

            logger.warning("cancel_session_not_found", session_id=session_id)
            return False

    async def remove(self, session_id: str):
        """Remove completed analysis from registry"""
        async with self._lock:
            if session_id in self._analyses:
                context = self._analyses.pop(session_id)
                logger.info(
                    "analysis_unregistered",
                    session_id=session_id,
                    cancelled=context.is_cancelled(),
                    elapsed_seconds=(datetime.now(timezone.utc) - context.started_at).total_seconds(),
                    active_analyses=len(self._analyses)
                )

    async def get_all_active(self) -> Dict[str, Dict]:
        """Get status of all active analyses"""
        async with self._lock:
            return {
                session_id: context.get_status()
                for session_id, context in self._analyses.items()
            }

    async def cancel_all(self, reason: str = "System shutdown"):
        """Cancel all active analyses (e.g., during shutdown)"""
        async with self._lock:
            session_ids = list(self._analyses.keys())
            for session_id in session_ids:
                self._analyses[session_id].cancel(reason)

            logger.info("all_analyses_cancelled", count=len(session_ids), reason=reason)

    def count_active(self) -> int:
        """Get count of active (non-cancelled) analyses"""
        return sum(1 for ctx in self._analyses.values() if not ctx.is_cancelled())


# Global registry instance
analysis_registry = AnalysisRegistry()


# Convenience decorator for cancellable operations
def cancellable(func):
    """
    Decorator to make an async function cancellable

    The function must accept an `AnalysisContext` parameter.

    Usage:
        @cancellable
        async def analyze_module(context: AnalysisContext, module):
            await context.check_cancelled()  # Periodic checks
            # ... do work ...
    """
    async def wrapper(*args, **kwargs):
        # Try to find AnalysisContext in args/kwargs
        context = None
        for arg in args:
            if isinstance(arg, AnalysisContext):
                context = arg
                break

        if context is None:
            context = kwargs.get('context')

        if context is None:
            # No context provided, just run normally
            return await func(*args, **kwargs)

        try:
            # Check cancelled before starting
            await context.check_cancelled()

            # Run function
            result = await func(*args, **kwargs)

            return result

        except AnalysisCancelledError:
            logger.info("operation_cancelled", function=func.__name__)
            raise

    return wrapper
