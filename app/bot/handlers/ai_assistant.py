"""Conversational AI Assistant handler for natural language business queries."""

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import User
from app.services.ai_assistant import AIAssistantService
from app.bot.states.bot_states import AIAssistantStates
from app.bot.keyboards.main_menu import get_cancel_keyboard, get_main_menu_keyboard

router = Router(name="ai_assistant_router")


@router.message(F.text == "🤖 AI Assistant")
async def start_ai_assistant(message: Message, state: FSMContext, session: AsyncSession, user: User) -> None:
    await state.set_state(AIAssistantStates.chatting)
    welcome_text = (
        "🤖 <b>AI Business Assistant</b>\n\n"
        "Ask me anything about your business in plain English!\n\n"
        "<b>Examples you can try:</b>\n"
        "• <i>'How much did we sell this week?'</i>\n"
        "• <i>'Who has the highest sales this month?'</i>\n"
        "• <i>'How many orders are pending?'</i>\n"
        "• <i>'Show low stock products'</i>\n"
        "• <i>'Who hasn't submitted today's report?'</i>\n"
        "• <i>'Remind me to follow up with customer John'</i>\n\n"
        "Type your question below (or tap ❌ Cancel to exit):"
    )
    await message.answer(welcome_text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")


@router.message(AIAssistantStates.chatting)
async def process_ai_chat(message: Message, state: FSMContext, session: AsyncSession, user: User) -> None:
    text = (message.text or "").strip()
    if not text:
        return

    # Check for cancel
    if text.lower() in ("❌ cancel", "/cancel"):
        await state.clear()
        await message.answer("Exited AI Assistant mode.", reply_markup=get_main_menu_keyboard(user.role))
        return

    ai_service = AIAssistantService(session)
    response = await ai_service.ask(user=user, prompt=text)
    await message.answer(response, reply_markup=get_cancel_keyboard(), parse_mode="HTML")


@router.message(F.text.startswith(("How much", "how much", "Who has", "who has", "how many", "How many", "Show low", "show low", "remind me", "Remind me")))
async def process_natural_language_direct(message: Message, session: AsyncSession, user: User) -> None:
    """Catch natural language questions sent outside of explicit AI Assistant state."""
    text = message.text.strip()
    ai_service = AIAssistantService(session)
    response = await ai_service.ask(user=user, prompt=text)
    await message.answer(response, parse_mode="HTML")
