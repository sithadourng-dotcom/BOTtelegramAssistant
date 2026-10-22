"""Admin console commands and security management."""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import User, UserRole, UserStatus
from app.services.users import UserService, has_permission
from app.database.repositories.audit_repo import AuditRepository

router = Router(name="admin_router")


@router.message(Command("admin"))
async def cmd_admin_console(message: Message, session: AsyncSession, user: User) -> None:
    if not has_permission(user, UserRole.ADMIN):
        await message.answer("🚫 <b>Unauthorized:</b> Admin access only.", parse_mode="HTML")
        return

    user_service = UserService(session)
    pending = await user_service.list_pending_users()
    members = await user_service.list_team_members()

    text = (
        f"🛡️ <b>ADMINISTRATION CONTROL PANEL</b>\n\n"
        f"👑 Administrator: <b>{user.full_name}</b>\n"
        f"👥 Active Team Members: <b>{len(members)}</b>\n"
        f"⏳ Pending User Approvals: <b>{len(pending)}</b>\n\n"
        f"Use commands or buttons below to manage system:"
    )

    buttons = [
        [InlineKeyboardButton(text=f"⏳ Pending Approvals ({len(pending)})", callback_data="team:pending")],
        [InlineKeyboardButton(text="📜 Audit Logs", callback_data="admin:audit_logs")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")],
    ]
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")


@router.callback_query(F.data == "admin:audit_logs")
async def cb_admin_audit_logs(callback: CallbackQuery, session: AsyncSession, user: User) -> None:
    if not has_permission(user, UserRole.ADMIN):
        await callback.answer("Admin only.", show_alert=True)
        return

    audit_repo = AuditRepository(session)
    logs = await audit_repo.list_logs(limit=10)

    if not logs:
        await callback.message.edit_text(
            "📜 No audit logs recorded yet.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="admin_panel")]]
            ),
        )
        await callback.answer()
        return

    lines = ["📜 <b>Recent Audit Logs:</b>\n"]
    for l in logs:
        actor_name = l.user.full_name if l.user else f"User {l.user_id or 'System'}"
        time_str = l.timestamp.strftime("%m-%d %H:%M")
        lines.append(f"• <code>{time_str}</code> | <b>{l.action}</b> by {actor_name}\n  Entity: {l.entity_type} {l.entity_id or ''}")

    lines.append("\n<i>All critical changes are parameter-logged for accountability.</i>")
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="admin_panel")]]
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "admin_panel")
async def cb_admin_panel(callback: CallbackQuery, session: AsyncSession, user: User) -> None:
    if not has_permission(user, UserRole.ADMIN):
        await callback.answer("Admin only.", show_alert=True)
        return

    user_service = UserService(session)
    pending = await user_service.list_pending_users()
    members = await user_service.list_team_members()

    text = (
        f"🛡️ <b>ADMINISTRATION CONTROL PANEL</b>\n\n"
        f"👑 Administrator: <b>{user.full_name}</b>\n"
        f"👥 Active Team Members: <b>{len(members)}</b>\n"
        f"⏳ Pending User Approvals: <b>{len(pending)}</b>"
    )

    buttons = [
        [InlineKeyboardButton(text=f"⏳ Pending Approvals ({len(pending)})", callback_data="team:pending")],
        [InlineKeyboardButton(text="📜 Audit Logs", callback_data="admin:audit_logs")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")],
    ]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await callback.answer()
