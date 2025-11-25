import json
import aiosqlite
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pathlib import Path

from eidolon.models import Card, Agent


class Database:
    """Simple SQLite-based storage for cards and agents"""

    def __init__(self, db_path: str = "monad.db"):
        self.db_path = db_path
        self.db: Optional[aiosqlite.Connection] = None
        # Serialize transactional operations to avoid nested transaction errors
        self._txn_lock = asyncio.Lock()
        # Serialize all cursor usage; aiosqlite connection is not concurrent-safe
        self._db_lock = asyncio.Lock()

    async def connect(self):
        """Initialize database connection and create tables"""
        async with self._db_lock:
            self.db = await aiosqlite.connect(self.db_path)
            self.db.row_factory = aiosqlite.Row
            await self._create_tables()

    async def close(self):
        """Close database connection"""
        if self.db:
            async with self._db_lock:
                await self.db.close()

    async def _create_tables(self):
        """Create database tables if they don't exist"""
        async with self.db.cursor() as cursor:
            # Cards table
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS cards (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT,
                    status TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    owner_agent TEXT,
                    parent TEXT,
                    children TEXT,
                    issues TEXT,
                    links TEXT,
                    metrics TEXT,
                    log TEXT,
                    routing TEXT,
                    proposed_fix TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Best-effort column add for existing databases
            await self._ensure_column("cards", "issues", "TEXT")

            # Agents table
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS agents (
                    id TEXT PRIMARY KEY,
                    scope TEXT NOT NULL,
                    target TEXT NOT NULL,
                    status TEXT NOT NULL,
                    parent_id TEXT,
                    children_ids TEXT,
                    session_id TEXT,
                    messages TEXT,
                    snapshots TEXT,
                    findings TEXT,
                    cards_created TEXT,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    total_tokens INTEGER DEFAULT 0,
                    total_cost REAL DEFAULT 0.0
                )
            """)

            # Card sequences for ID generation
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS sequences (
                    name TEXT PRIMARY KEY,
                    value INTEGER DEFAULT 0
                )
            """)

            # Analysis sessions for incremental analysis tracking
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_sessions (
                    id TEXT PRIMARY KEY,
                    path TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    git_commit TEXT,
                    git_branch TEXT,
                    files_analyzed TEXT,
                    files_skipped TEXT,
                    total_modules INTEGER DEFAULT 0,
                    total_functions INTEGER DEFAULT 0,
                    cache_hits INTEGER DEFAULT 0,
                    cache_misses INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                )
            """)

            # Create indices for faster queries
            await cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_cards_status ON cards(status)
            """)
            await cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_cards_owner ON cards(owner_agent)
            """)
            await cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_cards_type ON cards(type)
            """)
            await cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status)
            """)
            await cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_agents_parent ON agents(parent_id)
            """)
            await cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_agents_scope ON agents(scope)
            """)

        await self.db.commit()

    async def _get_next_sequence(self, name: str) -> int:
        """
        Get next sequence number for ID generation (thread-safe)

        Uses UPDATE...RETURNING to avoid race conditions in concurrent environments.
        """
        async with self._db_lock:
            async with self._txn_lock:
                # Ensure sequence exists
                await self.db.execute(
                    "INSERT OR IGNORE INTO sequences (name, value) VALUES (?, 0)",
                    (name,)
                )
            # Atomic increment and return
            cursor = await self.db.execute(
                "UPDATE sequences SET value = value + 1 WHERE name = ? RETURNING value",
                (name,)
            )
            result = await cursor.fetchone()
            await self.db.commit()
            return result[0]

    async def generate_card_id(self, card_type: str) -> str:
        """Generate a unique card ID"""
        year = datetime.now(timezone.utc).year
        seq = await self._get_next_sequence(f"card_{card_type}")
        return f"Eidolon-{year}-{card_type.upper()[:3]}-{seq:04d}"

    async def generate_agent_id(self, scope: str) -> str:
        """Generate a unique agent ID"""
        seq = await self._get_next_sequence(f"agent_{scope}")
        return f"AGN-{scope.upper()[:3]}-{seq:04d}"

    # Card operations
    async def create_card(self, card: Card) -> Card:
        """Create a new card"""
        if not card.id or not card.id.startswith("Eidolon-"):
            card.id = await self.generate_card_id(card.type)

        async with self._db_lock:
            async with self.db.cursor() as cursor:
                await cursor.execute("""
                    INSERT INTO cards (
                        id, type, title, summary, status, priority, owner_agent,
                        parent, children, issues, links, metrics, log, routing,
                        proposed_fix, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    card.id,
                    card.type,
                    card.title,
                    card.summary,
                    card.status,
                    card.priority,
                    card.owner_agent,
                    card.parent,
                    json.dumps(card.children),
                    json.dumps([issue.model_dump() for issue in card.issues]),
                    json.dumps(card.links.model_dump()),
                    json.dumps(card.metrics.model_dump()),
                    json.dumps([log.model_dump() for log in card.log], default=str),
                    json.dumps(card.routing.model_dump()),
                    json.dumps(card.proposed_fix.model_dump()) if card.proposed_fix else None,
                    card.created_at.isoformat(),
                    card.updated_at.isoformat()
                ))
                await self.db.commit()

        return card

    async def get_card(self, card_id: str) -> Optional[Card]:
        """Get a card by ID"""
        async with self._db_lock:
            async with self.db.cursor() as cursor:
                await cursor.execute("SELECT * FROM cards WHERE id = ?", (card_id,))
                row = await cursor.fetchone()

        if not row:
            return None

        return self._row_to_card(row)

    async def get_all_cards(self, filters: Optional[Dict[str, Any]] = None) -> List[Card]:
        """Get all cards with optional filters"""
        query = "SELECT * FROM cards"
        params = []

        if filters:
            conditions = []
            if "type" in filters:
                conditions.append("type = ?")
                params.append(filters["type"])
            if "status" in filters:
                conditions.append("status = ?")
                params.append(filters["status"])
            if "owner_agent" in filters:
                conditions.append("owner_agent = ?")
                params.append(filters["owner_agent"])

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created_at DESC"

        async with self._db_lock:
            async with self.db.cursor() as cursor:
                await cursor.execute(query, params)
                rows = await cursor.fetchall()

        return [self._row_to_card(row) for row in rows]

    async def update_card(self, card: Card) -> Card:
        """Update an existing card"""
        card.updated_at = datetime.now(timezone.utc)

        async with self._db_lock:
            async with self.db.cursor() as cursor:
                await cursor.execute("""
                    UPDATE cards SET
                        type = ?, title = ?, summary = ?, status = ?, priority = ?,
                        owner_agent = ?, parent = ?, children = ?, issues = ?, links = ?,
                        metrics = ?, log = ?, routing = ?, proposed_fix = ?, updated_at = ?
                    WHERE id = ?
                """, (
                    card.type,
                    card.title,
                    card.summary,
                    card.status,
                    card.priority,
                    card.owner_agent,
                    card.parent,
                    json.dumps(card.children),
                    json.dumps([issue.model_dump() for issue in card.issues]),
                    json.dumps(card.links.model_dump()),
                    json.dumps(card.metrics.model_dump()),
                    json.dumps([log.model_dump() for log in card.log], default=str),
                    json.dumps(card.routing.model_dump()),
                    json.dumps(card.proposed_fix.model_dump()) if card.proposed_fix else None,
                    card.updated_at.isoformat(),
                    card.id
                ))
                await self.db.commit()

        return card

    async def delete_card(self, card_id: str):
        """Delete a card"""
        async with self._db_lock:
            async with self.db.cursor() as cursor:
                await cursor.execute("DELETE FROM cards WHERE id = ?", (card_id,))
                await self.db.commit()

    # Agent operations
    async def create_agent(self, agent: Agent) -> Agent:
        """Create a new agent"""
        if not agent.id or not agent.id.startswith("AGN-"):
            agent.id = await self.generate_agent_id(agent.scope)

        async with self._db_lock:
            async with self.db.cursor() as cursor:
                await cursor.execute("""
                    INSERT INTO agents (
                        id, scope, target, status, parent_id, children_ids,
                        session_id, messages, snapshots, findings, cards_created,
                        created_at, started_at, completed_at, total_tokens, total_cost
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    agent.id,
                    agent.scope,
                    agent.target,
                    agent.status,
                    agent.parent_id,
                    json.dumps(agent.children_ids),
                    agent.session_id,
                    json.dumps([msg.model_dump() for msg in agent.messages], default=str),
                    json.dumps([snap.model_dump() for snap in agent.snapshots], default=str),
                    json.dumps(agent.findings),
                    json.dumps(agent.cards_created),
                    agent.created_at.isoformat(),
                    agent.started_at.isoformat() if agent.started_at else None,
                    agent.completed_at.isoformat() if agent.completed_at else None,
                    agent.total_tokens,
                    agent.total_cost
                ))
                await self.db.commit()

        return agent

    async def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get an agent by ID"""
        async with self._db_lock:
            async with self.db.cursor() as cursor:
                await cursor.execute("SELECT * FROM agents WHERE id = ?", (agent_id,))
                row = await cursor.fetchone()

        if not row:
            return None

        return self._row_to_agent(row)

    async def get_all_agents(self) -> List[Agent]:
        """Get all agents"""
        async with self._db_lock:
            async with self.db.cursor() as cursor:
                await cursor.execute("SELECT * FROM agents ORDER BY created_at DESC")
                rows = await cursor.fetchall()

        return [self._row_to_agent(row) for row in rows]

    async def update_agent(self, agent: Agent) -> Agent:
        """Update an existing agent"""
        async with self._db_lock:
            async with self.db.cursor() as cursor:
                await cursor.execute("""
                    UPDATE agents SET
                        scope = ?, target = ?, status = ?, parent_id = ?,
                        children_ids = ?, session_id = ?, messages = ?,
                        snapshots = ?, findings = ?, cards_created = ?,
                        started_at = ?, completed_at = ?, total_tokens = ?,
                        total_cost = ?
                    WHERE id = ?
                """, (
                    agent.scope,
                    agent.target,
                    agent.status,
                    agent.parent_id,
                    json.dumps(agent.children_ids),
                    agent.session_id,
                    json.dumps([msg.dict() for msg in agent.messages], default=str),
                    json.dumps([snap.dict() for snap in agent.snapshots], default=str),
                    json.dumps(agent.findings),
                    json.dumps(agent.cards_created),
                    agent.started_at.isoformat() if agent.started_at else None,
                    agent.completed_at.isoformat() if agent.completed_at else None,
                    agent.total_tokens,
                    agent.total_cost,
                    agent.id
                ))
                await self.db.commit()

        return agent

    def _row_to_card(self, row: aiosqlite.Row) -> Card:
        """Convert database row to Card model"""
        return Card(
            id=row["id"],
            type=row["type"],
            title=row["title"],
            summary=row["summary"] or "",
            status=row["status"],
            priority=row["priority"],
            owner_agent=row["owner_agent"],
            parent=row["parent"],
            children=json.loads(row["children"]),
            issues=json.loads(row["issues"]) if row["issues"] else [],
            links=json.loads(row["links"]),
            metrics=json.loads(row["metrics"]),
            log=json.loads(row["log"]),
            routing=json.loads(row["routing"]),
            proposed_fix=json.loads(row["proposed_fix"]) if row["proposed_fix"] else None,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"])
        )

    async def _ensure_column(self, table: str, column: str, column_type: str):
        """Add a column if it doesn't exist (best-effort, ignores failures)"""
        async with self.db.cursor() as cursor:
            await cursor.execute(f"PRAGMA table_info({table})")
            cols = [row[1] for row in await cursor.fetchall()]
            if column not in cols:
                try:
                    await cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
                    await self.db.commit()
                except Exception:
                    # Ignore if cannot add (e.g., duplicate) to avoid breaking startup
                    pass

    def _row_to_agent(self, row: aiosqlite.Row) -> Agent:
        """Convert database row to Agent model"""
        return Agent(
            id=row["id"],
            scope=row["scope"],
            target=row["target"],
            status=row["status"],
            parent_id=row["parent_id"],
            children_ids=json.loads(row["children_ids"]),
            session_id=row["session_id"],
            messages=json.loads(row["messages"]),
            snapshots=json.loads(row["snapshots"]),
            findings=json.loads(row["findings"]),
            cards_created=json.loads(row["cards_created"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            total_tokens=row["total_tokens"],
            total_cost=row["total_cost"]
        )

    # Analysis session operations
    async def create_analysis_session(
        self,
        session_id: str,
        path: str,
        mode: str,
        git_commit: Optional[str] = None,
        git_branch: Optional[str] = None
    ) -> str:
        """Create a new analysis session"""
        async with self._db_lock:
            async with self.db.cursor() as cursor:
                await cursor.execute("""
                    INSERT INTO analysis_sessions
                    (id, path, mode, git_commit, git_branch, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    path,
                    mode,
                    git_commit,
                    git_branch,
                    datetime.now(timezone.utc).isoformat()
                ))
                await self.db.commit()

        return session_id

    async def update_analysis_session(
        self,
        session_id: str,
        files_analyzed: List[str],
        files_skipped: List[str],
        total_modules: int,
        total_functions: int,
        cache_hits: int,
        cache_misses: int
    ):
        """Update an analysis session with completion data"""
        async with self._db_lock:
            async with self.db.cursor() as cursor:
                await cursor.execute("""
                    UPDATE analysis_sessions SET
                        files_analyzed = ?,
                        files_skipped = ?,
                        total_modules = ?,
                        total_functions = ?,
                        cache_hits = ?,
                        cache_misses = ?,
                        completed_at = ?
                    WHERE id = ?
                """, (
                    json.dumps(files_analyzed),
                    json.dumps(files_skipped),
                    total_modules,
                    total_functions,
                    cache_hits,
                    cache_misses,
                    datetime.now(timezone.utc).isoformat(),
                    session_id
                ))
                await self.db.commit()

    async def get_last_analysis_session(self, path: str) -> Optional[Dict[str, Any]]:
        """Get the most recent analysis session for a given path"""
        async with self._db_lock:
            async with self.db.cursor() as cursor:
                await cursor.execute("""
                    SELECT * FROM analysis_sessions
                    WHERE path = ? AND completed_at IS NOT NULL
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (path,))
                row = await cursor.fetchone()

        if not row:
            return None

        return {
            'id': row['id'],
            'path': row['path'],
            'mode': row['mode'],
            'git_commit': row['git_commit'],
            'git_branch': row['git_branch'],
            'files_analyzed': json.loads(row['files_analyzed']) if row['files_analyzed'] else [],
            'files_skipped': json.loads(row['files_skipped']) if row['files_skipped'] else [],
            'total_modules': row['total_modules'],
            'total_functions': row['total_functions'],
            'cache_hits': row['cache_hits'],
            'cache_misses': row['cache_misses'],
            'created_at': row['created_at'],
            'completed_at': row['completed_at']
        }
