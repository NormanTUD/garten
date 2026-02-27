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
    existing = await service.get_user_by_username(db, data.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )
    return await service.create_user(db, data)


@user_router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: int, admin: AdminUser, db: DBSession):
    user = await service.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@user_router.patch("/{user_id}", response_model=UserRead)
async def update_user(user_id: int, data: UserUpdate, admin: AdminUser, db: DBSession):
    user = await service.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return await service.update_user(db, user, data)


@user_router.put("/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
async def admin_reset_password(
    user_id: int, data: AdminPasswordReset, admin: AdminUser, db: DBSession
):
    user = await service.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await service.change_password(db, user, data.new_password)

