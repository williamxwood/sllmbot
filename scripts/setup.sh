#!/bin/bash
# Interactive setup script for Slackbot OSS
# Prompts for credentials and creates .env file

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "\n${BLUE}======================================================================${NC}"
    echo -e "  ${BOLD}$1${NC}"
    echo -e "${BLUE}======================================================================${NC}\n"
}

print_step() {
    echo -e "\n${BLUE}──────────────────────────────────────────────────────────────────────${NC}"
    echo -e "${BOLD}Step $1: $2${NC}"
    echo -e "${BLUE}──────────────────────────────────────────────────────────────────────${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

prompt_input() {
    local prompt="$1"
    local default="$2"
    local secret="$3"
    local value
    
    if [ -n "$default" ]; then
        prompt="$prompt [$default]"
    fi
    
    if [ "$secret" = "true" ]; then
        read -s -p "$prompt: " value
        echo  # New line after hidden input
    else
        read -p "$prompt: " value
    fi
    
    # Use default if no input provided
    if [ -z "$value" ] && [ -n "$default" ]; then
        echo "$default"
    else
        echo "$value"
    fi
}

prompt_choice() {
    local prompt="$1"
    shift
    local options=("$@")
    local choice
    
    echo "$prompt"
    for i in "${!options[@]}"; do
        echo "  $((i+1)). ${options[$i]}"
    done
    
    while true; do
        read -p $'\nEnter choice (1-'"${#options[@]}"'): ' choice
        if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le "${#options[@]}" ]; then
            echo "$((choice-1))"
            return
        fi
        print_error "Please enter a number between 1 and ${#options[@]}"
    done
}

test_slack_connection() {
    local bot_token="$1"
    
    # Simple test - just check if token format is valid
    if [[ $bot_token == xoxb-* ]]; then
        print_success "Slack bot token format looks valid"
        return 0
    else
        print_warning "Slack bot token format may be invalid (should start with xoxb-)"
        return 1
    fi
}

test_anthropic_key() {
    local api_key="$1"
    
    # Simple test - check format
    if [[ $api_key == sk-ant-* ]]; then
        print_success "Anthropic API key format looks valid"
        return 0
    else
        print_warning "Anthropic API key format may be invalid (should start with sk-ant-)"
        return 1
    fi
}

setup_direct_sql() {
    print_step 2 "Direct SQL Bot Configuration"
    
    # Slack credentials
    echo "📱 Slack Configuration:"
    SLACK_BOT_TOKEN=$(prompt_input "Slack Bot Token (xoxb-...)" "" false)
    SLACK_APP_TOKEN=$(prompt_input "Slack App Token (xapp-...)" "" false)
    
    echo -e "\n🧪 Testing Slack token..."
    test_slack_connection "$SLACK_BOT_TOKEN"
    
    # Snowflake credentials
    echo -e "\n❄️  Snowflake Configuration:"
    SNOWFLAKE_USER=$(prompt_input "Snowflake Username" "" false)
    SNOWFLAKE_ACCOUNT=$(prompt_input "Snowflake Account (e.g., abc123.us-east-1)" "" false)
    SNOWFLAKE_WAREHOUSE=$(prompt_input "Warehouse Name" "COMPUTE_WH" false)
    SNOWFLAKE_DATABASE=$(prompt_input "Database Name" "" false)
    SNOWFLAKE_SCHEMA=$(prompt_input "Schema Name" "PUBLIC" false)
    
    # Auth method
    local auth_idx=$(prompt_choice "🔐 Snowflake Authentication Method:" \
        "Password authentication (recommended for Heroku)" \
        "Browser SSO (for local development)")
    
    if [ "$auth_idx" = "0" ]; then
        SNOWFLAKE_PASSWORD=$(prompt_input "Snowflake Password" "" true)
    else
        SNOWFLAKE_AUTHENTICATOR="externalbrowser"
    fi
    
    # LLM credentials
    echo -e "\n🤖 LLM Configuration:"
    ANTHROPIC_API_KEY=$(prompt_input "Anthropic API Key (sk-ant-...)" "" true)
    
    echo -e "\n🧪 Testing Anthropic API key..."
    test_anthropic_key "$ANTHROPIC_API_KEY"
    
    # Write .env file
    ENV_FILE=".env"
    TEMPLATE_FILE="env_no_mcp.example"
    BOT_FILE="slack_bot_no_mcp.py"
    REQUIREMENTS_FILE="requirements_no_mcp.txt"
}

