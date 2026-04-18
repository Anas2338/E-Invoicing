# AI Agent - Dual Provider Setup (Claude + Gemini)

## Overview

The AI Agent supports two AI providers with automatic environment-based switching:

- **Claude (Anthropic)**: Production environment - High accuracy, enterprise-grade
- **Gemini (Google)**: Development environment - Free tier with generous limits

## Quick Start - Get Free Gemini API Key

### Step 1: Get Gemini API Key (Free)

1. Visit: **https://aistudio.google.com/app/apikey**
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the generated key (starts with `AIza...`)

### Step 2: Configure Environment

Update `ai-agent/.env`:

```bash
# AI Provider Selection
AI_PROVIDER=gemini

# Gemini Configuration (Development/Free)
GEMINI_API_KEY=AIzaSy...your-actual-key-here
GEMINI_MODEL=gemini-1.5-flash
```

### Step 3: Run AI Agent

```bash
cd ai-agent
uv run python main.py
```

## Configuration

### Environment Variables

```bash
# AI Provider Selection
# Options: "claude" (production) or "gemini" (development)
# Default: "gemini" in development, "claude" in production
AI_PROVIDER=gemini

# Claude Configuration (Production)
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Gemini Configuration (Development/Free)
GEMINI_API_KEY=AIzaSy-your-key-here
GEMINI_MODEL=gemini-1.5-flash

# Application Environment
APP_ENV=development  # or "production"
```

## Provider Selection Logic

1. **Explicit**: Set `AI_PROVIDER=claude` or `AI_PROVIDER=gemini`
2. **Automatic**: Based on `APP_ENV`:
   - `APP_ENV=development` → Gemini (free)
   - `APP_ENV=production` → Claude (paid)

## Provider Comparison

| Feature | Claude (Production) | Gemini (Development) |
|---------|-------------------|-------------------|
| Cost | Paid (per token) | **Free tier: 1,500 RPD** |
| Rate Limit | 50 RPM | 15 RPM (free tier) |
| Model | claude-sonnet-4-6 | gemini-1.5-flash |
| Accuracy | Enterprise-grade | Excellent for testing |
| Use Case | Production workloads | Development/testing |
| API Key | console.anthropic.com | aistudio.google.com |

## Gemini Free Tier Limits

- **1,500 requests per day (RPD)**
- **15 requests per minute (RPM)**
- **1 million tokens per minute**
- **1,500 requests per minute (burst)**

Perfect for development and testing!

## Usage

The AI Agent automatically uses the configured provider:

```python
from ai_client import AIClient

# Automatically selects provider based on configuration
client = AIClient()

# Classify errors
result = client.classify_error(
    error_message="Connection timeout",
    error_context={
        "invoice_number": "INV-001",
        "retry_count": 2,
        "error_source": "fbr_api"
    }
)

# Analyze failure patterns
analysis = client.analyze_failure_patterns(failure_data)

# Get usage statistics
stats = client.get_usage_stats()
print(f"Provider: {stats['provider']}")
print(f"Rate Limit: {stats['rate_limit_rpm']} RPM")
```

## Testing

Test the AI client:

```bash
cd ai-agent
uv run python test_gemini.py
```

Expected output:
```
AI Client Provider Test - Gemini
Environment: development
AI Provider: gemini

[OK] AI Client initialized successfully
  Provider: gemini

Usage Stats:
  Provider: gemini
  Rate Limit: 15 RPM
  Tokens Available: 15
```

## Switching Providers

### Development → Production

1. Update `.env`:
   ```bash
   APP_ENV=production
   ANTHROPIC_API_KEY=sk-ant-your-real-key
   ```

2. Restart AI Agent:
   ```bash
   uv run python main.py
   ```

3. Verify in logs:
   ```
   AI Client initialized with Claude provider (production)
   ```

### Manual Override

Force a specific provider regardless of environment:

```bash
AI_PROVIDER=claude  # Always use Claude
# or
AI_PROVIDER=gemini  # Always use Gemini
```

## Fallback Behavior

If API calls fail (invalid key, network issues, quota exceeded), the AI client falls back to:

- **Error Classification**: Treats as "transient" with 0.3 confidence
- **Failure Analysis**: Returns empty patterns with "medium" severity

This ensures the agent continues processing even if AI features are unavailable.

## Architecture

```
ai_client.py (Abstraction Layer)
    ├── claude_client.py (Anthropic SDK)
    └── gemini_client.py (Google Genai SDK)

skills/error_handler.py
    └── Uses AIClient (provider-agnostic)

agent.py
    └── Initializes skills with AIClient
```

## Rate Limiting

Both providers implement token bucket algorithm:

- **Claude**: 50 requests/minute
- **Gemini**: 15 requests/minute (free tier)

Rate limits are enforced client-side to prevent API quota exhaustion.

## Troubleshooting

### "GEMINI_API_KEY not configured" warning
- Get free API key from: https://aistudio.google.com/app/apikey
- Add to `.env`: `GEMINI_API_KEY=AIzaSy...`

### "ANTHROPIC_API_KEY not configured" warning
- Add valid Claude API key to `.env`
- Or switch to Gemini: `AI_PROVIDER=gemini`

### "Unknown AI provider" error
- Check `AI_PROVIDER` value (must be "claude" or "gemini")
- Check `.env` file is loaded correctly

### API 503 errors (Gemini high demand)
- This is temporary - Gemini will retry automatically
- Fallback behavior ensures agent continues working
- Try again in a few minutes

### API 429 errors (Rate limit exceeded)
- Gemini free tier: 15 RPM, 1,500 RPD
- Agent has built-in rate limiting to prevent this
- If exceeded, wait for quota to reset

## Why Gemini?

1. **Completely Free**: No credit card required
2. **Generous Limits**: 1,500 requests/day is plenty for development
3. **High Quality**: Gemini 1.5 Flash is fast and accurate
4. **Easy Setup**: Get API key in 30 seconds
5. **Production Ready**: Switch to Claude when ready to deploy

## Next Steps

1. Get your free Gemini API key: https://aistudio.google.com/app/apikey
2. Add it to `ai-agent/.env`
3. Run the agent: `uv run python main.py`
4. Test error classification with real invoices
5. Switch to Claude for production deployment
