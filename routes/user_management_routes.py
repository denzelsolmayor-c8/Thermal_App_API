from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete
import hashlib
from typing import Optional, List
import os

from database import Base, get_async_session


router = APIRouter(prefix="", tags=["user-management"])  # no prefix to keep endpoints short


def hash_password_sha256(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def is_sha256_hex(value: str) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
        return True
    except Exception:
        return False


def get_default_password() -> str:
    return os.getenv("DEFAULT_USER_PASSWORD", "helios")


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict
    must_change_password: bool


class ChangePasswordRequest(BaseModel):
    username: str
    current_password: str
    new_password: str = Field(min_length=8)


class CreateUserRequest(BaseModel):
    username: str
    role_id: Optional[int] = None
    role_name: Optional[str] = None
    default_password: Optional[str] = None


class UpdateUserRequest(BaseModel):
    role_id: Optional[int] = None
    role_name: Optional[str] = None


def get_tables():
    Users = Base.classes["usm_user_accounts"]
    Roles = Base.classes["usm_roles"]
    RolePrivs = Base.classes["usm_role_privileges"]
    Privs = Base.classes["usm_privileges"]
    return Users, Roles, RolePrivs, Privs


@router.post("/auth/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_async_session)):
    Users, Roles, _, _ = get_tables()

    q = select(Users).where(Users.username == payload.username)
    res = await db.execute(q)
    user_row = res.scalar_one_or_none()
    if not user_row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    stored_password = user_row.password or ""
    migrated = False
    if is_sha256_hex(stored_password):
        if hash_password_sha256(payload.password) != stored_password:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    else:
        # One-time plaintext migration path
        if payload.password != stored_password:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        # Migrate to SHA-256
        new_hash = hash_password_sha256(payload.password)
        await db.execute(
            update(Users).where(Users.id == user_row.id).values(password=new_hash)
        )
        await db.commit()
        migrated = True
        stored_password = new_hash

    # resolve role name
    role_name = None
    if user_row.role_id is not None:
        r = await db.execute(select(Roles).where(Roles.id == user_row.role_id))
        role = r.scalar_one_or_none()
        role_name = getattr(role, "role_name", None)

    # Determine if they are still using the default password by comparing the stored hash
    default_pwd = (hash_password_sha256(get_default_password()) == stored_password)

    user_dict = {
        "id": user_row.id,
        "username": user_row.username,
        "role_id": user_row.role_id,
        "role": role_name,
    }

    # UI can treat this as a token for now; swap to real JWT later
    return TokenResponse(access_token="token", user=user_dict, must_change_password=bool(default_pwd or migrated))


@router.post("/auth/change-password")
async def change_password(payload: ChangePasswordRequest, db: AsyncSession = Depends(get_async_session)):
    Users, _, _, _ = get_tables()
    res = await db.execute(select(Users).where(Users.username == payload.username))
    user_row = res.scalar_one_or_none()
    if not user_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    stored = user_row.password or ""
    if is_sha256_hex(stored):
        if hash_password_sha256(payload.current_password) != stored:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    else:
        if payload.current_password != stored:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    # NIST guidelines: block extremely common passwords and those containing username
    COMMON = {
        "123456","password","123456789","qwerty","12345678","111111","123123","abc123","password1","1234567",
        "iloveyou","000000","zaq12wsx","dragon","sunshine","letmein","monkey","football","admin","welcome"
    }
    if payload.new_password.lower() in COMMON:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password is too common")
    if payload.username.lower() in payload.new_password.lower():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must not contain username")

    new_hash = hash_password_sha256(payload.new_password)
    await db.execute(
        update(Users)
        .where(Users.id == user_row.id)
        .values(password=new_hash)
    )
    await db.commit()
    return {"status": "ok"}


@router.get("/users")
async def list_users(db: AsyncSession = Depends(get_async_session)):
    Users, Roles, _, _ = get_tables()
    res = await db.execute(select(Users))
    rows = res.scalars().all()
    users = []
    for u in rows:
        role_name = None
        if u.role_id is not None:
            r = await db.execute(select(Roles).where(Roles.id == u.role_id))
            role = r.scalar_one_or_none()
            role_name = getattr(role, "role_name", None)
        users.append({
            "id": u.id,
            "username": u.username,
            "role_id": u.role_id,
            "role": role_name,
            "created_at": getattr(u, "created_at", None),
            "updated_at": getattr(u, "updated_at", None),
        })
    return users


@router.post("/users")
async def create_user(payload: CreateUserRequest, db: AsyncSession = Depends(get_async_session)):
    Users, Roles, _, _ = get_tables()
    if not payload.username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="username is required")

    # Resolve role_id by name if provided
    role_id = payload.role_id
    if role_id is None and payload.role_name:
        r = await db.execute(select(Roles).where(Roles.role_name == payload.role_name))
        role = r.scalar_one_or_none()
        if not role:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="role_name not found")
        role_id = role.id

    default_password = payload.default_password or get_default_password()
    password_hash = hash_password_sha256(default_password)

    await db.execute(
        insert(Users).values(username=payload.username, password=password_hash, role_id=role_id)
    )
    await db.commit()
    return {"status": "ok"}


@router.patch("/users/{user_id}")
async def update_user(user_id: int, payload: UpdateUserRequest, db: AsyncSession = Depends(get_async_session)):
    Users, Roles, _, _ = get_tables()
    # Resolve role
    new_role_id = payload.role_id
    if new_role_id is None and payload.role_name:
        r = await db.execute(select(Roles).where(Roles.role_name == payload.role_name))
        role = r.scalar_one_or_none()
        if not role:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="role_name not found")
        new_role_id = role.id

    if new_role_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nothing to update")

    await db.execute(update(Users).where(Users.id == user_id).values(role_id=new_role_id))
    await db.commit()
    return {"status": "ok"}


@router.delete("/users/{user_id}")
async def delete_user(user_id: int, db: AsyncSession = Depends(get_async_session)):
    Users, _, _, _ = get_tables()
    await db.execute(delete(Users).where(Users.id == user_id))
    await db.commit()
    return {"status": "ok"}


@router.get("/roles")
async def list_roles(db: AsyncSession = Depends(get_async_session)):
    _, Roles, _, _ = get_tables()
    res = await db.execute(select(Roles))
    rows = res.scalars().all()
    return [{"id": r.id, "role_name": r.role_name, "description": getattr(r, "description", None)} for r in rows]


@router.get("/roles/{role_id}/privileges")
async def role_privileges(role_id: int, db: AsyncSession = Depends(get_async_session)):
    _, _, RolePrivs, Privs = get_tables()
    rp_res = await db.execute(select(RolePrivs).where(RolePrivs.role_id == role_id))
    rp_rows = rp_res.scalars().all()
    priv_ids = [rp.privilege_id for rp in rp_rows]
    if not priv_ids:
        return []
    p_res = await db.execute(select(Privs).where(Privs.id.in_(priv_ids)))
    privs = p_res.scalars().all()
    return [{"id": p.id, "privilege_name": p.privilege_name, "description": getattr(p, "description", None)} for p in privs]