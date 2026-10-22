"""Notification delivery and alert broadcast service."""

from typing import List, Optional
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.product import Product
from app.database.models.task import Task
from app.database.models.user import User, UserRole, UserStatus
from app.database.repositories.notification_repo import NotificationRepository
from app.database.repositories.user_repo import UserRepository
from app.utils.logger import logger


class NotificationService:
    """Service handling multi-channel Telegram alerts and broadcasts."""

    def __init__(self, session: AsyncSession, bot: Bot):
        self.session = session
        self.bot = bot
        self.notif_repo = NotificationRepository(session)
        self.user_repo = UserRepository(session)

    async def send_to_user(self, user: User, message: str, title: str = "Alert") -> bool:
        """Send message directly to user Telegram chat."""
        try:
            await self.bot.send_message(chat_id=user.telegram_id, text=message, parse_mode="HTML")
            return True
        except Exception as e:
            logger.warning(f"Failed to send message to user {user.telegram_id}: {e}")
            return False

    async def broadcast_announcement(
        self,
        sender: User,
        message: str,
        target_role: Optional[str] = "ALL",
        target_user_id: Optional[int] = None,
    ) -> int:
        """Broadcast text message to filtered audience."""
        recipients: List[User] = []

        if target_user_id:
            target_user = await self.user_repo.get_by_id(target_user_id)
            if target_user and target_user.status == UserStatus.APPROVED:
                recipients = [target_user]
        else:
            all_users = await self.user_repo.get_active_team_members()
            if target_role == "ALL" or not target_role:
                recipients = list(all_users)
            else:
                try:
                    role_enum = UserRole(target_role.upper())
                    recipients = [u for u in all_users if u.role == role_enum]
                except ValueError:
                    recipients = list(all_users)

        success_count = 0
        header = f"📢 <b>ANNOUNCEMENT</b>\n<i>From: {sender.full_name}</i>\n\n"
        full_text = header + message

        for u in recipients:
            if await self.send_to_user(u, full_text):
                success_count += 1

        # Record in database
        await self.notif_repo.create_notification(
            title="Broadcast Announcement",
            message=message,
            notification_type="ANNOUNCEMENT",
            sender_id=sender.id,
            target_role=target_role,
            target_user_id=target_user_id,
        )

        return success_count

    async def notify_low_stock(self, product: Product) -> None:
        """Send urgent low stock alert to all Admins and Owners."""
        admins = await self.user_repo.list_users(role=UserRole.ADMIN, status=UserStatus.APPROVED)
        owners = await self.user_repo.list_users(role=UserRole.OWNER, status=UserStatus.APPROVED)
        recipients = {u.telegram_id: u for u in list(admins) + list(owners)}.values()

        alert_text = (
            f"⚠️ <b>LOW STOCK ALERT</b>\n\n"
            f"📦 <b>Product:</b> {product.name}\n"
            f"🏷️ <b>SKU:</b> <code>{product.sku}</code>\n"
            f"📉 <b>Current Stock:</b> <code>{product.stock_quantity}</code>\n"
            f"🚨 <b>Minimum Required:</b> <code>{product.minimum_stock}</code>\n\n"
            f"<i>Please restock inventory as soon as possible.</i>"
        )

        for u in recipients:
            await self.send_to_user(u, alert_text)

    async def notify_new_order(self, order_number: str, seller_name: str, total_amount: str) -> None:
        """Alert managers and admins about a new order."""
        managers = await self.user_repo.list_users(role=UserRole.MANAGER, status=UserStatus.APPROVED)
        admins = await self.user_repo.list_users(role=UserRole.ADMIN, status=UserStatus.APPROVED)
        owners = await self.user_repo.list_users(role=UserRole.OWNER, status=UserStatus.APPROVED)
        recipients = {u.telegram_id: u for u in list(managers) + list(admins) + list(owners)}.values()

        alert_text = (
            f"🛒 <b>NEW ORDER CREATED</b>\n\n"
            f"🔢 <b>Order:</b> <code>{order_number}</code>\n"
            f"👤 <b>Seller:</b> {seller_name}\n"
            f"💰 <b>Total:</b> {total_amount}\n\n"
            f"<i>Check the orders dashboard to process shipment.</i>"
        )

        for u in recipients:
            await self.send_to_user(u, alert_text)

    async def send_morning_reminder(self) -> int:
        """Deliver daily morning priorities to active team members."""
        users = await self.user_repo.get_active_team_members()
        text = (
            f"☀️ <b>GOOD MORNING TEAM!</b>\n\n"
            f"Here are today's core priorities:\n"
            f"1. 📞 Follow up with existing customers & prospects\n"
            f"2. 📱 Post your daily promotional content (TikTok/FB/Live)\n"
            f"3. 💰 Record all sales & customer inquiries promptly\n"
            f"4. ✅ Check and complete your assigned tasks\n\n"
            f"<i>Let's make today productive and successful!</i>"
        )
        count = 0
        for u in users:
            if await self.send_to_user(u, text):
                count += 1
        return count

    async def send_report_reminder(self, missing_users: List[User]) -> int:
        """Remind users who haven't submitted their daily report."""
        text = (
            f"⏰ <b>DAILY REPORT REMINDER</b>\n\n"
            f"You haven't submitted your daily report yet.\n"
            f"Please take 2 minutes to summarize your sales, activities, and goals for today.\n\n"
            f"👉 <i>Click <b>📝 Daily Report</b> in the main menu to submit now.</i>"
        )
        count = 0
        for u in missing_users:
            if await self.send_to_user(u, text):
                count += 1
        return count