setup_fastmcp() {
    print_step 2 "FastMCP Bot Configuration"
    
    # Slack credentials
    echo "📱 Slack Configuration:"
    SLACK_BOT_TOKEN=$(prompt_input "Slack Bot Token (xoxb-...)" "" false)
    SLACK_APP_TOKEN=$(prompt_input "Slack App Token (xapp-...)" "" false)
    
    # FastMCP server
    echo -e "\n🔌 FastMCP Server Configuration:"
    FASTMCP_SERVER_URL=$(prompt_input "FastMCP Server URL (https://...)" "" false)
    FASTMCP_TOKEN=$(prompt_input "FastMCP Token (fmcp_...)" "" true)
    
    # LLM choice
    local llm_idx=$(prompt_choice "🤖 Choose LLM Provider:" \
        "Claude (Anthropic) - Recommended" \
        "GPT-4 (OpenAI)")
    
    if [ "$llm_idx" = "0" ]; then
        LLM_PROVIDER="anthropic"
        ANTHROPIC_API_KEY=$(prompt_input "Anthropic API Key (sk-ant-...)" "" true)
    else
        LLM_PROVIDER="openai"
        OPENAI_API_KEY=$(prompt_input "OpenAI API Key (sk-...)" "" true)
    fi
    
    ENV_FILE=".env"
    TEMPLATE_FILE="env.example"
    BOT_FILE="slack_bot.py"
    REQUIREMENTS_FILE="requirements.txt"
}

setup_cortex() {
    print_step 2 "Snowflake Cortex Bot Configuration"
    
    # Slack credentials
    echo "📱 Slack Configuration:"
    SLACK_BOT_TOKEN=$(prompt_input "Slack Bot Token (xoxb-...)" "" false)
    SLACK_APP_TOKEN=$(prompt_input "Slack App Token (xapp-...)" "" false)
    
    # Snowflake credentials
    echo -e "\n❄️  Snowflake Configuration (must have Cortex enabled):"
    SNOWFLAKE_USER=$(prompt_input "Snowflake Username" "" false)
    SNOWFLAKE_ACCOUNT=$(prompt_input "Snowflake Account" "" false)
    SNOWFLAKE_PASSWORD=$(prompt_input "Snowflake Password" "" true)
    SNOWFLAKE_WAREHOUSE=$(prompt_input "Warehouse Name" "COMPUTE_WH" false)
    SNOWFLAKE_DATABASE=$(prompt_input "Database Name" "" false)
    SNOWFLAKE_SCHEMA=$(prompt_input "Schema Name" "PUBLIC" false)
    
    # Cortex model
    local model_idx=$(prompt_choice "🧠 Choose Cortex Model:" \
        "mistral-large (best quality, higher cost)" \
        "mistral-7b (faster, lower cost)" \
        "llama3-70b (high quality)" \
        "mixtral-8x7b (balanced)")
    
    case $model_idx in
        0) CORTEX_MODEL="mistral-large" ;;
        1) CORTEX_MODEL="mistral-7b" ;;
        2) CORTEX_MODEL="llama3-70b" ;;
        3) CORTEX_MODEL="mixtral-8x7b" ;;
    esac
    
    ENV_FILE=".env"
    TEMPLATE_FILE="env_cortex.example"
    BOT_FILE="slack_bot_cortex.py"
    REQUIREMENTS_FILE="requirements_cortex.txt"
}

