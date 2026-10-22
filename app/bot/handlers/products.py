"""Product catalog management handlers and creation workflow."""

from decimal import Decimal
from typing import Optional
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import User, UserRole
from app.services.products import ProductService
from app.services.users import has_permission
from app.bot.states.bot_states import ProductStates, SearchStates
from app.bot.keyboards.main_menu import get_cancel_keyboard, get_main_menu_keyboard
from app.bot.keyboards.inline_helpers import get_products_menu_keyboard
from app.utils.formatters import format_currency

router = Router(name="products_router")


@router.message(Command("products"))
@router.message(F.text == "📦 Products")
async def show_products_menu(message: Message, user: User) -> None:
    is_admin = has_permission(user, UserRole.ADMIN)
    await message.answer(
        "📦 <b>Product & Inventory Management</b>\n\n"
        "Select an option to view inventory, search products, or manage catalog:",
        reply_markup=get_products_menu_keyboard(is_admin),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "prod:view_all")
async def cb_view_all_products(callback: CallbackQuery, session: AsyncSession) -> None:
    prod_service = ProductService(session)
    products = await prod_service.list_products(active_only=True)

    if not products:
        await callback.message.edit_text(
            "📦 No products found in the catalog.\nClick ➕ Add Product to add one.",
            reply_markup=get_products_menu_keyboard(True),
        )
        await callback.answer()
        return

    lines = ["📦 <b>Product Catalog:</b>\n"]
    for p in products[:25]:
        stock_badge = "🔴 Low Stock" if p.is_low_stock else "🟢 In Stock"
        lines.append(
            f"• <b>{p.name}</b> (<code>{p.sku}</code>)\n"
            f"  Category: {p.category} | Stock: {p.stock_quantity} ({stock_badge})\n"
            f"  Retail: {format_currency(p.retail_price)} | Wholesale: {format_currency(p.wholesale_price)}\n"
        )

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="products_menu")]]
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "prod:low_stock")
async def cb_view_low_stock(callback: CallbackQuery, session: AsyncSession) -> None:
    prod_service = ProductService(session)
    low_stock = await prod_service.get_low_stock_products()

    if not low_stock:
        await callback.message.edit_text(
            "✅ <b>Inventory Status Healthy</b>\n\nNo products are currently at or below their minimum stock threshold.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="products_menu")]]
            ),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    lines = ["⚠️ <b>LOW STOCK PRODUCTS:</b>\n"]
    for p in low_stock:
        lines.append(
            f"• <b>{p.name}</b> (<code>{p.sku}</code>)\n"
            f"  Current Stock: <b>{p.stock_quantity}</b> | Minimum Required: {p.minimum_stock}\n"
        )

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="products_menu")]]
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "products_menu")
async def cb_products_menu(callback: CallbackQuery, user: User) -> None:
    is_admin = has_permission(user, UserRole.ADMIN)
    await callback.message.edit_text(
        "📦 <b>Product & Inventory Management</b>\n\nSelect an option:",
        reply_markup=get_products_menu_keyboard(is_admin),
        parse_mode="HTML",
    )
    await callback.answer()


# ---------------- Product Creation Flow ---------------- #

