import json
import logging
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter
from pydantic import BaseModel

from app.version import APP_VERSION, load_version_data

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/version", tags=["version"])


class VersionInfoResponse(BaseModel):
    version: str
    repository: str
    branch: str
    changelog: list[dict[str, Any]]


class VersionCheckResponse(BaseModel):
    current: str
    latest: str
    has_update: bool
    changelog: list[dict[str, Any]]
    remote_url: str
    check_error: str | None = None


def _parse_version(value: str) -> tuple[int, ...]:
    parts: list[int] = []
    for piece in value.strip().split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def _remote_version_url() -> str:
    local = load_version_data()
    custom_url = (local.get("version_url") or "").strip()
    if custom_url:
        return custom_url
    repo = local.get("repository", "iStarCc/TGMedia")
    branch = local.get("branch", "main")
    return f"https://raw.githubusercontent.com/{repo}/{branch}/version.json"


def _fetch_error_message(exc: Exception) -> str:
    if isinstance(exc, HTTPError):
        if exc.code == 404:
            return (
                "无法访问远程 version.json（GitHub 私有仓库无法通过 raw 链接读取，"
                "请将仓库设为公开，或在 version.json 配置 version_url 指向可公开访问的地址）"
            )
        return f"获取版本信息失败（HTTP {exc.code}）"
    if isinstance(exc, URLError):
        reason = getattr(exc, "reason", exc)
        return f"无法连接更新服务器：{reason}"
    return "检查更新失败"


def _fetch_remote_version_data() -> dict[str, Any]:
    url = _remote_version_url()
    req = Request(url, headers={"User-Agent": "TGMedia/version-check"})
    with urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


@router.get("")
async def get_version_info() -> VersionInfoResponse:
    data = load_version_data()
    return VersionInfoResponse(
        version=data["version"],
        repository=data.get("repository", "iStarCc/TGMedia"),
        branch=data.get("branch", "main"),
        changelog=data.get("changelog", []),
    )


@router.get("/check")
async def check_version_update() -> VersionCheckResponse:
    local = load_version_data()
    repo = local.get("repository", "iStarCc/TGMedia")
    remote_url = f"https://github.com/{repo}"

    try:
        remote = _fetch_remote_version_data()
    except (HTTPError, URLError, json.JSONDecodeError) as e:
        logger.warning("Version check failed: %s", e)
        return VersionCheckResponse(
            current=APP_VERSION,
            latest=APP_VERSION,
            has_update=False,
            changelog=local.get("changelog", []),
            remote_url=remote_url,
            check_error=_fetch_error_message(e) if not isinstance(e, json.JSONDecodeError) else "远程 version.json 格式无效",
        )

    latest = remote.get("version", "")
    if not latest:
        return VersionCheckResponse(
            current=APP_VERSION,
            latest=APP_VERSION,
            has_update=False,
            changelog=local.get("changelog", []),
            remote_url=remote_url,
            check_error="远程 version.json 缺少 version 字段",
        )

    return VersionCheckResponse(
        current=APP_VERSION,
        latest=latest,
        has_update=_parse_version(latest) > _parse_version(APP_VERSION),
        changelog=remote.get("changelog", []),
        remote_url=remote_url,
    )
