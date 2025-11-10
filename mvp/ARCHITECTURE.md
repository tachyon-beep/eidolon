# MVP Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI / Web UI                         │
│              (User Interface Layer)                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│                    Agent Orchestrator                       │
│         (Spawns and coordinates agents)                     │
└────────────┬────────────────────────────────┬───────────────┘
             │                                │
             ↓                                ↓
┌────────────────────────┐      ┌────────────────────────┐
│    ModuleAgent         │      │    ModuleAgent         │
│  (src/auth/login.py)   │      │  (src/data/users.py)   │
└────────┬───────────────┘      └─────────┬──────────────┘
         │                                │
         ├─────────┬──────────┐          ├─────────┬───────┐
         ↓         ↓          ↓          ↓         ↓       ↓
    ┌─────────┐┌─────────┐┌─────────┐┌─────────┐┌────┐┌────┐
    │Function ││Function ││Function ││Function ││... ││... │
    │Agent    ││Agent    ││Agent    ││Agent    ││    ││    │
    └────┬────┘└────┬────┘└────┬────┘└────┬────┘└────┘└────┘
         │          │          │          │
         └──────────┴──────────┴──────────┘
                     │
                     ↓
         ┌───────────────────────┐
         │   AgentMemoryStore    │
         │     (Postgres)        │
         └───────────────────────┘
                     ↑
                     │
         ┌───────────┴───────────┐
         │      CodeGraph        │
         │     (Read-only)       │
         └───────────────────────┘
```

## Core Components

### 1. Agent Base Classes

```python
# src/eidolon/agents/base.py

class Agent(ABC):
    """Base class for all agents"""

    def __init__(self, agent_id: str, scope: Scope, memory_store: MemoryStore):
        self.agent_id = agent_id
        self.scope = scope
        self.memory = AgentMemory(agent_id, memory_store)
        self.findings = []

    @abstractmethod
    async def analyze(self) -> List[Finding]:
        """Run analysis on this agent's scope"""
        pass

    def report(self) -> Report:
        """Generate report of findings"""
        pass

    async def handle_question(self, question: Question) -> Answer:
        """Answer questions about previous analyses"""
        pass

    async def correct_analysis(self, correction: Correction):
        """Record a correction to previous analysis"""
        pass
```

### 2. Agent Memory System

```python
# src/eidolon/memory/agent_memory.py

class AgentMemory:
    """Persistent memory for an agent"""

    def __init__(self, agent_id: str, store: MemoryStore):
        self.agent_id = agent_id
        self.store = store

    def record_analysis(self, analysis: Analysis):
        """Store an analysis"""
        self.store.save_analysis(self.agent_id, analysis)

    def get_analyses(self,
                     commit_sha: Optional[str] = None,
                     after: Optional[datetime] = None) -> List[Analysis]:
        """Retrieve past analyses"""
        return self.store.get_analyses(
            agent_id=self.agent_id,
            commit_sha=commit_sha,
            after=after
        )

    def record_conversation(self, conversation: Conversation):
        """Store agent conversation"""
        self.store.save_conversation(self.agent_id, conversation)

    def record_correction(self,
                         original_analysis_id: int,
                         correction: Correction):
        """Record when agent corrects previous analysis"""
        self.store.mark_incorrect(original_analysis_id)
        self.store.save_correction(self.agent_id, correction)
```

### 3. Concrete Agent Implementations

#### FunctionAgent

```python
# src/eidolon/agents/function_agent.py

