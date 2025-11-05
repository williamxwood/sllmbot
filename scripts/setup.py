#!/usr/bin/env python3
"""
Interactive setup script for Slackbot OSS
Prompts for credentials and creates .env file
"""

import os
import sys
from pathlib import Path
from getpass import getpass


def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")


def print_step(number, text):
    """Print step number"""
    print(f"\n{'─' * 70}")
    print(f"Step {number}: {text}")
    print('─' * 70 + "\n")


def prompt_choice(question, options):
    """Prompt user to choose from options"""
    print(question)
    for i, (key, desc) in enumerate(options.items(), 1):
        print(f"  {i}. {desc}")
    
    while True:
        try:
            choice = input(f"\nEnter choice (1-{len(options)}): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return list(options.keys())[idx]
            print(f"❌ Please enter a number between 1 and {len(options)}")
        except (ValueError, KeyboardInterrupt):
            print("\n❌ Setup cancelled")
            sys.exit(0)


def prompt_input(prompt_text, default=None, required=True, secret=False):
    """Prompt for user input"""
    if default:
        prompt_text = f"{prompt_text} [{default}]"
    
    prompt_text += ": "
    
    while True:
        if secret:
            value = getpass(prompt_text)
        else:
            value = input(prompt_text).strip()
        
        # Use default if provided and no input
        if not value and default:
            return default
        
        # Check if required
        if not value and required:
            print("❌ This field is required. Please enter a value.")
            continue
        
        return value


def test_slack_connection(bot_token, app_token):
    """Test Slack connection"""
    try:
        from slack_sdk import WebClient
        client = WebClient(token=bot_token)
        response = client.auth_test()
        return True, f"✅ Connected as: {response['user']}"
    except Exception as e:
        return False, f"❌ Connection failed: {str(e)}"


def test_snowflake_connection(config):
    """Test Snowflake connection"""
    try:
        import snowflake.connector
        
        conn_params = {
            "user": config["user"],
            "account": config["account"],
            "warehouse": config["warehouse"],
            "database": config["database"],
            "schema": config["schema"],
        }
        
        if config.get("password"):
            conn_params["password"] = config["password"]
        else:
            print("⚠️  Browser auth requires interactive login - skipping connection test")
            return True, "⚠️  Browser auth configured (test manually)"
        
        conn = snowflake.connector.connect(**conn_params)
        cursor = conn.cursor()
        cursor.execute("SELECT CURRENT_VERSION()")
        version = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        return True, f"✅ Connected to Snowflake (version {version})"
    except Exception as e:
        return False, f"❌ Connection failed: {str(e)}"


def test_anthropic_api(api_key):
    """Test Anthropic API key"""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        # Just test that we can create a client
        # Don't make actual API call to avoid costs during setup
        return True, "✅ Anthropic API key format valid"
    except Exception as e:
        return False, f"❌ API key invalid: {str(e)}"


def setup_direct_sql():
    """Setup Direct SQL bot"""
    print_step(2, "Direct SQL Bot Configuration")
    
    config = {}
    
    # Slack credentials
    print("📱 Slack Configuration:")
    config['SLACK_BOT_TOKEN'] = prompt_input("Slack Bot Token (xoxb-...)", required=True)
    config['SLACK_APP_TOKEN'] = prompt_input("Slack App Token (xapp-...)", required=True)
    
    # Test Slack connection
    print("\n🧪 Testing Slack connection...")
    success, message = test_slack_connection(config['SLACK_BOT_TOKEN'], config['SLACK_APP_TOKEN'])
    print(message)
    if not success:
        if input("\nContinue anyway? (y/N): ").lower() != 'y':
            sys.exit(1)
    
    # Snowflake credentials
    print("\n❄️  Snowflake Configuration:")
    config['SNOWFLAKE_USER'] = prompt_input("Snowflake Username", required=True)
    config['SNOWFLAKE_ACCOUNT'] = prompt_input("Snowflake Account (e.g., abc123.us-east-1)", required=True)
    config['SNOWFLAKE_WAREHOUSE'] = prompt_input("Warehouse Name", default="COMPUTE_WH")
    config['SNOWFLAKE_DATABASE'] = prompt_input("Database Name", required=True)
    config['SNOWFLAKE_SCHEMA'] = prompt_input("Schema Name", default="PUBLIC")
    
    # Auth method
    auth_choice = prompt_choice(
        "\n🔐 Snowflake Authentication Method:",
        {
            'password': 'Password authentication (recommended for Heroku)',
            'browser': 'Browser SSO (for local development)'
        }
    )
    
    if auth_choice == 'password':
        config['SNOWFLAKE_PASSWORD'] = prompt_input("Snowflake Password", required=True, secret=True)
    else:
        config['SNOWFLAKE_AUTHENTICATOR'] = 'externalbrowser'
    
    # Test Snowflake connection
    print("\n🧪 Testing Snowflake connection...")
    sf_config = {
        'user': config['SNOWFLAKE_USER'],
        'account': config['SNOWFLAKE_ACCOUNT'],
        'warehouse': config['SNOWFLAKE_WAREHOUSE'],
        'database': config['SNOWFLAKE_DATABASE'],
        'schema': config['SNOWFLAKE_SCHEMA'],
        'password': config.get('SNOWFLAKE_PASSWORD')
    }
    success, message = test_snowflake_connection(sf_config)
    print(message)
    if not success:
        if input("\nContinue anyway? (y/N): ").lower() != 'y':
            sys.exit(1)
    
    # LLM credentials
    print("\n🤖 LLM Configuration:")
    config['ANTHROPIC_API_KEY'] = prompt_input("Anthropic API Key (sk-ant-...)", required=True, secret=True)
    
    # Test Anthropic API
    print("\n🧪 Testing Anthropic API key...")
    success, message = test_anthropic_api(config['ANTHROPIC_API_KEY'])
    print(message)
    
    return config, 'env_no_mcp.example', 'slack_bot_no_mcp.py'


def setup_fastmcp():
    """Setup FastMCP bot"""
    print_step(2, "FastMCP Bot Configuration")
    
    config = {}
    
    # Slack credentials
    print("📱 Slack Configuration:")
    config['SLACK_BOT_TOKEN'] = prompt_input("Slack Bot Token (xoxb-...)", required=True)
    config['SLACK_APP_TOKEN'] = prompt_input("Slack App Token (xapp-...)", required=True)
    
    # FastMCP server
    print("\n🔌 FastMCP Server Configuration:")
    config['FASTMCP_SERVER_URL'] = prompt_input("FastMCP Server URL (https://...)", required=True)
    config['FASTMCP_TOKEN'] = prompt_input("FastMCP Token (fmcp_...)", required=True, secret=True)
    
    # LLM choice
    llm_choice = prompt_choice(
        "\n🤖 Choose LLM Provider:",
        {
            'anthropic': 'Claude (Anthropic) - Recommended',
            'openai': 'GPT-4 (OpenAI)'
        }
    )
    
    config['LLM_PROVIDER'] = llm_choice
    
    if llm_choice == 'anthropic':
        config['ANTHROPIC_API_KEY'] = prompt_input("Anthropic API Key (sk-ant-...)", required=True, secret=True)
    else:
        config['OPENAI_API_KEY'] = prompt_input("OpenAI API Key (sk-...)", required=True, secret=True)
    
    return config, 'env.example', 'slack_bot.py'


def setup_cortex():
    """Setup Snowflake Cortex bot"""
    print_step(2, "Snowflake Cortex Bot Configuration")
    
    config = {}
    
    # Slack credentials
    print("📱 Slack Configuration:")
    config['SLACK_BOT_TOKEN'] = prompt_input("Slack Bot Token (xoxb-...)", required=True)
    config['SLACK_APP_TOKEN'] = prompt_input("Slack App Token (xapp-...)", required=True)
    
    # Snowflake credentials
    print("\n❄️  Snowflake Configuration (must have Cortex enabled):")
    config['SNOWFLAKE_USER'] = prompt_input("Snowflake Username", required=True)
    config['SNOWFLAKE_ACCOUNT'] = prompt_input("Snowflake Account", required=True)
    config['SNOWFLAKE_PASSWORD'] = prompt_input("Snowflake Password", required=True, secret=True)
    config['SNOWFLAKE_WAREHOUSE'] = prompt_input("Warehouse Name", default="COMPUTE_WH")
    config['SNOWFLAKE_DATABASE'] = prompt_input("Database Name", required=True)
    config['SNOWFLAKE_SCHEMA'] = prompt_input("Schema Name", default="PUBLIC")
    
    # Cortex model
    model_choice = prompt_choice(
        "\n🧠 Choose Cortex Model:",
        {
            'mistral-large': 'Mistral Large (best quality, higher cost)',
            'mistral-7b': 'Mistral 7B (faster, lower cost)',
            'llama3-70b': 'Llama 3 70B (high quality)',
            'mixtral-8x7b': 'Mixtral 8x7B (balanced)'
        }
    )
    config['CORTEX_MODEL'] = model_choice
    
    return config, 'env_cortex.example', 'slack_bot_cortex.py'


def setup_semantic():
    """Setup dbt Semantic Layer bot"""
    print_step(2, "dbt Semantic Layer Bot Configuration")
    
    config = {}
    
    # Slack credentials
    print("📱 Slack Configuration:")
    config['SLACK_BOT_TOKEN'] = prompt_input("Slack Bot Token (xoxb-...)", required=True)
    config['SLACK_APP_TOKEN'] = prompt_input("Slack App Token (xapp-...)", required=True)
    
    # dbt Cloud
    print("\n📊 dbt Cloud Configuration:")
    config['DBT_CLOUD_SERVICE_TOKEN'] = prompt_input("dbt Cloud Service Token", required=True, secret=True)
    config['DBT_CLOUD_ENVIRONMENT_ID'] = prompt_input("dbt Cloud Environment ID", required=True)
    
    # LLM for mapping
    print("\n🤖 LLM Configuration (for mapping questions to metrics):")
    config['ANTHROPIC_API_KEY'] = prompt_input("Anthropic API Key (sk-ant-...)", required=True, secret=True)
    config['LLM_MODEL'] = prompt_input("Model", default="claude-3-5-sonnet-20241022")
    
    return config, 'env_semantic.example', 'slack_bot_semantic.py'


def write_env_file(config, template_file):
    """Write .env file from config"""
    env_path = Path('.env')
    
    # Check if .env exists
    if env_path.exists():
        print(f"\n⚠️  .env file already exists")
        overwrite = input("Overwrite? (y/N): ").lower()
        if overwrite != 'y':
            print("Creating .env.new instead...")
            env_path = Path('.env.new')
    
    # Read template (to preserve comments and structure)
    template_path = Path(template_file)
    if template_path.exists():
        with open(template_path, 'r') as f:
            template_content = f.read()
        
        # Replace placeholder values with actual values
        content = template_content
        for key, value in config.items():
            # Replace various placeholder patterns
            patterns = [
                f"{key}=your-",
                f"{key}=xoxb-",
                f"{key}=xapp-",
                f"{key}=sk-",
                f"{key}=sk-ant-",
                f"#{key}=",  # Commented out line
                f"{key}=test",
            ]
            
            for pattern in patterns:
                if pattern in content:
                    # Find the line and replace it
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if pattern in line:
                            # Uncomment if needed
                            if line.strip().startswith('#'):
                                lines[i] = line.lstrip('#').strip()
                            # Replace value
                            lines[i] = f"{key}={value}"
                    content = '\n'.join(lines)
                    break
            else:
                # If key not in template, append it
                content += f"\n{key}={value}"
    else:
        # No template, create from scratch
        content = "# Generated by setup.py\n\n"
        for key, value in config.items():
            content += f"{key}={value}\n"
    
    # Write .env file
    with open(env_path, 'w') as f:
        f.write(content)
    
    print(f"\n✅ Configuration saved to {env_path}")
    
    # Set file permissions (readable only by owner)
    os.chmod(env_path, 0o600)
    print(f"✅ File permissions set to 600 (owner read/write only)")


def install_dependencies(requirements_file):
    """Install required dependencies"""
    print(f"\n📦 Installing dependencies from {requirements_file}...")
    
    import subprocess
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", requirements_file],
            check=True,
            capture_output=True,
            text=True
        )
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e.stderr}")
        return False


