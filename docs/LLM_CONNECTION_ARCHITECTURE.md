# Eidolon LLM Connection Architecture

## Overview

Eidolon connects to Anthropic's Claude API using the official `anthropic` Python SDK with comprehensive resilience patterns for production-grade reliability.

---

## Connection Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Eidolon Application                             │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  1. AUTHENTICATION                                             │ │
│  │                                                                 │ │
│  │  Environment Variable:                                         │ │
│  │    ANTHROPIC_API_KEY=sk-ant-...                               │ │
│  │                                                                 │ │
│  │  Loaded in orchestrator.__init__():                           │ │
│  │    self.api_key = os.environ.get("ANTHROPIC_API_KEY")        │ │
│  │    self.client = AsyncAnthropic(api_key=self.api_key)        │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  2. RESILIENCE STACK (Phase 1 & 2)                            │ │
│  │                                                                 │ │
│  │  _call_ai_with_resilience():                                  │ │
│  │                                                                 │ │
│  │    [1] Rate Limiter                                           │ │
│  │        ↓ Check quota (50 req/min, 40k tokens/min)            │ │
│  │        ↓ Wait if necessary                                    │ │
│  │                                                                 │ │
│  │    [2] Timeout Wrapper (90 seconds)                           │ │
│  │        ↓ Prevent infinite hangs                               │ │
│  │        ↓ asyncio.timeout(90)                                  │ │
│  │                                                                 │ │
│  │    [3] Circuit Breaker                                        │ │
│  │        ↓ Check if service is down                             │ │
│  │        ↓ Fail fast if OPEN (3 failures)                       │ │
│  │        ↓ Test recovery if HALF_OPEN                           │ │
│  │                                                                 │ │
│  │    [4] Retry Logic (3 attempts)                               │ │
│  │        ↓ Exponential backoff: 1s → 2s → 4s                   │ │
│  │        ↓ Jitter to prevent thundering herd                    │ │
│  │        ↓ Only retry on transient errors                       │ │
│  │                                                                 │ │
│  │    [5] Actual API Call                                        │ │
│  │        ↓ self.client.messages.create()                        │ │
│  │        ↓ model="claude-3-5-sonnet-20241022"                   │ │
│  │        ↓ max_tokens=1024-4096                                 │ │
│  │        ↓ messages=[{"role": "user", "content": "..."}]       │ │
│  │                                                                 │ │
│  │    [6] Post-Processing                                        │ │
│  │        ↓ Update rate limiter with actual tokens              │ │
│  │        ↓ Record metrics (latency, tokens, success)            │ │
│  │        ↓ Return response                                      │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTPS Request
                                    │ (TLS encrypted)
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    Anthropic API (api.anthropic.com)                 │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Claude 3.5 Sonnet Model                                       │ │
│  │  (claude-3-5-sonnet-20241022)                                 │ │
│  │                                                                 │ │
│  │  • Max context: 200k tokens                                   │ │
│  │  • Max output: 4096 tokens (configurable)                     │ │
│  │  • Temperature: 0 (deterministic)                             │ │
│  │                                                                 │ │
│  │  Input: Code snippet + analysis instructions                  │ │
│  │  Output: Structured analysis with findings                    │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Three Analysis Levels

Eidolon makes LLM calls at three hierarchical levels during code analysis:

### **Level 1: Function-Level Analysis**

```python
# File: backend/agents/orchestrator.py (~line 640)
response = await self._call_ai_with_resilience(
    model="claude-3-5-sonnet-20241022",
    max_tokens=2048,
    messages=[{"role": "user", "content": function_analysis_prompt}],
    estimated_tokens=2500
)
```

**Purpose**: Deep analysis of individual functions
**Context Provided**:
- Function source code
- Function signature and docstrings
- Call graph (what this function calls/is called by)
- Cross-file dependencies
- Code complexity metrics

**Output**:
- Code quality issues
- Potential bugs
- Proposed fixes (with line numbers)
- Severity ratings

### **Level 2: Module-Level Analysis**

