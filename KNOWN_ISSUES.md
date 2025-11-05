# Known Issues & Limitations

This document tracks known issues, limitations, and areas needing testing for each bot implementation.

---

## ✅ slack_bot_no_mcp.py (Direct SQL)

### Status: **Production Ready** (95% confidence)

#### ✅ Fixed Issues
- ✅ SQL injection vulnerability in `get_table_columns()` - **FIXED** (using parameterized queries)
- ✅ Missing password authentication support - **FIXED** (supports both password and browser auth)

#### ⚠️ Known Limitations

**1. Schema Discovery Could Be Improved**
- **Issue:** Basic table listing, LLM doesn't know all column names upfront
- **Impact:** Medium - LLM may need to call `get_schema_info` tool first
- **Workaround:** Enhance system prompt with full schema (see CONTEXT_GUIDE.md)
- **Priority:** Low (works, just not optimal)

**2. No Query Timeout Protection**
- **Issue:** Long-running queries could timeout Slack response
- **Impact:** Low - most queries are fast
- **Fix:** Add timeout parameter to cursor.execute()
```python
cursor.execute(sql, timeout=30)  # 30 second timeout
```
- **Priority:** Medium

**3. Result Size Limits**
- **Issue:** No hard limit on result set size
- **Impact:** Low - LLM prompts usually include LIMIT
- **Fix:** Add max rows check
```python
if len(rows) > 1000:
    rows = rows[:1000]
    logger.warning("Result set truncated to 1000 rows")
```
- **Priority:** Low

#### 🧪 Needs Testing
- Large result sets (>1000 rows)
- Complex multi-table JOINs
- Edge cases with NULL values
- Non-Snowflake databases (Postgres, BigQuery, etc.)

#### 🎯 Expected Success Rate
- **First run:** 85% (most setups will work)
- **After env var fixes:** 95%
- **After schema enhancement:** 98%

---

## ⚠️ slack_bot.py (FastMCP)

### Status: **Requires MCP Server** (70% confidence)

#### ✅ What Works
- ✅ Slack integration (copied from tested bot)
- ✅ LLM provider abstraction (standard pattern)
- ✅ Tool calling logic (follows Anthropic/OpenAI specs)
- ✅ Error handling

#### ❌ Untested Components

**1. FastMCP Server Communication**
- **Issue:** Never tested with a real MCP server
- **Impact:** High - core functionality
- **What might break:**
  - Tool format mismatch
  - Authentication issues
  - Response parsing
- **Testing needed:** Connect to real FastMCP server

**2. Tool Call Format**
- **Issue:** Assumed OpenAI tool format works with all MCP servers
- **Impact:** Medium
- **Fix:** May need to adapt tool format for specific MCP implementations

**3. Missing MCP Server Deployment Guide**
- **Issue:** Users need to deploy MCP server but no detailed guide
- **Impact:** High - blocker for users
- **Fix:** Add MCP server deployment instructions

#### 🎯 Expected Success Rate
- **With working MCP server:** 70%
- **First-time MCP setup:** 40% (users will struggle with server setup)

**Recommendation:** Only use if you already have a FastMCP server running

---

## 🔴 slack_bot_cortex.py (Snowflake Cortex)

### Status: **Experimental** (40% confidence)

#### ❌ Critical Unknowns

**1. Cortex API Never Tested**
- **Issue:** Written from Snowflake docs, never executed
- **Impact:** CRITICAL
- **What might break:**
  - `SNOWFLAKE.CORTEX.COMPLETE()` syntax
  - Response format
  - Model names
  - Token limits
  - Prompt escaping

**2. Prompt Escaping Likely Insufficient (Line 123-128)**
```python
sql_generation = f"""
SELECT SNOWFLAKE.CORTEX.COMPLETE(
    '{self.model}',
    '{sql_prompt.replace("'", "''")}'  # Only escapes single quotes
) as generated_sql
"""
```

**Issues:**
- Multi-line prompts with newlines
- Special characters in schema info
- Long prompts (>1000 chars)

