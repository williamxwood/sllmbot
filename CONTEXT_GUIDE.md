# Adding Context to Your Slackbot

Guide to enhancing LLM responses with different types of context.

---

## 📚 Types of Context

1. **[Schema Context](#1-schema-context)** - What tables/columns exist
2. **[Business Context](#2-business-context)** - Domain knowledge, terminology
3. **[Data Context](#3-data-context)** - Column meanings, important values
4. **[Conversational Context](#4-conversational-context)** - Thread history
5. **[User Context](#5-user-context)** - Who's asking, their role
6. **[Example Context](#6-example-context)** - Sample queries/answers
7. **[Temporal Context](#7-temporal-context)** - Current date, timeframes

---

## 1. Schema Context

### Current Implementation

In `slack_bot_no_mcp.py` (line 150):

```python
system_prompt = f"""You are a data analytics assistant...

Available tables: {', '.join(self.db.get_available_tables())}

Main table: orders - Contains order data with columns like:
- order_id, customer_id, order_date
- amount, status, payment_method
...
"""
```

### Enhanced Schema Context

Add detailed schema with descriptions:

```python
def get_enhanced_schema(self) -> str:
    """Get schema with column descriptions"""
    return """
Available Tables & Columns:

🛒 ORDERS (Customer Order Data)
Core Identifiers:
  - order_id (INTEGER): Unique order identifier (primary key)
  - customer_id (INTEGER): Customer who placed the order (foreign key to customers)
  - order_date (DATE): When the order was placed
  
Financial Metrics:
  - amount (DECIMAL): Total order amount in USD
  - tax_amount (DECIMAL): Sales tax charged
  - shipping_amount (DECIMAL): Shipping cost
  - discount_amount (DECIMAL): Total discounts applied
  
Order Details:
  - status (VARCHAR): Order status ('pending', 'shipped', 'delivered', 'cancelled')
  - payment_method (VARCHAR): How customer paid ('credit_card', 'debit_card', 'paypal', 'gift_card')
  - shipping_method (VARCHAR): Shipping speed ('standard', 'express', 'overnight')
  - items_count (INTEGER): Number of items in order
  
Fulfillment:
  - shipped_date (DATE): When order was shipped (NULL if not shipped)
  - delivered_date (DATE): When order was delivered (NULL if not delivered)
  - warehouse_id (INTEGER): Which warehouse fulfilled the order

👥 CUSTOMERS (Customer Information)
Core Identifiers:
  - customer_id (INTEGER): Unique customer identifier (primary key)
  - email (VARCHAR): Customer email address (unique)
  - created_at (TIMESTAMP): When customer account was created
  
Demographics:
  - first_name (VARCHAR): Customer first name
  - last_name (VARCHAR): Customer last name
  - city (VARCHAR): Customer city
  - state (VARCHAR): Customer state (2-letter code)
  - country (VARCHAR): Customer country (default 'US')
  - zip_code (VARCHAR): ZIP/postal code
  
Engagement:
  - total_orders (INTEGER): Lifetime order count
  - total_spent (DECIMAL): Lifetime spend amount
  - last_order_date (DATE): Date of most recent order
  - customer_segment (VARCHAR): Segment ('new', 'active', 'at_risk', 'churned')

📦 ORDER_ITEMS (Individual Items in Orders)
Core Identifiers:
  - order_item_id (INTEGER): Unique line item identifier
  - order_id (INTEGER): Parent order (foreign key to orders)
  - product_id (INTEGER): Product purchased (foreign key to products)
  
Quantities & Pricing:
  - quantity (INTEGER): Number of units ordered
  - unit_price (DECIMAL): Price per unit at time of order
  - line_total (DECIMAL): quantity × unit_price
  - discount_percent (DECIMAL): Discount applied (0.1 = 10% off)

🏷️ PRODUCTS (Product Catalog)
Core Identifiers:
  - product_id (INTEGER): Unique product identifier (primary key)
  - sku (VARCHAR): Stock keeping unit (unique)
  - product_name (VARCHAR): Display name
  
Details:
  - category (VARCHAR): Product category ('Electronics', 'Clothing', 'Home', 'Books', etc.)
  - brand (VARCHAR): Product brand/manufacturer
  - unit_cost (DECIMAL): Cost to acquire/produce
  - list_price (DECIMAL): Current retail price
  - in_stock (BOOLEAN): Currently available
  - stock_quantity (INTEGER): Units in inventory

IMPORTANT NOTES:
- All amounts are in USD
- Dates are in YYYY-MM-DD format
- Use CURRENT_DATE() for "today"
- Status values are lowercase with underscores
- Always JOIN on foreign keys (customer_id, order_id, product_id)
- Use ILIKE for case-insensitive searches
"""

# Update system prompt:
system_prompt = f"""You are a data analytics assistant with direct SQL access.

{self.get_enhanced_schema()}

When answering questions:
1. Use execute_sql tool to query the database
2. Use proper JOINs when combining tables
3. Format currency as $X,XXX.XX
4. Be concise but informative
"""
```

---

## 2. Business Context

Add domain knowledge and terminology:

```python
def get_business_context(self) -> str:
    """Add business/industry context"""
    return """
BUSINESS CONTEXT:

Industry Focus: E-commerce / Online Retail
  - Direct-to-consumer sales
  - Focus on repeat purchase behavior
  - Track customer lifetime value

Key Terminology:
  - AOV: Average Order Value (total revenue / number of orders)
  - LTV: Lifetime Value (total amount a customer spends over their lifetime)
  - CAC: Customer Acquisition Cost (marketing spend / new customers)
  - Repeat Rate: % of customers who make more than one purchase
  - Cart Abandonment: Orders started but not completed
  - Conversion Rate: % of visitors who complete a purchase

Customer Segments:
  - New: First order within last 30 days
  - Active: Ordered within last 90 days
  - At Risk: Last order 90-180 days ago
  - Churned: No order in 180+ days

Benchmark Ranges (typical for e-commerce):
  - AOV: $50-150 (varies by category)
  - Repeat Purchase Rate: 20-40% is healthy
  - Shipping conversion: Express (15%), Standard (70%), Overnight (15%)
  - Return Rate: <5% is excellent, >15% is concerning

Order Status Lifecycle:
  1. pending → order placed, awaiting fulfillment
  2. shipped → left warehouse, in transit
  3. delivered → customer received
  4. cancelled → order cancelled (refund issued)

Payment Methods:
  - credit_card: ~60% of orders
  - debit_card: ~25% of orders
  - paypal: ~10% of orders
  - gift_card: ~5% of orders

Seasonality:
  - Q4 (Nov-Dec): Highest volume (holidays)
  - Q1 (Jan-Mar): Typically slowest
  - Watch for: Black Friday, Cyber Monday, back-to-school

When analyzing:
  - Compare metrics month-over-month (MoM) and year-over-year (YoY)
  - Account for seasonality in trends
  - Look at both order count AND revenue (they don't always move together)
  - Consider customer cohorts for retention analysis
"""

# Add to system prompt:
system_prompt = f"""You are a data analytics assistant specializing in e-commerce analytics.

{self.get_enhanced_schema()}

{self.get_business_context()}

When answering questions:
...
"""
```

---

## 3. Data Context

Add context about specific data values and patterns:

```python
def get_data_context(self) -> str:
    """Context about the actual data"""
    return """
DATA CHARACTERISTICS:

Coverage:
  - ~10,000 customers
  - ~50,000 orders
  - ~100,000 order line items
  - ~500 products across 8 categories

Date Ranges:
  - Historical data from: 2020-01-01
  - Latest data through: {current_date}
  - Updated: Daily (orders, inventory)
  - Refreshed: Hourly during business hours

Data Quality Notes:
  - Some early orders (2020) missing shipping details
  - Customer segments recalculated nightly
  - Stock quantities updated in real-time
  - Addresses may be incomplete for guest checkouts

Common Patterns:
  - Orders spike on weekends
  - Average 2-3 items per order
  - ~30% of customers are repeat purchasers
  - Electronics category has highest AOV
  - Clothing has highest return rate
  - Peak hours: 12pm-2pm, 7pm-9pm EST

Missing Data Handling:
  - NULL shipped_date/delivered_date for pending/cancelled orders
  - Some products missing brand information
  - Guest checkouts may have minimal customer data
  - Use COALESCE or IS NOT NULL for aggregations

Typical Data Volumes:
  - Daily orders: 100-500
  - Average cart: $75-125
  - Products per order: 2-4
  - Peak day (Black Friday): 2,000+ orders
"""
```

---

## 4. Conversational Context

Remember thread history for follow-up questions:

```python
class AnthropicProvider:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.db = DatabaseTools()
        self.conversation_history = {}  # thread_id -> messages
    
    async def chat(self, query: str, thread_id: str = None) -> str:
        """Process query with conversation history"""
        
        # Get conversation history for this thread
        if thread_id and thread_id in self.conversation_history:
            messages = self.conversation_history[thread_id]
        else:
            messages = []
        
        # Add new user message
        messages.append({"role": "user", "content": query})
        
        # System prompt
        system_prompt = self.get_system_prompt()
        
        # Call LLM with history
        response = await self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            system=system_prompt,
            messages=messages,  # Full conversation history
            tools=self.get_tools()
        )
        
        # ... handle tool use ...
        
        # Add assistant response to history
        messages.append({
            "role": "assistant",
            "content": response.content
        })
        
        # Store updated history (keep last 10 exchanges)
        if thread_id:
            self.conversation_history[thread_id] = messages[-20:]  # Last 10 Q&A pairs
        
        return final_answer

# In slack event handler:
@slack_app.event("app_mention")
async def handle_mention(event, say):
    thread_ts = event.get("thread_ts", event["ts"])
    
    # Pass thread_id to maintain context
    answer = await llm_provider.chat(
        query=question,
        thread_id=thread_ts  # Use thread_ts as conversation ID
    )
```

**Example conversation with context:**
```
User: "Show me top 10 customers by revenue"
Bot: [lists top 10 customers with their total spend]

User: "How many orders did they place?"  # "they" = top 10 from previous message
Bot: [shows order counts for those same 10 customers]

User: "What's their average order value?"  # Still referring to same 10
Bot: [calculates AOV for those customers]
```

---

## 5. User Context

Add context about who's asking:

```python
def get_user_context(self, user_id: str, channel_id: str) -> str:
    """Add context about the user"""
    
    # Map Slack users to roles (could be from database or config)
    user_roles = {
        "U01ABC": "CEO",
        "U02DEF": "Head of Marketing",
        "U03GHI": "Data Analyst",
        "U04JKL": "Warehouse Manager",
    }
    
    role = user_roles.get(user_id, "Team Member")
    
    return f"""
USER CONTEXT:
  - Asking user role: {role}
  - Channel: {channel_id}

RESPONSE GUIDELINES BY ROLE:
  - CEO: High-level KPIs, trends, focus on revenue and growth
  - Head of Marketing: Customer acquisition, retention, segment analysis
  - Data Analyst: Show SQL, explain methodology, detailed breakdowns
  - Warehouse Manager: Inventory, fulfillment, shipping metrics
  - Team Member: Clear explanations, avoid technical jargon
"""

# In chat method:
async def chat(self, query: str, user_id: str = None, channel_id: str = None) -> str:
    user_ctx = self.get_user_context(user_id, channel_id) if user_id else ""
    
    system_prompt = f"""You are a data analytics assistant.
    
{self.get_enhanced_schema()}
{self.get_business_context()}
{user_ctx}

When answering:
- Tailor detail level to user role
- Executives want summaries, analysts want details
...
"""
```

---

## 6. Example Context

Provide few-shot examples:

```python
def get_example_context(self) -> str:
    """Add example queries and answers"""
    return """
EXAMPLE QUERIES:

Example 1: Simple aggregation
User: "What's our average order value?"
SQL: 
  SELECT AVG(amount) as avg_order_value
  FROM orders
  WHERE status != 'cancelled'
    AND order_date >= DATEADD(month, -1, CURRENT_DATE())
Answer: "The average order value over the last month is $87.32 across 3,847 orders."

Example 2: Customer segmentation
User: "How many customers in each segment?"
SQL:
  SELECT 
    customer_segment,
    COUNT(*) as customer_count,
    AVG(total_spent) as avg_lifetime_value
  FROM customers
  GROUP BY customer_segment
  ORDER BY customer_count DESC
Answer: "Customer breakdown: Active (4,523 customers, $245 avg LTV), At Risk (2,341, $189 avg LTV), New (1,876, $67 avg LTV), Churned (1,260, $123 avg LTV)."

Example 3: Product performance
User: "Top 5 selling products this month"
SQL:
  SELECT 
    p.product_name,
    SUM(oi.quantity) as units_sold,
    SUM(oi.line_total) as revenue
  FROM order_items oi
  JOIN orders o ON oi.order_id = o.order_id
  JOIN products p ON oi.product_id = p.product_id
  WHERE o.order_date >= DATE_TRUNC('month', CURRENT_DATE())
    AND o.status != 'cancelled'
  GROUP BY p.product_id, p.product_name
  ORDER BY revenue DESC
  LIMIT 5
Answer: "Top 5 this month: 1. Wireless Headphones ($24,350, 487 units), 2. Smart Watch ($19,200, 160 units)..."

Example 4: Time-based trend
User: "Show daily orders for last week"
SQL:
  SELECT 
    order_date,
    COUNT(*) as order_count,
    SUM(amount) as total_revenue
  FROM orders
  WHERE order_date >= DATEADD(day, -7, CURRENT_DATE())
    AND status != 'cancelled'
  GROUP BY order_date
  ORDER BY order_date
Answer: "Daily orders last week: Mon (127 orders, $9,845), Tue (143, $11,234), Wed (156, $12,890)... Highest on Sat (298, $23,456)."

Example 5: Customer cohort analysis
User: "Repeat purchase rate for customers acquired in January"
SQL:
  SELECT 
    COUNT(CASE WHEN total_orders > 1 THEN 1 END) * 100.0 / COUNT(*) as repeat_rate
  FROM customers
  WHERE DATE_TRUNC('month', created_at) = '2024-01-01'
Answer: "35.2% of customers acquired in January 2024 have made repeat purchases (421 out of 1,196 customers)."

KEY PATTERNS:
- Use != 'cancelled' to exclude cancelled orders from revenue calculations
- Use DATE_TRUNC for grouping by time periods
- JOIN tables on foreign keys (customer_id, order_id, product_id)
- Format currency with $ and commas: $1,234.56
- Use IS NOT NULL to avoid including missing data in averages
- Always include context: time periods, counts, percentages
"""
```

---

## 7. Temporal Context

Add current date and time context:

```python
from datetime import datetime, timedelta

def get_temporal_context(self) -> str:
    """Add date/time context"""
    now = datetime.now()
    current_month = now.strftime('%B %Y')  # "November 2024"
    current_year = now.year
    last_month = (now - timedelta(days=30)).strftime('%B')
    
    return f"""
TEMPORAL CONTEXT:
  - Current date: {now.strftime('%Y-%m-%d')}
  - Current month: {current_month}
  - Current year: {current_year}
  - Last month: {last_month}
  - Previous year: {current_year - 1}

TIME-BASED INTERPRETATIONS:
  - "today" = WHERE order_date = CURRENT_DATE()
  - "this week" = last 7 days
  - "this month" = WHERE order_date >= DATE_TRUNC('month', CURRENT_DATE())
  - "last month" = previous calendar month
  - "this year" = WHERE YEAR(order_date) = {current_year}
  - "YTD" (year-to-date) = Jan 1 to today
  - "last 30 days" = WHERE order_date >= DATEADD(day, -30, CURRENT_DATE())

When dealing with dates:
  - Use DATE_TRUNC for month/year grouping
  - Use DATEADD for relative dates (-30 days, -1 year, etc.)
  - Group by week: DATE_TRUNC('week', order_date)
  - Compare periods: "vs last year" = same period in {current_year - 1}
  
Common date filters:
  - Last 7 days: order_date >= DATEADD(day, -7, CURRENT_DATE())
  - Last 30 days: order_date >= DATEADD(day, -30, CURRENT_DATE())
  - This month: order_date >= DATE_TRUNC('month', CURRENT_DATE())
  - Last month: order_date >= DATE_TRUNC('month', DATEADD(month, -1, CURRENT_DATE()))
                AND order_date < DATE_TRUNC('month', CURRENT_DATE())
"""
```

---

## 🔧 Complete Implementation Example

Here's how to combine all context types:

```python
class AnthropicProvider:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.db = DatabaseTools()
        self.conversation_history = {}
        
        # Load context on init (cache these)
        self.schema_context = self.get_enhanced_schema()
        self.business_context = self.get_business_context()
        self.data_context = self.get_data_context()
        self.example_context = self.get_example_context()
        self.temporal_context = self.get_temporal_context()
    
    def build_system_prompt(self, user_id: str = None, channel_id: str = None) -> str:
        """Build comprehensive system prompt"""
        
        user_ctx = self.get_user_context(user_id, channel_id) if user_id else ""
        
        return f"""You are a data analytics assistant specializing in e-commerce analytics.
You have direct SQL access to the company's database.

{self.schema_context}

{self.business_context}

{self.data_context}

{self.temporal_context}

{user_ctx}

{self.example_context}

RESPONSE GUIDELINES:
1. Use execute_sql tool to query the database
2. Exclude cancelled orders from revenue calculations: WHERE status != 'cancelled'
3. Format currency nicely: $1,234.56
4. Format percentages: 35.2%, not 0.352
5. Always include context: time periods, sample sizes
6. Use proper JOINs to combine tables
7. Highlight interesting patterns or outliers
8. Be concise but informative

QUERY BEST PRACTICES:
- Use IS NOT NULL to exclude missing data from averages
- Use DATE_TRUNC for time-based grouping
- Use DATEADD for relative date filters
- JOIN on foreign keys: customer_id, order_id, product_id
- Use ILIKE for case-insensitive string matching
- LIMIT results to prevent overwhelming responses (top 10, top 20, etc.)
- Always explain your calculations and assumptions
"""
    
    async def chat(
        self, 
        query: str, 
        thread_id: str = None,
        user_id: str = None,
        channel_id: str = None
    ) -> str:
        """Process query with full context"""
        
        # Get conversation history
        if thread_id and thread_id in self.conversation_history:
            messages = self.conversation_history[thread_id]
        else:
            messages = []
        
        # Add user message
        messages.append({"role": "user", "content": query})
        
        # Build system prompt with all context
        system_prompt = self.build_system_prompt(user_id, channel_id)
        
        # Call LLM
        response = await self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            system=system_prompt,
            messages=messages,
            tools=self.get_tools()
        )
        
        # ... handle tool use and store history ...
        
        return final_answer
```

And update the Slack handler:

```python
@slack_app.event("app_mention")
async def handle_mention(event, say):
    user_id = event["user"]
    channel_id = event["channel"]
    thread_ts = event.get("thread_ts", event["ts"])
    question = text.split(">", 1)[1].strip() if ">" in text else text
    
    # Pass all context
    answer = await llm_provider.chat(
        query=question,
        thread_id=thread_ts,      # Conversation history
        user_id=user_id,          # User context
        channel_id=channel_id     # Channel context
    )
    
    await say(text=answer, thread_ts=thread_ts)
```

---

## 📊 Context Tradeoffs

| Context Type | Value | Token Cost | Update Frequency |
|--------------|-------|------------|------------------|
| Schema | ⭐⭐⭐⭐⭐ High | ~500-1000 | When schema changes |
| Business | ⭐⭐⭐⭐ High | ~300-500 | Quarterly |
| Data | ⭐⭐⭐ Medium | ~200-300 | Monthly |
| Examples | ⭐⭐⭐⭐ High | ~400-600 | As needed |
| Temporal | ⭐⭐ Low | ~100-200 | Daily (cache) |
| User | ⭐⭐ Low | ~50-100 | Per request |
| Conversation | ⭐⭐⭐⭐⭐ High | ~100-500/msg | Per request |

**Recommendation:** Include all except user context (unless role-specific responses needed).

---

## 🎯 Best Practices

### 1. Cache Static Context
```python
# Cache on init, not per request
def __init__(self):
    self.schema_context = self.get_enhanced_schema()  # Load once
```

### 2. Keep Token Budget in Mind
- Full context: ~2000-3000 tokens
- Leaves ~1000 for question + 4000 for answer
- Total budget: ~7000 tokens per request (for Claude Sonnet)

### 3. Layer Context by Priority
```python
# Essential (always include)
system_prompt = f"""
{schema_context}        # MUST HAVE
{business_context}      # MUST HAVE
{example_context}       # VERY HELPFUL
"""

# Optional (include if room)
if include_history:
    messages = conversation_history  # VERY HELPFUL
    
if include_data_notes:
    system_prompt += data_context    # HELPFUL
```

### 4. Update Context Regularly
- **Schema:** When tables/columns change (migrations)
- **Business:** Quarterly (benchmark updates, new categories)
- **Examples:** When you find good patterns
- **Temporal:** Daily (automated with current date)

### 5. Test Context Impact
```python
# A/B test with/without context
results_with_context = test_queries(include_context=True)
results_without = test_queries(include_context=False)

# Measure:
# - Answer accuracy
# - Query correctness
# - Response relevance
```

---

## 🚀 Quick Implementation

**Minimal (just add better schema):**
```python
system_prompt = f"""You are a data analyst.

{self.get_enhanced_schema()}  # Just this!

Answer questions clearly and accurately.
"""
```

**Recommended (schema + business + examples):**
```python
system_prompt = f"""You are an e-commerce data analyst.

{self.get_enhanced_schema()}
{self.get_business_context()}
{self.get_example_context()}

Follow best practices for SQL and formatting.
"""
```

**Full (all context types):**
```python
system_prompt = self.build_system_prompt(user_id, channel_id)  # Everything!
```

Start with "Recommended" and add more as needed!

---

## 📝 Example Context Files

For easier maintenance, store context in separate files:

```
slackbot_oss/
├── context/
│   ├── schema.txt          # Enhanced schema
│   ├── business.txt        # Business context
│   ├── examples.txt        # Query examples
│   └── data_notes.txt      # Data characteristics
├── slack_bot_no_mcp.py
└── ...
```

Then load:
```python
def load_context_file(filename: str) -> str:
    with open(f"context/{filename}", "r") as f:
        return f.read()

schema_context = load_context_file("schema.txt")
```

---

## 💡 Context Customization for Your Domain

### For Different Industries

**SaaS/B2B:**
- Focus on ARR, MRR, churn, expansion revenue
- Customer cohorts, usage metrics
- Contract values, renewal rates

**E-commerce/Retail:**
- AOV, conversion rate, cart abandonment
- Customer segments, repeat purchase rate
- Inventory turnover, fulfillment metrics

**Marketplace:**
- GMV (Gross Merchandise Value), take rate
- Buyer/seller metrics, liquidity
- Match rates, transaction volume

**Media/Content:**
- DAU/MAU, engagement metrics
- Content performance, view time
- Subscription conversions, churn

### Adapt the Schema
Replace table/column names with your own:
- `orders` → `transactions`, `bookings`, `subscriptions`
- `customers` → `users`, `accounts`, `members`
- `amount` → `revenue`, `gmv`, `arr`

### Adapt the Business Context
Update terminology and benchmarks for your industry:
```python
# E-commerce
"AOV: Average Order Value"

# SaaS
"ARR: Annual Recurring Revenue"

# Marketplace
"GMV: Gross Merchandise Value"
```

---

## 🧪 Testing Your Context

### Create a Test Suite

```python
test_queries = [
    {
        "question": "What's our revenue this month?",
        "expected_tables": ["orders"],
        "expected_filters": ["order_date", "status"]
    },
    {
        "question": "Top 5 customers by spend",
        "expected_tables": ["customers", "orders"],
        "expected_sort": "DESC",
        "expected_limit": 5
    },
    {
        "question": "Average order value by month",
        "expected_tables": ["orders"],
        "expected_group_by": ["month"],
        "expected_aggregation": "AVG"
    }
]

def test_context_quality():
    for test in test_queries:
        result = llm_provider.chat(test["question"])
        # Verify SQL contains expected elements
        # Check answer makes sense
        # Log accuracy
```

### Monitor in Production

```python
# Log all queries for analysis
logger.info(f"Question: {question}")
logger.info(f"Generated SQL: {sql}")
logger.info(f"Results: {len(results)} rows")
logger.info(f"Answer: {answer}")

# Track metrics
metrics = {
    "queries_per_day": count_queries(),
    "avg_response_time": measure_latency(),
    "sql_error_rate": count_errors() / count_queries(),
    "user_satisfaction": collect_reactions()  # 👍 / 👎 in Slack
}
```

---

Need help implementing any of these context types? Let me know which ones to add to your specific use case!