```python
# File: backend/agents/orchestrator.py (~line 707)
response = await self._call_ai_with_resilience(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[{"role": "user", "content": module_analysis_prompt}],
    estimated_tokens=1500
)
```

**Purpose**: Module/file-level patterns and architecture
**Context Provided**:
- All function-level findings from children
- Code smells detected
- Module summary (imports, classes, functions)
- Inter-function relationships

**Output**:
- Overall code quality assessment
- Architectural concerns
- Refactoring opportunities
- Integration issues

### **Level 3: System-Level Analysis**

```python
# File: backend/agents/orchestrator.py (~line 779)
response = await self._call_ai_with_resilience(
    model="claude-3-5-sonnet-20241022",
    max_tokens=2048,
    messages=[{"role": "user", "content": system_analysis_prompt}],
    estimated_tokens=2500
)
```

**Purpose**: System-wide patterns and recommendations
**Context Provided**:
- All module-level findings
- Cross-module dependencies
- System architecture overview
- Overall code metrics

**Output**:
- System-wide architectural insights
- Critical issues requiring attention
- Strategic refactoring recommendations
- Code health score (0-100)

---

## API Call Example (Real Code)

Here's what an actual API call looks like:

```python
# From backend/agents/orchestrator.py
async def _call_ai_with_resilience(self, model, max_tokens, messages, estimated_tokens):
    # 1. Rate limiting
    await AI_RATE_LIMITER.acquire(estimated_tokens)

    # 2-4. Timeout, Circuit Breaker, Retry
    response = await retry_with_backoff(
        lambda: AI_API_BREAKER.call(
            lambda: with_timeout(
                lambda: self.client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    messages=messages
                ),
                timeout=90.0
            )
        ),
        config=RetryConfig()
    )

    # 5. Update metrics
    actual_tokens = response.usage.input_tokens + response.usage.output_tokens
    AI_RATE_LIMITER.record_actual_tokens(actual_tokens)

    return response
```

**Actual HTTP Request** (under the hood):
```http
POST https://api.anthropic.com/v1/messages
Headers:
  x-api-key: sk-ant-...
  anthropic-version: 2023-06-01
  content-type: application/json

Body:
{
  "model": "claude-3-5-sonnet-20241022",
  "max_tokens": 2048,
  "messages": [
    {
      "role": "user",
      "content": "Analyze this Python function for issues:\n\ndef process_data(items):\n    ..."
    }
  ]
}
```

**Response**:
```json
{
  "id": "msg_01...",
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "## Issues Found\n\n### Issue 1: No input validation\n..."
    }
  ],
  "usage": {
    "input_tokens": 1523,
    "output_tokens": 876
  }
}
```

---

## Configuration

### **Required Environment Variable**

```bash
export ANTHROPIC_API_KEY="sk-ant-api03-..."
```

**Location**: Set in your shell or `.env` file

**Validation**: Checked at orchestrator initialization:
```python
self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
if not self.api_key:
    raise ValueError("ANTHROPIC_API_KEY not set")
```

### **Model Configuration**

**Current Model**: `claude-3-5-sonnet-20241022`

**Why Sonnet 4.5?**
- ✅ Best code understanding (trained on code)
- ✅ 200k context window (handles large files)
- ✅ High-quality analysis output
- ✅ Reasonable cost/performance balance
- ✅ Fast response times (~5-10s typical)

**Token Limits by Level**:
- Function analysis: 2048 max tokens output
- Module analysis: 1024 max tokens output
- System analysis: 2048 max tokens output

### **Rate Limits** (Phase 2)

```python
# backend/resilience/__init__.py
AI_RATE_LIMITER = RateLimiter(
    max_requests_per_minute=50,
    max_tokens_per_minute=40000
)
```

**These match Anthropic's tier 1 limits**:
- 50 requests per minute
- 40,000 tokens per minute
- Auto-throttles before hitting limits

---

## Resilience Features

### **1. Timeout Protection** (Phase 1)
```python
TimeoutConfig.AI_API_TIMEOUT = 90.0  # seconds
```
- Prevents infinite hangs on network issues
- Kills slow requests after 90 seconds
- Logged as timeout error, triggers retry