@router.callback_query(F.data == "prod:add")
async def cb_add_product_start(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    if not has_permission(user, UserRole.ADMIN):
        await callback.answer("Only Admins can add products.", show_alert=True)
        return

    await state.set_state(ProductStates.waiting_for_name)
    await callback.message.answer(
        "➕ <b>Add New Product</b>\n\nEnter the product name (e.g. 'Whitening Body Lotion'):",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(ProductStates.waiting_for_name)
async def prod_input_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Please enter a valid product name:")
        return
    await state.update_data(name=name)
    await state.set_state(ProductStates.waiting_for_sku)
    await message.answer("Enter unique SKU code (e.g. 'LOTION-01'):", reply_markup=get_cancel_keyboard())


@router.message(ProductStates.waiting_for_sku)
async def prod_input_sku(message: Message, state: FSMContext, session: AsyncSession) -> None:
    sku = (message.text or "").strip().upper()
    prod_service = ProductService(session)
    existing = await prod_service.product_repo.get_by_sku(sku)
    if existing:
        await message.answer(f"SKU '{sku}' already exists! Please enter a unique SKU:")
        return

    await state.update_data(sku=sku)
    await state.set_state(ProductStates.waiting_for_category)
    await message.answer("Enter Category (e.g. 'Skincare', 'Supplements', 'Cosmetics'):", reply_markup=get_cancel_keyboard())


@router.message(ProductStates.waiting_for_category)
async def prod_input_category(message: Message, state: FSMContext) -> None:
    cat = (message.text or "").strip() or "General"
    await state.update_data(category=cat)
    await state.set_state(ProductStates.waiting_for_retail_price)
    await message.answer("Enter Retail Selling Price (e.g. 25.00):", reply_markup=get_cancel_keyboard())


@router.message(ProductStates.waiting_for_retail_price)
async def prod_input_retail_price(message: Message, state: FSMContext) -> None:
    try:
        val = Decimal(message.text.replace("$", "").strip())
        if val < 0:
            raise ValueError
    except Exception:
        await message.answer("Please enter a valid positive number for retail price (e.g. 25.00):")
        return
    await state.update_data(retail_price=val)
    await state.set_state(ProductStates.waiting_for_wholesale_price)
    await message.answer("Enter Wholesale Price (e.g. 18.00):", reply_markup=get_cancel_keyboard())


@router.message(ProductStates.waiting_for_wholesale_price)
async def prod_input_wholesale_price(message: Message, state: FSMContext) -> None:
    try:
        val = Decimal(message.text.replace("$", "").strip())
        if val < 0:
            raise ValueError
    except Exception:
        await message.answer("Please enter a valid positive number for wholesale price (e.g. 18.00):")
        return
    await state.update_data(wholesale_price=val)
    await state.set_state(ProductStates.waiting_for_cost)
    await message.answer("Enter Product Cost Price (e.g. 10.00):", reply_markup=get_cancel_keyboard())


@router.message(ProductStates.waiting_for_cost)
async def prod_input_cost(message: Message, state: FSMContext) -> None:
    try:
        val = Decimal(message.text.replace("$", "").strip())
        if val < 0:
            raise ValueError
    except Exception:
        await message.answer("Please enter a valid positive cost price (e.g. 10.00):")
        return
    await state.update_data(cost=val)
    await state.set_state(ProductStates.waiting_for_stock)
    await message.answer("Enter Initial Stock Quantity (e.g. 100):", reply_markup=get_cancel_keyboard())


@router.message(ProductStates.waiting_for_stock)
async def prod_input_stock(message: Message, state: FSMContext) -> None:
    try:
        val = int(message.text.strip())
        if val < 0:
            raise ValueError
    except Exception:
        await message.answer("Please enter a valid positive integer for stock:")
        return
    await state.update_data(stock=val)
    await state.set_state(ProductStates.waiting_for_min_stock)
    await message.answer("Enter Minimum Stock Threshold for low stock alert (e.g. 15):", reply_markup=get_cancel_keyboard())


@router.message(ProductStates.waiting_for_min_stock)
async def prod_input_min_stock(message: Message, state: FSMContext, session: AsyncSession, user: User) -> None:
    try:
        min_stock = int(message.text.strip())
        if min_stock < 0:
            raise ValueError
    except Exception:
        min_stock = 10

    data = await state.get_data()
    await state.clear()

    prod_service = ProductService(session)
    product = await prod_service.create_product(
        actor=user,
        name=data["name"],
        sku=data["sku"],
        category=data["category"],
        retail_price=data["retail_price"],
        wholesale_price=data["wholesale_price"],
        cost=data["cost"],
        stock_quantity=data["stock"],
        minimum_stock=min_stock,
    )
    await session.commit()

    kb = get_main_menu_keyboard(user.role)
    await message.answer(
        f"✅ <b>Product Created Successfully!</b>\n\n"
        f"• <b>Name:</b> {product.name}\n"
        f"• <b>SKU:</b> <code>{product.sku}</code>\n"
        f"• <b>Category:</b> {product.category}\n"
        f"• <b>Retail Price:</b> {format_currency(product.retail_price)}\n"
        f"• <b>Wholesale:</b> {format_currency(product.wholesale_price)}\n"
        f"• <b>Cost:</b> {format_currency(product.cost)}\n"
        f"• <b>Stock:</b> {product.stock_quantity} (Min: {product.minimum_stock})",
        reply_markup=kb,
        parse_mode="HTML",
    )


# ---------------- Product Search ---------------- #

@router.callback_query(F.data == "prod:search")
async def cb_search_product_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SearchStates.waiting_for_query)
    await callback.message.answer(
        "🔍 Enter product name or SKU to search:",
        reply_markup=get_cancel_keyboard(),
    )
    await callback.answer()


@router.message(SearchStates.waiting_for_query)
async def process_prod_search(message: Message, state: FSMContext, session: AsyncSession, user: User) -> None:
    q = (message.text or "").strip()
    await state.clear()

    prod_service = ProductService(session)
    results = await prod_service.search_products(q)

    kb = get_main_menu_keyboard(user.role)
    if not results:
        await message.answer(f"🔍 No products matching '<b>{q}</b>' found.", reply_markup=kb, parse_mode="HTML")
        return

    lines = [f"🔍 <b>Search results for '{q}':</b>\n"]
    for p in results:
        lines.append(
            f"• <b>{p.name}</b> (<code>{p.sku}</code>)\n"
            f"  Stock: {p.stock_quantity} | Price: {format_currency(p.retail_price)}"
        )

    await message.answer("\n".join(lines), reply_markup=kb, parse_mode="HTML")
