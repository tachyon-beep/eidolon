# Multi-Provider LLM Support Guide

MONAD now supports multiple LLM providers through a unified abstraction layer. You can easily switch between Anthropic Claude, OpenAI, OpenRouter, and any OpenAI-compatible API.

---

## Supported Providers

| Provider | Status | Models | Configuration |
|----------|--------|--------|---------------|
| **Anthropic** | ✅ Native | Claude 3.5 Sonnet, etc. | `ANTHROPIC_API_KEY` |
| **OpenAI** | ✅ Compatible | GPT-4, GPT-4 Turbo, GPT-4o | `OPENAI_API_KEY` |
| **OpenRouter** | ✅ Compatible | 100+ models from multiple providers | `OPENAI_API_KEY` + `OPENAI_BASE_URL` |
| **Together.ai** | ✅ Compatible | Llama 3.1, Mixtral, etc. | `OPENAI_API_KEY` + `OPENAI_BASE_URL` |
| **Groq** | ✅ Compatible | Fast inference models | `OPENAI_API_KEY` + `OPENAI_BASE_URL` |
| **Ollama (local)** | ✅ Compatible | Any local model | `OPENAI_BASE_URL` |

---

## Quick Start

### Option 1: Anthropic Claude (Default)

```bash
# Set API key
export ANTHROPIC_API_KEY="sk-ant-api03-..."

# Optional: Specify model (default: claude-3-5-sonnet-20241022)
export ANTHROPIC_MODEL="claude-3-5-sonnet-20241022"

# Start MONAD
python backend/main.py
```

### Option 2: OpenAI

```bash
# Set provider and API key
export LLM_PROVIDER="openai"
export OPENAI_API_KEY="sk-..."

# Optional: Specify model (default: gpt-4-turbo)
export OPENAI_MODEL="gpt-4-turbo"

# Start MONAD
python backend/main.py
```

### Option 3: OpenRouter (Access 100+ Models)

```bash
# Set provider and OpenRouter API key
export LLM_PROVIDER="openai"
export OPENAI_API_KEY="sk-or-v1-..."
export OPENAI_BASE_URL="https://openrouter.ai/api/v1"

# Choose any model from OpenRouter
export OPENAI_MODEL="anthropic/claude-3.5-sonnet"
# or
export OPENAI_MODEL="google/gemini-pro-1.5"
# or
export OPENAI_MODEL="meta-llama/llama-3.1-70b-instruct"

# Start MONAD
python backend/main.py
```

### Option 4: Together.ai

```bash
export LLM_PROVIDER="openai"
export OPENAI_API_KEY="your-together-api-key"
export OPENAI_BASE_URL="https://api.together.xyz/v1"
export OPENAI_MODEL="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"

python backend/main.py
```

### Option 5: Local Ollama

```bash
# Make sure Ollama is running locally
ollama serve

# Configure MONAD to use Ollama
export LLM_PROVIDER="openai"
export OPENAI_API_KEY="ollama"  # Dummy value, Ollama doesn't need a key
export OPENAI_BASE_URL="http://localhost:11434/v1"
export OPENAI_MODEL="llama3.1:70b"

python backend/main.py
```

---

## Environment Variables Reference

### Provider Selection

```bash
# LLM_PROVIDER: Which provider to use
# Values: "anthropic" (default) or "openai"
export LLM_PROVIDER="anthropic"
```

### Anthropic Configuration

```bash
# ANTHROPIC_API_KEY: Your Anthropic API key (required if using Anthropic)
export ANTHROPIC_API_KEY="sk-ant-api03-..."

# ANTHROPIC_MODEL: Model to use (optional, default: claude-3-5-sonnet-20241022)
export ANTHROPIC_MODEL="claude-3-5-sonnet-20241022"

# Available models:
# - claude-3-5-sonnet-20241022  (recommended: best for code)
# - claude-3-opus-20240229      (most capable, slower)
# - claude-3-haiku-20240307     (fastest, cheaper)
```

### OpenAI/Compatible Configuration

```bash
# OPENAI_API_KEY: Your API key (required if using OpenAI-compatible)
export OPENAI_API_KEY="sk-..."

# OPENAI_BASE_URL: API endpoint (optional, default: https://api.openai.com/v1)
export OPENAI_BASE_URL="https://api.openai.com/v1"

# OPENAI_MODEL: Model to use (optional, default: gpt-4-turbo)
export OPENAI_MODEL="gpt-4-turbo"

# OpenAI models:
# - gpt-4o                 (latest, multimodal)
# - gpt-4-turbo            (fast, good quality)
# - gpt-4                  (original, slower)
```

---

## Provider-Specific Guides

### OpenRouter

**What is OpenRouter?**
OpenRouter provides a unified API for 100+ LLMs from multiple providers (OpenAI, Anthropic, Meta, Google, etc.) with a single API key.

**Advantages:**
- ✅ Single API key for multiple models
- ✅ Automatic failover
- ✅ Usage-based pricing (no subscriptions)
- ✅ Access to models not available elsewhere

**Setup:**

