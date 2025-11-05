# Dependency Update Process

Step-by-step guide for safely updating Slack Bolt, FastMCP, and other dependencies.

---

## 🎯 Quick Reference

| Dependency | Update Frequency | Risk Level | Time Required |
|------------|-----------------|------------|---------------|
| **Slack Bolt** | Check monthly | 🟡 Medium | 30-60 min |
| **FastMCP** | Check monthly | 🔴 High | 1-3 hours |
| **Anthropic** | Check monthly | 🟡 Medium | 30-60 min |
| **Snowflake** | Check quarterly | 🟢 Low | 15-30 min |

---

## 📅 Update Schedule

### Weekly
- Check for **security updates** across all dependencies
- Apply critical security patches

### Monthly
- Review **changelogs** for new releases
- Test **minor/patch updates**
- Update if safe

### Quarterly
- **Major version** review
- Full testing of all bots
- Update locked requirements

---

## 🔔 Step 1: Get Notified of Updates

### Option A: GitHub Watch (Manual)

**Watch these repositories:**
1. **Slack Bolt:** https://github.com/slackapi/bolt-python
   - Click "Watch" → "Custom" → "Releases"
2. **FastMCP:** https://github.com/fastmcp/fastmcp
   - Click "Watch" → "Custom" → "Releases"
3. **Anthropic SDK:** https://github.com/anthropics/anthropic-sdk-python
   - Click "Watch" → "Custom" → "Releases"

**You'll get email when new versions release**

---

### Option B: Dependabot (Automated)

**Create `.github/dependabot.yml`:**

```yaml
version: 2
updates:
  # Python dependencies
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
    reviewers:
      - "williamxwood"
    labels:
      - "dependencies"
    # Group minor/patch updates
    groups:
      minor-updates:
        patterns:
          - "*"
        update-types:
          - "minor"
          - "patch"
```

**What this does:**
- ✅ Checks for updates weekly
- ✅ Auto-creates PRs with updates
- ✅ Groups minor updates together
- ✅ Assigns to you for review
- ✅ You test PR before merging

**Setup:**
```bash
cd /Users/willwood/repos/slackbot_oss
mkdir -p .github
# Create dependabot.yml as shown above
git add .github/dependabot.yml
git commit -m "Add Dependabot for dependency updates"
git push
```

---

### Option C: Manual Check (Simplest)

**Monthly checklist:**

```bash
# Check current versions
cd /Users/willwood/repos/slackbot_oss
pip list | grep -E "slack-bolt|fastmcp|anthropic|snowflake"

# Check for updates
pip list --outdated | grep -E "slack-bolt|fastmcp|anthropic|snowflake"

# Or check PyPI directly
pip index versions slack-bolt
pip index versions fastmcp
pip index versions anthropic
pip index versions snowflake-connector-python
```

---

## 🔄 Step 2: Review Changes

When you get a notification, review the changelog:

### For Slack Bolt Updates

**1. Check the release notes:**
```bash
# Visit: https://github.com/slackapi/bolt-python/releases
# Or use gh CLI:
gh release view v1.19.0 --repo slackapi/bolt-python
```

**2. Look for these keywords:**
- ❌ **"BREAKING"** - Major changes, will require code updates
- ⚠️ **"Deprecated"** - Features being removed, plan to update
- ✅ **"Fixed"** - Bug fixes, safe to update
- ✅ **"Added"** - New features, safe (opt-in)

**3. Check migration guide:**
- Look for `MIGRATION.md` or `UPGRADING.md` in release
- Read breaking changes section

---

### For FastMCP Updates

**1. Check releases:**
```bash
# Visit: https://github.com/fastmcp/fastmcp/releases
```

**2. Key things to check:**
- **Client API changes** - affects how we initialize/call MCP server
- **Tool format changes** - affects tool definitions
- **Auth changes** - affects authentication flow
- **Response format changes** - affects parsing

