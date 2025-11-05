#!/usr/bin/env python3
"""
Slack Bot with Direct Database Access (No FastMCP Required)

The LLM calls Python functions directly to query your database.
Simpler architecture - just Slack + LLM + Database.
"""

import os
import asyncio
import logging
import json
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

slack_app = AsyncApp(token=os.environ.get("SLACK_BOT_TOKEN"))


# ============================================================================
# DATABASE FUNCTIONS - The LLM calls these
# ============================================================================

class DatabaseTools:
    """Direct database access tools for the LLM"""
    
    def __init__(self):
        # Initialize your database connection
        import snowflake.connector
        self.conn = snowflake.connector.connect(
            user=os.environ.get("SNOWFLAKE_USER"),
            account=os.environ.get("SNOWFLAKE_ACCOUNT"),
            warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE"),
            database=os.environ.get("SNOWFLAKE_DATABASE"),
            schema=os.environ.get("SNOWFLAKE_SCHEMA"),
            authenticator=os.environ.get("SNOWFLAKE_AUTHENTICATOR", "externalbrowser")
        )
    
    def execute_query(self, sql: str) -> List[Dict]:
        """
        Execute a SQL query and return results as list of dicts
        
        Args:
            sql: SQL query to execute
        
        Returns:
            List of row dicts
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql)
            
            # Get column names
            columns = [col[0] for col in cursor.description]
            
            # Fetch all rows
            rows = cursor.fetchall()
            
            # Convert to list of dicts
            results = [dict(zip(columns, row)) for row in rows]
            
            cursor.close()
            return results
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return [{"error": str(e)}]
    
    def get_available_tables(self) -> List[str]:
        """Get list of available tables"""
        sql = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = CURRENT_SCHEMA()
        ORDER BY table_name
        """
        results = self.execute_query(sql)
        return [r['TABLE_NAME'] for r in results]
    
    def get_table_columns(self, table_name: str) -> List[Dict]:
        """Get columns for a specific table"""
        sql = f"""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = '{table_name}'
        AND table_schema = CURRENT_SCHEMA()
        ORDER BY ordinal_position
        """
        return self.execute_query(sql)


# ============================================================================
# LLM INTEGRATION
# ============================================================================

class LLMWithDirectDB:
    """LLM that can call database functions directly"""
    
    def __init__(self, api_key: str):
        from anthropic import AsyncAnthropic
        self.client = AsyncAnthropic(api_key=api_key)
        self.db = DatabaseTools()
    
    def get_tools(self) -> List[Dict]:
        """Define tools the LLM can use"""
        return [
            {
                "name": "execute_sql",
                "description": "Execute a SQL query against the database and return results. Use this for any data query.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "sql": {
                            "type": "string",
                            "description": "The SQL query to execute"
                        },
                        "explanation": {
                            "type": "string",
                            "description": "Brief explanation of what this query does"
                        }
                    },
                    "required": ["sql"]
                }
            },
            {
                "name": "get_schema_info",
                "description": "Get information about available tables and their columns",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "table_name": {
                            "type": "string",
                            "description": "Optional: specific table to get columns for"
                        }
                    }
                }
            }
        ]
    
    async def chat(self, query: str) -> str:
        """Process a query using Claude + direct DB access"""
        try:
            # System prompt with schema context
            system_prompt = f"""You are a data analytics assistant with direct SQL access to a Snowflake database.

Available tables: {', '.join(self.db.get_available_tables())}

Main table: public_comps - Contains company financial and trading data with columns like:
- company, ticker, date
- market_cap, enterprise_value, share_price
- arr, yo_y_implied_arr_growth, net_dollar_retention
- ev_arr_ratio, "EV / NTM Revenue"
- percent_ltm_gross_margin, percent_ltm_fcf_margin_of_revenue
- rule_of_40_ltm_fcf_margin_arr_yo_y_growth
- ltm_magic_number, payback_period
- twelve_month_performance, multiple_return_from_ipo

When answering questions:
1. Use execute_sql tool to query the database
2. Always filter to the most recent date using: WHERE date = (SELECT MAX(date) FROM public_comps)
3. Format numbers nicely (e.g., $1.2B instead of 1200000000)
4. Be concise but informative
"""
            
            messages = [{"role": "user", "content": query}]
            
            # Initial LLM call
            response = await self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                system=system_prompt,
                messages=messages,
                tools=self.get_tools()
            )
            
            # Handle tool use
            while response.stop_reason == "tool_use":
                # Execute tools
                for block in response.content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input
                        
                        logger.info(f"LLM calling: {tool_name}")
                        
                        # Execute tool
                        if tool_name == "execute_sql":
                            sql = tool_input.get("sql")
                            logger.info(f"SQL: {sql[:100]}...")
                            tool_result = self.db.execute_query(sql)
                            result_text = json.dumps(tool_result, default=str)
                        
                        elif tool_name == "get_schema_info":
                            table_name = tool_input.get("table_name")
                            if table_name:
                                tool_result = self.db.get_table_columns(table_name)
                            else:
                                tool_result = {"tables": self.db.get_available_tables()}
                            result_text = json.dumps(tool_result, default=str)
                        
                        else:
                            result_text = f"Unknown tool: {tool_name}"
                        
                        # Add tool result to conversation
                        messages.append({
                            "role": "assistant",
                            "content": response.content
                        })
                        messages.append({
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result_text
                            }]
                        })
                
                # Get final response from LLM
                response = await self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=4096,
                    system=system_prompt,
                    messages=messages,
                    tools=self.get_tools()
                )
            
            # Extract final text response
            final_text = ""
            for block in response.content:
                if block.type == "text":
                    final_text += block.text
            
            return final_text
            
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            return f"❌ Error: {str(e)}"


