from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session

# Reusable dependency type for database sessions
DBSession = Annotated[AsyncSession, Depends(get_async_session)]