**3. FastMCP is new/evolving:**
- ⚠️ **Higher risk** of breaking changes
- 🧪 **Test thoroughly** before updating
- 📖 **Read docs carefully** - API might change significantly

---

## 🧪 Step 3: Test the Update

### Create Test Environment

**Don't test in production!** Use isolated environment:

```bash
# Create test branch
cd /Users/willwood/repos/slackbot_oss
git checkout -b test-slack-bolt-1.19.0

# Create isolated Python environment
python3 -m venv test_env
source test_env/bin/activate

# Install the NEW version to test
pip install slack-bolt==1.19.0  # Specific version to test
pip install -r requirements_no_mcp.txt  # Other deps
```

---

### Test Checklist

#### For Slack Bolt Updates

**Test each bot:**

```bash
# 1. Test Direct SQL bot
export SLACK_BOT_TOKEN=xoxb-test
export SLACK_APP_TOKEN=xapp-test
export SNOWFLAKE_USER=test
# ... other env vars ...

# 2. Run the bot (should start without errors)
python slack_bot_no_mcp.py

# Expected output:
# "Slack bot starting..."
# "Connected to Snowflake"
# No import errors, no crashes

# 3. Test in Slack (if possible)
# - Send @mention
# - Send DM
# - Test in thread
# - Verify responses work

# 4. Check logs for errors
# Look for deprecation warnings, API errors
```

**Repeat for all 4 bots:**
```bash
python slack_bot_no_mcp.py    # Test
python slack_bot.py           # Test
python slack_bot_cortex.py    # Test
python slack_bot_semantic.py  # Test
```

---

#### For FastMCP Updates

**Only affects slack_bot.py:**

```bash
# 1. Install new FastMCP version
pip install fastmcp==3.0.0  # New version

# 2. Test imports
python -c "from fastmcp import Client; from fastmcp.client.auth import BearerAuth; print('OK')"

# 3. Test client initialization
python -c "
from fastmcp import Client
from fastmcp.client.auth import BearerAuth
client = Client(
    server_url='http://test',
    auth=BearerAuth(token='test')
)
print('Client created OK')
"

# 4. If imports work, test full bot
python slack_bot.py
# Check startup logs for errors
```

---

## ✅ Step 4: Apply the Update

### If Tests Pass

**1. Update requirements file:**

```bash
# Edit requirements_no_mcp.txt
# Change:
# slack-bolt>=1.18.0
# To:
slack-bolt>=1.19.0  # Update minimum version
```

**2. Commit the change:**

```bash
git add requirements_no_mcp.txt
git commit -m "Update slack-bolt to 1.19.0

Tested:
- All 4 bots start successfully
- Event handlers work
- No breaking changes found
- See release notes: https://github.com/slackapi/bolt-python/releases/tag/v1.19.0
"
git push
```

**3. Deploy to production:**

```bash
# If using Heroku
git push heroku main

# Verify deployment
heroku logs --tail

# Test in production Slack
@Bot hello
```

**4. Update DEPENDENCY_MANAGEMENT.md:**

Add to changelog section:
```markdown
## Update History

### 2025-11-15: slack-bolt 1.18.0 → 1.19.0
- Tested: All 4 bots
- Breaking changes: None
- New features: Improved error messages
- Status: ✅ Deployed successfully
```

---

### If Tests Fail

**1. Document the issue:**

```bash
# Create GitHub issue
gh issue create --repo williamxwood/slackbot \
  --title "slack-bolt 1.19.0 breaks event handlers" \
  --body "
## Issue
Updating to slack-bolt 1.19.0 causes import errors

## Error
\`\`\`
ImportError: cannot import name 'AsyncApp' from 'slack_bolt.async_app'
\`\`\`

## To Reproduce
1. Install slack-bolt==1.19.0
2. Run python slack_bot_no_mcp.py
3. See error

## Expected Behavior
Bot should start successfully

## Environment
- Python: 3.11
- OS: macOS
- Previous slack-bolt: 1.18.1
"
```

