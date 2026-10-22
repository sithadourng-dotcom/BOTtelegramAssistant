"""Start handler, onboarding, user registration flow, and admin approvals."""

from typing import Optional
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.models.user import User, UserRole, UserStatus
from app.database.repositories.user_repo import UserRepository
from app.services.users import UserService, has_permission
from app.bot.states.bot_states import RegistrationStates
from app.bot.keyboards.main_menu import get_main_menu_keyboard, get_cancel_keyboard
from app.bot.keyboards.inline_helpers import get_approval_keyboard, get_role_selection_keyboard

router = Router(name="start_router")


@router.message(Command("cancel"))
@router.message(F.text.casefold() == "❌ cancel")
async def cmd_cancel(message: Message, state: FSMContext, user: Optional[User]) -> None:
    """Universal cancel handler resetting any active state."""
    current_state = await state.get_state()
    if current_state:
        await state.clear()
    kb = get_main_menu_keyboard(user.role if user else UserRole.VIEWER)
    await message.answer("Action cancelled. Returned to main menu.", reply_markup=kb)


@router.callback_query(F.data == "cancel_action")
async def cb_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.delete()
    await callback.answer("Cancelled.")


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery, state: FSMContext, user: Optional[User]) -> None:
    await state.clear()
    role = user.role if user else UserRole.VIEWER
    kb = get_main_menu_keyboard(role)
    await callback.message.answer("🏠 <b>Main Menu</b>\nWhat would you like to do?", reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession, user: Optional[User], bot: Bot) -> None:
    """Welcome user, verify registration status or trigger onboarding."""
    await state.clear()

    # If user exists and is approved, display Main Menu
    if user and user.status == UserStatus.APPROVED:
        role_label = UserRole.get_display_name(user.role)
        welcome_text = (
            f"🤖 <b>Business Assistant</b>\n\n"
            f"Welcome back, <b>{user.full_name}</b>!\n"
            f"Role: <b>{role_label}</b>\n\n"
            f"What would you like to do today?"
        )
        await message.answer(welcome_text, reply_markup=get_main_menu_keyboard(user.role), parse_mode="HTML")
        return

    # If user exists and is pending
    if user and user.status == UserStatus.PENDING:
        await message.answer(
            "⏳ <b>Account Pending Approval</b>\n\n"
            "Your registration has been submitted to the Admin for approval.\n"
            "You will be notified once access is granted.",
            parse_mode="HTML",
        )
        return

    # User does not exist in DB: start onboarding
    await state.set_state(RegistrationStates.waiting_for_name)
    await message.answer(
        "👋 <b>Welcome to Business Assistant Bot!</b>\n\n"
        "To get started, please enter your <b>Full Name</b>:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML",
    )


