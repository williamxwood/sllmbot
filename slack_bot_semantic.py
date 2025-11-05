"""
Slack Bot with dbt Semantic Layer Integration
Uses dbt Cloud's Semantic Layer API to query predefined metrics

Architecture:
- User asks question in Slack
- LLM maps question to semantic layer metrics
- Bot queries dbt Cloud Semantic Layer API
- LLM formats answer from metric data
- Bot returns to Slack
"""

import os
import logging
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
import anthropic
import requests
from typing import Dict, List, Optional
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


class DBTSemanticLayerProvider:
    """dbt Cloud Semantic Layer integration"""
    
    def __init__(self):
        self.service_token = os.environ.get("DBT_CLOUD_SERVICE_TOKEN")
        self.environment_id = os.environ.get("DBT_CLOUD_ENVIRONMENT_ID")
        self.base_url = "https://semantic-layer.cloud.getdbt.com/api/graphql"
        
        # Load available metrics on startup
        self.metrics_catalog = self._get_metrics_catalog()
        logger.info(f"Loaded {len(self.metrics_catalog)} metrics from dbt Semantic Layer")
    
    def _make_request(self, query: str) -> Dict:
        """Make GraphQL request to Semantic Layer"""
        headers = {
            "Authorization": f"Token {self.service_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            self.base_url,
            headers=headers,
            json={"query": query}
        )
        
        if response.status_code != 200:
            raise Exception(f"Semantic Layer API error: {response.status_code} - {response.text}")
        
        data = response.json()
        if "errors" in data:
            raise Exception(f"GraphQL errors: {data['errors']}")
        
        return data.get("data", {})
    
    def _get_metrics_catalog(self) -> List[Dict]:
        """Get list of available metrics and dimensions"""
        query = f"""
        query {{
            metrics(environmentId: {self.environment_id}) {{
                name
                description
                type
                dimensions {{
                    name
                    description
                    type
                }}
                queryableGranularities
            }}
        }}
        """
        
        result = self._make_request(query)
        return result.get("metrics", [])
    
    def get_metrics_description(self) -> str:
        """Get human-readable description of available metrics"""
        descriptions = []
        for metric in self.metrics_catalog:
            desc = f"**{metric['name']}**: {metric.get('description', 'No description')}"
            
            if metric.get('dimensions'):
                dims = [d['name'] for d in metric['dimensions'][:5]]
                desc += f"\n  Dimensions: {', '.join(dims)}"
            
            descriptions.append(desc)
        
        return "\n\n".join(descriptions)
    
    def query_metrics(
        self,
        metrics: List[str],
        group_by: Optional[List[str]] = None,
        where: Optional[List[Dict]] = None,
        order_by: Optional[List[str]] = None,
        limit: int = 100
    ) -> Dict:
        """Query specific metrics from Semantic Layer"""
        
        # Build GraphQL query
        group_by_str = json.dumps(group_by) if group_by else "[]"
        where_str = json.dumps(where) if where else "[]"
        order_str = json.dumps(order_by) if order_by else "[]"
        
        query = f"""
        query {{
            query(
                environmentId: {self.environment_id},
                metrics: {json.dumps(metrics)},
                groupBy: {group_by_str},
                where: {where_str},
                orderBy: {order_str},
                limit: {limit}
            ) {{
                sql
                rows {{
                    dimensions {{
                        name
                        value
                    }}
                    measures {{
                        name
                        value
                    }}
                }}
            }}
        }}
        """
        
        logger.info(f"Querying metrics: {metrics}")
        result = self._make_request(query)
        
        # Convert to more friendly format
        query_result = result.get("query", {})
        rows = []
        
        for row in query_result.get("rows", []):
            row_data = {}
            
            # Add dimensions
            for dim in row.get("dimensions", []):
                row_data[dim["name"]] = dim["value"]
            
            # Add measures
            for measure in row.get("measures", []):
                row_data[measure["name"]] = measure["value"]
            
            rows.append(row_data)
        
        return {
            "sql": query_result.get("sql"),
            "data": rows,
            "row_count": len(rows)
        }


