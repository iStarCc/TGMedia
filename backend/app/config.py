import json
from pathlib import Path

from pydantic_settings import BaseSettings

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DATA_ROOT = _PROJECT_ROOT / ".data"


class Settings(BaseSettings):
    model_config = {"env_prefix": "TGMEDIA_"}

    data_dir: str = str(_DATA_ROOT / "data")
    var_dir: str = str(_DATA_ROOT / "var")
    etc_dir: str = str(_DATA_ROOT / "etc")
    sock: str = str(_DATA_ROOT / "tgmedia.sock")
    root_path: str = ""
    max_concurrent: int = 3
    auto_download: bool = False
    ws_throttle_ms: int = 500
    download_path: str = ""
    download_by_channel: bool = False
    download_by_media_type: bool = False
    allowed_extensions: list[str] = []
    sync_limit: int = 100
    sync_days: int = 0

    @property
    def db_path(self) -> Path:
        return Path(self.var_dir) / "tgmedia.db"

    @property
    def download_dir(self) -> Path:
        p = Path(self.download_path) if self.download_path else Path(self.data_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def _conf_path(self) -> Path:
        return Path(self.etc_dir) / "app.conf"

    def load_from_etc(self) -> None:
        if not self._conf_path.exists():
            return
        for line in self._conf_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, value = line.partition("=")
            key, value = key.strip().lower(), value.strip()
            match key:
                case "max_concurrent":
                    self.max_concurrent = int(value)
                case "download_path":
                    self.download_path = value
                case "download_by_channel":
                    self.download_by_channel = value.lower() in ("1", "true")
                case "download_by_media_type":
                    self.download_by_media_type = value.lower() in ("1", "true")
                case "allowed_extensions":
                    self.allowed_extensions = json.loads(value) if value else []
                case "sync_limit":
                    self.sync_limit = int(value)
                case "sync_days":
                    self.sync_days = int(value)
                case "auto_download":
                    self.auto_download = value.lower() in ("1", "true")

    def save_to_etc(self) -> None:
        self._conf_path.parent.mkdir(parents=True, exist_ok=True)
        self._conf_path.write_text(
            f"max_concurrent={self.max_concurrent}\n"
            f"auto_download={'1' if self.auto_download else '0'}\n"
            f"download_path={self.download_path}\n"
            f"download_by_channel={'1' if self.download_by_channel else '0'}\n"
            f"download_by_media_type={'1' if self.download_by_media_type else '0'}\n"
            f"allowed_extensions={json.dumps(self.allowed_extensions)}\n"
            f"sync_limit={self.sync_limit}\n"
            f"sync_days={self.sync_days}\n"
        )


settings = Settings()
settings.load_from_etc()
