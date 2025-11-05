# Dependency Management & Update Impact

How updates to Slack Bolt and FastMCP would impact this project.

---

## 📦 Current Dependencies

### All Bots Use:
- **slack-bolt >= 1.18.0** - Slack integration
- **python-dotenv >= 1.0.0** - Environment variables

### Bot-Specific:
- **Direct SQL:** snowflake-connector-python, anthropic
- **FastMCP:** fastmcp >= 2.0.0, anthropic/openai
- **Cortex:** snowflake-connector-python
- **Semantic:** anthropic, requests

---

## 🎯 Slack Bolt Dependency Analysis

### What We Use From Slack Bolt

All 4 bots use these Slack Bolt APIs:

```python
# 1. Core initialization
from slack_bolt.async_app import AsyncApp
slack_app = AsyncApp(token=os.environ.get("SLACK_BOT_TOKEN"))

# 2. Socket Mode handler
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
handler = AsyncSocketModeHandler(slack_app, os.environ.get("SLACK_APP_TOKEN"))

# 3. Event decorators
@slack_app.event("app_mention")
async def handle_mention(event, say):
    ...

@slack_app.event("message")
async def handle_message(event, say):
    ...

# 4. Event handler parameters
event = {
    "user": "U123",
    "text": "question",
    "channel": "C123",
    "ts": "timestamp",
    "thread_ts": "parent_timestamp"
}

# 5. Say function
await say(text="response", thread_ts=thread_ts)

# 6. Client API
await slack_app.client.auth_test()
```

### Slack Bolt API Surface Area

**Total API surface used:** ~6 functions/patterns

| API | Used In | Risk Level | Notes |
|-----|---------|------------|-------|
| `AsyncApp()` | All 4 bots | 🟢 Low | Core API, stable since v1.0 |
| `AsyncSocketModeHandler()` | All 4 bots | 🟢 Low | Stable async pattern |
| `@event()` decorator | All 4 bots | 🟢 Low | Core feature, unlikely to change |
| `say()` function | All 4 bots | 🟢 Low | Standard parameter passing |
| `event` dict structure | All 4 bots | 🟡 Medium | Keys could change |
| `client.auth_test()` | 2 bots | 🟢 Low | Standard Slack Web API |

### What Could Break

#### 🟢 **Low Risk (Unlikely to Break)**

**1. AsyncApp Initialization**
```python
slack_app = AsyncApp(token=os.environ.get("SLACK_BOT_TOKEN"))
```
- This is core Slack Bolt API
- Stable since v1.0 (2020)
- Would require major version bump (v2.0, v3.0) to change
- **Impact:** Would affect line 1 in each bot

**2. Event Decorators**
```python
@slack_app.event("app_mention")
async def handle_mention(event, say):
```
- Core pattern, very stable
- Hasn't changed since introduction
- **Impact:** Would affect event handler definitions

#### 🟡 **Medium Risk (Possible Changes)**

**1. Event Dict Structure**
```python
event = {
    "user": "U123",      # ⚠️ Key names could change
    "text": "...",       # ⚠️ Structure could evolve
    "channel": "C123",
    "thread_ts": "..."
}
```
- Slack could add/change fields
- We access: `event["user"]`, `event["text"]`, `event.get("thread_ts")`
- **Impact:** Runtime errors if keys change
- **Mitigation:** Use `.get()` with defaults (we already do this for thread_ts)

**2. Say Function Parameters**
```python
await say(text="response", thread_ts=thread_ts)
```
- Could add required parameters
- Could change parameter names
- **Impact:** Function call errors
- **Mitigation:** Stay within documented API

#### 🔴 **Breaking Changes to Watch**

**1. Socket Mode Handler Changes**
- Slack Bolt v2.0 could change async patterns
- **Impact:** High - bot won't start
- **Fix time:** 30-60 minutes (update initialization)

**2. Client API Changes**
- `slack_app.client.*` methods could change
- **Impact:** Medium - auth check fails
- **Fix time:** 15 minutes

---

## 🔧 FastMCP Dependency Analysis

### What We Use From FastMCP

Only **slack_bot.py** uses FastMCP:

```python
# 1. Import
from fastmcp import Client
from fastmcp.client.auth import BearerAuth

# 2. Initialize client
self.mcp_client = Client(
    server_url=os.environ.get("FASTMCP_SERVER_URL"),
    auth=BearerAuth(token=os.environ.get("FASTMCP_TOKEN"))
)

# 3. Get available tools (assumed)
tools = await self.mcp_client.get_tools()

# 4. Call tools (assumed)
result = await self.mcp_client.call_tool(
    tool_name="query_data",
    arguments={"param": "value"}
)
```

