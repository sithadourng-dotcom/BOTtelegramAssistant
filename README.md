# 🤖 Telegram Business Assistant Bot

A production-ready **Business Operating System** managed entirely through Telegram. Built with Python 3.12, **FastAPI**, **aiogram 3.x**, **PostgreSQL / SQLite**, **SQLAlchemy 2.0 (async)**, **Alembic**, **APScheduler**, and **OpenAI**.

---

## 🌟 Key Highlights & Features

- 👑 **Role-Based Access Control (RBAC):**
  - **Owner**: Full access, settings configuration, role assignment.
  - **Admin**: Catalog, approvals, user management, broadcast alerts.
  - **Manager**: Team oversight, order fulfillment, report audits.
  - **Leader**: Subordinate management & team coaching.
  - **Seller**: Order placement, customer CRM, sale tracking, daily reports.
  - **Promoter**: Content creation & marketing activity reports.
  - **Viewer**: Read-only reporting access.
- 👤 **Onboarding & Approval Flow:**
  - Automated detection of Telegram user ID.
  - Multi-step registration for new users (Name, Phone, Role).
  - Instant Telegram notification sent to Owner/Admin with inline `✅ Approve`, `❌ Reject`, and `👤 Assign Role` actions.
- 📊 **Real-Time Live Dashboard:**
  - Real database aggregation (no mockups, zero fake metrics).
  - Timeframe toggling: **Today**, **Yesterday**, **This Week**, **This Month**.
  - Track Sales Revenue, Orders, Active Sellers, Content Posted, Reports Submitted, Growth %, and Top Selling Products.
- 📦 **Product & Inventory Management:**
  - Complete SKU tracking with Retail Price, Wholesale Price, and Cost Price.
  - Real-time stock decrement upon order creation or quick sales.
  - Automatic **Low Stock Notifications** sent immediately when items drop below threshold.
- 🛒 **Order Management System:**
  - Server-side recalculation of subtotal, discounts, shipping, and grand total. Never trusts client totals.
  - Lifecycle states: `📝 Pending` ➔ `💵 Paid` ➔ `📦 Processing` ➔ `🚚 Shipping` ➔ `✅ Completed` / `❌ Cancelled`.
  - Automatic inventory restocking if order is cancelled.
- 👥 **Customer CRM:**
  - Phone-based deduplication and profile tracking.
  - Lifetime order counts, total spent, and repeat customer detection.
- 💰 **Sales Tracking & Gross Profit:**
  - Record quick direct sales with instantaneous calculation of **Revenue**, **Cost**, and **Gross Profit**.
  - Team leaderboards and monthly seller performance rankings.
- 📝 **Daily Report Workflow:**
  - Standardized 8-point daily reports: Sales, Orders, New Customers, Content/Videos, Replies, Follow-ups, Obstacles, Tomorrow's Goal.
  - Automated daily reminder alert at 18:00 to team members who haven't submitted their report yet.
- ⏰ **Background Job Scheduler (APScheduler):**
  - Daily Morning Motivation & Priorities (08:00).
  - Daily Report Reminder (18:00).
  - Periodic Low Stock Inventory Monitor (Every 4h).
- 🤖 **AI Business Assistant (OpenAI Function Calling):**
  - Natural language querying powered by OpenAI Tool Calling.
  - **Zero hallucinated numbers:** All metrics are fetched via safe, controlled internal application services (`get_sales_summary`, `get_team_rankings`, `get_low_stock_products`, `get_pending_orders_count`, `create_reminder_task`).
  - No arbitrary SQL generation. Safe rule-based fallback when no OpenAI key is configured.
- 📥 **Executive Report Exports:**
  - 1-click export of structured **CSV** and multi-sheet **Excel (.xlsx)** workbooks directly in Telegram chat.
- 📜 **Audit Trail:**
  - Every price change, user approval, order status update, and role assignment is logged with actor, old value, and new value.

---

## 📁 Project Structure

