# Using OpenRouter with Eidolon MVP

OpenRouter provides access to multiple LLM providers through a single API, including Claude models.

## Setup

1. **Get an OpenRouter API key** from https://openrouter.ai/

2. **Configure environment variables:**

```bash
cd mvp/
cp .env.example .env

# Edit .env:
export LLM_PROVIDER=openai-compatible
export OPENAI_API_KEY=sk-or-v1-your-openrouter-key-here
export OPENAI_BASE_URL=https://openrouter.ai/api/v1
export LLM_MODEL=anthropic/claude-3.5-sonnet
```

## Available Models

OpenRouter supports many models. Good options for code analysis:

- `anthropic/claude-3.5-sonnet` - Best for code (recommended)
- `anthropic/claude-3-opus`
- `openai/gpt-4-turbo`
- `openai/gpt-4o`
- `meta-llama/llama-3.1-70b-instruct` - Cheaper alternative

See full list: https://openrouter.ai/models

## Usage

### Analyze a file with LLM

```bash
cd mvp/

# Set up environment
source .env  # or manually export variables

# Analyze with LLM
python analyze_file.py /path/to/file.py --llm
```

### Check configuration

```bash
python -c "
from src.eidolon_mvp.llm.config import create_llm_from_env
llm = create_llm_from_env()
if llm:
    print(f'Provider: {llm.provider}')
    print(f'Model: {llm.model}')
    print(f'Base URL: {llm.base_url}')
else:
    print('No LLM configured')
"
```

## Cost

OpenRouter charges per token. Typical costs for code analysis:

- **Claude 3.5 Sonnet**: ~$3 per 1M input tokens, ~$15 per 1M output tokens
- **GPT-4 Turbo**: ~$10 per 1M input tokens, ~$30 per 1M output tokens

For a typical function analysis:
- Input: ~1000 tokens (function code + prompt)
- Output: ~200 tokens (findings)
- Cost: ~$0.006 per function

**Caching** significantly reduces costs for repeated analysis.

## Troubleshooting

### "No API key configured"

Make sure environment variables are set:
```bash
echo $OPENAI_API_KEY
echo $OPENAI_BASE_URL
```

### "Invalid API key"

Check your OpenRouter key at https://openrouter.ai/keys

### "Model not found"

Use the exact model name from https://openrouter.ai/models

Example: `anthropic/claude-3.5-sonnet` (not just `claude-3.5-sonnet`)

## Example Session

```bash
$ cd mvp/

$ export LLM_PROVIDER=openai-compatible
$ export OPENAI_API_KEY=sk-or-v1-...
$ export OPENAI_BASE_URL=https://openrouter.ai/api/v1
$ export LLM_MODEL=anthropic/claude-3.5-sonnet

$ python analyze_file.py ../src/eidolon/rulepack/parser.py --llm

Analyzing: ../src/eidolon/rulepack/parser.py

  Lines of code: 234
  Using: LLM-enhanced analysis (openai-compatible)
  Base URL: https://openrouter.ai/api/v1
  Model: anthropic/claude-3.5-sonnet

🔍 Running analysis...

Module ../src/eidolon/rulepack/parser.py: found 8 functions
Analyzing 8 functions in parallel...
  Progress: 8/8 (100%)
✓ Complete

=======================================================================
RESULTS
=======================================================================
...
```

## Alternative: Direct Anthropic

If you have an Anthropic API key, you can use it directly (no OpenRouter):

```bash
export LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-...
unset OPENAI_BASE_URL

python analyze_file.py file.py --llm
```

This avoids the OpenRouter middleman but requires an Anthropic account.
