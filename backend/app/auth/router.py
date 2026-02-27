from fastapi import APIRouter, HTTPException, status

from app.auth import service
from app.auth.schemas import (
    AccessTokenResponse,
    AdminPasswordReset,
    LoginRequest,
    PasswordChange,
    RefreshRequest,
    TokenResponse,
    UserCreate,
    UserRead,
    UserUpdate,
)
from app.auth.utils import (
    TOKEN_TYPE_REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.dependencies import AdminUser, CurrentUser, DBSession

router = APIRouter(prefix="/api/auth", tags=["auth"])
user_router = APIRouter(prefix="/api/users", tags=["users"])


# ─── Auth Endpoints ──────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: DBSession):
    user = await service.authenticate_user(db, data.username, data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_token(data: RefreshRequest, db: DBSession):
    payload = decode_token(data.refresh_token)
    if payload is None or payload.get("type") != TOKEN_TYPE_REFRESH:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user_id = int(payload["sub"])
    user = await service.get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return AccessTokenResponse(
        access_token=create_access_token(user.id, user.role),
    )


@router.get("/me", response_model=UserRead)
async def get_current_user_info(current_user: CurrentUser):
    return current_user


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_own_password(data: PasswordChange, current_user: CurrentUser, db: DBSession):
    if not service.verify_password_for_user(current_user, data.current_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    await service.change_password(db, current_user, data.new_password)


# ─── User Management (Admin only) ────────────────────────────────

@user_router.get("/", response_model=list[UserRead])
async def list_users(admin: AdminUser, db: DBSession):
    return await service.get_all_users(db)


@user_router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(data: UserCreate, admin: AdminUser, db: DBSession):
    """Admin creates a new user."""
    existing = await get_user_by_username(db, data.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{data.username}' already exists",
        )
    user = await create_user_in_db(db, data)
    return user

@user_router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: int, admin: AdminUser, db: DBSession):
    user = await service.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@user_router.patch("/{user_id}", response_model=UserRead)
async def update_user(user_id: int, data: UserUpdate, admin: AdminUser, db: DBSession):
    """Admin updates a user. Cannot deactivate admins or self."""
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Prevent deactivating yourself
    if data.is_active is False and user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot deactivate yourself",
        )

    # Prevent deactivating other admins
    if data.is_active is False and user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin accounts cannot be deactivated",
        )

    for field, value in data.model_dump(exclude_unset=True).items():
        if field == "password" and value is not None:
            from app.auth.security import hash_password
            setattr(user, "password_hash", hash_password(value))
        elif field != "password":
            setattr(user, field, value)

    await db.flush()
    await db.refresh(user)
    return user

@user_router.put("/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
async def admin_reset_password(
    user_id: int, data: AdminPasswordReset, admin: AdminUser, db: DBSession
):
    user = await service.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await service.change_password(db, user, data.new_password)

