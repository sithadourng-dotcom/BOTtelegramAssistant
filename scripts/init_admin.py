import argparse
import asyncio
import sys
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.database.database import get_db_context
from app.database.models.user import UserRole, UserStatus
from app.database.repositories.user_repo import UserRepository


async def init_admin(telegram_id: int, full_name: str, username: str = None) -> None:
    async with get_db_context() as session:
        repo = UserRepository(session)
        user = await repo.get_by_telegram_id(telegram_id)
        if user:
            user.role = UserRole.OWNER
            user.status = UserStatus.APPROVED
            if username:
                user.username = username.lstrip("@")
            print(f"Updated existing user '{user.full_name}' (ID: {user.id}) to OWNER.")
        else:
            user = await repo.create_user(
                telegram_id=telegram_id,
                full_name=full_name,
                username=username,
                role=UserRole.OWNER,
                status=UserStatus.APPROVED,
            )
            print(f"Created new OWNER '{user.full_name}' (ID: {user.id}, TG: {user.telegram_id}).")


def main() -> None:
    parser = argparse.ArgumentParser(description="Promote or create an OWNER user by Telegram ID.")
    parser.add_argument("--telegram-id", type=int, required=True, help="Telegram user ID")
    parser.add_argument("--name", type=str, default="Business Owner", help="Full name")
    parser.add_argument("--username", type=str, default=None, help="Telegram username (without @)")
    args = parser.parse_args()

    asyncio.run(init_admin(args.telegram_id, args.name, args.username))


if __name__ == "__main__":
    main()
