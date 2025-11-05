#!/usr/bin/env python3
"""
Open Source Slack Bot with FastMCP Integration

This bot connects Slack to any MCP server, allowing LLMs to query your data
through natural language. Plug in your preferred LLM (Claude, GPT-4, etc).

Architecture:
  Slack → This Bot → LLM (you choose) → FastMCP Server → Your Data
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Slack app
slack_app = AsyncApp(token=os.environ.get("SLACK_BOT_TOKEN"))


class LLMProvider:
    """Base class for LLM providers - implement this for your LLM of choice"""
    
    async def chat(self, messages: List[Dict], tools: Optional[List[Dict]] = None) -> Dict:
        """
        Send a chat request to your LLM
        
        Args:
            messages: Chat history in OpenAI format
            tools: Available tools in OpenAI format (optional)
        
        Returns:
            Response dict with 'content' and optional 'tool_calls'
        """
        raise NotImplementedError("Implement this method for your LLM")


class AnthropicProvider(LLMProvider):
    """Claude/Anthropic implementation"""
    
    def __init__(self, api_key: str):
        from anthropic import AsyncAnthropic
        self.client = AsyncAnthropic(api_key=api_key)
    
    async def chat(self, messages: List[Dict], tools: Optional[List[Dict]] = None) -> Dict:
        """Call Claude API"""
        try:
            # Convert to Anthropic format
            system_msg = next((m['content'] for m in messages if m['role'] == 'system'), None)
            user_messages = [m for m in messages if m['role'] != 'system']
            
            kwargs = {
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 4096,
                "messages": user_messages
            }
            
            if system_msg:
                kwargs["system"] = system_msg
            
            if tools:
                kwargs["tools"] = tools
            
            response = await self.client.messages.create(**kwargs)
            
            # Convert response
            if response.stop_reason == "tool_use":
                tool_calls = [
                    {
                        "id": block.id,
                        "name": block.name,
                        "arguments": block.input
                    }
                    for block in response.content if block.type == "tool_use"
                ]
                text = next((block.text for block in response.content if block.type == "text"), "")
                return {"content": text, "tool_calls": tool_calls}
            else:
                text = next((block.text for block in response.content if block.type == "text"), "")
                return {"content": text}
                
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return {"content": f"Error: {str(e)}"}


class OpenAIProvider(LLMProvider):
    """OpenAI/GPT-4 implementation"""
    
    def __init__(self, api_key: str):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=api_key)
    
    async def chat(self, messages: List[Dict], tools: Optional[List[Dict]] = None) -> Dict:
        """Call OpenAI API"""
        try:
            kwargs = {
                "model": "gpt-4-turbo-preview",
                "messages": messages
            }
            
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"
            
            response = await self.client.chat.completions.create(**kwargs)
            message = response.choices[0].message
            
            result = {"content": message.content or ""}
            
            if message.tool_calls:
                result["tool_calls"] = [
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                    for tc in message.tool_calls
                ]
            
            return result
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return {"content": f"Error: {str(e)}"}


class FastMCPClient:
    """Client for FastMCP server"""
    
    def __init__(self, server_url: str, token: str):
        from fastmcp import Client
        from fastmcp.client.auth import BearerAuth
        self.client = Client(server_url, auth=BearerAuth(token=token))
    
    async def get_tools(self) -> List[Dict]:
        """Get available tools from MCP server in OpenAI format"""
        try:
            async with self.client as client:
                tools_list = await client.list_tools()
                
                # Convert to OpenAI tool format
                openai_tools = []
                for tool in tools_list:
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description or "",
                            "parameters": tool.inputSchema or {}
                        }
                    })
                
                return openai_tools
        except Exception as e:
            logger.error(f"Failed to get tools: {e}")
            return []
    
    async def call_tool(self, tool_name: str, arguments: Dict) -> str:
        """Call a tool on the MCP server"""
        try:
            async with self.client as client:
                result = await client.call_tool(tool_name, arguments)
                
                # Extract text content
                if hasattr(result, 'content') and result.content:
                    return result.content[0].text
                return str(result)
                
        except Exception as e:
            logger.error(f"Tool call failed: {e}")
            return f"Error calling {tool_name}: {str(e)}"


class SlackBot:
    """Main Slack bot orchestrator"""
    
    def __init__(self, llm: LLMProvider, mcp: FastMCPClient):
        self.llm = llm
        self.mcp = mcp
        self.bot_user_id = None
        self.tools_cache = None
    
    async def initialize(self):
        """Initialize bot"""
        try:
            # Get bot user ID
            auth_response = await slack_app.client.auth_test()
            self.bot_user_id = auth_response["user_id"]
            
            # Cache available tools
            self.tools_cache = await self.mcp.get_tools()
            
            logger.info(f"✓ Bot initialized with {len(self.tools_cache)} tools")
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            raise
    
    async def process_query(self, query: str, channel_id: str, thread_id: str) -> str:
        """Process a user query using LLM + MCP tools"""
        try:
            # Build conversation
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful data analytics assistant. Use the available tools to answer questions about company data, financial metrics, and market analytics. Always use tools when data queries are needed."
                },
                {
                    "role": "user",
                    "content": query
                }
            ]
            
            # First LLM call (may include tool calls)
            logger.info(f"Sending query to LLM...")
            llm_response = await self.llm.chat(messages, tools=self.tools_cache)
            
            # Handle tool calls
            if llm_response.get("tool_calls"):
                logger.info(f"LLM requested {len(llm_response['tool_calls'])} tool calls")
                
                # Execute each tool call
                for tool_call in llm_response["tool_calls"]:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["arguments"]
                    
                    if isinstance(tool_args, str):
                        import json
                        tool_args = json.loads(tool_args)
                    
                    logger.info(f"Calling tool: {tool_name}")
                    tool_result = await self.mcp.call_tool(tool_name, tool_args)
                    
                    # Add to conversation
                    messages.append({
                        "role": "assistant",
                        "content": llm_response.get("content", ""),
                        "tool_calls": llm_response["tool_calls"]
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": tool_result
                    })
                
                # Second LLM call with tool results
                logger.info("Sending tool results back to LLM...")
                final_response = await self.llm.chat(messages)
                return final_response["content"]
            
            # No tools needed - return LLM response
            return llm_response["content"]
            
        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            return f"❌ Error: {str(e)}"


# Initialize components
llm_provider_type = os.environ.get("LLM_PROVIDER", "anthropic").lower()

if llm_provider_type == "anthropic":
    llm = AnthropicProvider(api_key=os.environ.get("ANTHROPIC_API_KEY"))
elif llm_provider_type == "openai":
    llm = OpenAIProvider(api_key=os.environ.get("OPENAI_API_KEY"))
else:
    raise ValueError(f"Unsupported LLM provider: {llm_provider_type}")

mcp = FastMCPClient(
    server_url=os.environ.get("FASTMCP_SERVER_URL"),
    token=os.environ.get("FASTMCP_TOKEN")
)

bot = SlackBot(llm=llm, mcp=mcp)


@slack_app.event("app_mention")
async def handle_mention(event, say):
    """Handle @mentions"""
    try:
        user_id = event["user"]
        channel_id = event["channel"]
        thread_id = event.get("thread_ts") or event["ts"]
        text = event.get("text", "")
        
        # Remove bot mention
        if bot.bot_user_id:
            text = text.replace(f"<@{bot.bot_user_id}>", "").strip()
        
        if not text:
            await say(
                text="👋 Ask me anything about your data!",
                thread_ts=thread_id
            )
            return
        
        logger.info(f"Query from {user_id}: {text}")
        
        # Send thinking message
        await say(text="🤔 Processing...", thread_ts=thread_id)
        
        # Process query
        response = await bot.process_query(text, channel_id, thread_id)
        
        # Send response
        await say(text=response, thread_ts=thread_id)
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        await say(text=f"❌ Error: {str(e)}", thread_ts=thread_id)


@slack_app.event("message")
async def handle_message(event, say):
    """Handle direct messages"""
    if event.get("channel_type") == "im" and not event.get("bot_id"):
        user_id = event["user"]
        channel_id = event["channel"]
        text = event.get("text", "").strip()
        thread_id = event.get("thread_ts") or event["ts"]
        
        if text:
            logger.info(f"DM from {user_id}: {text}")
            
            # Send thinking message
            await say(text="🤔 Processing...", thread_ts=thread_id)
            
            # Process
            response = await bot.process_query(text, channel_id, thread_id)
            await say(text=response, thread_ts=thread_id)


async def main():
    """Main entry point"""
    logger.info("🤖 Starting FastMCP Slack Bot")
    logger.info("=" * 60)
    
    # Initialize
    await bot.initialize()
    
    logger.info(f"✓ LLM Provider: {llm_provider_type}")
    logger.info(f"✓ Bot User ID: {bot.bot_user_id}")
    logger.info(f"✓ Available Tools: {len(bot.tools_cache)}")
    logger.info("✓ Ready!")
    logger.info("=" * 60)
    
    # Start
    handler = AsyncSocketModeHandler(slack_app, os.environ.get("SLACK_APP_TOKEN"))
    await handler.start_async()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Shutting down")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)