1. Get API key from [openrouter.ai](https://openrouter.ai/)

2. Configure MONAD:
```bash
export LLM_PROVIDER="openai"
export OPENAI_API_KEY="sk-or-v1-..."
export OPENAI_BASE_URL="https://openrouter.ai/api/v1"
```

3. Choose a model:
```bash
# Anthropic Claude via OpenRouter
export OPENAI_MODEL="anthropic/claude-3.5-sonnet"

# Google Gemini via OpenRouter
export OPENAI_MODEL="google/gemini-pro-1.5"

# Meta Llama via OpenRouter
export OPENAI_MODEL="meta-llama/llama-3.1-70b-instruct"

# OpenAI GPT-4 via OpenRouter
export OPENAI_MODEL="openai/gpt-4-turbo"
```

**See all models:** [https://openrouter.ai/models](https://openrouter.ai/models)

### Together.ai

**What is Together.ai?**
Fast, cost-effective inference for open-source models.

**Advantages:**
- ✅ Very fast inference
- ✅ Competitive pricing
- ✅ Good support for open models (Llama, Mixtral, etc.)

**Setup:**

1. Get API key from [together.ai](https://together.ai/)

2. Configure:
```bash
export LLM_PROVIDER="openai"
export OPENAI_API_KEY="your-together-key"
export OPENAI_BASE_URL="https://api.together.xyz/v1"
export OPENAI_MODEL="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"
```

**Popular models:**
- `meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo`
- `meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo`
- `mistralai/Mixtral-8x22B-Instruct-v0.1`

### Local Models with Ollama

**What is Ollama?**
Run LLMs locally on your machine.

**Advantages:**
- ✅ Completely private (no data sent to cloud)
- ✅ No API costs
- ✅ No internet required
- ✅ Customizable models

**Setup:**

1. Install Ollama: [ollama.com](https://ollama.com/)

2. Download a model:
```bash
ollama pull llama3.1:70b
# or
ollama pull codellama:34b
```

3. Start Ollama server:
```bash
ollama serve
```

4. Configure MONAD:
```bash
export LLM_PROVIDER="openai"
export OPENAI_API_KEY="ollama"  # Dummy value
export OPENAI_BASE_URL="http://localhost:11434/v1"
export OPENAI_MODEL="llama3.1:70b"
```

**Recommended models for code analysis:**
- `codellama:34b` - Specialized for code
- `llama3.1:70b` - General purpose, high quality
- `deepseek-coder:33b` - Good for code understanding

---

## Cost Comparison

### Anthropic Claude 3.5 Sonnet
- Input: $3 / 1M tokens
- Output: $15 / 1M tokens
- **Typical function analysis:** ~$0.017

### OpenAI GPT-4 Turbo
- Input: $10 / 1M tokens
- Output: $30 / 1M tokens
- **Typical function analysis:** ~$0.045

### OpenRouter (Claude via OpenRouter)
- Input: $3 / 1M tokens
- Output: $15 / 1M tokens
- **Typical function analysis:** ~$0.017
- Plus small OpenRouter fee

### OpenRouter (Llama 3.1 70B)
- Input: $0.88 / 1M tokens
- Output: $0.88 / 1M tokens
- **Typical function analysis:** ~$0.002 (90% cheaper!)

### Ollama (Local)
- **Cost:** $0 (hardware only)
- **Trade-off:** Slower, requires GPU

---

## Model Recommendations

### Best for Code Analysis

| Use Case | Recommended Model | Provider | Why |
|----------|-------------------|----------|-----|
| **Highest Quality** | Claude 3.5 Sonnet | Anthropic | Best code understanding |
| **Cost-Effective** | Llama 3.1 70B | OpenRouter/Together | Good quality, 90% cheaper |
| **Private/Local** | CodeLlama 34B | Ollama | No data leaves your machine |
| **Balanced** | GPT-4 Turbo | OpenAI | Good quality, widely available |

### For Different Analysis Workloads

**Large Codebase (1000+ files):**
- Use: Llama 3.1 70B via OpenRouter
- Why: Cost adds up, 90% savings significant
- Trade-off: Slightly lower quality

**Critical Production Code:**
- Use: Claude 3.5 Sonnet (Anthropic)
- Why: Best quality, worth the cost for critical code
- Trade-off: Higher cost

**Private/Sensitive Code:**
- Use: CodeLlama via Ollama (local)
- Why: Data never leaves your machine
- Trade-off: Slower, requires good GPU

**Experimentation:**
- Use: Any model via OpenRouter
- Why: Easy to switch, pay-as-you-go
- Trade-off: Small OpenRouter fee

---

## Testing Your Configuration

### Check Configuration

```bash
# Start MONAD
python backend/main.py

# Check logs for provider info:
# You should see something like:
# [info] orchestrator_llm_provider provider=anthropic model=claude-3-5-sonnet-20241022
# or
# [info] orchestrator_llm_provider provider=openrouter model=anthropic/claude-3.5-sonnet
```

### Test Analysis

```bash
# Make a request to the API
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/your/code"}'

# Check the response for successful analysis
```

### Monitor Costs

```bash
# Check metrics endpoint for token usage
curl http://localhost:8000/metrics | grep ai_api_tokens

# Output:
# monad_ai_api_tokens_total{direction="input",model="..."} 1234
# monad_ai_api_tokens_total{direction="output",model="..."} 5678
```

---

## Switching Providers

You can easily switch providers by changing environment variables:

```bash
# Currently using Anthropic
export LLM_PROVIDER="anthropic"
export ANTHROPIC_API_KEY="sk-ant-..."

# Switch to OpenRouter
export LLM_PROVIDER="openai"
export OPENAI_API_KEY="sk-or-..."
export OPENAI_BASE_URL="https://openrouter.ai/api/v1"
export OPENAI_MODEL="anthropic/claude-3.5-sonnet"

# Restart MONAD
# Changes take effect immediately
```

**No code changes needed!** Just restart the server.

---

## Troubleshooting

### "ValueError: ANTHROPIC_API_KEY not set"

**Problem:** No API key configured for the selected provider.

**Solution:**
```bash
# Check which provider is selected
echo $LLM_PROVIDER  # Should be "anthropic" or "openai"

# Set the correct API key
export ANTHROPIC_API_KEY="sk-ant-..."  # if using Anthropic
export OPENAI_API_KEY="sk-..."         # if using OpenAI-compatible
```

### "ValueError: Unknown provider"

**Problem:** Invalid `LLM_PROVIDER` value.

**Solution:**
```bash
# Must be exactly "anthropic" or "openai" (lowercase)
export LLM_PROVIDER="anthropic"  # or "openai"
```

### "Connection refused" (Ollama)

**Problem:** Ollama server not running.

**Solution:**
```bash
# Start Ollama server
ollama serve

# Verify it's running
curl http://localhost:11434/api/tags
```

### "Model not found" (OpenRouter)

**Problem:** Invalid model name for OpenRouter.

**Solution:**
Check available models at [https://openrouter.ai/models](https://openrouter.ai/models)

Use exact model ID:
```bash
export OPENAI_MODEL="anthropic/claude-3.5-sonnet"  # Correct
# NOT: "claude-3.5-sonnet" (missing provider prefix)
```

### High API costs

**Problem:** Unexpected API costs.

**Solution:**

1. Check token usage:
```bash
curl http://localhost:8000/metrics | grep tokens
```

2. Switch to cheaper model:
```bash
# From Claude Sonnet (~$0.017/function)
# To Llama 3.1 70B (~$0.002/function)
export OPENAI_MODEL="meta-llama/llama-3.1-70b-instruct"
```

3. Enable caching (should be on by default):
```python
# In orchestrator initialization
enable_cache=True  # 80-95% cache hit rate saves cost
```

---

## Advanced: Programmatic Configuration

You can also configure the provider programmatically:

```python
from llm_providers import create_provider, AnthropicProvider, OpenAICompatibleProvider

# Option 1: Auto-detect from environment
provider = create_provider()

# Option 2: Explicit Anthropic
provider = create_provider("anthropic", api_key="sk-ant-...")

# Option 3: Explicit OpenAI
provider = create_provider(
    "openai",
    api_key="sk-...",
    model="gpt-4-turbo"
)

# Option 4: OpenRouter
provider = create_provider(
    "openai",
    api_key="sk-or-...",
    base_url="https://openrouter.ai/api/v1",
    model="anthropic/claude-3.5-sonnet"
)

# Use with orchestrator
orchestrator = AgentOrchestrator(db, llm_provider=provider)
```

---

## FAQ

**Q: Can I use multiple providers at once?**

A: Not currently, but you can switch between providers by changing environment variables and restarting.

**Q: Which provider is fastest?**

A: Groq and Together.ai typically have the lowest latency. Claude and GPT-4 have higher latency but better quality.

**Q: Can I use fine-tuned models?**

A: Yes! With OpenAI-compatible providers, just set `OPENAI_MODEL` to your fine-tuned model ID.

**Q: Does caching work across different models?**

A: No, cache is file-hash based. Changing models won't invalidate cache, but different models may produce different analyses.

**Q: How do I know which model is actually being used?**

A: Check the logs:
```bash
grep "orchestrator_llm_provider" logs.txt
```

Or check metrics:
```bash
curl http://localhost:8000/metrics | grep model
```

---

## Summary

MONAD supports:
- ✅ **Anthropic Claude** - Native, best quality
- ✅ **OpenAI GPT-4** - Compatible
- ✅ **OpenRouter** - 100+ models, single API key
- ✅ **Together.ai** - Fast, cost-effective open models
- ✅ **Ollama** - Local, private, free
- ✅ **Any OpenAI-compatible API** - Easy to add

**Switching is as simple as:**
```bash
export LLM_PROVIDER="openai"
export OPENAI_API_KEY="your-key"
export OPENAI_MODEL="your-model"
```

**All resilience features work across all providers:**
- Timeouts
- Retries
- Circuit breakers
- Rate limiting
- Metrics collection
- Structured logging