setup_semantic() {
    print_step 2 "dbt Semantic Layer Bot Configuration"
    
    # Slack credentials
    echo "📱 Slack Configuration:"
    SLACK_BOT_TOKEN=$(prompt_input "Slack Bot Token (xoxb-...)" "" false)
    SLACK_APP_TOKEN=$(prompt_input "Slack App Token (xapp-...)" "" false)
    
    # dbt Cloud
    echo -e "\n📊 dbt Cloud Configuration:"
    DBT_CLOUD_SERVICE_TOKEN=$(prompt_input "dbt Cloud Service Token" "" true)
    DBT_CLOUD_ENVIRONMENT_ID=$(prompt_input "dbt Cloud Environment ID" "" false)
    
    # LLM
    echo -e "\n🤖 LLM Configuration (for mapping questions):"
    ANTHROPIC_API_KEY=$(prompt_input "Anthropic API Key (sk-ant-...)" "" true)
    LLM_MODEL=$(prompt_input "Model" "claude-3-5-sonnet-20241022" false)
    
    ENV_FILE=".env"
    TEMPLATE_FILE="env_semantic.example"
    BOT_FILE="slack_bot_semantic.py"
    REQUIREMENTS_FILE="requirements_semantic.txt"
}

write_env_file() {
    local env_file="$1"
    
    # Check if .env exists
    if [ -f "$env_file" ]; then
        print_warning ".env file already exists"
        read -p "Overwrite? (y/N): " overwrite
        if [[ ! $overwrite =~ ^[Yy]$ ]]; then
            env_file=".env.new"
            echo "Creating $env_file instead..."
        fi
    fi
    
    # Write environment variables
    {
        echo "# Generated by setup.sh on $(date)"
        echo ""
        echo "# Slack Configuration"
        echo "SLACK_BOT_TOKEN=$SLACK_BOT_TOKEN"
        echo "SLACK_APP_TOKEN=$SLACK_APP_TOKEN"
        echo ""
        
        # Add integration-specific vars
        if [ -n "$SNOWFLAKE_USER" ]; then
            echo "# Snowflake Configuration"
            echo "SNOWFLAKE_USER=$SNOWFLAKE_USER"
            echo "SNOWFLAKE_ACCOUNT=$SNOWFLAKE_ACCOUNT"
            echo "SNOWFLAKE_WAREHOUSE=$SNOWFLAKE_WAREHOUSE"
            echo "SNOWFLAKE_DATABASE=$SNOWFLAKE_DATABASE"
            echo "SNOWFLAKE_SCHEMA=$SNOWFLAKE_SCHEMA"
            if [ -n "$SNOWFLAKE_PASSWORD" ]; then
                echo "SNOWFLAKE_PASSWORD=$SNOWFLAKE_PASSWORD"
            else
                echo "SNOWFLAKE_AUTHENTICATOR=$SNOWFLAKE_AUTHENTICATOR"
            fi
            echo ""
        fi
        
        if [ -n "$FASTMCP_SERVER_URL" ]; then
            echo "# FastMCP Configuration"
            echo "FASTMCP_SERVER_URL=$FASTMCP_SERVER_URL"
            echo "FASTMCP_TOKEN=$FASTMCP_TOKEN"
            echo ""
        fi
        
        if [ -n "$DBT_CLOUD_SERVICE_TOKEN" ]; then
            echo "# dbt Cloud Configuration"
            echo "DBT_CLOUD_SERVICE_TOKEN=$DBT_CLOUD_SERVICE_TOKEN"
            echo "DBT_CLOUD_ENVIRONMENT_ID=$DBT_CLOUD_ENVIRONMENT_ID"
            echo ""
        fi
        
        if [ -n "$CORTEX_MODEL" ]; then
            echo "# Cortex Configuration"
            echo "CORTEX_MODEL=$CORTEX_MODEL"
            echo ""
        fi
        
        if [ -n "$LLM_PROVIDER" ]; then
            echo "# LLM Configuration"
            echo "LLM_PROVIDER=$LLM_PROVIDER"
        fi
        
        if [ -n "$ANTHROPIC_API_KEY" ]; then
            echo "ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY"
        fi
        
        if [ -n "$OPENAI_API_KEY" ]; then
            echo "OPENAI_API_KEY=$OPENAI_API_KEY"
        fi
        
        if [ -n "$LLM_MODEL" ]; then
            echo "LLM_MODEL=$LLM_MODEL"
        fi
        
    } > "$env_file"
    
    # Set secure permissions
    chmod 600 "$env_file"
    
    print_success "Configuration saved to $env_file"
    print_success "File permissions set to 600 (owner read/write only)"
}

