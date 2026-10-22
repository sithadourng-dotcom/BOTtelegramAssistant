"""Task delegation and tracking handlers."""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.task import TaskPriority, TaskStatus
from app.database.models.user import User, UserRole
from app.services.tasks import TaskService
from app.services.users import UserService, has_permission
from app.bot.states.bot_states import TaskStates
from app.bot.keyboards.main_menu import get_cancel_keyboard, get_main_menu_keyboard
from app.bot.keyboards.inline_helpers import get_tasks_menu_keyboard

router = Router(name="tasks_router")


@router.message(Command("tasks"))
@router.message(F.text == "✅ Tasks")
async def show_tasks_menu(message: Message, user: User) -> None:
    await message.answer(
        "✅ <b>Task & Action Management</b>\n\n"
        "Assign tasks to team members, track deadlines, or update completion status:",
        reply_markup=get_tasks_menu_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "task:my_tasks")
async def cb_my_tasks(callback: CallbackQuery, session: AsyncSession, user: User) -> None:
    task_service = TaskService(session)
    tasks = await task_service.list_tasks(assigned_to=user.id, status=TaskStatus.TODO)

    if not tasks:
        await callback.message.edit_text(
            "✅ You have no pending tasks! Everything is completed.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="tasks_menu")]]
            ),
        )
        await callback.answer()
        return

    buttons = []
    lines = ["📋 <b>My Open Tasks:</b>\n"]
    for t in tasks:
        p_badge = TaskPriority.get_badge(t.priority)
        lines.append(f"• <b>{t.title}</b> ({p_badge})\n  Status: {t.status.value}")
        buttons.append([
            InlineKeyboardButton(text=f"✅ Complete #{t.id}", callback_data=f"task_done:{t.id}"),
            InlineKeyboardButton(text=f"🔄 In Progress", callback_data=f"task_prog:{t.id}"),
        ])

    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="tasks_menu")])
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "task:overdue")
async def cb_overdue_tasks(callback: CallbackQuery, session: AsyncSession, user: User) -> None:
    task_service = TaskService(session)
    tasks = await task_service.get_overdue_tasks()

    if not tasks:
        await callback.message.edit_text(
            "✅ No overdue tasks found!",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="tasks_menu")]]
            ),
        )
        await callback.answer()
        return

    lines = ["🚨 <b>OVERDUE TASKS:</b>\n"]
    for t in tasks:
        assignee_name = t.assignee.full_name if t.assignee else "Unassigned"
        due_str = t.due_date.strftime("%Y-%m-%d %H:%M") if t.due_date else "N/A"
        lines.append(f"• <b>{t.title}</b>\n  Assignee: {assignee_name} | Due: <b>{due_str}</b>\n")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="tasks_menu")]]
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("task_done:"))
async def cb_task_done(callback: CallbackQuery, session: AsyncSession, user: User) -> None:
    task_id = int(callback.data.split(":")[1])
    task_service = TaskService(session)
    try:
        await task_service.update_task_status(actor=user, task_id=task_id, status=TaskStatus.COMPLETED)
        await session.commit()
    except Exception as e:
        await callback.answer(str(e), show_alert=True)
        return

    await callback.answer("Task marked as COMPLETED! 🎉")
    await cb_my_tasks(callback, session, user)


@router.callback_query(F.data.startswith("task_prog:"))
async def cb_task_prog(callback: CallbackQuery, session: AsyncSession, user: User) -> None:
    task_id = int(callback.data.split(":")[1])
    task_service = TaskService(session)
    try:
        await task_service.update_task_status(actor=user, task_id=task_id, status=TaskStatus.IN_PROGRESS)
        await session.commit()
    except Exception as e:
        await callback.answer(str(e), show_alert=True)
        return

    await callback.answer("Task set to IN PROGRESS 🔄")
    await cb_my_tasks(callback, session, user)


@router.callback_query(F.data == "tasks_menu")
async def cb_tasks_menu(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "✅ <b>Task & Action Management</b>\n\nSelect an option:",
        reply_markup=get_tasks_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


# ---------------- Interactive Task Creation Flow ---------------- #

@router.callback_query(F.data == "task:create")
async def cb_create_task_start(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    await state.set_state(TaskStates.waiting_for_title)
    await callback.message.answer(
        "➕ <b>Create New Task</b>\n\nEnter task title (e.g. 'Follow up with wholesale client'):",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(TaskStates.waiting_for_title)
async def task_step_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if len(title) < 3:
        await message.answer("Please enter a descriptive task title (at least 3 characters):")
        return
    await state.update_data(title=title)
    await state.set_state(TaskStates.waiting_for_description)
    await message.answer(
        "Enter additional details or instructions (or enter 'none'):",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(TaskStates.waiting_for_description)
async def task_step_desc(message: Message, state: FSMContext) -> None:
    desc = (message.text or "").strip()
    if desc.lower() == "none":
        desc = None
    await state.update_data(description=desc)
    await state.set_state(TaskStates.waiting_for_priority)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔴 High", callback_data="pri:HIGH"),
                InlineKeyboardButton(text="🟡 Medium", callback_data="pri:MEDIUM"),
                InlineKeyboardButton(text="🟢 Low", callback_data="pri:LOW"),
            ]
        ]
    )
    await message.answer("Select Task Priority:", reply_markup=kb)


@router.callback_query(F.data.startswith("pri:"))
async def cb_task_priority(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    pri_str = callback.data.split(":")[1]
    priority = TaskPriority(pri_str)
    data = await state.get_data()
    await state.clear()

    task_service = TaskService(session)
    task = await task_service.create_task(
        creator=user,
        title=data["title"],
        description=data.get("description"),
        assigned_to=user.id,
        priority=priority,
    )
    await session.commit()

    kb = get_main_menu_keyboard(user.role)
    await callback.message.answer(
        f"✅ <b>Task Created Successfully!</b>\n\n"
        f"📌 <b>Title:</b> {task.title}\n"
        f"⚡ <b>Priority:</b> {TaskPriority.get_badge(task.priority)}\n"
        f"👤 <b>Assigned To:</b> {user.full_name}\n"
        f"Status: 📝 To Do",
        reply_markup=kb,
        parse_mode="HTML",
    )
    await callback.answer()