```text
2026 Telegram Bot of TSA/
├── app/
│   ├── main.py                     # FastAPI application, webhook listener & bot lifespan
│   ├── config.py                   # Pydantic BaseSettings loaded from .env
│   │
│   ├── bot/                        # Telegram Bot Layer (aiogram 3.x)
│   │   ├── handlers/               # Modular command & message routers
│   │   │   ├── start.py            # /start, onboarding, admin approvals
│   │   │   ├── dashboard.py        # /dashboard, metrics render & export
│   │   │   ├── products.py         # /products, catalog CRUD & search
│   │   │   ├── orders.py           # /orders, order creation & status flow
│   │   │   ├── sales.py            # /sales, quick sale & profit tracking
│   │   │   ├── reports.py          # /reports, daily reports & reminders
│   │   │   ├── tasks.py            # /tasks, task delegation & completion
│   │   │   ├── team.py             # /team, member directory & roles
│   │   │   ├── notifications.py    # /broadcast, announcements
│   │   │   ├── search.py           # /search [term], global search
│   │   │   ├── settings.py         # /settings, timezone & preferences
│   │   │   ├── admin.py            # /admin, audit logs & console
│   │   │   └── ai_assistant.py     # Natural language conversational handler
│   │   ├── keyboards/              # Reply & Inline keyboards
│   │   │   ├── main_menu.py        # Primary reply menu layout
│   │   │   └── inline_helpers.py   # Contextual inline button builders
│   │   ├── middlewares/            # Session, Auth, and Rate-limiting
│   │   │   ├── auth.py             # User authentication & DB session injection
│   │   │   └── rate_limit.py       # Anti-spam rate limiter
│   │   └── states/                 # aiogram FSM States
│   │       └── bot_states.py       # Multi-step conversational flows
│   │
│   ├── database/                   # Database Layer (SQLAlchemy 2.0 Async)
│   │   ├── database.py             # Async engine, sessionmaker & pool
│   │   ├── models/                 # Relational database models
│   │   │   ├── base.py             # DeclarativeBase & TimestampMixin
│   │   │   ├── user.py             # User account, Role & Status enums
│   │   │   ├── product.py          # Product catalog & stock
│   │   │   ├── customer.py         # Customer CRM & repeat tracking
│   │   │   ├── order.py            # Orders & line items
│   │   │   ├── sale.py             # Individual sale transaction & profit
│   │   │   ├── daily_report.py     # Daily operational reports
│   │   │   ├── activity.py         # Marketing & promotional activities
│   │   │   ├── task.py             # Task assignment & deadlines
│   │   │   ├── notification.py     # System notifications & broadcasts
│   │   │   ├── audit_log.py        # Immutable audit trail
│   │   │   └── setting.py          # Dynamic system configuration
│   │   ├── repositories/           # Repository pattern data access
│   │   └── migrations/             # Alembic database migrations
│   │
│   ├── services/                   # Business Logic Layer
│   │   ├── users.py                # Onboarding, approvals & permission matrix
│   │   ├── products.py             # Product inventory & stock validation
│   │   ├── customers.py            # CRM profiles & order statistics
│   │   ├── orders.py               # Server-side calculation & stock consistency
│   │   ├── sales.py                # Sales analytics & ranking
│   │   ├── reports.py              # Operational report aggregation
│   │   ├── activities.py           # Promotional content metrics
│   │   ├── tasks.py                # Task lifecycle & overdue scanning
│   │   ├── notifications.py        # Alert delivery & broadcast engine
│   │   ├── dashboard.py            # Live dashboard metric aggregation
│   │   ├── search.py               # Multi-entity global search
│   │   ├── export.py               # CSV & Excel report generators
│   │   └── ai_assistant.py         # OpenAI Tool Calling & safe query dispatch
│   │
│   ├── scheduler/                  # Background Scheduling (APScheduler)
│   │   └── jobs.py                 # Morning priorities, report alerts, stock scans
│   └── utils/                      # Utilities
│       ├── logger.py               # Token-sanitizing logging setup
│       ├── tz.py                   # Timezone localization (Asia/Phnom_Penh)
│       └── formatters.py           # Currency and number formatting
│
├── tests/                          # Automated Pytest Suite (21 tests)
│   ├── conftest.py                 # In-memory async SQLite fixtures
│   ├── test_users.py               # Registration, approval & RBAC tests
│   ├── test_products.py            # SKU uniqueness, prices & low stock tests
│   ├── test_orders_and_sales.py    # Math calculation & inventory stock tests
│   ├── test_reports_and_tasks.py   # Daily reports & task deadline tests
│   ├── test_dashboard_and_ai.py    # Dashboard stats & AI query router tests
│   ├── test_search_and_export.py   # Global search & CSV/Excel export tests
│   └── test_fastapi.py             # FastAPI /health endpoint test
│
├── scripts/                        # Management CLI Scripts
│   ├── init_admin.py               # Direct owner/admin promotion script
│   └── seed_demo_data.py           # Pre-populate catalog, sales & tasks
│
├── .env.example                    # Environment template
├── requirements.txt                # Production dependencies
├── Dockerfile                      # Production container image
├── docker-compose.yml              # Multi-container orchestration (Bot + PG + Redis)
├── alembic.ini                     # Migration configuration
└── pytest.ini                      # Test runner configuration
```

---

## 🚀 Step-by-Step Setup & Deployment Guide

### 1. Create a Telegram Bot using BotFather
1. Open Telegram and search for `@BotFather`.
2. Send `/newbot`.
3. Enter your bot's display name (e.g. `TSA Business Assistant`).
4. Enter a unique username ending with `bot` (e.g. `tsa_business_assistant_bot`).
5. Copy the **HTTP API Bot Token** provided (looks like `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`).

### 2. Obtain your Telegram User ID
1. Search for `@userinfobot` on Telegram.
2. Send `/start`.
3. Note your numeric **Id** (e.g. `1234567890`).

