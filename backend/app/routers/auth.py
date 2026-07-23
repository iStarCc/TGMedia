import logging
import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pytdbot import types

from app.config import settings
from app.database import get_db
from app.services.scheduler import start_event_listener
from app.services.telegram import tg_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class CreateAccountRequest(BaseModel):
    phone: str
    api_id: int
    api_hash: str


class SendCodeRequest(BaseModel):
    account_id: int
    phone: str


class VerifyRequest(BaseModel):
    account_id: int
    phone: str
    code: str
    phone_code_hash: str


class TwoFARequest(BaseModel):
    account_id: int
    password: str


def _mask(s: str) -> str:
    if len(s) <= 8:
        return "*" * len(s)
    return s[:4] + "*" * (len(s) - 8) + s[-4:]


@router.get("/accounts")
async def list_accounts():
    db = await get_db()
    rows = await db.execute_fetchall("SELECT * FROM accounts ORDER BY created_at DESC")
    accounts = []
    for r in rows:
        acc = dict(r)
        acc["api_hash"] = _mask(acc["api_hash"])
        authorized = await tg_manager.is_authorized(acc["id"])
        acc["authorized"] = authorized
        if authorized and not _avatar_path(acc["id"]).exists():
            await _download_avatar(acc["id"])
        accounts.append(acc)
    return accounts


@router.post("/accounts")
async def create_account(req: CreateAccountRequest):
    db = await get_db()
    try:
        cursor = await db.execute(
            "INSERT INTO accounts (phone, api_id, api_hash, session_file) VALUES (?, ?, ?, ?)",
            (req.phone, req.api_id, req.api_hash, ""),
        )
        await db.commit()
        account_id = cursor.lastrowid

        session_file = f"tdlib_{account_id}"
        await db.execute(
            "UPDATE accounts SET session_file=? WHERE id=?",
            (session_file, account_id),
        )
        await db.commit()

        tg_manager.register_credentials(account_id, req.api_id, req.api_hash)
        return {"id": account_id, "phone": req.phone}
    except Exception:
        raise HTTPException(409, "该手机号已存在")


@router.post("/send-code")
async def send_code(req: SendCodeRequest):
    try:
        phone_code_hash = await tg_manager.send_code(req.account_id, req.phone)
        return {"phone_code_hash": phone_code_hash}
    except Exception as e:
        raise HTTPException(400, str(e))


@router.post("/verify")
async def verify(req: VerifyRequest):
    try:
        user = await tg_manager.sign_in(
            req.account_id, req.phone, req.code, req.phone_code_hash
        )

        db = await get_db()
        await db.execute(
            """UPDATE accounts SET telegram_id=?, first_name=?, last_name=?, username=?
               WHERE id=?""",
            (user["id"], user["first_name"], user["last_name"], user["username"], req.account_id),
        )
        await db.commit()

        await _download_avatar(req.account_id)
        await start_event_listener()
        return {"user": user}
    except Exception as e:
        error_msg = str(e)
        if "Two-steps verification" in error_msg or "2FA" in error_msg:
            raise HTTPException(403, "需要两步验证密码")
        raise HTTPException(400, error_msg)


@router.post("/verify-2fa")
async def verify_2fa(req: TwoFARequest):
    try:
        user = await tg_manager.sign_in_2fa(req.account_id, req.password)

        db = await get_db()
        await db.execute(
            """UPDATE accounts SET telegram_id=?, first_name=?, last_name=?, username=?
               WHERE id=?""",
            (user["id"], user["first_name"], user["last_name"], user["username"], req.account_id),
        )
        await db.commit()

        await _download_avatar(req.account_id)
        await start_event_listener()
        return {"user": user}
    except Exception as e:
        raise HTTPException(400, str(e))


@router.delete("/accounts/{account_id}")
async def delete_account(account_id: int):
    await tg_manager.logout(account_id)
    db = await get_db()
    await db.execute("DELETE FROM channels WHERE account_id=?", (account_id,))
    await db.execute("DELETE FROM accounts WHERE id=?", (account_id,))
    await db.commit()
    return {"ok": True}


@router.get("/accounts/{account_id}/status")
async def account_status(account_id: int):
    authorized = await tg_manager.is_authorized(account_id)
    return {"authorized": authorized}


def _avatar_path(account_id: int) -> Path:
    return Path(settings.var_dir) / f"avatar_{account_id}.jpg"


async def _download_avatar(account_id: int) -> None:
    try:
        client = await tg_manager.get_client(account_id)
        if not client.is_authenticated:
            return
        me = client.me
        if not me or not me.profile_photo:
            return

        small_file = me.profile_photo.small
        if not small_file:
            return

        local_path = await tg_manager.download_file(client, small_file.id)
        if local_path and Path(local_path).exists():
            dest = _avatar_path(account_id)
            shutil.copy2(local_path, str(dest))
    except Exception as e:
        logger.warning("Failed to download avatar for account %d: %s", account_id, e)


@router.get("/accounts/{account_id}/avatar")
async def get_avatar(account_id: int):
    path = _avatar_path(account_id)
    if not path.exists():
        raise HTTPException(404, "头像未找到")
    return FileResponse(path, media_type="image/jpeg")
