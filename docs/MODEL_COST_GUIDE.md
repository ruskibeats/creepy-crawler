# Model Cost Guide for N8N Workflow Processor

This guide provides information about different language models you can use with the N8N Workflow Processor and their relative costs.

## Available Models

### OpenAI Models (via OpenRouter)

| Model | Relative Cost | Capabilities | Use Case |
|-------|---------------|--------------|----------|
| `openai/gpt-4-turbo` | $$$$ | Highest reasoning, best analysis | When you need the most detailed analysis |
| `openai/gpt-4o-mini` | $$$ | Strong reasoning, good analysis | Good balance of cost and quality |
| `openai/gpt-3.5-turbo` | $ | Good for structured tasks | **Best for JSON fixing** (default) |

### Anthropic Models (via OpenRouter)

| Model | Relative Cost | Capabilities | Use Case |
|-------|---------------|--------------|----------|
| `anthropic/claude-3-opus` | $$$$ | Highest reasoning, best analysis | When you need the most detailed analysis |
| `anthropic/claude-3-sonnet` | $$$ | Strong reasoning, good analysis | Good balance of cost and quality |
| `anthropic/claude-instant-1` | $ | Good for structured tasks | Good alternative for JSON fixing |

### Open Source Models (via OpenRouter)

| Model | Relative Cost | Capabilities | Use Case |
|-------|---------------|--------------|----------|
| `mistralai/mistral-7b-instruct` | Free/$ | Basic reasoning, good for simple tasks | When cost is the primary concern |
| `meta-llama/llama-2-13b-chat` | Free/$ | Basic reasoning, good for simple tasks | When cost is the primary concern |

## Cost Comparison

For JSON fixing tasks (like repairing malformed workflow JSON):

1. **Cheapest Options**:
   - `openai/gpt-3.5-turbo` (default)
   - `anthropic/claude-instant-1`
   - Open source models

2. **Mid-Range Options**:
   - `openai/gpt-4o-mini`
   - `anthropic/claude-3-sonnet`

3. **Premium Options** (not recommended for simple JSON fixing):
   - `openai/gpt-4-turbo`
   - `anthropic/claude-3-opus`

## Usage Examples

To use a specific model:

```bash
# Use the default (cheapest) model
python n8n_workflow_processor.py 2859-chat-with-postgresql-database

# Use a specific model
python n8n_workflow_processor.py 2859-chat-with-postgresql-database --model openai/gpt-3.5-turbo

# Use a different model
python n8n_workflow_processor.py 2859-chat-with-postgresql-database --model anthropic/claude-instant-1
```

## Recommendations

1. **For JSON Fixing**: Use the default `openai/gpt-3.5-turbo` model. It's cost-effective and performs well for structured tasks like fixing JSON.

2. **For Detailed Analysis**: If you need more comprehensive workflow analysis, consider using `openai/gpt-4o-mini` or `anthropic/claude-3-sonnet` for a good balance of cost and quality.

3. **For Budget Constraints**: If cost is a major concern, try the open source models like `mistralai/mistral-7b-instruct` or `meta-llama/llama-2-13b-chat`.

## Pricing Notes

- Actual pricing may vary based on OpenRouter's current rates
- Token usage depends on the size of your workflow JSON
- The analysis phase typically uses more tokens than the JSON fixing phase