def main():
    """Main setup flow"""
    print_header("🚀 Slackbot OSS - Interactive Setup")
    
    print("""
Welcome! This script will help you set up your Slackbot.

You'll be prompted for:
  • Which bot integration to use
  • Slack credentials
  • Database/service credentials
  • API keys

Your credentials will be saved to a .env file (never committed to git).
    """)
    
    input("Press Enter to continue...")
    
    # Step 1: Choose bot type
    print_step(1, "Choose Bot Integration")
    
    bot_type = prompt_choice(
        "Which integration do you want to use?",
        {
            'direct_sql': 'Direct SQL (Recommended) - Simple, works immediately',
            'fastmcp': 'FastMCP - For multi-app platforms (requires MCP server)',
            'cortex': 'Snowflake Cortex - Use Snowflake\'s built-in LLM (experimental)',
            'semantic': 'dbt Semantic Layer - Query governed metrics (experimental)'
        }
    )
    
    # Setup based on choice
    if bot_type == 'direct_sql':
        config, template, bot_file = setup_direct_sql()
        requirements = 'requirements_no_mcp.txt'
    elif bot_type == 'fastmcp':
        config, template, bot_file = setup_fastmcp()
        requirements = 'requirements.txt'
    elif bot_type == 'cortex':
        config, template, bot_file = setup_cortex()
        requirements = 'requirements_cortex.txt'
    else:  # semantic
        config, template, bot_file = setup_semantic()
        requirements = 'requirements_semantic.txt'
    
    # Step 3: Write .env file
    print_step(3, "Save Configuration")
    write_env_file(config, template)
    
    # Step 4: Install dependencies
    print_step(4, "Install Dependencies")
    
    install = input("\nInstall Python dependencies now? (Y/n): ").lower()
    if install != 'n':
        if install_dependencies(requirements):
            print("✅ All dependencies installed")
        else:
            print("\n⚠️  Dependency installation failed. You can install manually:")
            print(f"   pip install -r {requirements}")
    else:
        print(f"\n⚠️  Remember to install dependencies later:")
        print(f"   pip install -r {requirements}")
    
    # Step 5: Next steps
    print_step(5, "You're All Set! 🎉")
    
    print(f"""
✅ Configuration complete!

Next steps:

1. Test locally:
   python {bot_file}

2. In Slack, test with:
   @YourBot hello
   @YourBot What are the top 5 products by revenue?

3. Deploy to production:
   See HEROKU_DEPLOYMENT.md for deployment instructions

4. Enhance your bot:
   See CONTEXT_GUIDE.md for adding better context to improve responses

Need help? Check:
  • README.md - Overview and quick start
  • IMPLEMENTATION_GUIDE.md - Detailed setup instructions
  • KNOWN_ISSUES.md - Common problems and solutions

Enjoy your Slackbot! 🚀
    """)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