@router.message(RegistrationStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Please enter a valid full name (at least 2 characters):")
        return

    await state.update_data(full_name=name)
    await state.set_state(RegistrationStates.waiting_for_phone)
    await message.answer(
        f"Thank you, <b>{name}</b>.\n\nPlease enter your <b>Phone Number</b> (e.g. +855 12 345 678):",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML",
    )


@router.message(RegistrationStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    phone = (message.text or "").strip()
    if len(phone) < 6:
        await message.answer("Please enter a valid phone number:")
        return

    data = await state.get_data()
    full_name = data.get("full_name", message.from_user.full_name or "New Member")
    await state.clear()

    # Register user as pending
    user_service = UserService(session)
    user, is_new = await user_service.get_or_register_user(
        telegram_id=message.from_user.id,
        full_name=full_name,
        username=message.from_user.username,
        phone_number=phone,
        requested_role=UserRole.SELLER,
    )
    await session.commit()

    await message.answer(
        "✅ <b>Registration Submitted!</b>\n\n"
        "Your account request has been sent to the Owner/Admin.\n"
        "You will receive an instant notification once approved.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML",
    )

    # Notify Owner/Admin
    admin_id = settings.ADMIN_TELEGRAM_ID
    if admin_id and admin_id != message.from_user.id:
        try:
            admin_msg = (
                f"👤 <b>NEW USER REGISTRATION</b>\n\n"
                f"• <b>Name:</b> {user.full_name}\n"
                f"• <b>Username:</b> @{user.username or 'none'}\n"
                f"• <b>Phone:</b> {user.phone_number}\n"
                f"• <b>Telegram ID:</b> <code>{user.telegram_id}</code>\n\n"
                f"Please approve, reject, or assign a role:"
            )
            await bot.send_message(
                chat_id=admin_id,
                text=admin_msg,
                reply_markup=get_approval_keyboard(user.id),
                parse_mode="HTML",
            )
        except Exception:
            pass


@router.callback_query(F.data.startswith("approve_user:"))
async def cb_approve_user(callback: CallbackQuery, session: AsyncSession, user: User, bot: Bot) -> None:
    """Admin approves pending user."""
    target_id = int(callback.data.split(":")[1])
    user_service = UserService(session)

    try:
        approved_user = await user_service.approve_user(admin_user=user, user_id=target_id)
        await session.commit()
    except Exception as e:
        await callback.answer(str(e), show_alert=True)
        return

    if approved_user:
        await callback.message.edit_text(
            f"✅ Approved <b>{approved_user.full_name}</b> as <b>{approved_user.role.value}</b>.",
            parse_mode="HTML",
        )
        # Notify the approved user
        try:
            await bot.send_message(
                chat_id=approved_user.telegram_id,
                text=(
                    f"🎉 <b>Congratulations, {approved_user.full_name}!</b>\n\n"
                    f"Your account has been approved with role: <b>{approved_user.role.value}</b>.\n"
                    f"You now have access to the business assistant.\n\n"
                    f"Type /start or tap below to open the main menu:"
                ),
                reply_markup=get_main_menu_keyboard(approved_user.role),
                parse_mode="HTML",
            )
        except Exception:
            pass
    await callback.answer("User approved!")


@router.callback_query(F.data.startswith("reject_user:"))
async def cb_reject_user(callback: CallbackQuery, session: AsyncSession, user: User, bot: Bot) -> None:
    """Admin rejects pending user."""
    target_id = int(callback.data.split(":")[1])
    user_service = UserService(session)

    try:
        rejected_user = await user_service.reject_user(admin_user=user, user_id=target_id)
        await session.commit()
    except Exception as e:
        await callback.answer(str(e), show_alert=True)
        return

    if rejected_user:
        await callback.message.edit_text(
            f"❌ Rejected registration for <b>{rejected_user.full_name}</b>.",
            parse_mode="HTML",
        )
        try:
            await bot.send_message(
                chat_id=rejected_user.telegram_id,
                text="❌ Your registration request was reviewed and declined by the administrator.",
            )
        except Exception:
            pass
    await callback.answer("User rejected.")


@router.callback_query(F.data.startswith("role_menu:"))
async def cb_role_menu(callback: CallbackQuery) -> None:
    target_id = int(callback.data.split(":")[1])
    await callback.message.edit_text(
        "Select the role to assign to this member:",
        reply_markup=get_role_selection_keyboard(target_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_role:"))
async def cb_set_role(callback: CallbackQuery, session: AsyncSession, user: User, bot: Bot) -> None:
    parts = callback.data.split(":")
    target_id = int(parts[1])
    new_role = UserRole(parts[2])

    user_service = UserService(session)
    try:
        updated = await user_service.approve_user(admin_user=user, user_id=target_id, assigned_role=new_role)
        await session.commit()
    except Exception as e:
        await callback.answer(str(e), show_alert=True)
        return

    if updated:
        await callback.message.edit_text(
            f"✅ Assigned role <b>{new_role.value}</b> to <b>{updated.full_name}</b> and approved.",
            parse_mode="HTML",
        )
        try:
            await bot.send_message(
                chat_id=updated.telegram_id,
                text=(
                    f"🎉 Your account has been approved!\n"
                    f"Assigned Role: <b>{new_role.value}</b>\n\n"
                    f"Welcome to the team!"
                ),
                reply_markup=get_main_menu_keyboard(new_role),
                parse_mode="HTML",
            )
        except Exception:
            pass
    await callback.answer(f"Role updated to {new_role.value}")


@router.message(Command("help"))
async def cmd_help(message: Message, user: Optional[User]) -> None:
    """Help reference guide."""
    role_str = user.role.value if user else "GUEST"
    help_text = (
        f"📖 <b>Business Assistant Help Guide</b>\n\n"
        f"Your Current Role: <b>{role_str}</b>\n\n"
        f"<b>Common Commands:</b>\n"
        f"• /start - Open main menu & check status\n"
        f"• /dashboard - View live sales & operational performance\n"
        f"• /products - Browse, add, or search catalog\n"
        f"• /orders - View & create customer orders\n"
        f"• /sales - Record sales and view profit\n"
        f"• /reports - Submit or review daily reports\n"
        f"• /tasks - Manage team tasks & deadlines\n"
        f"• /search [term] - Search products, customers, orders, tasks\n"
        f"• /settings - Adjust timezone, reminders & preferences\n\n"
        f"<b>Admin Commands:</b>\n"
        f"• /admin - Access administration console\n"
        f"• /broadcast - Send announcement to team members\n\n"
        f"💬 <b>AI Assistant:</b>\n"
        f"You can also ask questions naturally anytime, like:\n"
        f"<i>'How much did we sell this week?'</i> or <i>'Show low stock products'</i>"
    )
    await message.answer(help_text, parse_mode="HTML")
