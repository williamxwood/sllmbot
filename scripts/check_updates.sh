#!/bin/bash
# Check for dependency updates and test them
# Usage: ./scripts/check_updates.sh

set -e

echo "🔍 Checking for dependency updates..."
echo ""

# Check for outdated packages
outdated=$(pip list --outdated --format=json 2>/dev/null || echo "[]")

if [ "$outdated" = "[]" ]; then
    echo "✅ All dependencies are up to date!"
    exit 0
fi

echo "📦 Outdated packages found:"
echo "$outdated" | python3 -m json.tool | grep -E "name|version|latest_version" | paste - - - | sed 's/[",]//g'

echo ""
echo "🧪 Testing updates in isolated environment..."
echo ""

# Create test environment
TEST_ENV="/tmp/slackbot_test_env_$$"
python3 -m venv "$TEST_ENV"
source "$TEST_ENV/bin/activate"

# Install with latest versions
echo "Installing latest versions..."
pip install -q slack-bolt anthropic snowflake-connector-python requests python-dotenv

# Test imports
echo "Testing imports..."
python3 << 'EOF'
try:
    from slack_bolt.async_app import AsyncApp
    from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
    import anthropic
    import snowflake.connector
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import test failed: {e}")
    exit(1)
EOF

import_result=$?

if [ $import_result -ne 0 ]; then
    echo "❌ Import tests failed - updates may break bots"
    deactivate
    rm -rf "$TEST_ENV"
    exit 1
fi

# Show what versions were installed
echo ""
echo "📊 Tested versions (all imports successful):"
pip list | grep -E "slack-bolt|anthropic|snowflake-connector|fastmcp" || true

# Cleanup
deactivate
rm -rf "$TEST_ENV"

echo ""
echo "✅ Tests passed! Safe to update."
echo ""
echo "Next steps:"
echo "1. Review changes above"
echo "2. Update requirements_*.txt files with new minimum versions"
echo "3. Test locally: python slack_bot_no_mcp.py"
echo "4. Commit: git commit -m 'Update dependencies'"
echo "5. Deploy to production"
echo ""

