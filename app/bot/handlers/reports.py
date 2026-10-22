"""Daily operational report submission and monitoring handlers."""

from decimal import Decimal
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import User, UserRole
from app.services.reports import ReportService
from app.services.users import has_permission
from app.bot.states.bot_states import DailyReportStates
from app.bot.keyboards.main_menu import get_cancel_keyboard, get_main_menu_keyboard
from app.bot.keyboards.inline_helpers import get_reports_menu_keyboard
from app.utils.formatters import format_currency
from app.utils.tz import today_tz

router = Router(name="reports_router")


@router.message(Command("reports"))
@router.message(F.text == "📝 Daily Report")
async def show_reports_menu(message: Message, user: User) -> None:
    await message.answer(
        "📝 <b>Daily Report System</b>\n\n"
        "Submit your daily operational accomplishments, view submissions, or check missing reports:",
        reply_markup=get_reports_menu_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "report:view_my")
async def cb_view_my_report(callback: CallbackQuery, session: AsyncSession, user: User) -> None:
    report_service = ReportService(session)
    report = await report_service.get_user_report(user_id=user.id, report_date=today_tz())

    if not report:
        await callback.message.edit_text(
            f"📝 You haven't submitted a report for today ({today_tz()}) yet.\nClick below to submit now:",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="📝 Submit Report", callback_data="report:submit")],
                    [InlineKeyboardButton(text="⬅️ Back", callback_data="reports_menu")],
                ]
            ),
        )
        await callback.answer()
        return

    text = (
        f"📝 <b>MY DAILY REPORT</b>\n\n"
        f"📅 <b>Date:</b> {report.report_date}\n"
        f"1. 💰 <b>Sales:</b> {format_currency(report.sales_amount)}\n"
        f"2. 🛒 <b>Orders:</b> {report.orders_count}\n"
        f"3. 👤 <b>New Customers:</b> {report.new_customers_count}\n"
        f"4. 📱 <b>Videos Posted:</b> {report.videos_posted}\n"
        f"5. 💬 <b>Messages Answered:</b> {report.messages_answered}\n"
        f"6. 📞 <b>Customers Followed Up:</b> {report.followups_count}\n"
        f"7. ⚠️ <b>Problems Faced:</b> {report.problems_faced or 'None'}\n"
        f"8. 🎯 <b>Tomorrow's Goal:</b> {report.tomorrow_goal or 'None'}\n\n"
        f"<i>Submitted at: {report.submitted_at.strftime('%H:%M:%S')}</i>"
    )

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="reports_menu")]]
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "report:missing")
async def cb_missing_reports(callback: CallbackQuery, session: AsyncSession, user: User) -> None:
    report_service = ReportService(session)
    missing = await report_service.get_missing_reports(today_tz())

    if not missing:
        await callback.message.edit_text(
            "🎉 <b>Outstanding!</b>\n\nAll active team members have already submitted today's report.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="reports_menu")]]
            ),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    lines = [f"⏰ <b>Missing Reports for Today ({len(missing)} members):</b>\n"]
    for u in missing:
        lines.append(f"• <b>{u.full_name}</b> ({u.role.value}) — @{u.username or 'none'}")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="reports_menu")]]
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "report:team_list")
async def cb_team_reports(callback: CallbackQuery, session: AsyncSession, user: User) -> None:
    report_service = ReportService(session)
    reports = await report_service.list_reports(report_date=today_tz())

    if not reports:
        await callback.message.edit_text(
            f"No team reports submitted yet for today ({today_tz()}).",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="reports_menu")]]
            ),
        )
        await callback.answer()
        return

    lines = [f"👥 <b>Team Submissions Today ({len(reports)}):</b>\n"]
    for r in reports[:10]:
        name = r.user.full_name if r.user else f"User {r.user_id}"
        lines.append(f"• <b>{name}</b>: Sales: {format_currency(r.sales_amount)} | Orders: {r.orders_count} | Videos: {r.videos_posted}")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="reports_menu")]]
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "reports_menu")
async def cb_reports_menu(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "📝 <b>Daily Report System</b>\n\nSelect an option:",
        reply_markup=get_reports_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


# ---------------- Multi-step Report Submission Flow ---------------- #

@router.callback_query(F.data == "report:submit")
async def cb_submit_report_start(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    await state.set_state(DailyReportStates.waiting_for_sales)
    text = (
        f"📝 <b>DAILY REPORT SUBMISSION</b>\n"
        f"Date: <code>{today_tz()}</code>\n\n"
        f"1. Enter today's total <b>Sales Amount</b> (e.g. 150.00 or 0):"
    )
    await callback.message.answer(text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.message(DailyReportStates.waiting_for_sales)
async def rep_step_sales(message: Message, state: FSMContext) -> None:
    try:
        val = Decimal(message.text.replace("$", "").strip())
        if val < 0:
            raise ValueError
    except Exception:
        await message.answer("Please enter a valid sales amount (e.g. 120.00 or 0):")
        return
    await state.update_data(sales=val)
    await state.set_state(DailyReportStates.waiting_for_orders)
    await message.answer("2. Enter number of <b>Orders</b> today (e.g. 5):", reply_markup=get_cancel_keyboard())


@router.message(DailyReportStates.waiting_for_orders)
async def rep_step_orders(message: Message, state: FSMContext) -> None:
    try:
        val = int(message.text.strip())
        if val < 0:
            raise ValueError
    except Exception:
        await message.answer("Please enter a valid count of orders (e.g. 3):")
        return
    await state.update_data(orders=val)
    await state.set_state(DailyReportStates.waiting_for_customers)
    await message.answer("3. Enter number of <b>New Customers</b> gained today:", reply_markup=get_cancel_keyboard())


@router.message(DailyReportStates.waiting_for_customers)
async def rep_step_customers(message: Message, state: FSMContext) -> None:
    try:
        val = int(message.text.strip())
        if val < 0:
            raise ValueError
    except Exception:
        await message.answer("Please enter a valid integer for new customers:")
        return
    await state.update_data(new_cust=val)
    await state.set_state(DailyReportStates.waiting_for_videos)
    await message.answer("4. Enter number of <b>Videos/Posts Created</b> today:", reply_markup=get_cancel_keyboard())


@router.message(DailyReportStates.waiting_for_videos)
async def rep_step_videos(message: Message, state: FSMContext) -> None:
    try:
        val = int(message.text.strip())
        if val < 0:
            raise ValueError
    except Exception:
        val = 0
    await state.update_data(videos=val)
    await state.set_state(DailyReportStates.waiting_for_messages)
    await message.answer("5. Enter number of <b>Customer Messages Answered</b> today:", reply_markup=get_cancel_keyboard())


@router.message(DailyReportStates.waiting_for_messages)
async def rep_step_messages(message: Message, state: FSMContext) -> None:
    try:
        val = int(message.text.strip())
        if val < 0:
            raise ValueError
    except Exception:
        val = 0
    await state.update_data(messages=val)
    await state.set_state(DailyReportStates.waiting_for_followups)
    await message.answer("6. Enter number of <b>Customers Followed Up</b> today:", reply_markup=get_cancel_keyboard())


@router.message(DailyReportStates.waiting_for_followups)
async def rep_step_followups(message: Message, state: FSMContext) -> None:
    try:
        val = int(message.text.strip())
        if val < 0:
            raise ValueError
    except Exception:
        val = 0
    await state.update_data(followups=val)
    await state.set_state(DailyReportStates.waiting_for_problems)
    await message.answer("7. Any <b>Problems or Obstacles</b> faced? (or type 'None'):", reply_markup=get_cancel_keyboard())


@router.message(DailyReportStates.waiting_for_problems)
async def rep_step_problems(message: Message, state: FSMContext) -> None:
    problems = (message.text or "").strip()
    await state.update_data(problems=problems)
    await state.set_state(DailyReportStates.waiting_for_goal)
    await message.answer("8. What is your primary <b>Goal for Tomorrow</b>?", reply_markup=get_cancel_keyboard())


@router.message(DailyReportStates.waiting_for_goal)
async def rep_step_goal(message: Message, state: FSMContext, session: AsyncSession, user: User) -> None:
    goal = (message.text or "").strip()
    data = await state.get_data()
    await state.clear()

    report_service = ReportService(session)
    report = await report_service.submit_daily_report(
        actor=user,
        sales_amount=data["sales"],
        orders_count=data["orders"],
        new_customers_count=data["new_cust"],
        videos_posted=data["videos"],
        messages_answered=data["messages"],
        followups_count=data["followups"],
        problems_faced=data["problems"],
        tomorrow_goal=goal,
    )
    await session.commit()

    kb = get_main_menu_keyboard(user.role)
    await message.answer(
        f"✅ <b>DAILY REPORT SUBMITTED!</b>\n\n"
        f"📅 <b>Date:</b> {report.report_date}\n"
        f"💰 <b>Sales:</b> {format_currency(report.sales_amount)}\n"
        f"🛒 <b>Orders:</b> {report.orders_count}\n"
        f"👥 <b>New Customers:</b> {report.new_customers_count}\n"
        f"📱 <b>Videos/Posts:</b> {report.videos_posted}\n"
        f"💬 <b>Replies:</b> {report.messages_answered}\n"
        f"📞 <b>Follow-ups:</b> {report.followups_count}\n"
        f"🎯 <b>Tomorrow's Goal:</b> {report.tomorrow_goal}\n\n"
        f"<i>Great job today, {user.full_name}!</i>",
        reply_markup=kb,
        parse_mode="HTML",
    )