class LLMProvider:
    """Claude integration for mapping questions to metrics"""
    
    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )
        self.model = os.environ.get("LLM_MODEL", "claude-3-5-sonnet-20241022")
    
    async def map_question_to_metrics(
        self,
        question: str,
        metrics_catalog: str
    ) -> Dict:
        """Map user question to semantic layer metric query"""
        
        prompt = f"""You are a data analyst helping map user questions to dbt Semantic Layer metrics.

Available Metrics:
{metrics_catalog}

User Question: {question}

Determine which metrics to query and how to query them. Return a JSON object with:
{{
    "metrics": ["metric_name1", "metric_name2"],
    "group_by": ["dimension1", "dimension2"],  // optional
    "where": [{{"dimension": "sector", "operator": "=", "value": "SaaS"}}],  // optional
    "order_by": ["metric_name1 DESC"],  // optional
    "limit": 100,
    "explanation": "Brief explanation of what you're querying"
}}

If the question can't be answered with available metrics, return:
{{
    "error": "Cannot answer - explain why"
}}

Return ONLY valid JSON, no other text."""

        message = await asyncio.to_thread(
            self.client.messages.create,
            model=self.model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        content = message.content[0].text
        return json.loads(content)
    
    async def format_answer(
        self,
        question: str,
        query_plan: Dict,
        data: List[Dict]
    ) -> str:
        """Format metric query results into natural language answer"""
        
        prompt = f"""You are a helpful data analyst. Format this data into a clear answer.

User Question: {question}

Query Details: {query_plan.get('explanation', 'N/A')}

Data ({len(data)} rows):
{json.dumps(data, indent=2, default=str)}

Provide a clear, concise answer. Use bullet points or tables where appropriate.
Format numbers nicely (e.g., $1.2M instead of 1234567).
Be conversational and helpful."""

        message = await asyncio.to_thread(
            self.client.messages.create,
            model=self.model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return message.content[0].text


# Initialize providers
semantic_layer = DBTSemanticLayerProvider()
llm = LLMProvider()


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
        text="🤔 Analyzing your question...",
        thread_ts=thread_ts
    )
    
    try:
        # Step 1: Map question to metrics
        metrics_desc = semantic_layer.get_metrics_description()
        query_plan = await llm.map_question_to_metrics(question, metrics_desc)
        
        if "error" in query_plan:
            await say(
                text=f"❌ {query_plan['error']}\n\nAvailable metrics:\n{metrics_desc}",
                thread_ts=thread_ts
            )
            return
        
        logger.info(f"Query plan: {query_plan}")
        
        # Step 2: Query semantic layer
        result = await asyncio.to_thread(
            semantic_layer.query_metrics,
            metrics=query_plan["metrics"],
            group_by=query_plan.get("group_by"),
            where=query_plan.get("where"),
            order_by=query_plan.get("order_by"),
            limit=query_plan.get("limit", 100)
        )
        
        # Step 3: Format answer
        answer = await llm.format_answer(question, query_plan, result["data"])
        
        # Send answer
        response = f"{answer}\n\n_Queried {len(query_plan['metrics'])} metric(s), returned {result['row_count']} rows_"
        
        await say(
            text=response,
            thread_ts=thread_ts
        )
        
        # Optionally send SQL
        if os.environ.get("SHOW_SQL", "false").lower() == "true" and result.get("sql"):
            await say(
                text=f"```sql\n{result['sql']}\n```",
                thread_ts=thread_ts
            )
        
    except Exception as e:
        logger.error(f"Error processing question: {e}", exc_info=True)
        await say(
            text=f"❌ Sorry, I encountered an error: {str(e)}",
            thread_ts=thread_ts
        )


@slack_app.event("message")
async def handle_message(event, say):
    """Handle DMs to the bot"""
    # Only respond to DMs
    if event.get("channel_type") != "im":
        return
    
    question = event.get("text", "")
    
    logger.info(f"DM question: {question}")
    
    await say(text="🤔 Analyzing your question...")
    
    try:
        metrics_desc = semantic_layer.get_metrics_description()
        query_plan = await llm.map_question_to_metrics(question, metrics_desc)
        
        if "error" in query_plan:
            await say(text=f"❌ {query_plan['error']}")
            return
        
        result = await asyncio.to_thread(
            semantic_layer.query_metrics,
            metrics=query_plan["metrics"],
            group_by=query_plan.get("group_by"),
            where=query_plan.get("where"),
            order_by=query_plan.get("order_by"),
            limit=query_plan.get("limit", 100)
        )
        
        answer = await llm.format_answer(question, query_plan, result["data"])
        
        await say(text=f"{answer}\n\n_Queried {len(query_plan['metrics'])} metric(s)_")
        
        if os.environ.get("SHOW_SQL", "false").lower() == "true" and result.get("sql"):
            await say(text=f"```sql\n{result['sql']}\n```")
        
    except Exception as e:
        logger.error(f"Error processing DM: {e}", exc_info=True)
        await say(text=f"❌ Sorry, I encountered an error: {str(e)}")


@slack_app.command("/metrics")
async def handle_metrics_command(ack, say):
    """Slash command to list available metrics"""
    await ack()
    
    metrics_desc = semantic_layer.get_metrics_description()
    await say(f"📊 **Available Metrics:**\n\n{metrics_desc}")


async def main():
    """Main entry point"""
    handler = AsyncSocketModeHandler(slack_app, os.environ.get("SLACK_APP_TOKEN"))
    
    logger.info("🚀 Slack bot with dbt Semantic Layer starting...")
    logger.info(f"Loaded {len(semantic_layer.metrics_catalog)} metrics")
    
    await handler.start_async()


if __name__ == "__main__":
    asyncio.run(main())