class FunctionAgent(Agent):
    """Analyzes a single function for bugs"""

    def __init__(self,
                 function_id: str,
                 codegraph: CodeGraph,
                 llm: LLMClient,
                 memory_store: MemoryStore):
        super().__init__(
            agent_id=f"function:{function_id}",
            scope=Scope(type="function", id=function_id),
            memory_store=memory_store
        )
        self.codegraph = codegraph
        self.llm = llm

    async def analyze(self) -> List[Finding]:
        """Deep analysis of function"""

        # Get function from CodeGraph
        function = self.codegraph.get_function(self.scope.id)

        # Check if we've analyzed this before
        previous = self.memory.get_analyses(
            commit_sha=function.commit_sha
        )

        # Static checks
        findings = []
        findings += self._check_complexity(function)
        findings += self._check_unclosed_resources(function)
        findings += self._check_null_safety(function)

        # LLM deep analysis
        if self.llm:
            llm_findings = await self._llm_analyze(
                function,
                previous_analyses=previous
            )
            findings += llm_findings

        # Record this analysis
        analysis = Analysis(
            timestamp=datetime.utcnow(),
            commit_sha=function.commit_sha,
            trigger="audit",
            findings=findings,
            reasoning=self._build_reasoning(findings),
            confidence=self._calculate_confidence(findings)
        )

        self.memory.record_analysis(analysis)
        self.findings = findings

        return findings

    async def _llm_analyze(self,
                          function,
                          previous_analyses: List[Analysis]) -> List[Finding]:
        """Use LLM for deep reasoning"""

        # Build context-aware prompt
        prompt = self._build_prompt(function, previous_analyses)

        # Call LLM
        response = await self.llm.complete(
            prompt,
            json_mode=True,
            cache_key=f"function:{function.id}:{function.sha256}"
        )

        # Parse findings
        return self._parse_llm_findings(response)

    async def handle_question(self, question: Question) -> Answer:
        """Answer questions about previous analyses"""

        # Load relevant analysis
        if question.about_commit:
            analyses = self.memory.get_analyses(
                commit_sha=question.about_commit
            )
        else:
            analyses = self.memory.get_analyses()
            analyses = analyses[:5]  # Most recent 5

        if not analyses:
            return Answer(
                text="I haven't analyzed this yet",
                confidence=1.0
            )

        # Use LLM to answer based on stored analyses
        prompt = f"""
        Question: {question.text}

        My previous analyses:
        {self._format_analyses(analyses)}

        Answer the question based on my previous analyses.
        If I made a mistake, acknowledge it.
        """

        response = await self.llm.complete(prompt)

        # Record this conversation
        self.memory.record_conversation(Conversation(
            timestamp=datetime.utcnow(),
            from_agent=question.from_agent,
            question=question.text,
            answer=response
        ))

        return Answer(
            text=response,
            supporting_analyses=analyses
        )
```

#### ModuleAgent

```python
# src/eidolon/agents/module_agent.py

class ModuleAgent(Agent):
    """Analyzes a module by coordinating function agents"""

    def __init__(self,
                 module_path: str,
                 codegraph: CodeGraph,
                 llm: LLMClient,
                 memory_store: MemoryStore):
        super().__init__(
            agent_id=f"module:{module_path}",
            scope=Scope(type="module", path=module_path),
            memory_store=memory_store
        )
        self.codegraph = codegraph
        self.llm = llm
        self.function_agents = []

    async def analyze(self) -> List[Finding]:
        """Coordinate function agents"""

        # Get all functions in module
        functions = self.codegraph.get_functions_in_module(
            self.scope.path
        )

        print(f"Module {self.scope.path}: {len(functions)} functions")

        # Spawn function agents
        self.function_agents = [
            FunctionAgent(fn.id, self.codegraph, self.llm, self.memory.store)
            for fn in functions
        ]

        # Run all function agents in parallel
        results = await asyncio.gather(*[
            agent.analyze()
            for agent in self.function_agents
        ])

        # Aggregate findings
        all_findings = []
        for findings in results:
            all_findings.extend(findings)

        # Module-level checks
        module_findings = await self._check_module_architecture()
        all_findings.extend(module_findings)

        # Record analysis
        analysis = Analysis(
            timestamp=datetime.utcnow(),
            commit_sha=self._get_module_commit_sha(),
            trigger="audit",
            findings=all_findings,
            reasoning=self._summarize_findings(all_findings),
            metadata={
                "function_count": len(functions),
                "functions_with_bugs": sum(
                    1 for r in results if r
                )
            }
        )

        self.memory.record_analysis(analysis)
        self.findings = all_findings

        return all_findings

    async def _check_module_architecture(self) -> List[Finding]:
        """Check architectural rules"""
        findings = []

        # Get imports
        imports = self.codegraph.get_imports(self.scope.path)

        # Check against rulepacks
        # (This is where existing Rulepack DSL integrates)
        violations = self._check_import_rules(imports)

        for violation in violations:
            findings.append(Finding(
                location=f"{self.scope.path}:1",
                severity="high",
                type="architecture",
                description=violation.description,
                agent_id=self.agent_id
            ))

        return findings

    def report(self) -> Report:
        """Enhanced report with hierarchy"""
        return Report(
            agent_id=self.agent_id,
            scope=self.scope,
            findings=self.findings,
            children=[
                agent.report()
                for agent in self.function_agents
            ],
            summary=self._build_summary()
        )
