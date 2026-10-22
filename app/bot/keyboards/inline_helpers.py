"""Inline keyboard builders for business operations and interactive workflows."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.database.models.user import UserRole
from app.database.models.order import OrderStatus


def get_approval_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Buttons sent to admin when a new user registers."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_user:{user_id}"),
                InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_user:{user_id}"),
            ],
            [
                InlineKeyboardButton(text="👤 Assign Role", callback_data=f"role_menu:{user_id}"),
            ],
        ]
    )


def get_role_selection_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Role selection buttons."""
    roles = [
        ("Admin", UserRole.ADMIN),
        ("Manager", UserRole.MANAGER),
        ("Leader", UserRole.LEADER),
        ("Seller", UserRole.SELLER),
        ("Promoter", UserRole.PROMOTER),
        ("Viewer", UserRole.VIEWER),
    ]
    rows = []
    current_row = []
    for label, r in roles:
        current_row.append(InlineKeyboardButton(text=label, callback_data=f"set_role:{user_id}:{r.value}"))
        if len(current_row) == 2:
            rows.append(current_row)
            current_row = []
    if current_row:
        rows.append(current_row)

    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data=f"view_pending:{user_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_dashboard_keyboard(current_period: str = "today") -> InlineKeyboardMarkup:
    """Period switcher and report exporter buttons for Dashboard."""
    periods = [
        ("Today", "dash:today"),
        ("Yesterday", "dash:yesterday"),
        ("This Week", "dash:this_week"),
        ("This Month", "dash:this_month"),
    ]
    period_row = []
    for label, cb in periods:
        text = f"🔘 {label}" if cb.endswith(current_period) else label
        period_row.append(InlineKeyboardButton(text=text, callback_data=cb))

    return InlineKeyboardMarkup(
        inline_keyboard=[
            period_row[:2],
            period_row[2:],
            [
                InlineKeyboardButton(text="📥 Export CSV", callback_data=f"export:csv:{current_period}"),
                InlineKeyboardButton(text="📊 Export Excel", callback_data=f"export:excel:{current_period}"),
            ],
            [
                InlineKeyboardButton(text="🔄 Refresh", callback_data=f"dash:{current_period}"),
            ],
        ]
    )


def get_products_menu_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Products screen actions."""
    buttons = [
        [
            InlineKeyboardButton(text="📋 View All Products", callback_data="prod:view_all"),
            InlineKeyboardButton(text="🔍 Search Product", callback_data="prod:search"),
        ],
        [
            InlineKeyboardButton(text="⚠️ Low Stock Items", callback_data="prod:low_stock"),
        ],
    ]
    if is_admin:
        buttons.insert(0, [InlineKeyboardButton(text="➕ Add Product", callback_data="prod:add")])
    buttons.append([InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_orders_menu_keyboard() -> InlineKeyboardMarkup:
    """Orders screen actions."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Create Order", callback_data="order:create"),
                InlineKeyboardButton(text="📋 Recent Orders", callback_data="order:list"),
            ],
            [
                InlineKeyboardButton(text="⏳ Pending Orders", callback_data="order:filter:PENDING"),
                InlineKeyboardButton(text="🚚 In Shipping", callback_data="order:filter:SHIPPING"),
            ],
            [
                InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"),
            ],
        ]
    )


def get_order_action_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Status actions on a single order."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💵 Mark Paid", callback_data=f"order_pay:{order_id}"),
                InlineKeyboardButton(text="📦 Processing", callback_data=f"order_status:{order_id}:PROCESSING"),
            ],
            [
                InlineKeyboardButton(text="🚚 Shipping", callback_data=f"order_status:{order_id}:SHIPPING"),
                InlineKeyboardButton(text="✅ Completed", callback_data=f"order_status:{order_id}:COMPLETED"),
            ],
            [
                InlineKeyboardButton(text="❌ Cancel Order", callback_data=f"order_status:{order_id}:CANCELLED"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Back to Orders", callback_data="order:list"),
            ],
        ]
    )


def get_sales_menu_keyboard() -> InlineKeyboardMarkup:
    """Sales tracking actions."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💰 Record Quick Sale", callback_data="sale:record"),
                InlineKeyboardButton(text="📈 My Sales Today", callback_data="sale:my_today"),
            ],
            [
                InlineKeyboardButton(text="🏆 Team Leaderboard", callback_data="sale:leaderboard"),
            ],
            [
                InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"),
            ],
        ]
    )


def get_reports_menu_keyboard() -> InlineKeyboardMarkup:
    """Daily report actions."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📝 Submit Today's Report", callback_data="report:submit"),
                InlineKeyboardButton(text="👀 View My Report", callback_data="report:view_my"),
            ],
            [
                InlineKeyboardButton(text="👥 Team Submissions", callback_data="report:team_list"),
                InlineKeyboardButton(text="⏰ Missing Today", callback_data="report:missing"),
            ],
            [
                InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"),
            ],
        ]
    )


def get_tasks_menu_keyboard() -> InlineKeyboardMarkup:
    """Tasks management actions."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Create Task", callback_data="task:create"),
                InlineKeyboardButton(text="📋 My Tasks", callback_data="task:my_tasks"),
            ],
            [
                InlineKeyboardButton(text="🚨 Overdue Tasks", callback_data="task:overdue"),
                InlineKeyboardButton(text="👥 All Open Tasks", callback_data="task:all_open"),
            ],
            [
                InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"),
            ],
        ]
    )


def get_broadcast_target_keyboard() -> InlineKeyboardMarkup:
    """Audience selector for broadcasts."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📢 Everyone", callback_data="bcast_target:ALL"),
                InlineKeyboardButton(text="👔 Managers", callback_data="bcast_target:MANAGER"),
            ],
            [
                InlineKeyboardButton(text="⭐ Leaders", callback_data="bcast_target:LEADER"),
                InlineKeyboardButton(text="💼 Sellers", callback_data="bcast_target:SELLER"),
            ],
            [
                InlineKeyboardButton(text="📣 Promoters", callback_data="bcast_target:PROMOTER"),
            ],
            [
                InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_action"),
            ],
        ]
    )


def get_settings_menu_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Settings menu options."""
    buttons = [
        [InlineKeyboardButton(text="🌐 Timezone & Currency", callback_data="setting:tz_curr")],
        [InlineKeyboardButton(text="⏰ Reminder Schedule", callback_data="setting:reminders")],
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="🛡️ Admin Panel", callback_data="admin_panel")])
        buttons.append([InlineKeyboardButton(text="⚠️ Low-Stock Threshold", callback_data="setting:stock_thresh")])
    buttons.append([InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