### 3. Configure `.env`
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` and fill in your values:
```env
BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
ADMIN_TELEGRAM_ID=1234567890
DATABASE_URL=sqlite+aiosqlite:///./bot_database.db
TIMEZONE=Asia/Phnom_Penh
CURRENCY_SYMBOL=$
OPENAI_API_KEY=sk-...
```

### 4. Local Installation & Running Migrations
Create and activate virtual environment:
```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```
Install dependencies:
```bash
pip install -r requirements.txt
```
Run database migrations:
```bash
alembic upgrade head
```

### 5. Seed Demo Data (Optional but Recommended)
To immediately populate sample products, customers, and test sales:
```bash
python scripts/seed_demo_data.py
```

### 6. Start the Bot Locally
```bash
python -m app.main
```
Open Telegram, find your bot, and send `/start`.

### 7. Run Automated Tests
```bash
pytest -v
```
All 21 unit and integration tests run in memory and execute in ~2 seconds.

---

## 🐳 Docker & VPS Deployment

### Deploy with Docker Compose (PostgreSQL + Redis + Bot)
1. Clone repository to your VPS:
```bash
git clone <your-repo-url> /opt/tsa_business_bot
cd /opt/tsa_business_bot
```
2. Create `.env`:
```bash
cp .env.example .env
nano .env
```
3. Launch services:
```bash
docker compose up -d --build
```
4. Verify running containers:
```bash
docker compose ps
```
5. View logs:
```bash
docker compose logs -f bot
```
6. Restart services:
```bash
docker compose restart bot
```

---

## 🤖 Telegram Bot Commands

| Command | Allowed Roles | Description |
|---|---|---|
| `/start` | Everyone | Initialize bot, register, or open main menu |
| `/help` | Everyone | Detailed user and command documentation |
| `/dashboard` | Viewer+ | View real-time business metrics & growth |
| `/products` | Viewer+ | Browse catalog, check low stock, add items |
| `/orders` | Seller+ | Create new customer orders & update status |
| `/sales` | Seller+ | Record quick sales & review profit numbers |
| `/reports` | Seller+ | Submit daily 8-point operational report |
| `/tasks` | Seller+ | Assign, monitor, and complete team tasks |
| `/team` | Seller+ | Team directory, approvals & role assignments |
| `/search [term]` | Viewer+ | Search across Products, Customers, Orders, Tasks |
| `/settings` | Everyone | View timezone, reminders, and regional settings |
| `/admin` | Admin / Owner | System console, pending queues, audit logs |
| `/broadcast` | Manager+ | Broadcast announcements to selected roles |

---

## 👥 Role Permissions Matrix

| Feature | Owner | Admin | Manager | Leader | Seller | Promoter | Viewer |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| System Settings | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Approve / Reject Users | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Add / Edit Products | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Manage All Orders | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Broadcast Announcements| ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Assign Tasks to Team | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Create Orders & Sales | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Submit Daily Reports | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| View Dashboard & Stats | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## 💬 Natural Language AI Queries Supported

The bot translates conversational English into safe, database-backed queries:

- *"How much did we sell today?"* ➔ Instant revenue, profit, units, and orders breakdown.
- *"How much did we sell this week?"* ➔ Weekly sales aggregation.
- *"Who has the highest sales this month?"* ➔ Real seller leaderboard.
- *"How many orders are pending?"* ➔ Real-time pending fulfillment count.
- *"Show low stock products"* ➔ Products below minimum inventory.
- *"Who hasn't submitted today's report?"* ➔ List of team members missing reports.
- *"Remind me tomorrow at 9 AM to contact the supplier"* ➔ Automatically creates assigned task.

---

## 🔒 Security Best Practices

1. **No Hardcoded Secrets:** All credentials, tokens, and secrets are strictly retrieved from environment variables via Pydantic Settings.
2. **Parameterized Queries:** Every database interaction goes through SQLAlchemy 2.0 ORM expressions, preventing SQL injection.
3. **Server-Side Calculations:** Order totals, subtotal, discount, and inventory adjustments are strictly calculated server-side; client inputs are validated.
4. **Rate Limiting:** Sliding-window rate limiter prevents message flooding and API quota exhaustion.
5. **Sanitizing Logger:** Automatically scrubs Telegram Bot Tokens and OpenAI API keys from terminal logs.
6. **No Raw SQL from AI:** OpenAI function calling routes only to safe, pre-defined python services.

---

## 🔧 Future Extension Points

The clean service-repository architecture allows adding future business modules effortlessly:
- **Affiliate & Commission Engine:** Hook into `SaleService.record_sale` to calculate tier percentages.
- **TikTok & Facebook Pixel Webhooks:** Connect incoming ad conversions to `ActivityService`.
- **Payment Gateway Integration:** Plug Stripe, ABA PayWay, or Bakong KHQR into `OrderService.update_payment_status`.
- **Multi-Branch Inventory:** Extend `Product` model with `warehouse_id`.