**2. Roll back:**

```bash
# Delete test branch
git checkout main
git branch -D test-slack-bolt-1.19.0

# Keep current version
# Don't update requirements.txt
```

**3. Pin to working version:**

```bash
# Update requirements to block broken version
slack-bolt>=1.18.0,<1.19.0  # Block 1.19.0
```

**4. Check for fixes:**
- Wait for 1.19.1 or 1.20.0
- Watch for community discussion
- Check if others report same issue

---

## 🚨 Breaking Change Response Plan

### When a Major Version Releases (e.g., Slack Bolt 2.0)

**DON'T update immediately!** Follow this process:

**Week 1: Research**
- ✅ Read release notes thoroughly
- ✅ Check migration guide
- ✅ Search for community issues
- ✅ Estimate update effort
- ❌ Don't install yet

**Week 2-3: Test**
- ✅ Create test branch
- ✅ Update one bot at a time
- ✅ Document all changes needed
- ✅ Test thoroughly
- ❌ Don't deploy to production

**Week 4: Decide**
- ✅ If easy migration (<2 hours): Proceed
- ⚠️ If complex migration (2-8 hours): Schedule work
- ❌ If very complex (>8 hours): Wait for community solutions

**After Testing:**
- ✅ Create migration guide for this repo
- ✅ Update all 4 bots
- ✅ Update documentation
- ✅ Deploy

---

## 📋 Update Workflow Template

### Template: Updating Any Dependency

**Copy this checklist for each update:**

```markdown
## Updating [PACKAGE] from [OLD_VERSION] to [NEW_VERSION]

### Pre-Update
- [ ] Read release notes: [URL]
- [ ] Check for breaking changes
- [ ] Review migration guide (if exists)
- [ ] Estimate effort: [TIME]
- [ ] Create test branch: `git checkout -b update-[package]-[version]`

### Testing
- [ ] Create test environment: `python3 -m venv test_env`
- [ ] Install new version: `pip install [package]==[version]`
- [ ] Test imports: `python -c "import [package]"`
- [ ] Test affected bots:
  - [ ] slack_bot_no_mcp.py
  - [ ] slack_bot.py
  - [ ] slack_bot_cortex.py
  - [ ] slack_bot_semantic.py
- [ ] Check for deprecation warnings
- [ ] Test in real Slack workspace (if possible)

### Apply Update
- [ ] Update requirements file(s)
- [ ] Commit with detailed message
- [ ] Update DEPENDENCY_MANAGEMENT.md changelog
- [ ] Push to GitHub
- [ ] Create PR (if using PRs)
- [ ] Deploy to production
- [ ] Monitor logs for 24 hours

### Rollback Plan (if needed)
- [ ] Revert commit: `git revert [commit-hash]`
- [ ] Or downgrade: `pip install [package]==[old-version]`
- [ ] Document issue in KNOWN_ISSUES.md
- [ ] Create GitHub issue for tracking
```

---

## 🛠️ Automated Update Script

Create `scripts/check_updates.sh`:

```bash
#!/bin/bash
# Check for dependency updates and test them

set -e

echo "🔍 Checking for dependency updates..."

# Check for outdated packages
outdated=$(pip list --outdated --format=json)

if [ "$outdated" = "[]" ]; then
    echo "✅ All dependencies are up to date!"
    exit 0
fi

echo "📦 Outdated packages found:"
echo "$outdated" | jq -r '.[] | "\(.name): \(.version) → \(.latest_version)"'

echo ""
echo "🧪 Testing updates in isolated environment..."

# Create test environment
python3 -m venv /tmp/slackbot_test_env
source /tmp/slackbot_test_env/bin/activate

# Install with latest versions
pip install -r requirements_no_mcp.txt

# Test imports
echo "Testing imports..."
python -c "
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
import anthropic
import snowflake.connector
print('✅ All imports successful')
" || {
    echo "❌ Import test failed"
    exit 1
}

# Show what would be updated
echo ""
echo "📊 If you proceed, these packages will be updated in requirements:"
pip freeze | grep -E "slack-bolt|anthropic|snowflake|fastmcp"

# Cleanup
deactivate
rm -rf /tmp/slackbot_test_env

echo ""
echo "✅ Tests passed! Safe to update."
echo ""
echo "Next steps:"
echo "1. Review changes above"
echo "2. Update requirements_*.txt files"
echo "3. Test locally with: python slack_bot_no_mcp.py"
echo "4. Deploy to production"
```

