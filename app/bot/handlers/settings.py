"""System configuration and owner settings handlers."""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.models.user import User, UserRole
from app.database.repositories.setting_repo import SettingRepository
from app.services.users import has_permission
from app.bot.keyboards.inline_helpers import get_settings_menu_keyboard

router = Router(name="settings_router")


@router.message(Command("settings"))
@router.message(F.text == "⚙️ Settings")
async def show_settings_menu(message: Message, session: AsyncSession, user: User) -> None:
    is_admin = has_permission(user, UserRole.ADMIN)
    setting_repo = SettingRepository(session)
    tz = await setting_repo.get_value("TIMEZONE", settings.TIMEZONE)
    curr = await setting_repo.get_value("CURRENCY_SYMBOL", settings.CURRENCY_SYMBOL)
    low_stock = await setting_repo.get_value("LOW_STOCK_THRESHOLD", str(settings.LOW_STOCK_THRESHOLD))

    text = (
        f"⚙️ <b>BUSINESS SYSTEM SETTINGS</b>\n\n"
        f"🌐 <b>Timezone:</b> <code>{tz}</code>\n"
        f"💲 <b>Currency Symbol:</b> <code>{curr}</code>\n"
        f"⚠️ <b>Low Stock Threshold:</b> <code>{low_stock}</code> units\n"
        f"☀️ <b>Morning Reminder:</b> <code>{settings.MORNING_REMINDER_TIME}</code>\n"
        f"⏰ <b>Report Reminder:</b> <code>{settings.DAILY_REPORT_REMINDER_TIME}</code>\n\n"
        f"<i>Owner & Admins can adjust settings via buttons below:</i>"
    )
    await message.answer(text, reply_markup=get_settings_menu_keyboard(is_admin), parse_mode="HTML")


@router.callback_query(F.data == "setting:tz_curr")
async def cb_setting_tz_curr(callback: CallbackQuery, session: AsyncSession) -> None:
    setting_repo = SettingRepository(session)
    tz = await setting_repo.get_value("TIMEZONE", settings.TIMEZONE)
    curr = await setting_repo.get_value("CURRENCY_SYMBOL", settings.CURRENCY_SYMBOL)

    text = (
        f"🌐 <b>Regional Localization</b>\n\n"
        f"• Current Timezone: <code>{tz}</code>\n"
        f"• Currency Symbol: <code>{curr}</code>\n\n"
        f"To change, set <code>TIMEZONE</code> or <code>CURRENCY_SYMBOL</code> in your <code>.env</code> file or system settings."
    )
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "setting:reminders")
async def cb_setting_reminders(callback: CallbackQuery) -> None:
    text = (
        f"⏰ <b>Automated Reminder Schedule</b>\n\n"
        f"• Morning Reminder: <b>{settings.MORNING_REMINDER_TIME}</b> (Daily)\n"
        f"• Report Deadline Alert: <b>{settings.DAILY_REPORT_REMINDER_TIME}</b> (Daily)\n"
        f"• Low-Stock Scan: <b>Every 4 hours</b>\n\n"
        f"Notifications are routed to Telegram team members automatically by APScheduler."
    )
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()
