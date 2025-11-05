# Slackbot OSS - Natural Language Data Access

Connect Slack to your data using natural language. Choose from 4 integration patterns.

## 💡 Why This Exists

I built this Slackbot internally for my team to query our analytics database using natural language. After seeing a bunch of companies offering similar products as paid SaaS solutions, I decided to open source what we built—along with several variations—to help as many people as possible access their data without vendor lock-in or monthly subscriptions.

This repo includes 4 different integration approaches, from simple direct SQL to enterprise-grade semantic layers, so you can choose what fits your needs and infrastructure.

## 🎯 What This Does

Ask questions in Slack, get answers from your database:

```
You: @DataBot What's our average order value this month?
Bot: The average order value is $87.32 across 3,847 orders this month...
```

**How it works:**
1. User asks question in Slack
2. LLM understands question
3. Queries database (via FastMCP, direct SQL, Cortex, or Semantic Layer)
4. LLM formats answer
5. Posts to Slack

---

## ⚠️ Production Readiness

| Bot | Status | Confidence | Notes |
|-----|--------|------------|-------|
| **Direct SQL** | ✅ Production Ready | 95% | Tested pattern, minor bugs fixed |
| **FastMCP** | ⚠️ Requires Setup | 70% | Code tested, needs MCP server deployment |
| **Cortex** | 🧪 Experimental | 40% | Not tested with real Cortex API - expect debugging |
| **Semantic Layer** | 🧪 Experimental | 30% | Not tested with real dbt API - expect debugging |

**Recommendation:** Start with **Direct SQL** (`slack_bot_no_mcp.py`) for immediate use.

---

## 🚀 Quick Start (3 Steps)

### 1. Choose Your Integration

