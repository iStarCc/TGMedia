import asyncio
import logging
import shutil
from pathlib import Path

from pytdbot import Client, types

from app.config import settings

logger = logging.getLogger(__name__)


class TelegramManager:
    """管理多个 Telegram 账户的 TDLib 客户端"""

    def __init__(self):
        self._clients: dict[int, Client] = {}
        self._credentials: dict[int, tuple[int, str]] = {}
        self._auth_states: dict[int, str] = {}
        self._auth_waiters: dict[int, asyncio.Event] = {}

    def _files_dir(self, account_id: int) -> str:
        return str(Path(settings.var_dir) / f"tdlib_{account_id}")

    def register_credentials(self, account_id: int, api_id: int, api_hash: str) -> None:
        self._credentials[account_id] = (api_id, api_hash)

    async def get_client(self, account_id: int) -> Client:
        if account_id in self._clients:
            client = self._clients[account_id]
            if client.is_running:
                return client

        if account_id not in self._credentials:
            from app.database import get_db
            db = await get_db()
            rows = await db.execute_fetchall(
                "SELECT api_id, api_hash FROM accounts WHERE id=?", (account_id,)
            )
            if not rows:
                raise ValueError(f"Account {account_id} not found")
            self._credentials[account_id] = (rows[0]["api_id"], rows[0]["api_hash"])

        api_id, api_hash = self._credentials[account_id]
        files_dir = self._files_dir(account_id)
        Path(files_dir).mkdir(parents=True, exist_ok=True)

        client = Client(
            api_id=api_id,
            api_hash=api_hash,
            files_directory=files_dir,
            database_encryption_key="tgmedia",
            user_bot=True,
            td_verbosity=1,
            td_log=types.LogStreamFile(
                path=str(Path(settings.var_dir) / f"tdlib_{account_id}.log"),
                max_file_size=10 * 1024 * 1024,
            ),
            workers=4,
        )

        self._setup_auth_handler(client, account_id)
        await client.start(wait_login=False)
        self._clients[account_id] = client

        await self._wait_for_auth_state(
            account_id,
            {"authorizationStateReady", "authorizationStateWaitPhoneNumber"},
            timeout=15,
        )
        return client

    def _setup_auth_handler(self, client: Client, account_id: int) -> None:
        async def on_auth_state(_c: Client, update: types.UpdateAuthorizationState):
            state = update.authorization_state.getType()
            self._auth_states[account_id] = state
            logger.info("Account %d auth state: %s", account_id, state)
            if account_id in self._auth_waiters:
                self._auth_waiters[account_id].set()

        client.add_handler("updateAuthorizationState", on_auth_state)

    async def _wait_for_auth_state(
        self, account_id: int, target_states: set[str], timeout: float = 30
    ) -> str:
        if self._auth_states.get(account_id) in target_states:
            return self._auth_states[account_id]

        event = asyncio.Event()
        self._auth_waiters[account_id] = event
        try:
            while True:
                event.clear()
                await asyncio.wait_for(event.wait(), timeout=timeout)
                state = self._auth_states.get(account_id, "")
                if state in target_states:
                    return state
        except asyncio.TimeoutError:
            return self._auth_states.get(account_id, "")
        finally:
            self._auth_waiters.pop(account_id, None)

    async def is_authorized(self, account_id: int) -> bool:
        try:
            client = await self.get_client(account_id)
            return client.is_authenticated
        except Exception:
            return False

    async def send_code(self, account_id: int, phone: str) -> str:
        client = await self.get_client(account_id)
        result = await client.setAuthenticationPhoneNumber(phone_number=phone)
        if isinstance(result, types.Error):
            raise RuntimeError(result.message)
        await self._wait_for_auth_state(
            account_id,
            {"authorizationStateWaitCode", "authorizationStateReady"},
            timeout=30,
        )
        return "tdlib"

    async def sign_in(self, account_id: int, phone: str, code: str, phone_code_hash: str) -> dict:
        client = await self.get_client(account_id)
        result = await client.checkAuthenticationCode(code=code)
        if isinstance(result, types.Error):
            if "PASSWORD" in result.message.upper() or "Two-step" in result.message:
                raise RuntimeError("Two-steps verification is enabled")
            raise RuntimeError(result.message)

        state = await self._wait_for_auth_state(
            account_id,
            {"authorizationStateReady", "authorizationStateWaitPassword"},
            timeout=15,
        )
        if state == "authorizationStateWaitPassword":
            raise RuntimeError("Two-steps verification is enabled")

        return await self._get_user_info(client)

    async def sign_in_2fa(self, account_id: int, password: str) -> dict:
        client = await self.get_client(account_id)
        result = await client.checkAuthenticationPassword(password=password)
        if isinstance(result, types.Error):
            raise RuntimeError(result.message)

        await self._wait_for_auth_state(
            account_id, {"authorizationStateReady"}, timeout=15
        )
        return await self._get_user_info(client)

    async def logout(self, account_id: int) -> None:
        client = self._clients.get(account_id)
        if client and client.is_running:
            try:
                await client.logOut()
            except Exception:
                pass
            try:
                await client.stop()
            except Exception:
                pass
        self._clients.pop(account_id, None)
        self._credentials.pop(account_id, None)
        self._auth_states.pop(account_id, None)

        files_dir = Path(self._files_dir(account_id))
        if files_dir.exists():
            shutil.rmtree(files_dir, ignore_errors=True)

    async def stop_all(self) -> None:
        for account_id, client in list(self._clients.items()):
            try:
                if client.is_running:
                    await client.stop()
            except Exception:
                pass
        self._clients.clear()
        self._credentials.clear()
        self._auth_states.clear()

    async def disconnect(self, account_id: int) -> None:
        client = self._clients.pop(account_id, None)
        if client and client.is_running:
            await client.stop()

    def get_all_clients(self) -> dict[int, Client]:
        return {k: v for k, v in self._clients.items() if v.is_running}

    async def download_file(
        self, client: Client, file_id: int, priority: int = 32
    ) -> str | None:
        """下载文件并返回本地路径"""
        result = await client.downloadFile(
            file_id=file_id, priority=priority, synchronous=True
        )
        if isinstance(result, types.Error):
            raise RuntimeError(f"Download failed: {result.message}")
        if result.local and result.local.is_downloading_completed:
            return result.local.path
        return None

    @staticmethod
    async def _get_user_info(client: Client) -> dict:
        me = client.me
        if not me:
            me = await client.getMe()
        if isinstance(me, types.Error):
            return {"id": 0, "first_name": "", "last_name": "", "username": ""}
        username = ""
        if me.usernames and me.usernames.editable_username:
            username = me.usernames.editable_username
        return {
            "id": me.id,
            "first_name": me.first_name or "",
            "last_name": me.last_name or "",
            "username": username,
        }


tg_manager = TelegramManager()
