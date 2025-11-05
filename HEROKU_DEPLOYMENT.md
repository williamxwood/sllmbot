# Deploy to Heroku - Step by Step

## Prerequisites

- Heroku account (free tier works)
- Heroku CLI installed
- Slack app configured (see README.md)
- FastMCP server URL and token

## Deployment Steps

### 1. Install Heroku CLI

**macOS:**
```bash
brew install heroku
```

**Other platforms:**
Download from https://devcenter.heroku.com/articles/heroku-cli

### 2. Login to Heroku

```bash
heroku login
```

### 3. Create Heroku App

```bash
cd /path/to/slackbot_oss
heroku create your-bot-name
```

Or use existing app:
```bash
heroku git:remote -a existing-app-name
```

### 4. Set Environment Variables

```bash
# Slack
heroku config:set SLACK_BOT_TOKEN=xoxb-your-token-here
heroku config:set SLACK_APP_TOKEN=xapp-your-token-here

# FastMCP
heroku config:set FASTMCP_SERVER_URL=https://your-server.com/mcp
heroku config:set FASTMCP_TOKEN=fmcp_your-token-here

# LLM (choose one)
heroku config:set LLM_PROVIDER=anthropic
heroku config:set ANTHROPIC_API_KEY=sk-ant-your-key

# OR for OpenAI
# heroku config:set LLM_PROVIDER=openai
# heroku config:set OPENAI_API_KEY=sk-your-key
```

### 5. Deploy

```bash
git init  # if not already a git repo
git add .
git commit -m "Initial deployment"
git push heroku main
```

### 6. Scale Up Worker

```bash
heroku ps:scale worker=1
```

### 7. Verify It's Running

```bash
# Check status
heroku ps

# View logs
heroku logs --tail

# You should see:
# ✓ Bot initialized with X tools
# ✓ LLM Provider: anthropic
# ✓ Ready!
```

### 8. Test in Slack

Message your bot:
```
@YourBot What are the top companies by market cap?
```

## 🔄 Making Updates

```bash
# Make changes to slack_bot.py
git add .
git commit -m "Your update message"
git push heroku main

# Bot will automatically restart
```

## 🐛 Troubleshooting

### Bot doesn't respond

**Check environment variables:**
```bash
heroku config
```

**Verify all required vars are set:**
- SLACK_BOT_TOKEN
- SLACK_APP_TOKEN  
- FASTMCP_SERVER_URL
- FASTMCP_TOKEN
- LLM_PROVIDER
- ANTHROPIC_API_KEY (or OPENAI_API_KEY)

**Restart the worker:**
```bash
heroku restart worker
```

### Check logs for errors

```bash
heroku logs --tail

# Look for:
# - "Bot initialized" ✓
# - "LLM Provider: anthropic" ✓
# - Any error messages ❌
```

### Test LLM connection

```bash
heroku run python -c "
from slack_bot import AnthropicProvider
import asyncio
import os

async def test():
    llm = AnthropicProvider(os.environ['ANTHROPIC_API_KEY'])
    result = await llm.chat([{'role': 'user', 'content': 'Hello'}])
    print(result)

asyncio.run(test())
"
```

### Test FastMCP connection

```bash
heroku run python -c "
from slack_bot import FastMCPClient
import asyncio
import os

async def test():
    mcp = FastMCPClient(os.environ['FASTMCP_SERVER_URL'], os.environ['FASTMCP_TOKEN'])
    tools = await mcp.get_tools()
    print(f'Found {len(tools)} tools')

asyncio.run(test())
"
```

## 💰 Heroku Costs

### Free Tier (limited hours)
- Worker dyno: 550 free hours/month
- Good for testing

### Basic Plan ($7/month)
- Worker dyno: Always on
- Good for production

### LLM Costs (separate)
- Claude: ~$0.50-2.00 per query
- GPT-4: ~$0.30-1.50 per query

**Total:** ~$7-50/month depending on usage

## 🔄 Switch LLM Providers

### Switch to Claude
```bash
heroku config:set LLM_PROVIDER=anthropic
heroku config:set ANTHROPIC_API_KEY=sk-ant-your-key
heroku restart worker
```

### Switch to GPT-4
```bash
heroku config:set LLM_PROVIDER=openai
heroku config:set OPENAI_API_KEY=sk-your-key
heroku restart worker
```

## 📊 Monitor Usage

### View logs
```bash
heroku logs --tail -n 100
```

### Check dyno status
```bash
heroku ps
```

### View environment
```bash
heroku config
```

## 🎯 Advanced

### Auto-scaling
```bash
# Scale based on load
heroku ps:autoscale:enable worker --min 1 --max 3
```

### Add Redis (for caching)
```bash
heroku addons:create heroku-redis:mini
```

### Monitor with Datadog
```bash
heroku addons:create heroku-datadog
```

## 🆘 Getting Help

1. Check logs: `heroku logs --tail`
2. Restart: `heroku restart worker`
3. Check config: `heroku config`
4. View this guide: `HEROKU_DEPLOYMENT.md`
5. Create an issue on GitHub

---

**Last Updated:** November 2025  
**Tested On:** Heroku-24 stack with Python 3.11

