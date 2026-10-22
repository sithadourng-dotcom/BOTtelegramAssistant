"""AI Assistant service with safe function calling and internal service dispatch."""

import json
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.models.task import TaskPriority
from app.database.models.user import User
from app.database.repositories.order_repo import OrderRepository
from app.database.repositories.product_repo import ProductRepository
from app.database.repositories.report_repo import ReportRepository
from app.database.repositories.sale_repo import SaleRepository
from app.database.repositories.task_repo import TaskRepository
from app.database.repositories.user_repo import UserRepository
from app.services.tasks import TaskService
from app.utils.formatters import format_currency
from app.utils.logger import logger
from app.utils.tz import now_tz, today_tz


class AIAssistantService:
    """Intelligent assistant routing natural language to safe, verified queries."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.sale_repo = SaleRepository(session)
        self.order_repo = OrderRepository(session)
        self.product_repo = ProductRepository(session)
        self.report_repo = ReportRepository(session)
        self.task_repo = TaskRepository(session)
        self.user_repo = UserRepository(session)
        self.task_service = TaskService(session)

    # ---------------- Safe Controlled Service Functions ---------------- #

    async def get_sales_summary(self, timeframe: str = "today") -> Dict[str, Any]:
        """Fetch verified sales numbers for today, yesterday, this_week, or this_month."""
        today = today_tz()
        if timeframe == "yesterday":
            start = today - timedelta(days=1)
            end = start
        elif timeframe == "this_week":
            start = today - timedelta(days=today.weekday())
            end = today
        elif timeframe == "this_month":
            start = today.replace(day=1)
            end = today
        else:  # today
            start = today
            end = today

        summary = await self.sale_repo.get_summary(start_date=start, end_date=end)
        top_prod = await self.sale_repo.get_top_products(start_date=start, end_date=end, limit=1)
        top_prod_str = f"{top_prod[0][0]} — {top_prod[0][1]} units" if top_prod else "None yet"

        return {
            "timeframe": timeframe,
            "revenue": format_currency(summary["revenue"]),
            "cost": format_currency(summary["cost"]),
            "gross_profit": format_currency(summary["gross_profit"]),
            "units_sold": summary["units_sold"],
            "orders": summary["sales_count"],
            "top_product": top_prod_str,
        }

    async def get_team_rankings(self, timeframe: str = "this_month") -> List[Dict[str, Any]]:
        """Fetch real seller ranking by revenue."""
        today = today_tz()
        if timeframe == "today":
            start = today
        elif timeframe == "this_week":
            start = today - timedelta(days=today.weekday())
        else:
            start = today.replace(day=1)

        sellers = await self.sale_repo.get_top_sellers(start_date=start, end_date=today, limit=5)
        return [
            {"rank": idx + 1, "name": name, "revenue": format_currency(rev), "units": units}
            for idx, (name, rev, units) in enumerate(sellers)
        ]

    async def get_low_stock_products(self) -> List[Dict[str, Any]]:
        """List products currently below or at minimum stock."""
        prods = await self.product_repo.get_low_stock_products()
        return [
            {"name": p.name, "sku": p.sku, "stock": p.stock_quantity, "min_stock": p.minimum_stock}
            for p in prods
        ]

    async def get_pending_orders_count(self) -> int:
        """Count orders awaiting fulfillment or approval."""
        return await self.order_repo.count_pending_orders()

    async def get_missing_reports_today(self) -> List[str]:
        """Get names of users who have not submitted today's report."""
        users = await self.report_repo.get_users_without_report(today_tz())
        return [u.full_name for u in users]

    async def get_overdue_tasks(self) -> List[Dict[str, Any]]:
        """List open tasks that are past their due date."""
        tasks = await self.task_repo.get_overdue_tasks()
        return [
            {
                "id": t.id,
                "title": t.title,
                "assignee": t.assignee.full_name if t.assignee else "Unassigned",
                "due": t.due_date.strftime("%Y-%m-%d %H:%M") if t.due_date else "N/A",
            }
            for t in tasks
        ]

    async def create_reminder_task(self, user: User, title: str, due_date_str: Optional[str] = None) -> Dict[str, Any]:
        """Create a task/reminder for the user."""
        due_dt = None
        if due_date_str:
            try:
                due_dt = datetime.fromisoformat(due_date_str)
            except Exception:
                pass
        task = await self.task_service.create_task(
            creator=user,
            title=title,
            assigned_to=user.id,
            priority=TaskPriority.MEDIUM,
            due_date=due_dt,
        )
        return {"task_id": task.id, "title": task.title, "due_date": str(task.due_date)}

    # ---------------- Tool Dispatcher & Query Router ---------------- #

    async def ask(self, user: User, prompt: str) -> str:
        """
        Process natural language prompt from user.
        If OpenAI API key is set, use tool calling with safe functions.
        Otherwise, fall back to robust rule-based pattern dispatch.
        """
        cleaned = prompt.strip().lower()

        # Rule-based fast paths
        if any(w in cleaned for w in ["today's sale", "today sale", "how much did we sell today", "sales today"]):
            data = await self.get_sales_summary("today")
            return (
                f"📊 <b>Today's Sales</b>\n\n"
                f"💰 Revenue: {data['revenue']}\n"
                f"🛒 Orders: {data['orders']}\n"
                f"📈 Gross Profit: {data['gross_profit']}\n"
                f"📦 Units Sold: {data['units_sold']}\n"
                f"🌟 Top Product: {data['top_product']}"
            )

        if any(w in cleaned for w in ["this week's sale", "sales this week", "how much did we sell this week"]):
            data = await self.get_sales_summary("this_week")
            return (
                f"📊 <b>This Week's Sales</b>\n\n"
                f"💰 Revenue: {data['revenue']}\n"
                f"🛒 Orders: {data['orders']}\n"
                f"📈 Gross Profit: {data['gross_profit']}\n"
                f"📦 Units Sold: {data['units_sold']}\n"
                f"🌟 Top Product: {data['top_product']}"
            )

        if any(w in cleaned for w in ["this month's sale", "sales this month", "how much did we sell this month"]):
            data = await self.get_sales_summary("this_month")
            return (
                f"📊 <b>This Month's Sales</b>\n\n"
                f"💰 Revenue: {data['revenue']}\n"
                f"🛒 Orders: {data['orders']}\n"
                f"📈 Gross Profit: {data['gross_profit']}\n"
                f"📦 Units Sold: {data['units_sold']}\n"
                f"🌟 Top Product: {data['top_product']}"
            )

        if any(w in cleaned for w in ["pending order", "orders are pending", "orders pending"]):
            count = await self.get_pending_orders_count()
            return f"📝 There are currently <b>{count}</b> pending order(s) awaiting processing."

        if any(w in cleaned for w in ["low stock", "stock low", "out of stock"]):
            prods = await self.get_low_stock_products()
            if not prods:
                return "✅ All products have sufficient stock levels above their minimum threshold!"
            lines = [f"• <b>{p['name']}</b>: {p['stock']} remaining (Min: {p['min_stock']})" for p in prods[:10]]
            return f"⚠️ <b>Low Stock Alert ({len(prods)} products):</b>\n\n" + "\n".join(lines)

        if any(w in cleaned for w in ["who hasn't submitted", "missing report", "report not submitted"]):
            missing = await self.get_missing_reports_today()
            if not missing:
                return "✅ All team members have submitted today's report!"
            lines = [f"• {name}" for name in missing]
            return f"⏰ <b>Missing Reports Today ({len(missing)} members):</b>\n\n" + "\n".join(lines)

        if any(w in cleaned for w in ["highest sales", "top seller", "ranking", "best seller"]):
            rankings = await self.get_team_rankings("this_month")
            if not rankings:
                return "No sales recorded yet for this month."
            lines = [f"{r['rank']}. <b>{r['name']}</b>: {r['revenue']} ({r['units']} units)" for r in rankings]
            return f"🏆 <b>Top Sellers This Month:</b>\n\n" + "\n".join(lines)

        if any(w in cleaned for w in ["overdue task", "tasks overdue"]):
            overdue = await self.get_overdue_tasks()
            if not overdue:
                return "✅ No overdue tasks at this time!"
            lines = [f"• <b>{t['title']}</b> (Assignee: {t['assignee']}, Due: {t['due']})" for t in overdue]
            return f"🚨 <b>Overdue Tasks ({len(overdue)}):</b>\n\n" + "\n".join(lines)

        if cleaned.startswith("remind me") or "remind me to" in cleaned:
            task_title = prompt.replace("remind me to", "").replace("remind me", "").strip()
            res = await self.create_reminder_task(user, task_title or "Quick Reminder")
            return f"✅ Created reminder task: <b>{res['title']}</b>"

        # If OpenAI key is available, run tool calling
        if settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-proj-your"):
            try:
                client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                tools = [
                    {
                        "type": "function",
                        "function": {
                            "name": "get_sales_summary",
                            "description": "Get real sales summary (revenue, profit, orders, top product) for a timeframe.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "timeframe": {
                                        "type": "string",
                                        "enum": ["today", "yesterday", "this_week", "this_month"],
                                        "description": "Time period to query",
                                    }
                                },
                                "required": ["timeframe"],
                            },
                        },
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "get_team_rankings",
                            "description": "Get top sellers ranking by revenue.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "timeframe": {"type": "string", "enum": ["today", "this_week", "this_month"]}
                                },
                            },
                        },
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "get_low_stock_products",
                            "description": "List products whose stock is below minimum threshold.",
                            "parameters": {"type": "object", "properties": {}},
                        },
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "get_pending_orders_count",
                            "description": "Count how many orders are currently pending.",
                            "parameters": {"type": "object", "properties": {}},
                        },
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "get_missing_reports_today",
                            "description": "Get team members who have not submitted today's daily report.",
                            "parameters": {"type": "object", "properties": {}},
                        },
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "create_reminder_task",
                            "description": "Create a task or reminder for the user.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string", "description": "Title of the task"},
                                },
                                "required": ["title"],
                            },
                        },
                    },
                ]

                messages = [
                    {
                        "role": "system",
                        "content": (
                            "You are an intelligent business operating system assistant. "
                            "You NEVER hallucinate or invent business data, numbers, or rankings. "
                            "Always call the available tools to retrieve facts from the database. "
                            "Keep your response concise, professional, and formatted in clean HTML."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ]

                response = await client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                )

                choice = response.choices[0].message
                if choice.tool_calls:
                    tool_call = choice.tool_calls[0]
                    fn_name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)

                    if fn_name == "get_sales_summary":
                        result = await self.get_sales_summary(args.get("timeframe", "today"))
                    elif fn_name == "get_team_rankings":
                        result = await self.get_team_rankings(args.get("timeframe", "this_month"))
                    elif fn_name == "get_low_stock_products":
                        result = await self.get_low_stock_products()
                    elif fn_name == "get_pending_orders_count":
                        result = await self.get_pending_orders_count()
                    elif fn_name == "get_missing_reports_today":
                        result = await self.get_missing_reports_today()
                    elif fn_name == "create_reminder_task":
                        result = await self.create_reminder_task(user, args.get("title", "Task"))
                    else:
                        result = {}

                    # Send tool result back for final summary
                    messages.append(choice)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result, default=str),
                    })

                    second_resp = await client.chat.completions.create(
                        model=settings.OPENAI_MODEL,
                        messages=messages,
                    )
                    return second_resp.choices[0].message.content or "Completed."

                return choice.content or "How can I assist you with your business today?"

            except Exception as e:
                logger.error(f"OpenAI error: {e}")

        # Default fallback guidance
        return (
            "🤖 <b>AI Business Assistant</b>\n\n"
            "I can answer questions using real live data from your business database:\n\n"
            "• <i>'How much did we sell this week?'</i>\n"
            "• <i>'Who has the highest sales this month?'</i>\n"
            "• <i>'How many orders are pending?'</i>\n"
            "• <i>'Show low stock products'</i>\n"
            "• <i>'Who hasn't submitted today's report?'</i>\n"
            "• <i>'Remind me tomorrow to follow up with supplier'</i>\n\n"
            "What would you like to know?"
        )
