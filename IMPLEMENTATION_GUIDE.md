# Implementation Guide

Detailed implementation instructions for all 4 integration options.

---

## Table of Contents

1. [FastMCP Implementation](#fastmcp-implementation)
2. [Direct SQL Implementation](#direct-sql-implementation)
3. [Snowflake Cortex Implementation](#snowflake-cortex-implementation)
4. [dbt Semantic Layer Implementation](#dbt-semantic-layer-implementation)

---

# FastMCP Implementation

## Overview

FastMCP uses a separate MCP server that provides predefined tools to the LLM.

### Architecture

```
┌─────────┐     ┌─────────┐     ┌─────────────┐     ┌──────────────┐     ┌──────────┐
│  Slack  │ ──▶ │   Bot   │ ──▶ │     LLM     │ ──▶ │ FastMCP      │ ──▶ │ Database │
│  User   │ ◀── │         │ ◀── │ (Claude/    │ ◀── │ Server       │ ◀── │          │
└─────────┘     └─────────┘     │  GPT-4)     │     │ (Hosted)     │     └──────────┘
                                 └─────────────┘     └──────────────┘
```

## Setup

### 1. Deploy FastMCP Server

First, you need a running FastMCP server. See [FastMCP docs](https://github.com/fastmcp/fastmcp) for deployment options.

Your server should expose tools like:
```python
# Example MCP server tool
{
    "name": "query_companies",
    "description": "Get companies matching criteria",
    "parameters": {
        "min_revenue": {"type": "number", "optional": true},
        "sector": {"type": "string", "optional": true},
        "limit": {"type": "number", "default": 10}
    }
}
```

### 2. Configure Bot

```bash
cp env.example .env
```

Edit `.env`:
```bash
# Slack
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token

# FastMCP Server
FASTMCP_SERVER_URL=https://your-mcp-server.com/mcp
FASTMCP_TOKEN=fmcp_your-token

# LLM (choose one)
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-key
# or
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-your-key
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run

```bash
python slack_bot.py
```

## Tool Definitions

FastMCP provides structured tools. Example:

```python
# MCP Server defines:
tools = [
    {
        "name": "get_companies",
        "description": "Get list of companies",
        "parameters": {
            "as_of_date": "string",
            "limit": "number"
        }
    }
]

# Tool executes predefined SQL:
def get_companies(as_of_date, limit):
    sql = "SELECT * FROM companies WHERE date = ?"
    return execute(sql, as_of_date)
```

The LLM receives these tool definitions and calls them as needed.

## Security

- ✅ MCP server validates tool calls
- ✅ Predefined queries (SQL injection protected)
- ✅ Can restrict which queries are allowed
- ✅ Database credentials only on MCP server (not in bot)

## Pros & Cons

**Pros:**
- ✅ Structured tool definitions
- ✅ Server can be shared across apps
- ✅ Security layer (MCP validates queries)
- ✅ Version control tools separately
- ✅ Abstraction layer (swap DBs without changing bot)

**Cons:**
- ❌ Requires MCP server deployment
- ❌ Extra infrastructure to maintain
- ❌ Additional latency (extra hop)
- ❌ More complex setup

## Use Cases

Best for:
- Organizations with multiple apps needing data access
- Teams wanting strict control over available queries
- Production systems needing versioned, tested tools
- Platforms where abstraction is valuable

---

# Direct SQL Implementation

## Overview

LLM generates SQL directly, bot executes against database.

### Architecture

```
┌─────────┐     ┌─────────────────────┐     ┌──────────┐
│  Slack  │ ──▶ │   Bot + LLM         │ ──▶ │ Database │
│  User   │ ◀── │   Direct Functions  │ ◀── │          │
└─────────┘     └─────────────────────┘     └──────────┘
```

## Setup

### 1. Configure Bot

```bash
cp env_no_mcp.example .env
```

Edit `.env`:
```bash
# Slack
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token

# Snowflake Database
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_WAREHOUSE=your_warehouse
SNOWFLAKE_DATABASE=ANALYTICS
SNOWFLAKE_SCHEMA=PUBLIC

# LLM (choose one)
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-key
# or
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-your-key
```

### 2. Install Dependencies

```bash
pip install -r requirements_no_mcp.txt
```

### 3. Run

```bash
python slack_bot_no_mcp.py
```

## How It Works

1. User asks: "Top 5 customers by total spend?"
2. Bot sends question + schema to LLM
3. LLM generates SQL:
   ```sql
   SELECT 
     c.first_name || ' ' || c.last_name as customer_name,
     c.total_spent
   FROM customers c
   ORDER BY c.total_spent DESC 
   LIMIT 5
   ```
4. Bot executes SQL
5. LLM formats results into natural language answer

## SQL Validation

The bot includes built-in SQL safety:

```python
def validate_sql(sql: str) -> bool:
    """Block dangerous SQL"""
    sql_lower = sql.lower().strip()
    
    # Must start with SELECT
    if not sql_lower.startswith("select"):
        return False
    
    # Block destructive operations
    dangerous = ['drop', 'delete', 'truncate', 'update', 'insert', 'alter']
    if any(word in sql_lower for word in dangerous):
        return False
    
    return True
```

## Schema Discovery

On startup, the bot loads your database schema:

```python
def get_schema_info() -> str:
    """Get all table/column information"""
    cursor.execute("""
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'PUBLIC'
        ORDER BY table_name, ordinal_position
    """)
    # Returns: "table_name: column1 (type), column2 (type), ..."
```

This schema is included in every LLM prompt so it knows what tables/columns exist.

## Security

**Built-in protections:**
- ✅ Only SELECT statements allowed
- ✅ Blocks DROP, DELETE, UPDATE, INSERT, ALTER
- ✅ Query timeouts (30 seconds default)
- ✅ Result limits (1000 rows max)
- ✅ Read-only DB user recommended

**Mitigation strategy:**
```python
# In the bot code:
if not validate_sql(sql):
    raise ValueError("SQL query not allowed")

# Set query timeout
cursor.execute(sql, timeout=30)

# Limit results
cursor.execute(f"{sql} LIMIT 1000")
```

## Pros & Cons

**Pros:**
- ✅ Simple architecture (just bot + DB)
- ✅ No server to deploy
- ✅ Faster (fewer hops)
- ✅ Less infrastructure cost
- ✅ Easier to understand/debug
- ✅ Maximum flexibility (any question)

**Cons:**
- ❌ DB credentials in bot environment
- ❌ Less structured (LLM writes raw SQL)
- ❌ Harder to share logic across apps
- ❌ Security depends on LLM prompt constraints

## Use Cases

Best for:
- Single Slack bot deployments
- Internal tools where flexibility matters
- Solo developers or small teams
- Cost-sensitive projects
- Rapid prototyping

---

# Snowflake Cortex Implementation

## Overview

Uses Snowflake's built-in LLM (Mistral/Llama) for text-to-SQL **inside Snowflake**.

### Architecture

```
┌─────────┐     ┌─────────┐     ┌────────────────────────┐
│  Slack  │ ──▶ │   Bot   │ ──▶ │  Snowflake Cortex      │
│  User   │ ◀── │         │ ◀── │  (LLM + SQL + Data)    │
└─────────┘     └─────────┘     └────────────────────────┘
```

## What is Snowflake Cortex?

Snowflake Cortex is Snowflake's built-in AI/ML service:
- `COMPLETE()` - LLM completions (Mistral, Llama, etc.)
- Text-to-SQL capabilities
- Runs **inside Snowflake** (data never leaves)
- No external LLM API needed

## Setup

### 1. Enable Cortex in Snowflake

Cortex requires Snowflake Enterprise. Enable via:
```sql
-- Run as ACCOUNTADMIN
GRANT USAGE ON INTEGRATION SNOWFLAKE$CORTEX TO ROLE YOUR_ROLE;
```

### 2. Configure Bot

```bash
cp env_cortex.example .env
```

Edit `.env`:
```bash
# Slack
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token

# Snowflake
SNOWFLAKE_ACCOUNT=your_account.snowflakecomputing.com
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_WAREHOUSE=your_warehouse
SNOWFLAKE_DATABASE=ANALYTICS
SNOWFLAKE_SCHEMA=ANALYTICS

# Cortex Configuration
CORTEX_MODEL=mistral-large
# Options: mistral-large, mistral-7b, llama3-70b, llama3-8b, mixtral-8x7b

# Optional
SHOW_SQL=false  # Show generated SQL in responses
```

### 3. Install Dependencies

```bash
pip install -r requirements_cortex.txt
```

### 4. Run

```bash
python slack_bot_cortex.py
```

## How It Works

1. **User asks:** "What are the top 5 products by revenue?"

2. **Bot generates SQL prompt using Cortex:**
   ```sql
   SELECT SNOWFLAKE.CORTEX.COMPLETE(
       'mistral-large',
       'Given this schema: products (product_id, product_name), order_items (quantity, unit_price)
        Generate SQL for: top 5 products by revenue'
   ) as generated_sql
   ```

3. **Cortex returns SQL:**
   ```sql
   SELECT 
     p.product_name,
     SUM(oi.quantity * oi.unit_price) as total_revenue
   FROM products p
   JOIN order_items oi ON p.product_id = oi.product_id
   GROUP BY p.product_name
   ORDER BY total_revenue DESC
   LIMIT 5
   ```

4. **Bot executes the SQL:**
   ```sql
   -- Execute the generated SQL
   SELECT p.product_name, SUM(...) FROM ...
   ```

5. **Cortex formats the answer:**
   ```sql
   SELECT SNOWFLAKE.CORTEX.COMPLETE(
       'mistral-large',
       'Format this data into a clear answer:
        [{"product_name": "Wireless Headphones", "total_revenue": 24350}, ...]'
   ) as formatted_answer
   ```

6. **Bot posts to Slack**

## Schema Discovery

On startup, the bot loads schema from `INFORMATION_SCHEMA`:

```python
def _get_schema_info(self) -> str:
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = %s
    """, (self.schema,))
    
    # Get columns for each table
    # Returns: "table: col1 (type), col2 (type), ..."
```

## SQL Validation

Same safety as Direct SQL:

```python
def _is_safe_sql(self, sql: str) -> bool:
    # Must start with SELECT
    if not sql.lower().strip().startswith("select"):
        return False
    
    # Block dangerous keywords
    dangerous = ["drop", "delete", "truncate", "insert", "update", "alter"]
    if any(keyword in sql.lower() for keyword in dangerous):
        return False
    
    return True
```

## Available Cortex Models

| Model | Speed | Quality | Cost |
|-------|-------|---------|------|
| `mistral-large` | Medium | High | $$$ |
| `mistral-7b` | Fast | Medium | $ |
| `llama3-70b` | Slow | High | $$$ |
| `llama3-8b` | Fast | Medium | $ |
| `mixtral-8x7b` | Medium | High | $$ |

Set in `.env`:
```bash
CORTEX_MODEL=mistral-large
```

## Cost

Cortex charges per token:
- **Mistral Large:** ~$0.0002 per token
- **Average query:** 500-1000 tokens
- **Per query cost:** $0.10-$0.20
- **100 queries/day:** $10-20/day ($300-600/month)

**Warning:** Costs can add up quickly with high volume!

## Pros & Cons

**Pros:**
- ✅ **No external LLM costs** (Cortex pricing built into Snowflake)
- ✅ **Data never leaves Snowflake** (privacy/security)
- ✅ **Schema-aware** (Cortex can see your tables)
- ✅ **Multiple LLM options** (Mistral, Llama, etc.)
- ✅ **Simple architecture** (just bot + Snowflake)

**Cons:**
- ❌ Limited to Snowflake-supported LLMs (no Claude/GPT-4)
- ❌ Cortex costs can add up quickly
- ❌ Less control over prompts/behavior
- ❌ Requires Snowflake Enterprise
- ❌ LLM quality not as good as Claude/GPT-4

## Use Cases

Best for:
- Snowflake-centric organizations
- Privacy-focused teams (data stays in Snowflake)
- Teams comfortable with Mistral/Llama quality
- Low-medium query volumes
- Organizations already paying for Snowflake Enterprise

---

# dbt Semantic Layer Implementation

## Overview

Queries predefined metrics from dbt Cloud's Semantic Layer API.

### Architecture

```
┌─────────┐     ┌──────────────────┐     ┌──────────────────┐     ┌──────────┐
│  Slack  │ ──▶ │   Bot + LLM      │ ──▶ │   dbt Cloud      │ ──▶ │ Database │
│  User   │ ◀── │  (mapping only)  │ ◀── │  Semantic Layer  │ ◀── │          │
└─────────┘     └──────────────────┘     └──────────────────┘     └──────────┘
```

## What is dbt Semantic Layer?

The dbt Semantic Layer provides:
- **Predefined metrics** from your dbt project
- **GraphQL/REST API** to query metrics
- **Business logic in code** (not SQL)
- **Consistent definitions** across all tools

Instead of writing SQL, you query by metric name: `avg_order_value`.

## Setup

### 1. Define Metrics in dbt

In your dbt project (`dbt/models/marts/orders.yml`):

```yaml
semantic_models:
  - name: ecommerce_orders
    model: ref('orders')
    
    dimensions:
      - name: order_date
        type: time
        type_params:
          time_granularity: day
      
      - name: customer_segment
        type: categorical
      
      - name: payment_method
        type: categorical
    
    measures:
      - name: order_amount
        agg: avg
        description: "Average order value"
      
      - name: total_revenue
        agg: sum
        description: "Total revenue"
      
      - name: order_count
        agg: count
        description: "Total number of orders"

metrics:
  - name: avg_order_value
    type: simple
    type_params:
      measure: order_amount
    label: "Average Order Value"
  
  - name: total_revenue
    type: simple
    type_params:
      measure: total_revenue
    label: "Total Revenue"
  
  - name: total_orders
    type: simple
    type_params:
      measure: order_count
    label: "Total Orders"
```

### 2. Enable Semantic Layer in dbt Cloud

1. Go to **Account Settings** → **Projects**
2. Enable **Semantic Layer**
3. Generate **Service Token**
4. Note your **Environment ID**

### 3. Configure Bot

```bash
cp env_semantic.example .env
```

Edit `.env`:
```bash
# Slack
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token

# dbt Cloud Semantic Layer
DBT_CLOUD_SERVICE_TOKEN=your_service_token
DBT_CLOUD_ENVIRONMENT_ID=12345

# LLM for mapping questions (Claude recommended)
ANTHROPIC_API_KEY=sk-ant-your-key
LLM_MODEL=claude-3-5-sonnet-20241022

# Optional
SHOW_SQL=false
```

### 4. Install Dependencies

```bash
pip install -r requirements_semantic.txt
```

### 5. Run

```bash
python slack_bot_semantic.py
```

## How It Works

1. **User asks:** "What's the average order value by customer segment?"

2. **Bot loads available metrics** from Semantic Layer:
   ```graphql
   query {
       metrics(environmentId: 12345) {
           name
           description
           dimensions { name }
       }
   }
   ```

3. **LLM maps question to metrics:**
   ```json
   {
       "metrics": ["avg_order_value"],
       "group_by": ["customer_segment"],
       "limit": 100
   }
   ```

4. **Bot queries Semantic Layer:**
   ```graphql
   query {
       query(
           environmentId: 12345,
           metrics: ["avg_order_value"],
           groupBy: ["customer_segment"]
       ) {
           rows { values }
       }
   }
   ```

5. **Semantic Layer executes predefined query**

6. **LLM formats answer** from the data

7. **Bot posts to Slack**

## Querying Metrics

Example GraphQL query:

```python
query = """
query {
    metrics(
        environmentId: 12345,
        metrics: ["avg_order_value", "total_revenue"],
        groupBy: ["customer_segment", "order_date"],
        where: [
            {
                "dimension": "order_date",
                "operator": ">=",
                "value": "2024-01-01"
            }
        ],
        orderBy: ["total_revenue DESC"],
        limit: 100
    ) {
        sql
        rows {
            dimensions { name value }
            measures { name value }
        }
    }
}
"""
```

## Metrics Catalog

Bot automatically loads available metrics on startup:

```python
def get_metrics_catalog():
    # Returns:
    # - avg_order_value: Average order value across orders
    #   Dimensions: customer_segment, order_date, payment_method
    # - total_revenue: Total revenue from all orders
    #   Dimensions: customer_segment, order_date
    # ...
```

LLM uses this catalog to understand what metrics exist.

## Slash Commands

Add `/metrics` command to list available metrics:

```python
@slack_app.command("/metrics")
async def handle_metrics_command(ack, say):
    await ack()
    metrics_desc = semantic_layer.get_metrics_description()
    await say(f"📊 **Available Metrics:**\n\n{metrics_desc}")
```

Usage in Slack:
```
/metrics
```

## Pros & Cons

**Pros:**
- ✅ **Business logic in code** (version controlled)
- ✅ **Consistent metrics** across all tools
- ✅ **No SQL in bot** (queries via metric names)
- ✅ **Governed definitions** (one source of truth)
- ✅ **Can use any LLM** (just for mapping questions to metrics)

**Cons:**
- ❌ Requires dbt Cloud Team/Enterprise ($100+/month)
- ❌ Limited to predefined metrics (no ad-hoc queries)
- ❌ Requires maintaining semantic layer definitions
- ❌ Extra infrastructure (dbt Cloud)

## Use Cases

Best for:
- Teams already using dbt for transformations
- Organizations needing governed metrics
- Multi-tool environments (same metrics everywhere)
- Teams with data engineers defining business logic
- Controlled query environments

---

# Comparison Summary

## Feature Matrix

| Feature | FastMCP | Direct SQL | Cortex | Semantic |
|---------|---------|------------|--------|----------|
| **Complexity** | High | Low | Low | Medium |
| **Ad-hoc queries** | ❌ | ✅ | ✅ | ❌ |
| **LLM quality** | Best | Best | Good | Best |
| **Data governance** | Partial | None | None | Full |
| **External dependencies** | MCP Server | None | None | dbt Cloud |
| **Setup time** | 2-4 hours | 30 min | 1 hour | 2-3 hours |

## Cost Comparison (100 queries/day)

| Integration | Bot | Infrastructure | LLM | Total/Month |
|-------------|-----|----------------|-----|-------------|
| FastMCP | $7 | $7-25 | $30-60 | **$50-100** |
| Direct SQL | $7 | $0 | $30-60 | **$40-70** |
| Cortex | $7 | $0 | $300-600 | **$310-610** |
| Semantic | $7 | $100+ | $10-20 | **$120-150** |

## Recommended Use Cases

- **Solo dev, internal tool:** Direct SQL
- **Snowflake-only, privacy-focused:** Cortex
- **dbt users, governed metrics:** Semantic Layer
- **Multi-app platform:** FastMCP

---

# Troubleshooting

## All Integrations

### Bot doesn't respond
```bash
# Check logs
heroku logs --tail

# Verify env vars
heroku config

# Test locally
python slack_bot_*.py
```

### Slack connection errors
- Verify Socket Mode is enabled
- Check bot is invited to channel
- Regenerate tokens if needed

## Direct SQL & Cortex

### Database connection failed
```python
# Test connection
python -c "
import snowflake.connector
conn = snowflake.connector.connect(
    account='your_account',
    user='your_user',
    password='your_password'
)
print('Connected!')
"
```

### SQL validation errors
- Check if query starts with SELECT
- Look for blocked keywords (DROP, DELETE, etc.)
- Review logs for exact error

## Cortex

### Cortex COMPLETE not found
- Verify Snowflake Enterprise license
- Check Cortex is enabled: `SHOW INTEGRATIONS;`
- Grant usage: `GRANT USAGE ON INTEGRATION SNOWFLAKE$CORTEX TO ROLE YOUR_ROLE;`

### High costs
- Switch to cheaper model (mistral-7b vs mistral-large)
- Reduce query volume
- Consider Direct SQL with Claude instead

## Semantic Layer

### Metrics not found
```bash
# Test API connection
curl -X POST https://semantic-layer.cloud.getdbt.com/api/graphql \
  -H "Authorization: Token YOUR_TOKEN" \
  -d '{"query": "{ metrics(environmentId: 12345) { name } }"}'
```

### Metric definitions not updating
- Redeploy dbt project
- Check environment ID is correct
- Verify semantic model syntax

---

# Next Steps

1. **Choose your integration** based on requirements
2. **Follow setup instructions** for that option
3. **Deploy to Heroku** (see HEROKU_DEPLOYMENT.md)
4. **Test with real queries**
5. **Monitor costs and performance**
6. **Iterate and improve**

Need help? Check the main README or open an issue!

