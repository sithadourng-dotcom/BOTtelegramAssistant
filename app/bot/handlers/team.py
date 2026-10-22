"""Team management and hierarchy handlers."""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import User, UserRole
from app.services.users import UserService, has_permission
from app.bot.keyboards.inline_helpers import get_role_selection_keyboard

router = Router(name="team_router")


@router.message(Command("team"))
@router.message(F.text == "👥 Team")
async def show_team_menu(message: Message, session: AsyncSession, user: User) -> None:
    user_service = UserService(session)
    members = await user_service.list_team_members()
    pending = await user_service.list_pending_users()

    lines = [f"👥 <b>BUSINESS TEAM DIRECTORY</b> ({len(members)} active members)\n"]
    for m in members:
        role_label = UserRole.get_display_name(m.role)
        lines.append(f"• <b>{m.full_name}</b> ({role_label})\n  Phone: {m.phone_number or 'N/A'} | @{m.username or 'none'}")

    buttons = []
    if has_permission(user, UserRole.ADMIN):
        if pending:
            buttons.append([InlineKeyboardButton(text=f"⏳ Review Pending ({len(pending)})", callback_data="team:pending")])
        buttons.append([InlineKeyboardButton(text="👤 Change Member Roles", callback_data="team:roles")])

    buttons.append([InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")])

    await message.answer(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "team:pending")
async def cb_team_pending(callback: CallbackQuery, session: AsyncSession, user: User) -> None:
    if not has_permission(user, UserRole.ADMIN):
        await callback.answer("Admin only.", show_alert=True)
        return

    user_service = UserService(session)
    pending = await user_service.list_pending_users()

    if not pending:
        await callback.message.edit_text(
            "✅ No pending registrations waiting for review.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="team_menu")]]
            ),
        )
        await callback.answer()
        return

    buttons = []
    for p in pending:
        buttons.append([InlineKeyboardButton(text=f"Review {p.full_name}", callback_data=f"view_pending:{p.id}")])

    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="team_menu")])
    await callback.message.edit_text(
        f"⏳ <b>Pending Registrations ({len(pending)}):</b>\nSelect a user to approve or assign role:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("view_pending:"))
async def cb_view_pending_user(callback: CallbackQuery, session: AsyncSession) -> None:
    uid = int(callback.data.split(":")[1])
    user_service = UserService(session)
    target = await user_service.user_repo.get_by_id(uid)

    if not target:
        await callback.answer("User not found.", show_alert=True)
        return

    from app.bot.keyboards.inline_helpers import get_approval_keyboard
    text = (
        f"👤 <b>Pending Member Review</b>\n\n"
        f"• <b>Name:</b> {target.full_name}\n"
        f"• <b>Phone:</b> {target.phone_number}\n"
        f"• <b>Username:</b> @{target.username or 'none'}\n"
        f"• <b>ID:</b> <code>{target.telegram_id}</code>"
    )
    await callback.message.edit_text(text, reply_markup=get_approval_keyboard(target.id), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "team_menu")
async def cb_team_menu(callback: CallbackQuery, session: AsyncSession, user: User) -> None:
    user_service = UserService(session)
    members = await user_service.list_team_members()
    pending = await user_service.list_pending_users()

    lines = [f"👥 <b>BUSINESS TEAM DIRECTORY</b> ({len(members)} active members)\n"]
    for m in members:
        role_label = UserRole.get_display_name(m.role)
        lines.append(f"• <b>{m.full_name}</b> ({role_label}) — @{m.username or 'none'}")

    buttons = []
    if has_permission(user, UserRole.ADMIN):
        if pending:
            buttons.append([InlineKeyboardButton(text=f"⏳ Review Pending ({len(pending)})", callback_data="team:pending")])
    buttons.append([InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")])

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )
    await callback.answer()
