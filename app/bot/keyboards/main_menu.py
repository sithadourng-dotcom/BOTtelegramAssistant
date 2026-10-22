"""Main menu reply keyboards and common navigation buttons."""

from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from app.database.models.user import UserRole


def get_main_menu_keyboard(role: UserRole = UserRole.SELLER) -> ReplyKeyboardMarkup:
    """
    Generate main menu ReplyKeyboard layout matching business specification.
    """
    keyboard = [
        [KeyboardButton(text="📊 Dashboard"), KeyboardButton(text="🛒 Orders")],
        [KeyboardButton(text="📦 Products"), KeyboardButton(text="👥 Team")],
        [KeyboardButton(text="💰 Sales"), KeyboardButton(text="📝 Daily Report")],
        [KeyboardButton(text="✅ Tasks"), KeyboardButton(text="📢 Notifications")],
        [KeyboardButton(text="🤖 AI Assistant"), KeyboardButton(text="⚙️ Settings")],
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Select an option or type a question...",
    )


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard containing only the cancel button during FSM input."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Cancel")]],
        resize_keyboard=True,
    )


def get_nav_inline_keyboard(back_callback: str = "main_menu") -> InlineKeyboardMarkup:
    """Inline navigation buttons: Back and Main Menu."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⬅️ Back", callback_data=back_callback),
                InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"),
            ]
        ]
    )
