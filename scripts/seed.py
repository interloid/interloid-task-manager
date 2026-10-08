import asyncio
from datetime import date

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.enums import RoleName
from app.enums.task import TaskPriority, TaskStatus
from app.models.refresh_token import RefreshToken  # noqa: F401
from app.models.task import Task
from app.models.user import User
from scripts.seed_data import ADMIN, TASKS, USERS


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        users_by_email: dict[str, User] = {}

        # Create admin
        result = await session.execute(select(User).where(User.email == ADMIN["email"]))
        admin = result.scalar_one_or_none()

        if admin is None:
            admin = User(
                first_name=ADMIN["first_name"],
                last_name=ADMIN["last_name"],
                email=ADMIN["email"],
                password_hash=hash_password(ADMIN["password"]),
                role=RoleName.ADMIN,
                is_active=True,
                is_verified=True,
            )

            session.add(admin)
            await session.flush()

        users_by_email[ADMIN["email"]] = admin

        # Create normal users
        for user_data in USERS:
            result = await session.execute(
                select(User).where(User.email == user_data["email"])
            )

            user = result.scalar_one_or_none()

            if user is None:
                user = User(
                    first_name=user_data["first_name"],
                    last_name=user_data["last_name"],
                    email=user_data["email"],
                    password_hash=hash_password(user_data["password"]),
                    role=RoleName.USER,
                    is_active=True,
                    is_verified=True,
                )

                session.add(user)
                await session.flush()

            users_by_email[user_data["email"]] = user

        # Create tasks
        for (
            owner_email,
            title,
            description,
            status_value,
            priority_value,
            due_date_value,
        ) in TASKS:
            owner = users_by_email[owner_email]

            result = await session.execute(
                select(Task).where(
                    Task.owner_id == owner.id,
                    Task.title == title,
                )
            )

            existing_task = result.scalar_one_or_none()

            if existing_task is not None:
                continue

            task = Task(
                owner_id=owner.id,
                title=title,
                description=description,
                status=TaskStatus(status_value),
                priority=TaskPriority(priority_value),
                due_date=date.fromisoformat(due_date_value),
            )

            session.add(task)

        await session.commit()

        print("Seed completed successfully")


if __name__ == "__main__":
    asyncio.run(seed())
