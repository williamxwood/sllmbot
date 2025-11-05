"""
Slack Bot with Snowflake Cortex Integration
Uses Snowflake's built-in LLM to generate and execute SQL

Architecture:
- User asks question in Slack
- Bot sends to Snowflake Cortex (Mistral/Llama)
- Cortex generates SQL based on schema
- Cortex executes SQL and formats answer
- Bot returns to Slack
"""

import os
import logging
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
import snowflake.connector
from typing import Dict, List
import asyncio
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Slack app
slack_app = AsyncApp(token=os.environ.get("SLACK_BOT_TOKEN"))


class SnowflakeCortexProvider:
    """Snowflake Cortex integration for text-to-SQL"""
    
    def __init__(self):
        self.account = os.environ.get("SNOWFLAKE_ACCOUNT")
        self.user = os.environ.get("SNOWFLAKE_USER")
        self.password = os.environ.get("SNOWFLAKE_PASSWORD")
        self.warehouse = os.environ.get("SNOWFLAKE_WAREHOUSE")
        self.database = os.environ.get("SNOWFLAKE_DATABASE", "ANALYTICS")
        self.schema = os.environ.get("SNOWFLAKE_SCHEMA", "ANALYTICS")
        self.model = os.environ.get("CORTEX_MODEL", "mistral-large")  # or llama3-70b, etc.
        
        self.conn = None
        self._connect()
        
        # Get schema information on startup
        self.schema_info = self._get_schema_info()
        logger.info(f"Connected to Snowflake. Schema info loaded: {len(self.schema_info)} tables")
    
    def _connect(self):
        """Establish Snowflake connection"""
        try:
            self.conn = snowflake.connector.connect(
                account=self.account,
                user=self.user,
                password=self.password,
                warehouse=self.warehouse,
                database=self.database,
                schema=self.schema
            )
            logger.info("Snowflake connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Snowflake: {e}")
            raise
    
    def _get_schema_info(self) -> str:
        """Get schema information for all tables"""
        cursor = self.conn.cursor()
        
        # Get all tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = %s
        """, (self.schema,))
        
        tables = [row[0] for row in cursor.fetchall()]
        
        schema_parts = []
        for table in tables:
            # Get columns for each table
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
            """, (self.schema, table))
            
            columns = cursor.fetchall()
            col_desc = ", ".join([f"{col[0]} ({col[1]})" for col in columns])
            schema_parts.append(f"{table}: {col_desc}")
        
        return "\n".join(schema_parts)
    
    def query_with_cortex(self, user_question: str) -> Dict:
        """Use Cortex to generate SQL, execute, and format answer"""
        cursor = self.conn.cursor()
        
        try:
            # Step 1: Generate SQL using Cortex
            logger.info(f"Generating SQL for: {user_question}")
            
            sql_prompt = f"""You are a SQL expert analyzing a Snowflake database.

Database Schema:
{self.schema_info}

User Question: {user_question}

Generate a valid Snowflake SQL SELECT query to answer this question.
Rules:
- Only use SELECT (no INSERT, UPDATE, DELETE, DROP)
- Use proper JOINs if needed
- Include appropriate WHERE clauses
- Format dates properly
- Use LIMIT to avoid huge result sets
- Return ONLY the SQL query, no explanations or markdown

SQL Query:"""

            sql_generation = f"""
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                '{self.model}',
                '{sql_prompt.replace("'", "''")}'
            ) as generated_sql
            """
            
            cursor.execute(sql_generation)
            generated_sql = cursor.fetchone()[0].strip()
            
            # Clean up the SQL (remove markdown if present)
            if generated_sql.startswith("```"):
                lines = generated_sql.split("\n")
                generated_sql = "\n".join([l for l in lines if not l.startswith("```")])
            
            logger.info(f"Generated SQL: {generated_sql}")
            
            # Validate SQL (basic safety check)
            if not self._is_safe_sql(generated_sql):
                raise ValueError("Generated SQL failed safety validation")
            
            # Step 2: Execute the generated SQL
            logger.info("Executing generated SQL")
            cursor.execute(generated_sql)
            
            # Get column names
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            
            # Format as list of dicts
            results = []
            for row in rows[:100]:  # Limit to 100 rows
                results.append(dict(zip(columns, row)))
            
            logger.info(f"Query returned {len(results)} rows")
            
            # Step 3: Use Cortex to format the answer
            answer_prompt = f"""User asked: {user_question}

Query Results ({len(results)} rows):
{json.dumps(results, indent=2, default=str)}

Provide a clear, concise answer to the user's question based on this data.
Format numbers nicely. Use bullet points for lists.
Be helpful and conversational."""

            answer_generation = f"""
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                '{self.model}',
                '{answer_prompt.replace("'", "''")}'
            ) as formatted_answer
            """
            
            cursor.execute(answer_generation)
            formatted_answer = cursor.fetchone()[0]
            
            return {
                "answer": formatted_answer,
                "sql": generated_sql,
                "data": results,
                "row_count": len(results)
            }
            
        except Exception as e:
            logger.error(f"Error querying with Cortex: {e}")
            raise
        finally:
            cursor.close()
    
    def _is_safe_sql(self, sql: str) -> bool:
        """Validate that SQL is safe to execute"""
        sql_lower = sql.lower().strip()
        
        # Must start with SELECT
        if not sql_lower.startswith("select"):
            logger.warning(f"SQL doesn't start with SELECT: {sql_lower[:50]}")
            return False
        
        # Block dangerous keywords
        dangerous = [
            "drop ", "delete ", "truncate ", "insert ", "update ",
            "alter ", "create ", "grant ", "revoke ", "exec"
        ]
        
        for keyword in dangerous:
            if keyword in sql_lower:
                logger.warning(f"Dangerous keyword '{keyword}' found in SQL")
                return False
        
        return True
    
    def close(self):
        """Close Snowflake connection"""
        if self.conn:
            self.conn.close()
            logger.info("Snowflake connection closed")