**Usage:**
```bash
chmod +x scripts/check_updates.sh
./scripts/check_updates.sh
```

---

## 📝 Specific Update Procedures

### Updating Slack Bolt

**Example: 1.18.0 → 1.19.0**

#### Step 1: Check What's New
```bash
# View release notes
open https://github.com/slackapi/bolt-python/releases/tag/v1.19.0

# Key things to look for:
# - Breaking changes
# - Deprecated features
# - New required parameters
# - Changed behavior
```

#### Step 2: Create Test Branch
```bash
cd /Users/willwood/repos/slackbot_oss
git checkout -b update-slack-bolt-1.19.0
```

#### Step 3: Test in Isolation
```bash
# Create test environment
python3 -m venv test_env
source test_env/bin/activate

# Install new version
pip install slack-bolt==1.19.0
pip install -r requirements_no_mcp.txt

# Test imports
python -c "from slack_bolt.async_app import AsyncApp; print('✅ Import OK')"
```

#### Step 4: Test Each Bot

**Test Direct SQL:**
```bash
# Set test env vars (use test Slack workspace)
export SLACK_BOT_TOKEN=xoxb-test-token
export SLACK_APP_TOKEN=xapp-test-token
export SNOWFLAKE_USER=test_user
export SNOWFLAKE_ACCOUNT=test_account
export SNOWFLAKE_WAREHOUSE=test_wh
export SNOWFLAKE_DATABASE=test_db
export SNOWFLAKE_SCHEMA=test_schema
export SNOWFLAKE_PASSWORD=test_pass
export ANTHROPIC_API_KEY=sk-ant-test

# Run bot (should start without errors)
python slack_bot_no_mcp.py

# Watch for:
# ✅ "Slack bot starting..."
# ✅ "Connected to Snowflake"
# ❌ Any import errors
# ❌ Any AttributeError
# ❌ Any crashes
```

**If bot starts successfully:**
```bash
# Test in Slack:
# 1. @mention the bot
# 2. Send DM
# 3. Test in thread
# 4. Verify responses work correctly
```

**Repeat for other bots:**
```bash
# Test FastMCP bot (if you have MCP server)
python slack_bot.py

# Test Cortex bot (if you have Cortex)
python slack_bot_cortex.py

# Test Semantic bot (if you have dbt Cloud)
python slack_bot_semantic.py
```

#### Step 5: Update Requirements

**If all tests pass:**

```bash
# Update all requirements files that use slack-bolt
for file in requirements.txt requirements_no_mcp.txt requirements_cortex.txt requirements_semantic.txt; do
    sed -i '' 's/slack-bolt>=1.18.0/slack-bolt>=1.19.0/' $file
done

# Verify changes
git diff requirements*.txt
```

#### Step 6: Commit & Deploy