### FastMCP API Surface Area

**Total API surface used:** ~4 methods

| API | Risk Level | Notes |
|-----|------------|-------|
| `Client()` | 🟢 Low | Core initialization |
| `BearerAuth()` | 🟢 Low | Standard auth pattern |
| `get_tools()` | 🔴 High | **Not verified - might not exist** |
| `call_tool()` | 🔴 High | **Not verified - might not exist** |

### What Could Break

#### 🔴 **High Risk - Already Uncertain**

**1. FastMCP Client API Unknown**
```python
# These methods are ASSUMED but not verified:
tools = await self.mcp_client.get_tools()
result = await self.mcp_client.call_tool(...)
```

**Issue:** FastMCP API might be completely different
- Method names might be wrong
- Parameters might be different
- Response format unknown

**Impact:** slack_bot.py might not work at all with real FastMCP
**Fix time:** 2-4 hours (read FastMCP docs, update code)

**2. MCP Protocol Changes**
- FastMCP follows MCP protocol spec
- Protocol could evolve (tool formats, schemas, etc.)
- **Impact:** Medium - would need code updates
- **Fix time:** 1-2 hours

---

## 📊 Overall Dependency Risk Matrix

| Bot | Total Dependencies | Critical Dependencies | Update Risk | Maintenance Burden |
|-----|-------------------|----------------------|-------------|-------------------|
| **Direct SQL** | 3 packages | slack-bolt, anthropic | 🟢 Low | Low (stable APIs) |
| **FastMCP** | 5 packages | slack-bolt, fastmcp | 🔴 High | High (unverified API) |
| **Cortex** | 2 packages | slack-bolt, snowflake | 🟢 Low | Low (minimal deps) |
| **Semantic** | 3 packages | slack-bolt, anthropic | 🟡 Medium | Medium (API changes) |

---

## 🚨 Impact Scenarios

### Scenario 1: **Slack Bolt v2.0 Released**

**Potential Changes:**
- Async handler initialization
- Event decorator syntax
- Client API methods

**Impact on Our Bots:**

| Bot | Impact | Fix Time | Severity |
|-----|--------|----------|----------|
| Direct SQL | Update handler init | 30 min | 🟡 Medium |
| FastMCP | Update handler init | 30 min | 🟡 Medium |
| Cortex | Update handler init | 30 min | 🟡 Medium |
| Semantic | Update handler init | 30 min | 🟡 Medium |

**Migration Example:**
```python
# Old (v1.x)
handler = AsyncSocketModeHandler(slack_app, token)

# New (hypothetical v2.x)
handler = AsyncSocketModeHandler(app=slack_app, app_token=token, config={...})
```

**Mitigation:**
- Pin to `slack-bolt>=1.18.0,<2.0.0` in requirements
- Test with new version before upgrading
- Update all 4 bots simultaneously

---

### Scenario 2: **FastMCP v3.0 Released**

**Potential Changes:**
- Client initialization
- Authentication methods
- Tool calling format
- Response structure

**Impact:**

| Component | Impact | Fix Time | Severity |
|-----------|--------|----------|----------|
| slack_bot.py ONLY | Client API rewrite | 2-4 hours | 🔴 High |
| Other 3 bots | No impact | 0 min | 🟢 None |

**Why isolated:**
- Only slack_bot.py uses FastMCP
- Other 3 bots completely independent
- FastMCP changes don't cascade

**Mitigation:**
- Pin to `fastmcp>=2.0.0,<3.0.0`
- Read migration guide when v3.0 comes out
- Only update when ready

---

### Scenario 3: **Anthropic API v1.0 Released**

**Potential Changes:**
- Message format
- Tool calling syntax
- Response structure

**Impact:**

| Bot | Impact | Fix Time | Severity |
|-----|--------|----------|----------|
| Direct SQL | Update tool calls | 1-2 hours | 🟡 Medium |
| FastMCP | Update tool calls | 1-2 hours | 🟡 Medium |
| Cortex | No impact | 0 min | 🟢 None |
| Semantic | Update tool calls | 1-2 hours | 🟡 Medium |

**Migration Example:**
```python
# Old (current)
response = await client.messages.create(
    model="claude-3-5-sonnet-20241022",
    messages=[...],
    tools=[...]
)

# New (hypothetical breaking change)
response = await client.chat.create(
    model="claude-4-sonnet",
    conversation=[...],
    available_tools=[...]
)
```

