-- Eidolon MVP Database Schema
-- Agent Memory System

-- ============================================================================
-- AGENT MEMORY TABLES
-- ============================================================================

-- Registry of all agents
CREATE TABLE agent_memories (
    agent_id VARCHAR(500) PRIMARY KEY,  -- e.g., "function:auth.login.validate_token"
    agent_type VARCHAR(50) NOT NULL,     -- "function" | "module" | "class" | "system"
    scope JSONB NOT NULL,                -- What code this agent is responsible for
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_agent_memories_type ON agent_memories(agent_type);

-- All analyses performed by agents
CREATE TABLE agent_analyses (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(500) NOT NULL REFERENCES agent_memories(agent_id),
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    commit_sha VARCHAR(64) NOT NULL,
    trigger VARCHAR(100) NOT NULL,       -- "initial_audit" | "code_change" | "cross_agent_question" | "manual"
    findings JSONB NOT NULL,             -- Array of Finding objects
    reasoning TEXT NOT NULL,             -- Agent's explanation of its analysis
    confidence FLOAT,                    -- 0.0 to 1.0
    llm_prompt TEXT,                     -- The prompt sent to LLM
    llm_response TEXT,                   -- Raw LLM response
    metadata JSONB,                      -- Additional context
    was_correct BOOLEAN DEFAULT TRUE,    -- Updated when agent is proven wrong
    correction_timestamp TIMESTAMP,      -- When correction was made
    correction_id INTEGER               -- Link to agent_corrections
);

CREATE INDEX idx_analyses_agent ON agent_analyses(agent_id);
CREATE INDEX idx_analyses_commit ON agent_analyses(commit_sha);
CREATE INDEX idx_analyses_timestamp ON agent_analyses(timestamp DESC);
CREATE INDEX idx_analyses_trigger ON agent_analyses(trigger);

-- Agent corrections (when proven wrong)
CREATE TABLE agent_corrections (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(500) NOT NULL REFERENCES agent_memories(agent_id),
    original_analysis_id INTEGER NOT NULL REFERENCES agent_analyses(id),
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    trigger VARCHAR(200) NOT NULL,       -- What caused the correction
    new_findings JSONB NOT NULL,         -- Updated findings
    reasoning TEXT NOT NULL,             -- Why the original was wrong
    learned_lessons JSONB               -- What agent learned from mistake
);

CREATE INDEX idx_corrections_agent ON agent_corrections(agent_id);
CREATE INDEX idx_corrections_original ON agent_corrections(original_analysis_id);

-- Link back from original analysis to correction
ALTER TABLE agent_analyses
ADD CONSTRAINT fk_correction
FOREIGN KEY (correction_id) REFERENCES agent_corrections(id);

-- Agent conversations (with humans or other agents)
CREATE TABLE agent_conversations (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(500) NOT NULL REFERENCES agent_memories(agent_id),
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    from_agent VARCHAR(500),             -- Agent ID or "human:username"
    from_human VARCHAR(200),             -- Username if human
    message TEXT NOT NULL,               -- Question or statement
    response TEXT NOT NULL,              -- Agent's response
    context JSONB,                       -- Related analyses, etc.
    related_analysis_ids INTEGER[]       -- Analyses referenced in response
);

CREATE INDEX idx_conversations_agent ON agent_conversations(agent_id);
CREATE INDEX idx_conversations_timestamp ON agent_conversations(timestamp DESC);
CREATE INDEX idx_conversations_from ON agent_conversations(from_agent);

-- Agent decisions (specific conclusions)
CREATE TABLE agent_decisions (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(500) NOT NULL REFERENCES agent_memories(agent_id),
    analysis_id INTEGER REFERENCES agent_analyses(id),
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    question TEXT NOT NULL,              -- What was decided
    answer TEXT NOT NULL,                -- The decision
    confidence FLOAT,                    -- 0.0 to 1.0
    reasoning TEXT NOT NULL,             -- Why this decision
    was_correct BOOLEAN DEFAULT TRUE,    -- Updated if proven wrong
    correction_timestamp TIMESTAMP,
    correction TEXT                      -- What was actually correct
);

CREATE INDEX idx_decisions_agent ON agent_decisions(agent_id);
CREATE INDEX idx_decisions_analysis ON agent_decisions(analysis_id);

-- ============================================================================
-- AUDIT RUN TABLES
-- ============================================================================

-- Top-level audit runs
CREATE TABLE audit_runs (
    id SERIAL PRIMARY KEY,
    repo_path VARCHAR(500) NOT NULL,
    commit_sha VARCHAR(64),
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    status VARCHAR(50) NOT NULL,         -- "running" | "completed" | "failed"
    total_modules INTEGER,
    total_functions INTEGER,
    total_findings INTEGER,
    llm_provider VARCHAR(50),            -- "anthropic" | "openai" | null
    llm_model VARCHAR(100),
    error TEXT,                          -- If failed
    metadata JSONB
);

CREATE INDEX idx_runs_repo ON audit_runs(repo_path);
CREATE INDEX idx_runs_status ON audit_runs(status);
CREATE INDEX idx_runs_started ON audit_runs(started_at DESC);

-- Findings from audit runs
CREATE TABLE findings (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES audit_runs(id),
    agent_id VARCHAR(500) REFERENCES agent_memories(agent_id),
    analysis_id INTEGER REFERENCES agent_analyses(id),

    location VARCHAR(500) NOT NULL,      -- "file:line" or "file:line:column"
    severity VARCHAR(20) NOT NULL,       -- "critical" | "high" | "medium" | "low" | "info"
    type VARCHAR(50) NOT NULL,           -- "bug" | "security" | "performance" | "architecture" | "style"

    description TEXT NOT NULL,
    suggested_fix TEXT,
    code_snippet TEXT,                   -- The problematic code

    status VARCHAR(50) NOT NULL DEFAULT 'new',  -- "new" | "confirmed" | "false_positive" | "fixed" | "wont_fix" | "duplicate"
    assigned_to VARCHAR(100),
    resolved_at TIMESTAMP,
    resolved_by VARCHAR(100),
    resolution_notes TEXT,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_findings_run ON findings(run_id);
CREATE INDEX idx_findings_agent ON findings(agent_id);
CREATE INDEX idx_findings_severity ON findings(severity);
CREATE INDEX idx_findings_type ON findings(type);
CREATE INDEX idx_findings_status ON findings(status);
CREATE INDEX idx_findings_location ON findings(location);

-- ============================================================================
-- AGENT RELATIONSHIPS
-- ============================================================================

-- Agent hierarchy (parent-child relationships)
CREATE TABLE agent_hierarchy (
    parent_agent_id VARCHAR(500) NOT NULL REFERENCES agent_memories(agent_id),
    child_agent_id VARCHAR(500) NOT NULL REFERENCES agent_memories(agent_id),
    relationship_type VARCHAR(50) NOT NULL,  -- "coordinates" | "delegates_to"
    created_at TIMESTAMP DEFAULT NOW(),

    PRIMARY KEY (parent_agent_id, child_agent_id)
);

CREATE INDEX idx_hierarchy_parent ON agent_hierarchy(parent_agent_id);
CREATE INDEX idx_hierarchy_child ON agent_hierarchy(child_agent_id);

-- Agent dependencies (what agents reference each other)
CREATE TABLE agent_dependencies (
    source_agent_id VARCHAR(500) NOT NULL REFERENCES agent_memories(agent_id),
    target_agent_id VARCHAR(500) NOT NULL REFERENCES agent_memories(agent_id),
    dependency_type VARCHAR(50) NOT NULL,    -- "calls" | "imports" | "references"
    confidence FLOAT,
    discovered_at TIMESTAMP DEFAULT NOW(),

    PRIMARY KEY (source_agent_id, target_agent_id, dependency_type)
);

CREATE INDEX idx_deps_source ON agent_dependencies(source_agent_id);
CREATE INDEX idx_deps_target ON agent_dependencies(target_agent_id);

-- ============================================================================
-- HELPER VIEWS
-- ============================================================================

-- Latest analysis per agent
CREATE VIEW agent_latest_analyses AS
SELECT DISTINCT ON (agent_id)
    agent_id,
    id AS analysis_id,
    timestamp,
    commit_sha,
    findings,
    reasoning,
    confidence,
    was_correct
FROM agent_analyses
ORDER BY agent_id, timestamp DESC;

-- Agent health summary
CREATE VIEW agent_health_summary AS
SELECT
    am.agent_id,
    am.agent_type,
    COUNT(DISTINCT aa.id) AS total_analyses,
    COUNT(DISTINCT CASE WHEN aa.was_correct = FALSE THEN aa.id END) AS incorrect_analyses,
    AVG(aa.confidence) AS avg_confidence,
    MAX(aa.timestamp) AS last_analyzed,
    COUNT(DISTINCT ac.id) AS total_corrections,
    COUNT(DISTINCT f.id) AS total_findings
FROM agent_memories am
LEFT JOIN agent_analyses aa ON am.agent_id = aa.agent_id
LEFT JOIN agent_corrections ac ON am.agent_id = ac.agent_id
LEFT JOIN findings f ON am.agent_id = f.agent_id AND f.status = 'new'
GROUP BY am.agent_id, am.agent_type;

-- Finding summary by run
CREATE VIEW run_findings_summary AS
SELECT
    ar.id AS run_id,
    ar.repo_path,
    ar.status AS run_status,
    COUNT(f.id) AS total_findings,
    COUNT(CASE WHEN f.severity = 'critical' THEN 1 END) AS critical_count,
    COUNT(CASE WHEN f.severity = 'high' THEN 1 END) AS high_count,
    COUNT(CASE WHEN f.severity = 'medium' THEN 1 END) AS medium_count,
    COUNT(CASE WHEN f.severity = 'low' THEN 1 END) AS low_count,
    COUNT(CASE WHEN f.type = 'bug' THEN 1 END) AS bug_count,
    COUNT(CASE WHEN f.type = 'security' THEN 1 END) AS security_count,
    COUNT(CASE WHEN f.type = 'architecture' THEN 1 END) AS architecture_count,
    COUNT(CASE WHEN f.status = 'new' THEN 1 END) AS unresolved_count
FROM audit_runs ar
LEFT JOIN findings f ON ar.id = f.run_id
GROUP BY ar.id, ar.repo_path, ar.status;

-- Agent conversation history (most recent first)
CREATE VIEW agent_recent_conversations AS
SELECT
    agent_id,
    timestamp,
    from_agent,
    from_human,
    LEFT(message, 200) AS message_preview,
    LEFT(response, 200) AS response_preview
FROM agent_conversations
ORDER BY timestamp DESC
LIMIT 100;

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Update agent's updated_at timestamp
CREATE OR REPLACE FUNCTION update_agent_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE agent_memories
    SET updated_at = NOW()
    WHERE agent_id = NEW.agent_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger on new analysis
CREATE TRIGGER trigger_update_agent_on_analysis
AFTER INSERT ON agent_analyses
FOR EACH ROW
EXECUTE FUNCTION update_agent_timestamp();

-- Trigger on new conversation
CREATE TRIGGER trigger_update_agent_on_conversation
AFTER INSERT ON agent_conversations
FOR EACH ROW
EXECUTE FUNCTION update_agent_timestamp();

-- Update findings updated_at on status change
CREATE OR REPLACE FUNCTION update_finding_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_finding_timestamp
BEFORE UPDATE ON findings
FOR EACH ROW
EXECUTE FUNCTION update_finding_timestamp();

-- ============================================================================
-- SAMPLE QUERIES
-- ============================================================================

-- Get all analyses for a function agent
/*
SELECT
    aa.timestamp,
    aa.commit_sha,
    aa.trigger,
    jsonb_array_length(aa.findings) AS finding_count,
    aa.confidence,
    aa.was_correct
FROM agent_analyses aa
WHERE aa.agent_id = 'function:auth.login.validate_token'
ORDER BY aa.timestamp DESC;
*/

-- Get all corrections an agent has made
/*
SELECT
    ac.timestamp,
    aa.timestamp AS original_timestamp,
    aa.reasoning AS original_reasoning,
    ac.reasoning AS correction_reasoning,
    ac.trigger
FROM agent_corrections ac
JOIN agent_analyses aa ON ac.original_analysis_id = aa.id
WHERE ac.agent_id = 'function:auth.login.validate_token'
ORDER BY ac.timestamp DESC;
*/

-- Get conversation history for an agent
/*
SELECT
    timestamp,
    from_agent,
    from_human,
    message,
    response
FROM agent_conversations
WHERE agent_id = 'function:auth.login.validate_token'
ORDER BY timestamp DESC
LIMIT 10;
*/

-- Get all critical findings from latest run
/*
SELECT
    f.location,
    f.severity,
    f.type,
    f.description,
    am.agent_id
FROM findings f
JOIN agent_memories am ON f.agent_id = am.agent_id
WHERE f.run_id = (SELECT MAX(id) FROM audit_runs)
  AND f.severity = 'critical'
  AND f.status = 'new'
ORDER BY f.location;
*/

-- Get agents that have made the most corrections (learning curve)
/*
SELECT
    am.agent_id,
    am.agent_type,
    COUNT(ac.id) AS correction_count,
    jsonb_agg(ac.learned_lessons) AS all_lessons
FROM agent_memories am
JOIN agent_corrections ac ON am.agent_id = ac.agent_id
GROUP BY am.agent_id, am.agent_type
ORDER BY correction_count DESC
LIMIT 20;
*/
