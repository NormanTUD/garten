import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.auth.schemas import UserCreate, UserUpdate
from app.auth.utils import hash_password, verify_password

logger = logging.getLogger("gartenapp.auth")


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_all_users(db: AsyncSession) -> list[User]:
    result = await db.execute(select(User).order_by(User.created_at))
    return list(result.scalars().all())


async def create_user(db: AsyncSession, data: UserCreate) -> User:
    user = User(
        username=data.username,
        password_hash=hash_password(data.password),
        display_name=data.display_name,
        role=data.role,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    logger.info("User created: %s (role=%s)", user.username, user.role)
    return user


async def update_user(db: AsyncSession, user: User, data: UserUpdate) -> User:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    await db.flush()
    await db.refresh(user)
    logger.info("User updated: %s", user.username)
    return user


async def change_password(db: AsyncSession, user: User, new_password: str) -> None:
    user.password_hash = hash_password(new_password)
    await db.flush()
    logger.info("Password changed for user: %s", user.username)


async def authenticate_user(db: AsyncSession, username: str, password: str) -> User | None:
    user = await get_user_by_username(db, username)
    if user is None:
        return None
    if not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


async def get_user_count(db: AsyncSession) -> int:
    result = await db.execute(select(User))
    return len(result.scalars().all())


async def ensure_admin_exists(db: AsyncSession, username: str, password: str) -> None:
    """Create the first admin user if no users exist at all."""
    count = await get_user_count(db)
    if count > 0:
        return

    admin_data = UserCreate(
        username=username,
        password=password,
        display_name="Administrator",
        role="admin",
    )
    await create_user(db, admin_data)
    await db.commit()
    logger.info("Initial admin user '%s' created", username)