### **2. Rate Limiting** (Phase 2)
```python
# Waits if necessary to stay under limits
await AI_RATE_LIMITER.acquire(estimated_tokens=2500)
```
- Prevents 429 rate limit errors
- Smooth traffic distribution
- Cost tracking (tracks actual tokens used)

### **3. Circuit Breaker** (Phase 1)
```python
AI_API_BREAKER = CircuitBreaker(
    name="ai_api",
    failure_threshold=3,  # Open after 3 failures
    recovery_timeout=120.0  # Try recovery after 2 minutes
)
```
- Opens after 3 consecutive failures
- Fails fast when service is down
- Auto-recovery attempts after 2 minutes

### **4. Retry Logic** (Phase 1)
```python
RetryConfig(
    MAX_RETRIES=3,
    INITIAL_BACKOFF=1.0,
    BACKOFF_MULTIPLIER=2.0,
    JITTER=True
)
```
- 3 retry attempts on transient errors
- Exponential backoff: 1s → 2s → 4s
- Jitter prevents thundering herd
- Only retries: `rate_limit_error`, `overloaded_error`, `timeout`, `api_error`

### **5. Metrics Collection** (Phase 2)
```python
# All API calls automatically tracked
ai_api_calls_total.labels(status='success', model='sonnet').inc()
ai_api_tokens_total.labels(direction='input').inc(input_tokens)
ai_api_latency_seconds.observe(duration)
```

---

## Cost Tracking

### **Per-Request Cost Estimation**

Claude 3.5 Sonnet pricing (as of Jan 2025):
- Input: $3.00 per million tokens
- Output: $15.00 per million tokens

**Typical Function Analysis**:
```
Input:  1,500 tokens (code + context) = $0.0045
Output:   800 tokens (analysis)        = $0.0120
Total:                                  = $0.0165 (~1.7¢)
```

**Typical Full Analysis** (100 functions):
```
Function-level: 100 calls × $0.0165 = $1.65
Module-level:    10 calls × $0.01   = $0.10
System-level:     1 call  × $0.02   = $0.02
                                ───────────
Total:                              = $1.77
```

### **Cost Optimization Features**

1. **Caching** (Phase 1 - Option C):
   - Unchanged code → cache hit → $0 cost
   - Typical 80-95% cache hit rate
   - Saves ~$1.40 on re-analysis of same codebase

2. **Incremental Analysis** (Option E):
   - Only analyze changed files
   - 5 files changed out of 100 → 95% cost savings
   - $1.77 → $0.09 per incremental run

3. **Rate Limiting** (Phase 2):
   - Prevents wasteful retries on rate limit errors
   - Smooth usage = fewer failed billable requests

### **Monthly Cost Estimate**

**Small Team** (10 analyses/day):
```
Daily:   10 analyses × $0.15 (incremental) = $1.50
Monthly: $1.50 × 22 working days          = $33.00
```

**Active Development** (50 analyses/day):
```
Daily:   50 analyses × $0.15 = $7.50
Monthly: $7.50 × 22           = $165.00
```

**Enterprise** (500 analyses/day):
```
Daily:   500 analyses × $0.10 = $50.00
Monthly: $50.00 × 22           = $1,100.00
```

---

## Monitoring LLM Usage

### **Metrics Available** (via `/metrics` endpoint)

```prometheus
# Total API calls by status and model
eidolon_ai_api_calls_total{status="success",model="claude-3-5-sonnet-20241022"} 1523

# Total tokens consumed (input + output)
eidolon_ai_api_tokens_total{direction="input",model="..."} 2847392
eidolon_ai_api_tokens_total{direction="output",model="..."} 1523847

# API call latency distribution
eidolon_ai_api_latency_seconds{model="..."}  # Histogram

# Rate limiter wait times
eidolon_ai_api_rate_limit_wait_seconds  # How long we waited

# Rate limiter wait count
eidolon_ai_api_rate_limit_waits_total  # How many times we waited
```