```bash
# Commit
git add requirements*.txt
git commit -m "Update slack-bolt from 1.18.0 to 1.19.0

Tested:
- ✅ slack_bot_no_mcp.py - working
- ✅ slack_bot.py - working
- ✅ slack_bot_cortex.py - working
- ✅ slack_bot_semantic.py - working

Changes:
- No code changes required
- All bots start successfully
- Event handlers working correctly

Release notes: https://github.com/slackapi/bolt-python/releases/tag/v1.19.0
"

# Push
git push origin update-slack-bolt-1.19.0

# Create PR (or merge directly if you prefer)
gh pr create --title "Update slack-bolt to 1.19.0" \
  --body "Tested all 4 bots, no breaking changes"

# After review, merge
git checkout main
git merge update-slack-bolt-1.19.0
git push

# Deploy to production
git push heroku main
# Or your deployment method
```

#### Step 7: Monitor Production

```bash
# Watch logs for first hour after deploy
heroku logs --tail

# Check for:
# ✅ Bot starts successfully
# ✅ Responds to @mentions
# ✅ No new errors
# ❌ Any unexpected behavior
```

#### Step 8: Document

Update `DEPENDENCY_MANAGEMENT.md`:
```markdown
## Update History

### 2025-11-15: slack-bolt 1.18.0 → 1.19.0
- **Tested:** All 4 bots ✅
- **Breaking changes:** None
- **Code changes:** None required
- **Deployment:** Successful
- **Issues:** None
- **Notes:** Smooth upgrade, new error messages are clearer
```

---

## 🔧 Updating FastMCP

**Example: 2.0.0 → 3.0.0 (major version)**

#### Step 1: Research

```bash
# Read release notes carefully
open https://github.com/fastmcp/fastmcp/releases/tag/v3.0.0

# Look for:
# - Migration guide
# - Breaking changes list
# - New requirements
# - Changed APIs
```

#### Step 2: Identify Impact

**Check what we use:**
```bash
# Search our code for FastMCP usage
cd /Users/willwood/repos/slackbot_oss
grep -n "from fastmcp" slack_bot.py
grep -n "Client" slack_bot.py | grep -i mcp
grep -n "get_tools\|call_tool" slack_bot.py
```

**Compare with v3.0 docs:**
- Are method names the same?
- Are parameters the same?
- Is auth flow the same?

#### Step 3: Update Code

**Example migration (hypothetical):**

**If FastMCP changes Client API:**

```python
# OLD (v2.x) - in slack_bot.py
from fastmcp import Client
from fastmcp.client.auth import BearerAuth

client = Client(
    server_url=url,
    auth=BearerAuth(token=token)
)

# NEW (v3.x)
from fastmcp import FastMCPClient  # Name changed
from fastmcp.auth import TokenAuth  # Module changed

client = FastMCPClient(
    url=url,  # Parameter name changed
    auth=TokenAuth(token)  # Class name changed
)
```

**Update slack_bot.py accordingly**

#### Step 4: Test Thoroughly

```bash
# Install v3.0
pip install fastmcp==3.0.0

# Test bot with REAL MCP server
python slack_bot.py

# Test in Slack:
# - Ask complex question requiring multiple tools
# - Test error cases
# - Verify tool calling works
# - Check response formatting
```

#### Step 5: Document Changes

```bash
git commit -m "Update FastMCP to 3.0.0 - BREAKING CHANGES

Breaking changes:
- Client class renamed: Client → FastMCPClient
- Auth module changed: client.auth → auth
- Auth class renamed: BearerAuth → TokenAuth

Code changes:
- slack_bot.py lines 145-165: Updated client initialization
- slack_bot.py lines 220-240: Updated tool calling

Testing:
- ✅ Tested with production MCP server
- ✅ Tool discovery works
- ✅ Tool execution works
- ✅ Responses formatted correctly

Migration guide: https://github.com/fastmcp/fastmcp/blob/main/MIGRATION_v3.md
"
```

---

## 🔴 Handling Breaking Changes

### Major Version Update Workflow

#### 1. Assess Impact

**Create impact document:**