install_dependencies() {
    local requirements="$1"
    
    echo -e "\n📦 Installing dependencies from $requirements..."
    
    if command -v pip3 &> /dev/null; then
        PIP_CMD="pip3"
    elif command -v pip &> /dev/null; then
        PIP_CMD="pip"
    else
        print_error "pip not found. Please install Python and pip first."
        return 1
    fi
    
    if $PIP_CMD install -r "$requirements" > /dev/null 2>&1; then
        print_success "Dependencies installed successfully"
        return 0
    else
        print_error "Failed to install dependencies"
        echo "Try manually: $PIP_CMD install -r $requirements"
        return 1
    fi
}

# Main script
main() {
    print_header "🚀 Slackbot OSS - Interactive Setup"
    
    cat << 'EOF'
Welcome! This script will help you set up your Slackbot.

You'll be prompted for:
  • Which bot integration to use
  • Slack credentials
  • Database/service credentials
  • API keys

Your credentials will be saved to a .env file (never committed to git).

EOF
    
    read -p "Press Enter to continue..."
    
    # Step 1: Choose bot type
    print_step 1 "Choose Bot Integration"
    
    local bot_idx=$(prompt_choice "Which integration do you want to use?" \
        "Direct SQL (Recommended) - Simple, works immediately" \
        "FastMCP - For multi-app platforms (requires MCP server)" \
        "Snowflake Cortex - Use Snowflake's built-in LLM (experimental)" \
        "dbt Semantic Layer - Query governed metrics (experimental)")
    
    case $bot_idx in
        0) setup_direct_sql ;;
        1) setup_fastmcp ;;
        2) setup_cortex ;;
        3) setup_semantic ;;
    esac
    
    # Step 3: Write .env file
    print_step 3 "Save Configuration"
    write_env_file "$ENV_FILE"
    
    # Step 4: Install dependencies
    print_step 4 "Install Dependencies"
    
    read -p $'\nInstall Python dependencies now? (Y/n): ' install
    if [[ ! $install =~ ^[Nn]$ ]]; then
        install_dependencies "$REQUIREMENTS_FILE"
    else
        print_warning "Remember to install dependencies later:"
        echo "  pip install -r $REQUIREMENTS_FILE"
    fi
    
    # Step 5: Next steps
    print_step 5 "You're All Set! 🎉"
    
    cat << EOF

$(print_success "Configuration complete!")

Next steps:

1. Test locally:
   python $BOT_FILE

2. In Slack, test with:
   @YourBot hello
   @YourBot What are the top 5 products by revenue?

3. Deploy to production:
   See HEROKU_DEPLOYMENT.md for deployment instructions

4. Enhance your bot:
   See CONTEXT_GUIDE.md for adding better context

Need help? Check:
  • README.md - Overview and quick start
  • IMPLEMENTATION_GUIDE.md - Detailed setup
  • KNOWN_ISSUES.md - Common problems

Enjoy your Slackbot! 🚀

EOF
}

# Run main function
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main
fi

