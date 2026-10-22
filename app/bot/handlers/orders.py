"""Order management and creation handlers."""

from decimal import Decimal
from typing import Optional
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.order import OrderStatus, PaymentStatus
from app.database.models.user import User, UserRole
from app.services.orders import OrderService
from app.services.products import ProductService
from app.services.customers import CustomerService
from app.services.notifications import NotificationService
from app.services.users import has_permission
from app.bot.states.bot_states import OrderStates
from app.bot.keyboards.main_menu import get_cancel_keyboard, get_main_menu_keyboard
from app.bot.keyboards.inline_helpers import get_orders_menu_keyboard, get_order_action_keyboard
from app.utils.formatters import format_currency

router = Router(name="orders_router")


@router.message(Command("orders"))
@router.message(F.text == "🛒 Orders")
async def show_orders_menu(message: Message, user: User) -> None:
    await message.answer(
        "🛒 <b>Order Management</b>\n\n"
        "Create customer orders, review pending shipments, or update order statuses:",
        reply_markup=get_orders_menu_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "order:list")
async def cb_list_orders(callback: CallbackQuery, session: AsyncSession, user: User) -> None:
    order_service = OrderService(session)
    # Sellers see their orders, Managers/Admins see all
    seller_id = None if has_permission(user, UserRole.MANAGER) else user.id
    orders = await order_service.list_orders(seller_id=seller_id, limit=10)

    if not orders:
        await callback.message.edit_text(
            "🛒 No recent orders found.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="orders_menu")]]
            ),
        )
        await callback.answer()
        return

    buttons = []
    lines = ["🛒 <b>Recent Orders:</b>\n"]
    for o in orders:
        cust_name = o.customer.name if o.customer else "Unknown"
        status_badge = OrderStatus.get_badge(o.order_status)
        lines.append(
            f"• <b>{o.order_number}</b> | {cust_name}\n"
            f"  Total: {format_currency(o.total)} | Status: {status_badge}\n"
        )
        buttons.append([InlineKeyboardButton(text=f"View {o.order_number}", callback_data=f"order_view:{o.id}")])

    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="orders_menu")])
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("order:filter:"))
async def cb_filter_orders(callback: CallbackQuery, session: AsyncSession, user: User) -> None:
    status_str = callback.data.split(":")[2]
    status_enum = OrderStatus(status_str)
    order_service = OrderService(session)
    seller_id = None if has_permission(user, UserRole.MANAGER) else user.id
    orders = await order_service.order_repo.list_orders(seller_id=seller_id, status=status_enum, limit=10)

    if not orders:
        await callback.message.edit_text(
            f"No orders currently with status: <b>{status_str}</b>.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="orders_menu")]]
            ),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    buttons = []
    lines = [f"🛒 <b>{status_str} Orders:</b>\n"]
    for o in orders:
        cust_name = o.customer.name if o.customer else "Unknown"
        lines.append(f"• <b>{o.order_number}</b> | {cust_name} | {format_currency(o.total)}")
        buttons.append([InlineKeyboardButton(text=f"View {o.order_number}", callback_data=f"order_view:{o.id}")])

    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="orders_menu")])
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("order_view:"))
async def cb_view_single_order(callback: CallbackQuery, session: AsyncSession, user: User) -> None:
    order_id = int(callback.data.split(":")[1])
    order_service = OrderService(session)
    order = await order_service.get_order(order_id)

    if not order:
        await callback.answer("Order not found.", show_alert=True)
        return

    item_lines = []
    for it in order.items:
        prod_name = it.product.name if it.product else f"Product {it.product_id}"
        item_lines.append(f"• {prod_name} x {it.quantity} @ {format_currency(it.unit_price)} = {format_currency(it.total_price)}")

    text = (
        f"🛒 <b>ORDER DETAILS</b>\n\n"
        f"🔢 <b>Number:</b> <code>{order.order_number}</code>\n"
        f"👤 <b>Customer:</b> {order.customer.name} ({order.customer.phone})\n"
        f"💼 <b>Seller:</b> {order.seller.full_name}\n"
        f"📅 <b>Date:</b> {order.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        f"📦 <b>Status:</b> {OrderStatus.get_badge(order.order_status)}\n"
        f"💵 <b>Payment:</b> {order.payment_status.value}\n\n"
        f"<b>Items:</b>\n" + "\n".join(item_lines) + "\n\n"
        f"Subtotal: {format_currency(order.subtotal)}\n"
        f"Discount: -{format_currency(order.discount)}\n"
        f"Shipping: +{format_currency(order.shipping_fee)}\n"
        f"<b>Total: {format_currency(order.total)}</b>"
    )

    await callback.message.edit_text(text, reply_markup=get_order_action_keyboard(order.id), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("order_status:"))