**Mitigation:**
- Pin to `anthropic>=0.40.0,<1.0.0`
- Anthropic has good migration guides
- Usually provides backwards compatibility

---

## 🛡️ Protection Strategies

### 1. **Version Pinning (Conservative)**

**Current (permissive):**
```txt
slack-bolt>=1.18.0
fastmcp>=2.0.0
anthropic>=0.40.0
```
**Risk:** Could auto-upgrade to breaking versions

**Conservative (locked):**
```txt
slack-bolt>=1.18.0,<2.0.0
fastmcp>=2.0.0,<3.0.0
anthropic>=0.40.0,<1.0.0
```
**Benefit:** Won't break on major version updates

**Recommended for:** Production deployments

---

### 2. **Version Locking (Strict)**

**Exact versions:**
```txt
slack-bolt==1.18.1
fastmcp==2.0.3
anthropic==0.40.0
```

**Benefit:** 100% reproducible
**Risk:** Miss security patches and bug fixes

**Recommended for:** Critical production (manual updates only)

---

### 3. **Requirements Lock File**

**Create `requirements.lock`:**
```bash
# Generate from current environment
pip freeze > requirements.lock

# Install exact versions
pip install -r requirements.lock
```

**Benefit:** Exact reproducibility
**Use for:** Production deployments, testing

---

## 📅 Dependency Update Strategy

### Recommended Approach

**1. Use Version Ranges (Current Approach)**
```txt
slack-bolt>=1.18.0,<2.0.0
```
- ✅ Get bug fixes and security patches automatically
- ✅ Avoid breaking changes (major versions)
- ✅ Balanced approach

**2. Test Updates Locally First**
```bash
# Before deploying
pip install --upgrade slack-bolt
python slack_bot_no_mcp.py  # Test locally
# If works, deploy
```

**3. Monitor Changelogs**
- **Slack Bolt:** https://github.com/slackapi/bolt-python/releases
- **FastMCP:** https://github.com/fastmcp/fastmcp/releases
- **Anthropic:** https://github.com/anthropics/anthropic-sdk-python/releases

**4. Update Schedule**
- **Weekly:** Check for security updates
- **Monthly:** Review changelogs for new features
- **Quarterly:** Test with latest versions
- **Before major version:** Read migration guide, test thoroughly

---

## 🔍 Code Impact Surface Area

### Slack Bolt Changes Would Affect:

**All 4 Bots (Lines to Update):**
```
slack_bot_no_mcp.py:     Lines 15-16 (imports), 23 (init), 300-345 (events), 357 (handler)
slack_bot.py:            Lines 17-18 (imports), 31 (init), 290-345 (events), 361 (handler)
slack_bot_cortex.py:     Lines 15-16 (imports), 30 (init), 225-295 (events), 307 (handler)
slack_bot_semantic.py:   Lines 15-16 (imports), 31 (init), 256-372 (events), 378 (handler)
```

**Total lines at risk:** ~120 lines across 4 files

**Update difficulty:** Easy (mostly find/replace)

---

### FastMCP Changes Would Affect:

**Only slack_bot.py:**
```
Lines 145-146: imports
Lines 155-165: Client initialization
Lines 167-180: get_tools() calls (assumed)
Lines 220-240: call_tool() calls (assumed)
```

**Total lines at risk:** ~50 lines in 1 file

**Update difficulty:** Medium (need to understand new API)

---

### Other Dependencies