# ============================================================================
# SLACK BOT
# ============================================================================

class SlackBot:
    """Slack bot with direct LLM + DB integration"""
    
    def __init__(self, llm: LLMWithDirectDB):
        self.llm = llm
        self.bot_user_id = None
    
    async def initialize(self):
        """Initialize bot"""
        try:
            auth_response = await slack_app.client.auth_test()
            self.bot_user_id = auth_response["user_id"]
            logger.info(f"✓ Bot initialized: {self.bot_user_id}")
        except Exception as e:
            logger.error(f"Init failed: {e}")
            raise
    
    async def process_query(self, query: str) -> str:
        """Process user query"""
        return await self.llm.chat(query)


# Initialize
llm = LLMWithDirectDB(api_key=os.environ.get("ANTHROPIC_API_KEY"))
bot = SlackBot(llm=llm)


@slack_app.event("app_mention")
async def handle_mention(event, say):
    """Handle @mentions"""
    try:
        channel_id = event["channel"]
        thread_id = event.get("thread_ts") or event["ts"]
        text = event.get("text", "")
        
        if bot.bot_user_id:
            text = text.replace(f"<@{bot.bot_user_id}>", "").strip()
        
        if not text:
            await say(text="👋 Ask me about your data!", thread_ts=thread_id)
            return
        
        logger.info(f"Query: {text}")
        
        # Send thinking message
        await say(text="🤔 Analyzing...", thread_ts=thread_id)
        
        # Process
        response = await bot.process_query(text)
        
        # Reply
        await say(text=response, thread_ts=thread_id)
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        await say(text=f"❌ Error: {str(e)}", thread_ts=thread_id)


@slack_app.event("message")
async def handle_message(event, say):
    """Handle DMs"""
    if event.get("channel_type") == "im" and not event.get("bot_id"):
        text = event.get("text", "").strip()
        thread_id = event.get("thread_ts") or event["ts"]
        
        if text:
            logger.info(f"DM: {text}")
            await say(text="🤔 Analyzing...", thread_ts=thread_id)
            response = await bot.process_query(text)
            await say(text=response, thread_ts=thread_id)


async def main():
    """Main entry point"""
    logger.info("🤖 Starting Slack Bot (No FastMCP - Direct DB)")
    logger.info("=" * 60)
    
    await bot.initialize()
    
    logger.info("✓ Database connected")
    logger.info("✓ LLM ready (Claude)")
    logger.info("✓ Ready to receive messages!")
    logger.info("=" * 60)
    
    handler = AsyncSocketModeHandler(slack_app, os.environ.get("SLACK_APP_TOKEN"))
    await handler.start_async()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Shutting down")
    except Exception as e:
        logger.error(f"Fatal: {e}", exc_info=True)