```

### 4. LLM Integration

```python
# src/eidolon/llm/client.py

class LLMClient:
    """Unified interface for LLM providers"""

    def __init__(self,
                 provider: str = "anthropic",
                 model: str = "claude-3-5-sonnet-20241022",
                 cache_enabled: bool = True):
        self.provider = provider
        self.model = model
        self.cache = Cache() if cache_enabled else None

    async def complete(self,
                      prompt: str,
                      json_mode: bool = False,
                      cache_key: Optional[str] = None) -> str:
        """Call LLM with caching and retries"""

        # Check cache
        if cache_key and self.cache:
            cached = await self.cache.get(cache_key)
            if cached:
                return cached

        # Call provider
        if self.provider == "anthropic":
            response = await self._anthropic_call(prompt, json_mode)
        elif self.provider == "openai":
            response = await self._openai_call(prompt, json_mode)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

        # Store in cache
        if cache_key and self.cache:
            await self.cache.set(cache_key, response)

        return response

    async def _anthropic_call(self, prompt: str, json_mode: bool):
        """Call Anthropic API"""
        import anthropic

        client = anthropic.AsyncAnthropic()

        message = await client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )

        content = message.content[0].text

        if json_mode:
            import json
            # Extract JSON from markdown if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            return json.loads(content)

        return content
```

### 5. Memory Storage

```python
# src/eidolon/memory/store.py

