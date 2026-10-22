"""FSM states for multi-step interactive Telegram conversational flows."""

from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    """User registration flow."""
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_role = State()


class ProductStates(StatesGroup):
    """Product creation flow."""
    waiting_for_name = State()
    waiting_for_sku = State()
    waiting_for_category = State()
    waiting_for_retail_price = State()
    waiting_for_wholesale_price = State()
    waiting_for_cost = State()
    waiting_for_stock = State()
    waiting_for_min_stock = State()
    waiting_for_description = State()
    confirm_product = State()


class CustomerStates(StatesGroup):
    """Customer registration flow."""
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_telegram = State()
    waiting_for_notes = State()


class SaleStates(StatesGroup):
    """Quick sale recording flow."""
    selecting_product = State()
    waiting_for_quantity = State()
    selecting_customer = State()
    confirm_sale = State()


class OrderStates(StatesGroup):
    """Order creation flow."""
    selecting_customer = State()
    selecting_product = State()
    waiting_for_quantity = State()
    waiting_for_discount = State()
    waiting_for_shipping = State()
    waiting_for_notes = State()
    confirm_order = State()


class DailyReportStates(StatesGroup):
    """Daily report submission flow."""
    waiting_for_sales = State()
    waiting_for_orders = State()
    waiting_for_customers = State()
    waiting_for_videos = State()
    waiting_for_messages = State()
    waiting_for_followups = State()
    waiting_for_problems = State()
    waiting_for_goal = State()
    confirm_report = State()


class TaskStates(StatesGroup):
    """Task creation flow."""
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_assignee = State()
    waiting_for_priority = State()
    waiting_for_due_date = State()


class BroadcastStates(StatesGroup):
    """Broadcast announcement flow."""
    selecting_target = State()
    waiting_for_message = State()
    confirm_broadcast = State()


class SearchStates(StatesGroup):
    """Global search input flow."""
    waiting_for_query = State()


class AIAssistantStates(StatesGroup):
    """Conversational AI mode."""
    chatting = State()
