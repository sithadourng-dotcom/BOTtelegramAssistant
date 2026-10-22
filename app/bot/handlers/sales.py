"""Sales tracking handlers and interactive sale recording flow."""

from decimal import Decimal
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import User, UserRole
from app.services.sales import SaleService
from app.services.products import ProductService
from app.services.customers import CustomerService
from app.services.notifications import NotificationService
from app.services.users import has_permission
from app.bot.states.bot_states import SaleStates
from app.bot.keyboards.main_menu import get_cancel_keyboard, get_main_menu_keyboard
from app.bot.keyboards.inline_helpers import get_sales_menu_keyboard
from app.utils.formatters import format_currency
from app.utils.tz import today_tz

router = Router(name="sales_router")


@router.message(Command("sales"))
@router.message(F.text == "💰 Sales")
async def show_sales_menu(message: Message, user: User) -> None:
    await message.answer(
        "💰 <b>Sales Management</b>\n\n"
        "Record direct product sales, monitor daily revenue & gross profit, or view rankings:",
        reply_markup=get_sales_menu_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "sale:my_today")
async def cb_my_sales_today(callback: CallbackQuery, session: AsyncSession, user: User) -> None:
    sale_service = SaleService(session)
    today = today_tz()
    summary = await sale_service.get_summary_for_period(start_date=today, end_date=today, seller_id=user.id)
    sales = await sale_service.sale_repo.list_sales(seller_id=user.id, start_date=today, end_date=today)

    rev = format_currency(summary["revenue"])
    cost = format_currency(summary["cost"])
    profit = format_currency(summary["gross_profit"])

    lines = [
        f"📊 <b>My Sales Today ({today})</b>\n",
        f"💰 <b>Revenue:</b> {rev}",
        f"📉 <b>Cost:</b> {cost}",
        f"📈 <b>Gross Profit:</b> {profit}",
        f"📦 <b>Units Sold:</b> {summary['units_sold']}\n",
    ]

    if sales:
        lines.append("<b>Recent Transactions:</b>")
        for s in sales[:5]:
            p_name = s.product.name if s.product else f"Prod {s.product_id}"
            lines.append(f"• {p_name} x {s.quantity} — {format_currency(s.revenue)} (Profit: {format_currency(s.gross_profit)})")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="sales_menu")]]
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "sale:leaderboard")
async def cb_sales_leaderboard(callback: CallbackQuery, session: AsyncSession) -> None:
    sale_service = SaleService(session)
    month_start = today_tz().replace(day=1)
    rankings = await sale_service.get_top_sellers(start_date=month_start, end_date=today_tz(), limit=10)

    if not rankings:
        await callback.message.edit_text(
            "🏆 No sales recorded yet this month.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="sales_menu")]]
            ),
        )
        await callback.answer()
        return

    lines = ["🏆 <b>TEAM LEADERBOARD (This Month)</b>\n"]
    for idx, (name, rev, units) in enumerate(rankings):
        badge = "🥇" if idx == 0 else "🥈" if idx == 1 else "🥉" if idx == 2 else f"{idx + 1}."
        lines.append(f"{badge} <b>{name}</b>: {format_currency(rev)} ({units} units)")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="sales_menu")]]
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "sales_menu")
async def cb_sales_menu(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "💰 <b>Sales Management</b>\n\nSelect an option:",
        reply_markup=get_sales_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


# ---------------- Interactive Sale Recording Flow ---------------- #

@router.callback_query(F.data == "sale:record")
async def cb_record_sale_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User) -> None:
    if not has_permission(user, UserRole.SELLER):
        await callback.answer("Only approved sellers can record sales.", show_alert=True)
        return

    prod_service = ProductService(session)
    products = await prod_service.list_products(active_only=True)

    if not products:
        await callback.message.answer("No products available to sell.")
        await callback.answer()
        return

    buttons = []
    for p in products[:12]:
        buttons.append([InlineKeyboardButton(text=f"{p.name} ({format_currency(p.retail_price)})", callback_data=f"sel_prod:{p.id}")])
    buttons.append([InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_action")])

    await state.set_state(SaleStates.selecting_product)
    await callback.message.answer(
        "💰 <b>Record Sale</b>\n\nStep 1: Select the product sold:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("sel_prod:"))
async def cb_sale_selected_product(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    prod_id = int(callback.data.split(":")[1])
    prod_service = ProductService(session)
    prod = await prod_service.get_product(prod_id)

    if not prod:
        await callback.answer("Product not found.", show_alert=True)
        return

    if prod.stock_quantity <= 0:
        await callback.answer(f"'{prod.name}' is out of stock!", show_alert=True)
        return

    await state.update_data(product_id=prod.id, product_name=prod.name, stock=prod.stock_quantity)
    await state.set_state(SaleStates.waiting_for_quantity)

    await callback.message.answer(
        f"Selected: <b>{prod.name}</b>\n"
        f"Current Stock: <b>{prod.stock_quantity}</b> | Price: {format_currency(prod.retail_price)}\n\n"
        f"Step 2: Enter <b>Quantity</b> sold:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(SaleStates.waiting_for_quantity)
async def sale_step_quantity(message: Message, state: FSMContext) -> None:
    try:
        qty = int(message.text.strip())
        if qty <= 0:
            raise ValueError
    except Exception:
        await message.answer("Please enter a valid positive quantity:")
        return

    data = await state.get_data()
    if qty > data["stock"]:
        await message.answer(f"Quantity exceeds available stock ({data['stock']}). Enter a lower quantity:")
        return

    await state.update_data(quantity=qty)
    await state.set_state(SaleStates.selecting_customer)
    await message.answer(
        "Step 3: Enter Customer Phone or Name (or enter 'none'):",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(SaleStates.selecting_customer)
async def sale_step_confirm(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
    bot: Bot,
) -> None:
    cust_input = (message.text or "").strip()
    data = await state.get_data()
    await state.clear()

    cust_service = CustomerService(session)
    sale_service = SaleService(session)
    notif_service = NotificationService(session, bot)

    customer_id = None
    if cust_input.lower() != "none" and len(cust_input) > 2:
        cust = await cust_service.get_or_create_customer(actor=user, name=cust_input, phone=cust_input)
        customer_id = cust.id

    try:
        sale, low_stock = await sale_service.record_quick_sale(
            actor=user,
            product_id=data["product_id"],
            quantity=data["quantity"],
            customer_id=customer_id,
        )
        await session.commit()
    except Exception as e:
        await message.answer(f"⚠️ Error recording sale: {e}", reply_markup=get_main_menu_keyboard(user.role))
        return

    if low_stock:
        await notif_service.notify_low_stock(low_stock)

    kb = get_main_menu_keyboard(user.role)
    response_text = (
        f"✅ <b>SALE RECORDED</b>\n\n"
        f"<b>Product:</b> {data['product_name']}\n"
        f"<b>Quantity:</b> {sale.quantity}\n\n"
        f"<b>Revenue:</b> {format_currency(sale.revenue)}\n"
        f"<b>Cost:</b> {format_currency(sale.cost)}\n"
        f"<b>Gross Profit:</b> {format_currency(sale.gross_profit)}\n\n"
        f"<b>Seller:</b> {user.full_name}"
    )
    await message.answer(response_text, reply_markup=kb, parse_mode="HTML")