# Initialize Cortex provider
cortex_provider = SnowflakeCortexProvider()


@slack_app.event("app_mention")
async def handle_mention(event, say):
    """Handle @bot mentions"""
    user = event["user"]
    text = event["text"]
    channel = event["channel"]
    thread_ts = event.get("thread_ts", event["ts"])
    
    # Remove bot mention from text
    question = text.split(">", 1)[1].strip() if ">" in text else text
    
    logger.info(f"Question from {user} in {channel}: {question}")
    
    # Send thinking message
    await say(
        text="🤔 Thinking...",
        thread_ts=thread_ts
    )
    
    try:
        # Query using Cortex
        result = await asyncio.to_thread(
            cortex_provider.query_with_cortex,
            question
        )
        
        # Send answer
        response = f"{result['answer']}\n\n_Query returned {result['row_count']} rows_"
        
        await say(
            text=response,
            thread_ts=thread_ts
        )
        
        # Optionally send SQL in thread
        if os.environ.get("SHOW_SQL", "false").lower() == "true":
            await say(
                text=f"```sql\n{result['sql']}\n```",
                thread_ts=thread_ts
            )
        
    except Exception as e:
        logger.error(f"Error processing question: {e}")
        await say(
            text=f"❌ Sorry, I encountered an error: {str(e)}",
            thread_ts=thread_ts
        )


@slack_app.event("message")
async def handle_message(event, say):
    """Handle DMs to the bot"""
    # Only respond to DMs (not channel messages)
    if event.get("channel_type") != "im":
        return
    
    question = event.get("text", "")
    thread_ts = event.get("ts")
    
    logger.info(f"DM question: {question}")
    
    await say(text="🤔 Thinking...")
    
    try:
        result = await asyncio.to_thread(
            cortex_provider.query_with_cortex,
            question
        )
        
        response = f"{result['answer']}\n\n_Query returned {result['row_count']} rows_"
        await say(text=response)
        
        if os.environ.get("SHOW_SQL", "false").lower() == "true":
            await say(text=f"```sql\n{result['sql']}\n```")
        
    except Exception as e:
        logger.error(f"Error processing DM: {e}")
        await say(text=f"❌ Sorry, I encountered an error: {str(e)}")


async def main():
    """Main entry point"""
    handler = AsyncSocketModeHandler(slack_app, os.environ.get("SLACK_APP_TOKEN"))
    
    logger.info("🚀 Slack bot with Snowflake Cortex starting...")
    logger.info(f"Using Cortex model: {cortex_provider.model}")
    
    try:
        await handler.start_async()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        cortex_provider.close()


if __name__ == "__main__":
    asyncio.run(main())

