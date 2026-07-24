import json
import logging
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter
from pydantic import BaseModel

from app.version import get_app_version, load_version_data

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


def _repository() -> str:
    return load_version_data().get("repository", "iStarCc/TGMedia")


def _remote_release_api_url() -> str:
    local = load_version_data()
    custom_url = (local.get("release_api_url") or local.get("version_url") or "").strip()
    if custom_url:
        return custom_url
    repo = _repository()
    return f"https://api.github.com/repos/{repo}/releases/latest"


def _release_page_url() -> str:
    repo = _repository()
    return f"https://github.com/{repo}/releases/latest"


def _normalize_release_version(tag_name: str) -> str:
    tag = tag_name.strip()
    if tag.lower().startswith("v"):
        tag = tag[1:]
    return tag


def _fetch_error_message(exc: Exception) -> str:
    if isinstance(exc, HTTPError):
        if exc.code == 404:
            return "未找到 GitHub Release，请确认仓库已发布 Release 且为公开仓库"
        if exc.code == 403:
            return "GitHub API 访问受限，请稍后重试"
        return f"获取 Release 信息失败（HTTP {exc.code}）"
    if isinstance(exc, URLError):
        reason = getattr(exc, "reason", exc)
        return f"无法连接 GitHub：{reason}"
    return "检查更新失败"


def _fetch_remote_release() -> dict[str, Any]:
    url = _remote_release_api_url()
    req = Request(
        url,
        headers={
            "User-Agent": "TGMedia/version-check",
            "Accept": "application/vnd.github+json",
        },
    )
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
    fallback_url = f"https://github.com/{repo}/releases"
    current = get_app_version()

    try:
        release = _fetch_remote_release()
    except (HTTPError, URLError, json.JSONDecodeError) as e:
        logger.warning("Version check failed: %s", e)
        return VersionCheckResponse(
            current=current,
            latest=current,
            has_update=False,
            changelog=local.get("changelog", []),
            remote_url=fallback_url,
            check_error=(
                _fetch_error_message(e)
                if not isinstance(e, json.JSONDecodeError)
                else "GitHub Release 响应格式无效"
            ),
        )

    tag_name = (release.get("tag_name") or "").strip()
    latest = _normalize_release_version(tag_name) if tag_name else ""
    if not latest:
        return VersionCheckResponse(
            current=current,
            latest=current,
            has_update=False,
            changelog=local.get("changelog", []),
            remote_url=fallback_url,
            check_error="GitHub Release 缺少 tag_name 字段",
        )

    remote_url = (release.get("html_url") or _release_page_url()).strip()

    return VersionCheckResponse(
        current=current,
        latest=latest,
        has_update=_parse_version(latest) > _parse_version(current),
        changelog=local.get("changelog", []),
        remote_url=remote_url,
    )