| Integration | Best For | Setup | Cost/Month |
|-------------|----------|-------|------------|
| **[FastMCP](#fastmcp)** | Multi-app platforms | Complex | $50-100 |
| **[Direct SQL](#direct-sql)** | Solo developers | Simple | $40-70 |
| **[Snowflake Cortex](#snowflake-cortex)** | Snowflake-only orgs | Simple | $310-610* |
| **[dbt Semantic Layer](#dbt-semantic-layer)** | dbt users | Medium | $120-150 |

*Cortex costs vary significantly with query volume

**Not sure?** Use the [decision tree](#which-should-i-use) below.

### 2. Install & Configure

**Option A: Interactive Setup (Recommended)**
```bash
# Clone repo
git clone https://github.com/williamxwood/slackbot.git
cd slackbot

# Run interactive setup
./scripts/setup.sh

# Follow the prompts to:
# 1. Choose your integration (Direct SQL, FastMCP, Cortex, or Semantic)
# 2. Enter credentials (securely prompted)
# 3. Auto-install dependencies
# 4. Test connections

# Run the bot
python slack_bot_no_mcp.py  # Or whichever you chose
```

**Option B: Manual Setup**
```bash
# Clone repo
git clone https://github.com/williamxwood/slackbot.git
cd slackbot

# Choose your integration and copy env file
cp env_no_mcp.example .env    # Direct SQL (recommended for most)
# or cp env.example .env        # FastMCP
# or cp env_cortex.example .env # Snowflake Cortex
# or cp env_semantic.example .env # dbt Semantic Layer

# Edit .env with your credentials
nano .env

# Install dependencies (matches your choice)
pip install -r requirements_no_mcp.txt  # Direct SQL
# or pip install -r requirements.txt     # FastMCP
# etc.

# Run
python slack_bot_no_mcp.py  # Direct SQL
# or python slack_bot.py      # FastMCP
# etc.
```

### 3. Test & Deploy

```bash
# Test locally first
python slack_bot_no_mcp.py  # Or whichever you set up

# In Slack:
@YourBot hello
@YourBot What are the top 5 products by revenue?
```

**Deploy to production:**  
See [HEROKU_DEPLOYMENT.md](HEROKU_DEPLOYMENT.md) for detailed deployment instructions.

---

## 🎬 Interactive Setup Demo

Here's what the setup experience looks like:

```bash
$ ./scripts/setup.sh

======================================================================
  🚀 Slackbot OSS - Interactive Setup
======================================================================

Welcome! This script will help you set up your Slackbot...

Press Enter to continue...

──────────────────────────────────────────────────────────────────────
Step 1: Choose Bot Integration
──────────────────────────────────────────────────────────────────────

Which integration do you want to use?
  1. Direct SQL (Recommended) - Simple, works immediately
  2. FastMCP - For multi-app platforms (requires MCP server)
  3. Snowflake Cortex - Use Snowflake's built-in LLM (experimental)
  4. dbt Semantic Layer - Query governed metrics (experimental)

Enter choice (1-4): 1

──────────────────────────────────────────────────────────────────────
Step 2: Direct SQL Bot Configuration
──────────────────────────────────────────────────────────────────────

📱 Slack Configuration:
Slack Bot Token (xoxb-...): xoxb-1234-5678-abcd
Slack App Token (xapp-...): xapp-1-A123-456-xyz

🧪 Testing Slack connection...
✅ Connected as: DataBot

❄️  Snowflake Configuration:
Snowflake Username: john_doe
Snowflake Account (e.g., abc123.us-east-1): mycompany.us-west-2
Warehouse Name [COMPUTE_WH]: ANALYTICS_WH
Database Name: ANALYTICS
Schema Name [PUBLIC]: PUBLIC

🔐 Snowflake Authentication Method:
  1. Password authentication (recommended for Heroku)
  2. Browser SSO (for local development)

Enter choice (1-2): 1
Snowflake Password: ********

🧪 Testing Snowflake connection...
✅ Connected to Snowflake (version 8.15.0)

🤖 LLM Configuration:
Anthropic API Key (sk-ant-...): ********

🧪 Testing Anthropic API key...
✅ Anthropic API key format valid

──────────────────────────────────────────────────────────────────────
Step 3: Save Configuration
──────────────────────────────────────────────────────────────────────

✅ Configuration saved to .env
✅ File permissions set to 600 (owner read/write only)

──────────────────────────────────────────────────────────────────────
Step 4: Install Dependencies
──────────────────────────────────────────────────────────────────────

Install Python dependencies now? (Y/n): y

📦 Installing dependencies from requirements_no_mcp.txt...
✅ Dependencies installed successfully

──────────────────────────────────────────────────────────────────────
Step 5: You're All Set! 🎉
──────────────────────────────────────────────────────────────────────

✅ Configuration complete!

Next steps:

1. Test locally:
   python slack_bot_no_mcp.py

2. In Slack, test with:
   @YourBot hello
   @YourBot What are the top 5 products by revenue?

3. Deploy to production:
   See HEROKU_DEPLOYMENT.md for deployment instructions

Enjoy your Slackbot! 🚀
```

---

## 📊 Integration Comparison

### Quick Reference Table

| Feature | FastMCP | Direct SQL | Snowflake Cortex | dbt Semantic Layer |
|---------|---------|------------|------------------|-------------------|
| **File** | `slack_bot.py` | `slack_bot_no_mcp.py` | `slack_bot_cortex.py` | `slack_bot_semantic.py` |
| **Setup Complexity** | ⚠️ High | ✅ Low | ✅ Low | ⚠️ Medium |
| **External LLM** | Claude/GPT-4 | Claude/GPT-4 | Cortex (Mistral/Llama) | Claude/GPT-4 |
| **Infrastructure** | MCP Server + Bot | Bot only | Bot only | Bot + dbt Cloud |
| **Ad-hoc Queries** | ❌ No | ✅ Yes | ✅ Yes | ❌ No |
| **Governed Metrics** | ✅ Partial | ❌ No | ❌ No | ✅ Yes |
| **Data Stays in Snowflake** | ❌ No | ❌ No | ✅ Yes | ❌ No |
| **Best For** | Multi-app | Solo dev | Snowflake-only | dbt users |

---

## 🧭 Which Should I Use?

### Decision Tree

```
1. Do you already use dbt for metrics?
   ├─ YES → Try dbt Semantic Layer
   └─ NO  → Continue to 2

2. Do you need ad-hoc queries (users can ask anything)?
   ├─ NO  → dbt Semantic Layer (define metrics first)
   └─ YES → Continue to 3

3. Is all your data in Snowflake and want to keep it there?
   ├─ YES → Snowflake Cortex
   └─ NO  → Continue to 4

4. Do you need to share data tools across multiple apps?
   ├─ YES → FastMCP
   └─ NO  → Direct SQL ⭐ (Recommended)
```

### When To Use Each

#### FastMCP
✅ **Use when:**
- Multiple apps need same data access
- Want predefined, versioned tools
- Need abstraction layer (swap DBs without changing bot)
- Have team maintaining MCP server

❌ **Skip when:**
- Building single bot
- Want simplest setup
- Don't want to deploy/maintain MCP server

#### Direct SQL
✅ **Use when:**
- Building single Slack bot
- Want simplest possible setup
- Need maximum flexibility
- Trust LLM to write safe SQL
- Cost-conscious

❌ **Skip when:**
- Need strict query governance
- Multiple apps need same tools
- Want reusable tool library

#### Snowflake Cortex
✅ **Use when:**
- All data in Snowflake
- Want data to never leave Snowflake
- Don't want external LLM dependencies
- Comfortable with Mistral/Llama quality
- Low-medium query volume

❌ **Skip when:**
- High query volume (costs add up quickly)
- Need Claude/GPT-4 quality
- Don't have Snowflake Enterprise

#### dbt Semantic Layer
✅ **Use when:**
- Already using dbt for transformations
- Want governed, consistent metrics
- Need same definitions across tools
- Have team defining business logic
- Don't need ad-hoc queries

❌ **Skip when:**
- Don't want dbt Cloud costs ($100+/month)
- Need ad-hoc query flexibility
- Not using dbt

---

## 💡 Recommended Starting Point

**For most users: Start with Direct SQL** (`slack_bot_no_mcp.py`)

Why?
- ✅ Simplest setup (just bot + database)
- ✅ Lowest cost (~$40-70/month)
- ✅ Maximum flexibility (any question)
- ✅ Claude/GPT-4 writes excellent SQL
- ✅ Easy to switch to other options later

You can always migrate to FastMCP, Cortex, or Semantic Layer as your needs evolve!

---

## 📁 Integration Options

### FastMCP

**Architecture:**
```
Slack → Bot → LLM → FastMCP Server → Database
```

**Files:**
- Bot: `slack_bot.py`
- Config: `env.example`
- Requirements: `requirements.txt`

**Setup:**
```bash
cp env.example .env
pip install -r requirements.txt
python slack_bot.py
```

**Requires:** FastMCP server deployment

See [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md#fastmcp) for details.

---

### Direct SQL

**Architecture:**
```
Slack → Bot + LLM → Database
```

**Files:**
- Bot: `slack_bot_no_mcp.py`
- Config: `env_no_mcp.example`
- Requirements: `requirements_no_mcp.txt`

**Setup:**
```bash
cp env_no_mcp.example .env
pip install -r requirements_no_mcp.txt
python slack_bot_no_mcp.py
```

**Requires:** Database credentials only

See [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md#direct-sql) for details.

---

### Snowflake Cortex

**Architecture:**
```
Slack → Bot → Snowflake Cortex (LLM + Database)
```

**Files:**
- Bot: `slack_bot_cortex.py`
- Config: `env_cortex.example`
- Requirements: `requirements_cortex.txt`

**Setup:**
```bash
cp env_cortex.example .env
pip install -r requirements_cortex.txt
python slack_bot_cortex.py
```

**Requires:** Snowflake Enterprise with Cortex enabled

See [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md#snowflake-cortex) for details.

---

### dbt Semantic Layer

**Architecture:**
```
Slack → Bot + LLM → dbt Cloud API → Database
```

**Files:**
- Bot: `slack_bot_semantic.py`
- Config: `env_semantic.example`
- Requirements: `requirements_semantic.txt`

**Setup:**
```bash
cp env_semantic.example .env
pip install -r requirements_semantic.txt
python slack_bot_semantic.py
```

**Requires:** dbt Cloud Team/Enterprise plan

See [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md#dbt-semantic-layer) for details.

---

## 🌐 Deployment

### Heroku (Recommended)

Easiest way to deploy. See [HEROKU_DEPLOYMENT.md](HEROKU_DEPLOYMENT.md).

**Quick version:**
```bash
heroku create your-app-name
heroku config:set SLACK_BOT_TOKEN=xoxb-...
heroku config:set SLACK_APP_TOKEN=xapp-...
# ... set other env vars based on your integration choice
git push heroku main
heroku ps:scale worker=1
```

### Other Options

- **AWS Lambda**: Serverless deployment
- **Docker**: Container deployment
- **Local**: Run on any server with Python 3.11+

---

## 💰 Cost Comparison

**Monthly costs for 100 queries/day:**

| Component | FastMCP | Direct SQL | Cortex | Semantic |
|-----------|---------|------------|--------|----------|
| **Bot Hosting** | $7 | $7 | $7 | $7 |
| **Infrastructure** | $7-25 | $0 | $0 | $100+ |
| **LLM API** | $30-60 | $30-60 | $300-600 | $10-20 |
| **Total** | **$50-100** | **$40-70** | **$310-610** | **$120-150** |

*Cortex costs highly variable based on query complexity and volume*

---

## 🔐 Security

All integrations include:
- ✅ Read-only database access (recommended)
- ✅ SQL validation (blocks DROP, DELETE, etc.)
- ✅ Query logging
- ✅ Timeout protection
- ✅ Result size limits

**Best practices:**
- Use read-only DB credentials
- Rotate tokens regularly
- Monitor query logs
- Set appropriate timeouts
- Restrict to specific Slack channels

---

## 🎯 Example Queries

All integrations support natural language:

```
@DataBot What are the top 10 products by revenue?
@DataBot Show me customers with >5 orders
@DataBot What's the repeat purchase rate?
@DataBot Compare average order value by customer segment
@DataBot Which customers signed up in the last 30 days?
```

The LLM automatically:
- Understands the question
- Generates appropriate query
- Formats the answer clearly
- Handles follow-up questions in thread

---

## 📚 Documentation

- **[IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)** - Detailed setup for each integration
- **[HEROKU_DEPLOYMENT.md](HEROKU_DEPLOYMENT.md)** - Deployment instructions
- **[LICENSE](LICENSE)** - MIT License

---

## 🛠️ Development

### Local Setup

```bash
# Clone repo
git clone <this-repo>
cd slackbot_oss

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies (choose your integration)
pip install -r requirements_no_mcp.txt

# Configure
cp env_no_mcp.example .env
# Edit .env with your credentials

# Run
python slack_bot_no_mcp.py
```

### Testing

```bash
# Test bot connection
python slack_bot_no_mcp.py

# In Slack, test with:
@YourBot hello

# Ask a real question:
@YourBot What are the top 5 products by revenue?
```

---

## 🆘 Troubleshooting

### Bot doesn't respond
- Check Heroku logs: `heroku logs --tail`
- Verify environment variables are set
- Ensure bot is invited to channel
- Check Socket Mode is enabled

### Database connection errors
- Verify credentials in `.env`
- Check network access to database
- Test credentials directly with DB client

### LLM errors
- Verify API key is valid
- Check API quota/credits
- Review prompt length (token limits)

---

## 📝 License

MIT - See [LICENSE](LICENSE)

---

## 🙏 Contributing

Contributions welcome! Feel free to:
- Report bugs
- Suggest features
- Submit PRs
- Share improvements

---

## 🌟 Acknowledgments

Built with:
- [Slack Bolt](https://slack.dev/bolt-python/) - Slack integration
- [FastMCP](https://github.com/fastmcp/fastmcp) - MCP protocol
- [Anthropic Claude](https://anthropic.com) - LLM
- [Snowflake](https://snowflake.com) - Database & Cortex
- [dbt](https://getdbt.com) - Semantic Layer