**Likely fix needed:**
```python
# Use proper SQL string escaping or parameterized queries
prompt_param = sql_prompt.replace("'", "''").replace("\n", " ")
```

**3. Schema Loading Might Timeout**
- **Issue:** Loads all tables/columns on startup
- **Impact:** High - bot might crash on init
- **Fix:** Add timeout, limit to specific tables, or lazy load

**4. Response Format Unknown**
- **Issue:** Don't know if Cortex returns clean SQL or markdown-wrapped
- **Current cleanup:** Basic (removes ``` lines)
- **Might need:** More sophisticated parsing

**5. No Error Recovery**
- **Issue:** If Cortex generates bad SQL, no retry logic
- **Impact:** Medium - user gets error, can try again

#### 🧪 Must Test Before Using
- ✅ Basic Cortex COMPLETE() call
- ✅ SQL generation with real schema
- ✅ Prompt escaping with complex queries
- ✅ Response parsing
- ✅ Error cases

#### 🎯 Expected Success Rate
- **First run:** 20-40%
- **After debugging:** 70-80%
- **Debugging time:** 4-8 hours

**Recommendation:** Consider this a **starting template**, not production-ready code

---

## 🔴 slack_bot_semantic.py (dbt Semantic Layer)

### Status: **Experimental** (30% confidence)

#### ❌ Critical Unknowns

**1. GraphQL API Format Unknown**
- **Issue:** Never tested against real dbt Semantic Layer API
- **Impact:** CRITICAL
- **What's probably wrong:**
  - Query syntax
  - Variable interpolation (using f-strings with JSON)
  - Field names
  - Response structure

**Example that might fail (Line 118-143):**
```python
query = f"""
query {{
    query(
        environmentId: {self.environment_id},
        metrics: {json.dumps(metrics)},  # ❌ Might not work in GraphQL
        groupBy: {group_by_str},
        ...
    )
}}
"""
```

**Correct format might be:**
```python
query = """
query($envId: Int!, $metrics: [String!]!) {
    query(
        environmentId: $envId,
        metrics: $metrics,
        ...
    )
}
"""
variables = {
    "envId": int(self.environment_id),
    "metrics": metrics,
    ...
}
```

**2. Authentication Might Be Wrong**
- **Issue:** Using `Token` auth header
- **Actual format:** Might need `Bearer`, different header, or API key format
- **Impact:** High - won't connect at all

**3. Metrics Catalog Query Unproven**
- **Issue:** Initial metrics fetch might fail
- **Impact:** CRITICAL - bot won't start
- **Testing needed:** Real dbt Cloud account

**4. Response Transformation Fragile**
- **Issue:** Assumes specific nested structure
- **Code (Line 127-143):** Manually unpacks dimensions/measures
- **Risk:** Structure might be different, will crash

**5. LLM Mapping Might Fail**
- **Issue:** LLM must return perfect JSON
- **No validation:** Will crash on parse error
- **Fix needed:**
```python
try:
    query_plan = json.loads(content)
except json.JSONDecodeError:
    logger.error(f"LLM returned invalid JSON: {content}")
    return {"error": "Failed to parse query plan"}
```

#### 🧪 Must Test Before Using
- ✅ GraphQL authentication
- ✅ Metrics catalog query
- ✅ Actual metric query
- ✅ Response parsing
- ✅ Error handling
- ✅ LLM JSON generation

#### 🎯 Expected Success Rate
- **First run:** 10-30%
- **After debugging GraphQL:** 60%
- **After full testing:** 80%
- **Debugging time:** 8-16 hours

**Recommendation:** This is a **code sketch**, not working implementation. Budget time for development.

---

## 🛠️ Quick Fixes Available

### Direct SQL (slack_bot_no_mcp.py)

**Add Query Timeout:**
```python
def execute_query(self, sql: str) -> List[Dict]:
    try:
        cursor = self.conn.cursor()
        cursor.execute(sql, timeout=30)  # Add this
        # ...
```

**Add Result Limit:**
```python
def execute_query(self, sql: str, max_rows: int = 1000) -> List[Dict]:
    # ...
    rows = cursor.fetchall()
    
    if len(rows) > max_rows:
        logger.warning(f"Truncating {len(rows)} rows to {max_rows}")
        rows = rows[:max_rows]
    
    results = [dict(zip(columns, row)) for row in rows]
```

### Cortex (slack_bot_cortex.py)

**Test Basic Connection:**
```python
# Add to your test script
cursor.execute("""
    SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-7b', 'Say hello')
""")
print(cursor.fetchone()[0])
```

**Improve Prompt Escaping:**
```python
# Instead of simple replace
prompt = sql_prompt.replace("'", "''").replace("\n", " ").replace('"', '""')
```

### Semantic Layer (slack_bot_semantic.py)

**Test API First:**
```bash
curl -X POST https://semantic-layer.cloud.getdbt.com/api/graphql \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ __schema { types { name } } }"}'
```

**Add JSON Validation:**
```python
try:
    query_plan = json.loads(content)
    if "metrics" not in query_plan:
        raise ValueError("Missing metrics field")
except (json.JSONDecodeError, ValueError) as e:
    return {"error": f"Invalid query plan: {e}"}
```

---

## 📊 Testing Checklist

### Before Deploying to Production

#### Direct SQL ✅
- [x] Snowflake connection (password auth)
- [x] Snowflake connection (browser auth)
- [x] SQL injection protection
- [ ] Query timeout handling
- [ ] Large result sets (>1000 rows)
- [ ] Schema discovery with many tables
- [ ] Complex JOINs
- [ ] Error messages in Slack

#### FastMCP ⚠️
- [ ] Connect to real FastMCP server
- [ ] Tool discovery
- [ ] Tool execution
- [ ] Response handling
- [ ] Error cases
- [ ] Multiple LLM providers (Claude, GPT-4)

#### Cortex 🔴
- [ ] Basic COMPLETE() call
- [ ] SQL generation
- [ ] SQL execution
- [ ] Answer formatting
- [ ] Prompt escaping
- [ ] Schema loading
- [ ] Error handling
- [ ] All model types (mistral-large, llama, etc.)

#### Semantic Layer 🔴
- [ ] API authentication
- [ ] Metrics catalog fetch
- [ ] GraphQL query format
- [ ] Response parsing
- [ ] LLM JSON generation
- [ ] Error handling
- [ ] All metric types

---

## 🚀 Improvement Roadmap

### High Priority (Do Soon)
1. ✅ Fix SQL injection (Direct SQL) - **DONE**
2. ✅ Add password auth (Direct SQL) - **DONE**
3. Add query timeouts (Direct SQL)
4. Test Cortex API basics
5. Test Semantic Layer API basics

### Medium Priority (Nice to Have)
1. Add result size limits
2. Improve schema context
3. Add conversation history
4. Better error messages
5. Add retry logic

### Low Priority (Future)
1. Support more databases (Postgres, BigQuery)
2. Add query caching
3. Add user analytics
4. Custom slash commands
5. Message reactions for feedback

---

## 📝 Contributing

Found a bug? Tested a bot? Please contribute!

1. **Report Issues:** Open GitHub issue with:
   - Which bot (Direct SQL, Cortex, etc.)
   - Error message
   - Environment (Snowflake version, Python version, etc.)

2. **Share Fixes:** Submit PR with:
   - Description of issue
   - How you fixed it
   - Test results

3. **Share Success Stories:** Comment on issues if something works!

---

## 🆘 Getting Help

### If Direct SQL Doesn't Work
1. Check Snowflake credentials
2. Test connection outside bot: `python -c "import snowflake.connector; ..."`
3. Check env vars are loaded: `echo $SNOWFLAKE_USER`
4. Check logs: Look for connection errors

### If Cortex Doesn't Work
1. Verify Cortex is enabled: `SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-7b', 'test')`
2. Check grants: `SHOW GRANTS TO ROLE YOUR_ROLE`
3. Open issue with error message

### If Semantic Layer Doesn't Work
1. Test API directly with curl (see above)
2. Verify service token is valid
3. Check environment ID is correct
4. Open issue with API response

---

**Last Updated:** November 5, 2025  
**Maintainer:** @williamxwood