**Anthropic (affects 3 bots):**
- Used in: Direct SQL, FastMCP, Semantic Layer
- API surface: `messages.create()`, tool handling
- **Risk:** Medium (they're good about backwards compatibility)
- **Lines affected:** ~100 across 3 files

**Snowflake Connector (affects 2 bots):**
- Used in: Direct SQL, Cortex
- API surface: `connect()`, `cursor.execute()`
- **Risk:** Very low (stable for years)
- **Lines affected:** ~30 across 2 files

---

## 🔄 Update Process

### When a Dependency Updates

**Step 1: Check Changelog**
```bash
# Example for slack-bolt
pip show slack-bolt  # Current version
# Check GitHub releases for changes
```

**Step 2: Test in Dev**
```bash
# Create test environment
python3 -m venv test_env
source test_env/bin/activate

# Install new version
pip install slack-bolt==1.19.0  # New version

# Test each bot
python slack_bot_no_mcp.py
# Test in Slack
```

**Step 3: Update Requirements**
```txt
# If new version works
slack-bolt>=1.19.0,<2.0.0
```

**Step 4: Deploy**
```bash
git commit -m "Update slack-bolt to 1.19.0"
git push
# Deploy to production
```

---

## 🎯 Migration Guides for Breaking Changes

### If Slack Bolt v2.0 Breaks Things

**Common patterns that might need updates:**

**1. Initialization:**
```python
# Old
slack_app = AsyncApp(token=TOKEN)

# Might become
slack_app = AsyncApp(
    token=TOKEN,
    client=AsyncWebClient(token=TOKEN)  # More explicit
)
```

**Fix:** Update 1 line in each bot (4 files)

**2. Event Handlers:**
```python
# Old
@slack_app.event("app_mention")
async def handle(event, say):
    text = event["text"]

# Might become
@slack_app.event("app_mention")
async def handle(context):
    text = context.event["text"]
    await context.say("response")
```

**Fix:** Update event handlers in each bot (~20 lines per file)

---

### If FastMCP v3.0 Breaks Things

**Only affects: slack_bot.py**

**Possible changes:**

**1. Client Initialization:**
```python
# Old
client = Client(server_url=URL, auth=BearerAuth(token=TOKEN))

# Might become
client = FastMCPClient(
    connection=Connection(url=URL, auth=TokenAuth(TOKEN))
)
```

**Fix:** Update ~10 lines in slack_bot.py

**2. Tool Calling:**
```python
# Old
result = await client.call_tool(name, args)

# Might become
result = await client.execute(tool=name, params=args)
```

**Fix:** Update ~30 lines in slack_bot.py

**Total effort:** 1-2 hours for FastMCP v3.0 migration

---

## 📊 Dependency Update Frequency

Based on historical data:

| Package | Major Releases | Breaking Changes | Our Risk |
|---------|---------------|------------------|----------|
| **slack-bolt** | ~1/year | Rare | 🟢 Low |
| **fastmcp** | ~2-3/year | Common (new project) | 🔴 High |
| **anthropic** | ~3-4/year | Occasional | 🟡 Medium |
| **snowflake-connector** | ~2/year | Very rare | 🟢 Low |

**Expected maintenance:** 2-8 hours per year (mostly testing)

---

## 🔒 Recommended Versioning Strategy

### For Production Deployment

**Use conservative ranges:**

```txt
# requirements_no_mcp.txt (RECOMMENDED)
slack-bolt>=1.18.0,<2.0.0
snowflake-connector-python>=3.0.0,<4.0.0
anthropic>=0.40.0,<1.0.0
python-dotenv>=1.0.0,<2.0.0
```

**Why:**
- ✅ Get patch releases (1.18.1, 1.18.2) automatically
- ✅ Get minor releases (1.19.0, 1.20.0) automatically
- ❌ Block major releases (2.0.0) that could break
- ✅ Security patches applied automatically

---

### For Development

**Use minimum versions:**

```txt
# Keep as-is (more permissive)
slack-bolt>=1.18.0
anthropic>=0.40.0
```

**Why:**
- ✅ Test with latest versions
- ✅ Catch breaking changes early
- ✅ Contribute fixes back to project

---

## 🛡️ Protection Against Breaking Changes

### 1. **Automated Testing (Future Enhancement)**

Create `test_bots.py`:
```python
def test_slack_bot_imports():
    """Verify Slack Bolt imports work"""
    from slack_bolt.async_app import AsyncApp
    from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
    assert AsyncApp is not None
    assert AsyncSocketModeHandler is not None

def test_slack_event_handling():
    """Test event handler still works"""
    # Mock event
    event = {"user": "U123", "text": "test", "channel": "C123"}
    # Verify we can access fields
    assert event["user"] == "U123"
    assert event.get("thread_ts") is None  # Test .get() works
```

Run before deploying:
```bash
pytest test_bots.py
```

---

### 2. **Dependency Bot (GitHub)**

Enable Dependabot to auto-create PRs for updates:

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
    reviewers:
      - "williamxwood"
```

**Benefit:** Auto-notified of updates, can test PRs before merging

---

### 3. **Version Monitoring**

Add to CI/CD:
```bash
# Check for outdated packages
pip list --outdated

# Check for security vulnerabilities
pip-audit
```

---

## 🔄 What Happens When Dependencies Update

### Automatic Updates (Current Setup)

With `>=` versioning:

```bash
# Today
pip install -r requirements_no_mcp.txt
# Installs: slack-bolt 1.18.1

# Next month (Slack releases 1.19.0)
pip install -r requirements_no_mcp.txt
# Installs: slack-bolt 1.19.0  ← AUTO UPGRADE

# If breaking change in 1.19.0:
python slack_bot_no_mcp.py
# ❌ Error: AttributeError: 'AsyncApp' has no attribute 'event'
```

**Time to fix:** 30 min - 2 hours depending on changes

---

### Controlled Updates (Recommended)

With `>=X,<MAJOR` versioning:

```bash
# Today
pip install -r requirements_no_mcp.txt
# Installs: slack-bolt 1.18.1

# Next month (Slack releases 1.19.0)
pip install -r requirements_no_mcp.txt
# Installs: slack-bolt 1.19.0  ← Safe upgrade (same major version)

# Next year (Slack releases 2.0.0)
pip install -r requirements_no_mcp.txt
# Installs: slack-bolt 1.19.5  ← BLOCKED (different major version)
# Manual review required before upgrading to 2.0.0
```

**Benefit:** Breaking changes require explicit approval

---

## 💡 Recommendations

### Immediate Actions

**1. Update requirements files to use conservative ranges:**

Create `requirements_no_mcp_locked.txt`:
```txt
slack-bolt>=1.18.0,<2.0.0
snowflake-connector-python>=3.0.0,<4.0.0
anthropic>=0.40.0,<1.0.0
python-dotenv>=1.0.0,<2.0.0
```

**2. Add to README:**
```markdown
## 📦 Dependency Management

For production deployments, use locked requirements:
```bash
pip install -r requirements_no_mcp_locked.txt
```

For development, use standard requirements (gets latest compatible):
```bash
pip install -r requirements_no_mcp.txt
```
```

**3. Create test script:**
```python
# test_imports.py
def test_all_imports():
    """Verify all dependencies import correctly"""
    try:
        from slack_bolt.async_app import AsyncApp
        from anthropic import AsyncAnthropic
        import snowflake.connector
        print("✅ All imports successful")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        exit(1)

if __name__ == "__main__":
    test_all_imports()
```

---

### Long-Term Strategy

**1. Monitor Dependencies**
- Subscribe to GitHub releases for slack-bolt, fastmcp
- Review changelogs monthly
- Test updates in staging before production

**2. Maintain Compatibility Layer**
```python
# slack_compat.py - Abstracts Slack Bolt API
def create_slack_app(token):
    """Create Slack app with current API"""
    return AsyncApp(token=token)

def create_handler(app, app_token):
    """Create socket mode handler"""
    return AsyncSocketModeHandler(app, app_token)
```

**Benefit:** If API changes, update 1 file instead of 4

**3. Document API Usage**
- Keep this file updated
- Document which APIs we use
- Note when we upgrade dependencies

---

## 🎯 Bottom Line

### **How Updates Impact This Directory:**

**Slack Bolt Update:**
- 🟡 **Impact:** Medium (affects all 4 bots)
- ⏱️ **Fix time:** 30 min - 2 hours
- 🔄 **Frequency:** ~1/year for breaking changes
- 🛡️ **Protection:** Use `>=X,<MAJOR` versioning

**FastMCP Update:**
- 🟢 **Impact:** Low (only 1 bot)
- ⏱️ **Fix time:** 1-4 hours  
- 🔄 **Frequency:** ~2-3/year (new project, evolving)
- 🛡️ **Protection:** Pin version, update manually

**Anthropic Update:**
- 🟡 **Impact:** Medium (affects 3 bots)
- ⏱️ **Fix time:** 1-2 hours
- 🔄 **Frequency:** ~1/year for breaking changes
- 🛡️ **Protection:** Pin to <1.0.0

**Snowflake Update:**
- 🟢 **Impact:** Very low (stable API)
- ⏱️ **Fix time:** 15-30 min
- 🔄 **Frequency:** Rarely breaks
- 🛡️ **Protection:** Not needed, very stable

---

### **Expected Maintenance Burden:**

- **Best case:** 0 hours/year (no breaking changes)
- **Typical case:** 2-4 hours/year (minor updates)
- **Worst case:** 8-12 hours/year (multiple major updates)

**With locked versions:** ~2 hours/year (deliberate upgrades only)

---

## 📝 Action Items

- [ ] Update requirements files with version locks
- [ ] Add `requirements_*_locked.txt` for production
- [ ] Create `test_imports.py` script
- [ ] Enable Dependabot for update notifications
- [ ] Document current dependency versions
- [ ] Subscribe to release notifications

Want me to implement any of these protections?