class MemoryStore:
    """Persistent storage for agent memories"""

    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool = psycopg_pool.AsyncConnectionPool(dsn)

    async def save_analysis(self,
                           agent_id: str,
                           analysis: Analysis):
        """Store an analysis"""
        async with self.pool.connection() as conn:
            await conn.execute("""
                INSERT INTO agent_analyses
                (agent_id, timestamp, commit_sha, trigger,
                 findings, reasoning, confidence, llm_prompt, llm_response)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """, (
                agent_id,
                analysis.timestamp,
                analysis.commit_sha,
                analysis.trigger,
                json.dumps([f.to_dict() for f in analysis.findings]),
                analysis.reasoning,
                analysis.confidence,
                analysis.llm_prompt,
                analysis.llm_response
            ))

    async def get_analyses(self,
                          agent_id: str,
                          commit_sha: Optional[str] = None,
                          after: Optional[datetime] = None,
                          limit: int = 100) -> List[Analysis]:
        """Retrieve analyses"""
        async with self.pool.connection() as conn:
            query = """
                SELECT * FROM agent_analyses
                WHERE agent_id = $1
            """
            params = [agent_id]

            if commit_sha:
                query += " AND commit_sha = $2"
                params.append(commit_sha)

            if after:
                query += f" AND timestamp > ${len(params) + 1}"
                params.append(after)

            query += f" ORDER BY timestamp DESC LIMIT ${len(params) + 1}"
            params.append(limit)

            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()

            return [self._row_to_analysis(row) for row in rows]

    async def mark_incorrect(self, analysis_id: int):
        """Mark an analysis as incorrect"""
        async with self.pool.connection() as conn:
            await conn.execute("""
                UPDATE agent_analyses
                SET was_correct = FALSE,
                    correction_timestamp = NOW()
                WHERE id = $1
            """, (analysis_id,))

    async def save_correction(self,
                             agent_id: str,
                             correction: Correction):
        """Store a correction"""
        async with self.pool.connection() as conn:
            await conn.execute("""
                INSERT INTO agent_corrections
                (agent_id, original_analysis_id, timestamp,
                 new_findings, reasoning, trigger)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, (
                agent_id,
                correction.original_analysis_id,
                correction.timestamp,
                json.dumps([f.to_dict() for f in correction.new_findings]),
                correction.reasoning,
                correction.trigger
            ))
```

## Data Flow

### 1. Audit Run

```
1. User: eidolon audit --repo /path/to/code
2. CLI → CodeGraph: Scan repository
3. CLI → ModuleAgent.spawn(for each module)
4. ModuleAgent → FunctionAgent.spawn(for each function)
5. FunctionAgent → LLM: Analyze function
6. FunctionAgent → MemoryStore: Save analysis
7. FunctionAgent → ModuleAgent: Report findings
8. ModuleAgent → MemoryStore: Save analysis
9. ModuleAgent → CLI: Report findings
10. CLI: Display results
```

### 2. Question Agent

```
1. User: eidolon ask function:X "Why did you say Y?"
2. CLI → MemoryStore: Load agent memory
3. CLI → FunctionAgent: handle_question(...)
4. FunctionAgent → MemoryStore: Get previous analyses
5. FunctionAgent → LLM: Answer question based on history
6. FunctionAgent → MemoryStore: Save conversation
7. FunctionAgent → CLI: Return answer
8. CLI: Display answer
```

### 3. Agent Correction

```
1. ModuleAgent finds contradictory evidence
2. ModuleAgent → FunctionAgent: handle_question(challenge)
3. FunctionAgent → MemoryStore: Load original analysis
4. FunctionAgent → LLM: Re-analyze with new evidence
5. FunctionAgent detects contradiction
6. FunctionAgent → MemoryStore: mark_incorrect(original)
7. FunctionAgent → MemoryStore: save_correction(...)
8. FunctionAgent → ModuleAgent: Return corrected answer
```

## Database Schema

See `mvp/SCHEMA.sql` for complete schema.

Key tables:
- `agent_memories` - Agent registry
- `agent_analyses` - All analyses with reasoning
- `agent_conversations` - Agent Q&A history
- `agent_corrections` - When agents fix mistakes
- `audit_runs` - Top-level audit metadata
- `findings` - Actual bugs/issues found

## Integration with Existing Code

### CodeGraph
- **Read-only dependency**
- Use existing scanner for AST parsing
- Query function/module/import data
- No modifications to CodeGraph needed

### Rulepack
- **Integration point**: ModuleAgent architecture checks
- Use existing compiler to check import rules
- Extend with agent-specific rules later
- Keep existing packs working

### Orchestrator
- **Not used in MVP**
- Agents use simple asyncio for parallelism
- Can integrate later for distributed execution

## Performance Considerations

- **Parallel execution**: Function agents run concurrently (asyncio.gather)
- **LLM caching**: Cache by content hash to avoid duplicate calls
- **Database pooling**: Connection pool for all memory operations
- **Batch queries**: Load multiple analyses in single query

## Security Considerations

- **Prompt injection**: Sanitize all code before sending to LLM
- **API keys**: Load from environment, never log
- **Database access**: Use parameterized queries
- **Agent scope**: Agents can only access their assigned scope
