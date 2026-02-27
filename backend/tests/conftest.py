from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.schemas import UserCreate
from app.auth.service import create_user
from app.auth.utils import create_access_token
from app.database import Base, get_async_session
from app.main import create_app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

test_session_factory = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(autouse=True)
async def setup_database():
    """Create all tables before each test, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async test client with overridden DB dependency."""
    app = create_app()
    app.dependency_overrides[get_async_session] = override_get_async_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def admin_user():
    """Create an admin user in the test DB and return (user, token)."""
    async with test_session_factory() as session:
        user = await create_user(
            session,
            UserCreate(
                username="testadmin",
                password="admin123",
                display_name="Test Admin",
                role="admin",
            ),
        )
        await session.commit()
        token = create_access_token(user.id, user.role)
        return user, token


@pytest.fixture
async def normal_user():
    """Create a normal user in the test DB and return (user, token)."""
    async with test_session_factory() as session:
        user = await create_user(
            session,
            UserCreate(
                username="testuser",
                password="user1234",
                display_name="Test User",
                role="user",
            ),
        )
        await session.commit()
        token = create_access_token(user.id, user.role)
        return user, token


def auth_header(token: str) -> dict[str, str]:
    """Helper to create Authorization header."""
    return {"Authorization": f"Bearer {token}"}

