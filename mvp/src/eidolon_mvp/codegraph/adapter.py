"""Adapter to query CodeGraph for function call context.

This provides agents with:
- Who calls this function (callers)
- Who this function calls (callees)
- Import context
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class FunctionContext:
    """Context about a function from CodeGraph."""

    function_name: str
    file_path: str
    callers: list[str]  # Functions that call this one
    callees: list[str]  # Functions this one calls
    imports: list[str]  # Modules imported by this file


class CodeGraphAdapter:
    """Query CodeGraph database for function context."""

    def __init__(self, dsn: str, run_id: Optional[int] = None):
        """Initialize adapter.

        Args:
            dsn: PostgreSQL connection string
            run_id: Optional scan run ID (uses latest if not specified)
        """
        self.dsn = dsn
        self.run_id = run_id
        self._pool = None

    async def connect(self):
        """Initialize connection pool."""
        import psycopg_pool

        self._pool = psycopg_pool.AsyncConnectionPool(
            self.dsn, min_size=1, max_size=5, open=True
        )

    async def close(self):
        """Close connection pool."""
        if self._pool:
            await self._pool.close()

    async def get_function_context(
        self, function_name: str, file_path: str
    ) -> Optional[FunctionContext]:
        """Get call context for a function.

        Args:
            function_name: Name of function
            file_path: Path to file containing function

        Returns:
            FunctionContext or None if not found
        """
        if not self._pool:
            await self.connect()

        # Determine run_id if not specified
        if self.run_id is None:
            self.run_id = await self._get_latest_run_id()

        if self.run_id is None:
            return None  # No scans in database

        # Get callers (who calls this function)
        callers = await self._get_callers(function_name, file_path)

        # Get callees (who this function calls)
        callees = await self._get_callees(function_name, file_path)

        # Get imports for this file
        imports = await self._get_imports(file_path)

        return FunctionContext(
            function_name=function_name,
            file_path=file_path,
            callers=callers,
            callees=callees,
            imports=imports,
        )

    async def _get_latest_run_id(self) -> Optional[int]:
        """Get the most recent scan run ID."""
        async with self._pool.connection() as conn:
            result = await conn.execute(
                """
                SELECT id FROM scan_runs
                ORDER BY started_at DESC
                LIMIT 1
                """
            )
            row = await result.fetchone()
            return row[0] if row else None

    async def _get_callers(self, function_name: str, file_path: str) -> list[str]:
        """Get list of functions that call this one.

        Args:
            function_name: Target function
            file_path: File containing target

        Returns:
            List of caller function names
        """
        async with self._pool.connection() as conn:
            result = await conn.execute(
                """
                SELECT DISTINCT caller_function
                FROM function_calls
                WHERE run_id = %s
                  AND callee_function = %s
                  AND callee_file = %s
                ORDER BY caller_function
                LIMIT 50
                """,
                (self.run_id, function_name, file_path),
            )
            rows = await result.fetchall()
            return [row[0] for row in rows]

    async def _get_callees(self, function_name: str, file_path: str) -> list[str]:
        """Get list of functions that this one calls.

        Args:
            function_name: Source function
            file_path: File containing source

        Returns:
            List of callee function names
        """
        async with self._pool.connection() as conn:
            result = await conn.execute(
                """
                SELECT DISTINCT callee_function
                FROM function_calls
                WHERE run_id = %s
                  AND caller_function = %s
                  AND caller_file = %s
                ORDER BY callee_function
                LIMIT 50
                """,
                (self.run_id, function_name, file_path),
            )
            rows = await result.fetchall()
            return [row[0] for row in rows]

    async def _get_imports(self, file_path: str) -> list[str]:
        """Get imports for a file.

        Args:
            file_path: Path to file

        Returns:
            List of imported module names
        """
        async with self._pool.connection() as conn:
            result = await conn.execute(
                """
                SELECT DISTINCT imported_module
                FROM file_imports
                WHERE run_id = %s
                  AND file_path = %s
                ORDER BY imported_module
                LIMIT 100
                """,
                (self.run_id, file_path),
            )
            rows = await result.fetchall()
            return [row[0] for row in rows]

    def format_context_for_prompt(self, context: FunctionContext) -> str:
        """Format context for inclusion in LLM prompt.

        Args:
            context: Function context

        Returns:
            Formatted text for prompt
        """
        parts = []

        if context.callers:
            parts.append(
                f"Functions that call {context.function_name}:\n"
                + "\n".join(f"  - {c}" for c in context.callers[:10])
            )

        if context.callees:
            parts.append(
                f"\n{context.function_name} calls:\n"
                + "\n".join(f"  - {c}" for c in context.callees[:10])
            )

        if context.imports:
            parts.append(
                f"\nFile imports:\n" + "\n".join(f"  - {i}" for i in context.imports[:10])
            )

        if not parts:
            return "No call graph context available."

        return "\n".join(parts)
