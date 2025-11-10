# Claude Agent SDK Integration Guide

## Overview

The Claude Agent SDK can be integrated in two ways:
1. **TypeScript/Node.js SDK** - Official SDK with full features
2. **Python SDK** - Python bindings (if available)
3. **CLI Bridge** - Call Claude Code CLI from Python

## Current Status

✅ Python package `claude-agent-sdk==0.1.6` installed
❓ Need to verify if it's full SDK or just API wrapper
🔧 May need to use TypeScript SDK via subprocess

## Integration Options

### Option 1: Python SDK (Preferred if available)

```python
from claude_agent_sdk import ClaudeAgent

agent = ClaudeAgent(
    name="analyzer",
    system_prompt="You are a code analyzer...",
    working_directory="/tmp/agent-workspace",
    allowed_tools=["read", "write", "bash"],
)

response = await agent.run("Analyze this function...")
```

### Option 2: TypeScript SDK via Subprocess

If Python SDK is limited, use Node.js SDK:

```python
import asyncio
import json
from pathlib import Path

class ClaudeAgentBridge:
    """Bridge to TypeScript Claude Agent SDK."""

    async def spawn_agent(self, config: dict) -> str:
        """Spawn agent using Node.js SDK."""

        # Create agent config file
        config_file = Path(f"/tmp/agent-{config['name']}.json")
        config_file.write_text(json.dumps(config))

        # Run Node.js script that uses SDK
        proc = await asyncio.create_subprocess_exec(
            "node",
            "scripts/spawn_agent.js",
            str(config_file),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(f"Failed to spawn agent: {stderr.decode()}")

        # Return agent ID
        return stdout.decode().strip()

    async def send_message(self, agent_id: str, message: str) -> str:
        """Send message to agent."""

        # Write message to file
        msg_file = Path(f"/tmp/agent-{agent_id}-msg.txt")
        msg_file.write_text(message)

        # Run Node.js script
        proc = await asyncio.create_subprocess_exec(
            "node",
            "scripts/send_message.js",
            agent_id,
            str(msg_file),
            stdout=asyncio.subprocess.PIPE,
        )

        stdout, _ = await proc.communicate()
        return stdout.decode()
```

### Option 3: Claude Code CLI Bridge

Use the `claude-code` CLI directly:

```python
import asyncio
import tempfile
from pathlib import Path

class ClaudeCodeCLI:
    """Bridge to Claude Code CLI."""

    async def run_agent(
        self,
        task: str,
        workspace: Path,
        system_prompt: str = "",
    ) -> str:
        """Run Claude Code with a task."""

        # Create workspace
        workspace.mkdir(parents=True, exist_ok=True)

        # Write system prompt if provided
        if system_prompt:
            claude_md = workspace / ".claude" / "CLAUDE.md"
            claude_md.parent.mkdir(parents=True, exist_ok=True)
            claude_md.write_text(system_prompt)

        # Write task file
        task_file = workspace / "task.txt"
        task_file.write_text(task)

        # Run Claude Code
        proc = await asyncio.create_subprocess_exec(
            "claude-code",
            "--message", f"Complete the task in {task_file}",
            "--cwd", str(workspace),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(f"Claude Code failed: {stderr.decode()}")

        return stdout.decode()
```

## Recommended Approach

### Phase 1: Verify Python SDK Capabilities

```python
# Test what the Python SDK can do
import claude_agent_sdk

# Check available classes/functions
print(dir(claude_agent_sdk))

# Try basic usage
try:
    agent = claude_agent_sdk.ClaudeAgent(...)
    # Success - use Python SDK
except AttributeError:
    # Fall back to subprocess approach
    pass
```

### Phase 2: Implement Hybrid Approach

Support both modes:

```python
class AgentBackend:
    """Abstract backend for agent execution."""

    async def spawn_agent(self, config): ...
    async def send_message(self, agent_id, message): ...

class PythonSDKBackend(AgentBackend):
    """Use Python SDK directly."""
    # Implement using claude_agent_sdk

class NodeSDKBackend(AgentBackend):
    """Use Node.js SDK via subprocess."""
    # Implement via process communication

class CLIBackend(AgentBackend):
    """Use Claude Code CLI."""
    # Implement via claude-code command

# Auto-detect best backend
backend = detect_best_backend()
orchestrator = AgentOrchestrator(backend=backend)
```

### Phase 3: Feature Parity

Ensure all backends support:
- Agent spawning
- Message passing
- Workspace isolation
- Tool permissions
- Skill loading
- Session persistence

## Installation

### TypeScript SDK

```bash
npm install @anthropic-ai/claude-agent-sdk
```

### Python SDK

```bash
pip install claude-agent-sdk
# or
uv add claude-agent-sdk
```

### Claude Code CLI

Already available in your environment as `claude-code`.

## Testing

Create tests to verify each backend:

```python
async def test_backend(backend: AgentBackend):
    """Test agent backend functionality."""

    # Test agent spawning
    agent_id = await backend.spawn_agent({
        "name": "test-agent",
        "system_prompt": "You are a test agent.",
        "workspace": "/tmp/test",
    })

    # Test message passing
    response = await backend.send_message(
        agent_id,
        "What is 2+2?"
    )

    assert "4" in response.lower()

    # Test cleanup
    await backend.cleanup_agent(agent_id)
```

## Current Setup

We have:
✅ Orchestrator architecture designed
✅ Message passing framework
✅ Logging and observability
✅ Python SDK installed
❓ Need to verify SDK capabilities

Next steps:
1. Test Python SDK to see what it provides
2. Implement appropriate backend
3. Test with simple agent tasks
4. Scale to parallel agents

## Fallback: Keep Current LLM System

If Claude Agent SDK integration is complex, we can:

1. **Keep existing LLM client** for simple tasks
2. **Use Agent SDK** for complex refactoring that needs iteration
3. **Support both modes**:
   - `--mode=api` - Use remote LLM (current system)
   - `--mode=agents` - Use Claude Agent SDK
   - `--mode=hybrid` - Use both (agents for complex, API for simple)

This gives us:
- Immediate value from current system
- Progressive enhancement with agents
- Flexibility for users without Claude Code

## Configuration

```python
# config.yaml
agent_mode: "hybrid"  # api | agents | hybrid

backends:
  api:
    provider: "openrouter"
    model: "anthropic/claude-3.5-sonnet"

  agents:
    backend: "auto"  # python-sdk | node-sdk | cli | auto
    max_parallel: 10
    workspace_base: "/tmp/eidolon/agents"

  hybrid:
    use_agents_for:
      - refactoring
      - test_generation
      - complex_analysis
    use_api_for:
      - simple_analysis
      - quick_checks
```

## Summary

**Best case**: Python SDK works → Use it directly

**Good case**: Node SDK via subprocess → Some overhead but full features

**Acceptable case**: Claude Code CLI → Simple but effective

**Always available**: Current LLM API system as fallback

We'll support all modes for maximum flexibility!
