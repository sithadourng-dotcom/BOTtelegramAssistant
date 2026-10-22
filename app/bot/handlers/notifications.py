"""Notification and broadcast management handlers."""

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import User, UserRole
from app.services.notifications import NotificationService
from app.services.users import has_permission
from app.bot.states.bot_states import BroadcastStates
from app.bot.keyboards.main_menu import get_cancel_keyboard, get_main_menu_keyboard
from app.bot.keyboards.inline_helpers import get_broadcast_target_keyboard

router = Router(name="notifications_router")


@router.message(Command("broadcast"))
@router.message(F.text == "📢 Notifications")
async def show_notifications_menu(message: Message, user: User) -> None:
    if not has_permission(user, UserRole.MANAGER):
        await message.answer(
            "📢 <b>Notifications & Alerts</b>\n\n"
            "You are subscribed to operational alerts, morning priorities, and daily report reminders.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")]]
            ),
            parse_mode="HTML",
        )
        return

    await message.answer(
        "📢 <b>Team Announcements & Broadcasts</b>\n\n"
        "Select the audience for your announcement:",
        reply_markup=get_broadcast_target_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("bcast_target:"))
async def cb_broadcast_target(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    target_role = callback.data.split(":")[1]
    await state.update_data(target_role=target_role)
    await state.set_state(BroadcastStates.waiting_for_message)

    await callback.message.answer(
        f"📢 Target Audience: <b>{target_role}</b>\n\n"
        f"Enter the message you want to broadcast to the team:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(BroadcastStates.waiting_for_message)
async def broadcast_send(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
    bot: Bot,
) -> None:
    msg_text = (message.text or "").strip()
    if len(msg_text) < 3:
        await message.answer("Please enter a valid message:")
        return

    data = await state.get_data()
    target_role = data.get("target_role", "ALL")
    await state.clear()

    notif_service = NotificationService(session, bot)
    sent_count = await notif_service.broadcast_announcement(
        sender=user,
        message=msg_text,
        target_role=target_role,
    )
    await session.commit()

    kb = get_main_menu_keyboard(user.role)
    await message.answer(
        f"✅ <b>Broadcast Delivered!</b>\n\n"
        f"Delivered to <b>{sent_count}</b> team member(s) in audience <code>{target_role}</code>.",
        reply_markup=kb,
        parse_mode="HTML",
    )