async def cb_change_order_status(callback: CallbackQuery, session: AsyncSession, user: User) -> None:
    parts = callback.data.split(":")
    order_id = int(parts[1])
    new_status = OrderStatus(parts[2])

    order_service = OrderService(session)
    try:
        updated = await order_service.update_order_status(actor=user, order_id=order_id, new_status=new_status)
        await session.commit()
    except Exception as e:
        await callback.answer(str(e), show_alert=True)
        return

    await callback.answer(f"Status changed to {new_status.value}")
    # Refresh view
    await cb_view_single_order(callback, session, user)


@router.callback_query(F.data.startswith("order_pay:"))
async def cb_mark_order_paid(callback: CallbackQuery, session: AsyncSession, user: User) -> None:
    order_id = int(callback.data.split(":")[1])
    order_service = OrderService(session)
    try:
        await order_service.update_payment_status(actor=user, order_id=order_id, payment_status=PaymentStatus.PAID)
        await session.commit()
    except Exception as e:
        await callback.answer(str(e), show_alert=True)
        return

    await callback.answer("Order marked as PAID!")
    await cb_view_single_order(callback, session, user)


@router.callback_query(F.data == "orders_menu")
async def cb_orders_menu(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "🛒 <b>Order Management</b>\n\nSelect an option:",
        reply_markup=get_orders_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


# ---------------- Interactive Order Creation Flow ---------------- #

@router.callback_query(F.data == "order:create")
async def cb_create_order_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(OrderStates.selecting_customer)
    await callback.message.answer(
        "🛒 <b>Create New Order</b>\n\n"
        "Step 1: Enter Customer <b>Phone Number</b> (or search existing customer):",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(OrderStates.selecting_customer)
async def order_step_customer(message: Message, state: FSMContext, session: AsyncSession, user: User) -> None:
    text = (message.text or "").strip()
    cust_service = CustomerService(session)

    # Search by phone
    existing = await cust_service.customer_repo.get_by_phone(text)
    if existing:
        await state.update_data(customer_id=existing.id, customer_name=existing.name)
        await state.set_state(OrderStates.selecting_product)
        await message.answer(
            f"👤 Found Customer: <b>{existing.name}</b> ({existing.phone})\n\n"
            f"Step 2: Enter <b>Product SKU</b> or Product Name:",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML",
        )
    else:
        # Prompt for new customer name
        await state.update_data(customer_phone=text)
        await message.answer(
            f"New customer detected for phone <code>{text}</code>.\nEnter Customer <b>Name</b>:",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML",
        )


@router.message(OrderStates.selecting_customer)
async def order_step_new_customer_name(message: Message, state: FSMContext, session: AsyncSession, user: User) -> None:
    pass  # handled in combined block below


@router.message(OrderStates.selecting_product)
async def order_step_product(message: Message, state: FSMContext, session: AsyncSession) -> None:
    query = (message.text or "").strip()
    prod_service = ProductService(session)
    prods = await prod_service.search_products(query)

    if not prods:
        await message.answer(f"No active products matching '{query}'. Please enter a valid SKU or name:")
        return

    # Pick the best match
    selected = prods[0]
    if selected.stock_quantity <= 0:
        await message.answer(f"⚠️ '{selected.name}' is currently OUT OF STOCK (Stock: 0). Please choose another product:")
        return

    await state.update_data(
        product_id=selected.id,
        product_name=selected.name,
        unit_price=float(selected.retail_price),
        stock=selected.stock_quantity,
    )
    await state.set_state(OrderStates.waiting_for_quantity)
    await message.answer(
        f"📦 Selected: <b>{selected.name}</b>\n"
        f"Available Stock: <b>{selected.stock_quantity}</b> | Price: {format_currency(selected.retail_price)}\n\n"
        f"Step 3: Enter <b>Quantity</b> to order:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML",
    )


@router.message(OrderStates.waiting_for_quantity)
async def order_step_quantity(message: Message, state: FSMContext) -> None:
    try:
        qty = int(message.text.strip())
        if qty <= 0:
            raise ValueError
    except Exception:
        await message.answer("Please enter a valid positive quantity:")
        return

    data = await state.get_data()
    if qty > data["stock"]:
        await message.answer(f"Requested {qty} exceeds available stock ({data['stock']}). Please enter a lower quantity:")
        return

    await state.update_data(quantity=qty)
    await state.set_state(OrderStates.waiting_for_discount)
    await message.answer(
        "Step 4: Enter <b>Discount Amount</b> (or enter 0 for none):",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML",
    )


@router.message(OrderStates.waiting_for_discount)
async def order_step_discount(message: Message, state: FSMContext) -> None:
    try:
        disc = Decimal(message.text.replace("$", "").strip())
        if disc < 0:
            raise ValueError
    except Exception:
        disc = Decimal("0.00")

    await state.update_data(discount=float(disc))
    await state.set_state(OrderStates.waiting_for_shipping)
    await message.answer(
        "Step 5: Enter <b>Shipping Fee</b> (or enter 0 for free shipping):",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML",
    )


@router.message(OrderStates.waiting_for_shipping)
async def order_step_confirm(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
    bot: Bot,
) -> None:
    try:
        ship = Decimal(message.text.replace("$", "").strip())
        if ship < 0:
            raise ValueError
    except Exception:
        ship = Decimal("0.00")

    data = await state.get_data()
    await state.clear()

    cust_service = CustomerService(session)
    order_service = OrderService(session)
    notif_service = NotificationService(session, bot)

    # Ensure customer
    customer_id = data.get("customer_id")
    if not customer_id:
        phone = data.get("customer_phone", "000-000")
        name = data.get("customer_name", "Customer")
        cust = await cust_service.get_or_create_customer(actor=user, name=name, phone=phone)
        customer_id = cust.id

    # Create order via service (calculates totals server-side)
    try:
        order, low_stock = await order_service.create_order(
            actor=user,
            customer_id=customer_id,
            items=[(data["product_id"], data["quantity"])],
            discount=Decimal(str(data["discount"])),
            shipping_fee=ship,
        )
        await session.commit()
    except Exception as e:
        await message.answer(f"⚠️ Failed to create order: {e}", reply_markup=get_main_menu_keyboard(user.role))
        return

    # Notify managers/admins of new order
    await notif_service.notify_new_order(order.order_number, user.full_name, format_currency(order.total))

    # Send low stock alerts if any
    for lp in low_stock:
        await notif_service.notify_low_stock(lp)

    kb = get_main_menu_keyboard(user.role)
    await message.answer(
        f"✅ <b>Order Created Successfully!</b>\n\n"
        f"🔢 <b>Order Number:</b> <code>{order.order_number}</code>\n"
        f"📦 <b>Item:</b> {data['product_name']} x {data['quantity']}\n"
        f"Subtotal: {format_currency(order.subtotal)}\n"
        f"Discount: -{format_currency(order.discount)}\n"
        f"Shipping: +{format_currency(order.shipping_fee)}\n"
        f"💰 <b>Grand Total: {format_currency(order.total)}</b>\n\n"
        f"Status: 📝 Pending",
        reply_markup=kb,
        parse_mode="HTML",
    )