```markdown
# Impact Assessment: Slack Bolt 2.0.0

## Changes in 2.0.0
- AsyncApp initialization now requires explicit config
- Event handlers use new context object
- Say function renamed to respond()

## Impact on Our Code

### slack_bot_no_mcp.py
- Line 23: AsyncApp init needs update
- Lines 300-345: Event handlers need context param
- Lines 312, 318, 324: say() → respond()
**Effort:** 2-3 hours

### slack_bot.py
- Same as above
**Effort:** 2-3 hours

### slack_bot_cortex.py
- Same as above
**Effort:** 2-3 hours

### slack_bot_semantic.py
- Same as above
**Effort:** 2-3 hours

**Total effort:** 8-12 hours

## Decision
- [ ] Update now (schedule work)
- [ ] Wait for 2.1.0 (community shakes out issues)
- [ ] Stay on 1.x (pin version)
```

#### 2. Create Migration Branch

```bash
git checkout -b migrate-slack-bolt-2.0

# Update one bot at a time
# Test each thoroughly before moving to next
```

#### 3. Update Incrementally

```bash
# Day 1: Migrate slack_bot_no_mcp.py
# Test thoroughly in dev environment

# Day 2: Migrate slack_bot.py
# Test with MCP server

# Day 3: Migrate remaining bots

# Day 4: Integration testing
# Test all 4 together

# Day 5: Deploy to production
```

#### 4. Document Migration

Create `MIGRATION_v2.md`:
```markdown
# Migration to Slack Bolt v2.0

## What Changed
- Event handler signature
- Say function renamed
- Client initialization

## How to Update

### Step 1: Update imports
[show changes]

### Step 2: Update event handlers
[show changes]

### Step 3: Update function calls
[show changes]

## Testing
[show test commands]
```

---

## 🤖 Automated Update Testing

### Create GitHub Actions Workflow

**`.github/workflows/test-dependencies.yml`:**

```yaml
name: Test Dependency Updates

on:
  schedule:
    - cron: '0 10 * * 1'  # Every Monday at 10am
  workflow_dispatch:  # Manual trigger

jobs:
  test-latest-deps:
    runs-on: ubuntu-latest
    
    strategy:
      matrix:
        bot: 
          - slack_bot_no_mcp.py
          - slack_bot.py
          - slack_bot_cortex.py
          - slack_bot_semantic.py
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies with latest versions
        run: |
          pip install slack-bolt anthropic snowflake-connector-python
      
      - name: Test imports
        run: |
          python -c "
          from slack_bolt.async_app import AsyncApp
          from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
          print('✅ Slack Bolt imports OK')
          "
      
      - name: Check for syntax errors
        run: |
          python -m py_compile ${{ matrix.bot }}
      
      - name: Report results
        if: failure()
        uses: actions/github-script@v6
        with:
          script: |
            github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: 'Dependency update broke ${{ matrix.bot }}',
              body: 'Latest dependency versions are incompatible. Check workflow run.',
              labels: ['dependencies', 'automated']
            })
```

**What this does:**
- ✅ Tests weekly with latest versions
- ✅ Creates issue if something breaks
- ✅ Tests all 4 bots
- ✅ Can trigger manually

---

## 📊 Update Priority Matrix

When multiple updates are available:

| Package | Current | Available | Priority | Reason |
|---------|---------|-----------|----------|--------|
| slack-bolt | 1.18.0 | 1.18.5 | 🟢 **HIGH** | Patch release, likely bug fixes |
| anthropic | 0.40.0 | 0.41.0 | 🟡 **MEDIUM** | Minor release, test first |
| slack-bolt | 1.18.0 | 2.0.0 | 🔴 **LOW** | Major release, wait and research |
| fastmcp | 2.0.0 | 2.1.0 | 🟡 **MEDIUM** | Minor but evolving project |

**Update order:**
1. Security patches (ASAP)
2. Patch releases (1.18.0 → 1.18.1)
3. Minor releases (1.18.0 → 1.19.0)
4. Major releases (1.18.0 → 2.0.0) - plan carefully

