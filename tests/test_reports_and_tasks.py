"""Unit tests for daily report submission and task management."""

from datetime import datetime, timedelta
from decimal import Decimal
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.task import TaskPriority, TaskStatus
from app.database.models.user import User
from app.services.reports import ReportService
from app.services.tasks import TaskService
from app.utils.tz import today_tz


@pytest.mark.asyncio
async def test_daily_report_submission(db_session: AsyncSession, seller_user: User):
    report_service = ReportService(db_session)
    report = await report_service.submit_daily_report(
        actor=seller_user,
        sales_amount=Decimal("350.00"),
        orders_count=7,
        new_customers_count=3,
        videos_posted=2,
        messages_answered=15,
        followups_count=5,
        problems_faced="Stock ran low on tea",
        tomorrow_goal="Reach $500 in sales",
    )

    assert report.id is not None
    assert report.sales_amount == Decimal("350.00")
    assert report.orders_count == 7
    assert report.user_id == seller_user.id


@pytest.mark.asyncio
async def test_missing_daily_report_detection(db_session: AsyncSession, seller_user: User):
    report_service = ReportService(db_session)

    # Before submitting, seller_user is in missing list
    missing_before = await report_service.get_missing_reports(today_tz())
    assert any(u.id == seller_user.id for u in missing_before)

    # Submit report
    await report_service.submit_daily_report(actor=seller_user, sales_amount=Decimal("10.00"))

    # After submitting, seller_user is no longer missing
    missing_after = await report_service.get_missing_reports(today_tz())
    assert not any(u.id == seller_user.id for u in missing_after)


@pytest.mark.asyncio
async def test_task_creation_and_completion(db_session: AsyncSession, admin_user: User, seller_user: User):
    task_service = TaskService(db_session)

    # Admin creates task assigned to seller
    task = await task_service.create_task(
        creator=admin_user,
        title="Contact Supplier for Bottles",
        description="Negotiate wholesale bulk discount",
        assigned_to=seller_user.id,
        priority=TaskPriority.HIGH,
    )
    assert task.status == TaskStatus.TODO
    assert task.assigned_to == seller_user.id

    # Seller completes task
    updated = await task_service.update_task_status(actor=seller_user, task_id=task.id, status=TaskStatus.COMPLETED)
    assert updated.status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_overdue_task_detection(db_session: AsyncSession, admin_user: User, seller_user: User):
    task_service = TaskService(db_session)

    # Past due task
    past_time = datetime.now() - timedelta(days=2)
    task = await task_service.create_task(
        creator=admin_user,
        title="Old Follow-up",
        assigned_to=seller_user.id,
        due_date=past_time,
    )

    overdue_list = await task_service.get_overdue_tasks()
    assert any(t.id == task.id for t in overdue_list)
