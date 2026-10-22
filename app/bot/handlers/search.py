"""Global search command handler."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import User
from app.services.search import SearchService
from app.utils.formatters import format_currency

router = Router(name="search_router")


@router.message(Command("search"))
async def cmd_global_search(message: Message, session: AsyncSession, user: User) -> None:
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: <code>/search [query]</code>\nExample: <code>/search lotion</code>", parse_mode="HTML")
        return

    query = parts[1].strip()
    search_service = SearchService(session)
    results = await search_service.search_all(query)

    products = results.get("products", [])
    customers = results.get("customers", [])
    orders = results.get("orders", [])
    tasks = results.get("tasks", [])

    if not any([products, customers, orders, tasks]):
        await message.answer(f"🔍 No results found for '<b>{query}</b>'.", parse_mode="HTML")
        return

    lines = [f"🔍 <b>SEARCH RESULTS FOR '{query}':</b>\n"]

    if products:
        lines.append("<b>📦 Products:</b>")
        for p in products:
            lines.append(f"• {p.name} (<code>{p.sku}</code>) — Stock: {p.stock_quantity} | {format_currency(p.retail_price)}")
        lines.append("")

    if customers:
        lines.append("<b>👤 Customers:</b>")
        for c in customers:
            lines.append(f"• {c.name} ({c.phone}) — Orders: {c.total_orders}")
        lines.append("")

    if orders:
        lines.append("<b>🛒 Orders:</b>")
        for o in orders:
            lines.append(f"• {o.order_number} — Total: {format_currency(o.total)} ({o.order_status.value})")
        lines.append("")

    if tasks:
        lines.append("<b>✅ Tasks:</b>")
        for t in tasks:
            lines.append(f"• #{t.id} {t.title} ({t.status.value})")

    await message.answer(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")]]
        ),
        parse_mode="HTML",
    )