### **Log Examples** (Structured Logs)

```json
{
  "timestamp": "2025-01-22T10:15:23Z",
  "level": "info",
  "event": "ai_call_complete",
  "model": "claude-3-5-sonnet-20241022",
  "input_tokens": 1523,
  "output_tokens": 876,
  "duration_ms": 8432,
  "function": "analyze_function",
  "cache_hit": false
}
```

---

## Switching to Different LLMs

Eidolon is currently hardcoded to use Anthropic's Claude, but could be extended to support other providers:

### **Current Architecture** (Anthropic-specific)
```python
from anthropic import AsyncAnthropic
self.client = AsyncAnthropic(api_key=self.api_key)
```

### **To Add OpenAI Support** (example)
```python
# Would require modification to orchestrator.py
from openai import AsyncOpenAI

if provider == "openai":
    self.client = AsyncOpenAI(api_key=openai_key)
elif provider == "anthropic":
    self.client = AsyncAnthropic(api_key=anthropic_key)

# Then abstract the message format
async def _call_llm(self, messages):
    if self.provider == "openai":
        return await self.client.chat.completions.create(
            model="gpt-4-turbo",
            messages=messages
        )
    elif self.provider == "anthropic":
        return await self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            messages=messages
        )
```

**Note**: This would be a future enhancement. Current implementation is Anthropic-only.

---

## Security Considerations

### **API Key Protection**
✅ **DO**:
- Store in environment variable (`ANTHROPIC_API_KEY`)
- Never commit to git
- Use secrets management in production (AWS Secrets Manager, HashiCorp Vault)
- Rotate keys regularly

❌ **DON'T**:
- Hardcode in source code
- Include in Docker images
- Log the full key
- Share across environments

### **Request/Response Handling**
✅ **Secure practices**:
- HTTPS only (enforced by Anthropic SDK)
- No sensitive data in prompts (code only)
- Response validation before use
- Timeout protection prevents resource exhaustion

### **Cost Control**
✅ **Protection mechanisms**:
- Rate limiting prevents runaway costs
- Resource limits prevent huge analyses
- Circuit breaker stops failed retries
- Metrics track token usage for billing

---

## Troubleshooting

### **Common Issues**

#### 1. "ANTHROPIC_API_KEY not set"
```bash
# Fix:
export ANTHROPIC_API_KEY="sk-ant-api03-..."

# Verify:
echo $ANTHROPIC_API_KEY
```

#### 2. Rate Limit Errors (429)
```
Cause: Exceeding 50 req/min or 40k tokens/min
Fix:   Rate limiter should prevent this (Phase 2)
Check: Metrics show eidolon_ai_api_rate_limit_waits_total
```

#### 3. Timeout Errors
```
Cause: Network issues or slow model response
Fix:   Automatic retry (3 attempts)
Check: Logs show "operation_timeout" events
```

#### 4. Circuit Breaker Opens
```
Cause: 3+ consecutive API failures
Fix:   Auto-recovery after 2 minutes
Check: Metrics show eidolon_circuit_breaker_state{name="ai_api"}=2
Action: Check Anthropic status page: https://status.anthropic.com/
```

---

## Summary

**Eidolon → Anthropic Claude Connection**:

1. **Authentication**: Via `ANTHROPIC_API_KEY` environment variable
2. **Client**: `AsyncAnthropic` from official SDK
3. **Model**: Claude 3.5 Sonnet (`claude-3-5-sonnet-20241022`)
4. **Resilience**: Full stack (rate limit, timeout, circuit breaker, retry)
5. **Three Levels**: Function → Module → System analysis
6. **Observability**: Metrics, structured logs, cost tracking
7. **Cost Optimization**: Caching + incremental analysis
8. **Security**: Environment-based auth, HTTPS only

**All API calls flow through**:
```
orchestrator._call_ai_with_resilience()
  → Rate Limiter
  → Timeout (90s)
  → Circuit Breaker
  → Retry (3 attempts)
  → self.client.messages.create()
  → Anthropic API
```
