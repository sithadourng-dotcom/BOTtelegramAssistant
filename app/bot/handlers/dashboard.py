"""Dashboard handler for real-time business performance analytics."""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import User, UserRole
from app.services.dashboard import DashboardService
from app.services.export import ExportService
from app.services.users import has_permission
from app.bot.keyboards.inline_helpers import get_dashboard_keyboard
from app.utils.formatters import format_currency, format_number, format_percent

router = Router(name="dashboard_router")


def render_dashboard_text(metrics: dict) -> str:
    period_title = metrics["period"].replace("_", " ").title()
    rev = format_currency(metrics["revenue"])
    orders = format_number(metrics["orders_count"])
    sellers = format_number(metrics["active_sellers"])
    content = format_number(metrics["content_posted"])
    reports = format_number(metrics["reports_submitted"])
    growth = format_percent(metrics["growth_percent"])
    month_rev = format_currency(metrics["month_revenue"])
    month_orders = format_number(metrics["month_orders"])

    top_prod_str = ""
    if metrics.get("top_products"):
        top_prod_str = "\n\n<b>Top Selling Products:</b>\n" + "\n".join(
            [f"• {name} — {units} units ({format_currency(r)})" for name, units, r in metrics["top_products"]]
        )

    text = (
        f"📊 <b>BUSINESS DASHBOARD</b>\n\n"
        f"<b>{period_title}</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"💰 <b>Sales:</b> {rev}\n"
        f"🛒 <b>Orders:</b> {orders}\n"
        f"👥 <b>Active sellers:</b> {sellers}\n"
        f"📢 <b>Content posted:</b> {content}\n"
        f"📋 <b>Reports submitted:</b> {reports}\n"
        f"{top_prod_str}\n"
        f"<b>This Month</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"💰 <b>Revenue:</b> {month_rev}\n"
        f"🛒 <b>Orders:</b> {month_orders}\n"
        f"📈 <b>Growth:</b> {growth}\n\n"
        f"<i>Select a timeframe below or export report:</i>"
    )
    return text


@router.message(Command("dashboard"))
@router.message(F.text == "📊 Dashboard")
async def show_dashboard(message: Message, session: AsyncSession, user: User) -> None:
    """Display real-time business performance metrics."""
    if not has_permission(user, UserRole.VIEWER):
        await message.answer("Access restricted.")
        return

    dash_service = DashboardService(session)
    metrics = await dash_service.get_dashboard_metrics(period="today")
    text = render_dashboard_text(metrics)
    await message.answer(text, reply_markup=get_dashboard_keyboard("today"), parse_mode="HTML")


@router.callback_query(F.data.startswith("dash:"))
async def cb_dashboard_period(callback: CallbackQuery, session: AsyncSession, user: User) -> None:
    """Switch dashboard period dynamically."""
    period = callback.data.split(":")[1]
    dash_service = DashboardService(session)
    metrics = await dash_service.get_dashboard_metrics(period=period)
    text = render_dashboard_text(metrics)

    try:
        await callback.message.edit_text(text, reply_markup=get_dashboard_keyboard(period), parse_mode="HTML")
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("export:"))
async def cb_export_report(callback: CallbackQuery, session: AsyncSession, user: User) -> None:
    """Generate and dispatch CSV or Excel report as file attachment."""
    parts = callback.data.split(":")
    fmt = parts[1]  # csv or excel
    period = parts[2]  # today, this_week, this_month

    await callback.answer("Generating report...", show_alert=False)
    export_service = ExportService(session)

    try:
        if fmt == "excel":
            file_path = await export_service.generate_excel_report(period=period)
            caption = f"📊 <b>Executive Business Report ({period.title()})</b>"
        else:
            file_path = await export_service.generate_csv_report(period=period)
            caption = f"📥 <b>Sales Data Export ({period.title()})</b>"

        document = FSInputFile(path=str(file_path), filename=file_path.name)
        await callback.message.answer_document(document=document, caption=caption, parse_mode="HTML")
    except Exception as e:
        await callback.message.answer(f"⚠️ Error generating export: {e}")