---

## 🎯 Recommended Workflow

### Monthly Update Routine

**First Monday of each month:**

```bash
# 1. Check for updates
cd /Users/willwood/repos/slackbot_oss
pip list --outdated | grep -E "slack-bolt|fastmcp|anthropic|snowflake"

# 2. Review changelogs (if updates available)
# Visit GitHub releases for each package

# 3. Test updates (if safe)
./scripts/check_updates.sh

# 4. Apply updates (if tests pass)
# Update requirements files
# Commit and deploy

# 5. Document
# Add entry to DEPENDENCY_MANAGEMENT.md
```

**Time commitment:** 30 minutes to 2 hours per month

---

## 🚀 Quick Commands

### Check Current Versions
```bash
pip show slack-bolt fastmcp anthropic snowflake-connector-python | grep -E "Name:|Version:"
```

### Check for Updates
```bash
pip list --outdated | grep -E "slack-bolt|fastmcp|anthropic|snowflake"
```

### Test Specific Version
```bash
pip install slack-bolt==1.19.0 && python slack_bot_no_mcp.py
```

### Rollback to Previous Version
```bash
pip install slack-bolt==1.18.0
# Or revert git commit
git revert HEAD
git push
```

### Check Security Vulnerabilities
```bash
pip install pip-audit
pip-audit
```

---

## 📚 Resources

### Changelogs
- **Slack Bolt:** https://github.com/slackapi/bolt-python/releases
- **FastMCP:** https://github.com/fastmcp/fastmcp/releases
- **Anthropic:** https://github.com/anthropics/anthropic-sdk-python/releases
- **Snowflake:** https://docs.snowflake.com/en/release-notes/clients-drivers/python-connector

### Migration Guides
- **Slack Bolt:** Usually in release notes or `MIGRATION.md`
- **FastMCP:** Check docs/ folder in repo
- **Anthropic:** Usually very good migration guides

### Get Help
- **Slack Bolt:** https://github.com/slackapi/bolt-python/issues
- **FastMCP:** https://github.com/fastmcp/fastmcp/discussions
- **This Repo:** https://github.com/williamxwood/slackbot/issues

---

## ✅ Success Checklist

After each update:

- [ ] All bots start without errors
- [ ] Test @mentions work
- [ ] Test DMs work
- [ ] Test threaded responses
- [ ] No new errors in logs
- [ ] No deprecation warnings
- [ ] Production deployment successful
- [ ] Monitored for 24 hours
- [ ] Updated DEPENDENCY_MANAGEMENT.md
- [ ] Created git tag for release (optional)

---

## 🏷️ Version Tagging (Optional)

After successful updates, tag releases:

```bash
# Tag current working version
git tag -a v1.0.0 -m "Release v1.0.0
- slack-bolt 1.18.0
- anthropic 0.40.0
- All 4 bots tested and working
"
git push --tags

# Later, after updates
git tag -a v1.1.0 -m "Release v1.1.0
- Updated slack-bolt to 1.19.0
- Updated anthropic to 0.41.0
- No breaking changes
"
git push --tags
```

**Benefit:** Easy rollback to known-good versions

---

## 🎯 TL;DR - Quick Process

When Slack Bolt or FastMCP updates:

1. **Get notified** (GitHub watch, Dependabot, or manual check)
2. **Read changelog** (look for "BREAKING")
3. **Create test branch** (`git checkout -b update-package`)
4. **Test in isolation** (new venv, test imports, run bots)
5. **Update requirements** (if tests pass)
6. **Commit & push** (with detailed message)
7. **Deploy** (to production)
8. **Monitor** (logs for 24 hours)
9. **Document** (in DEPENDENCY_MANAGEMENT.md)

**Time:** 30 min for patches, 1-3 hours for minor, 4-12 hours for major

**Safety:** High (isolated testing before production)

---

Need help setting up Dependabot or the automated testing script?

