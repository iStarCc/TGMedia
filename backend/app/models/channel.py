from pydantic import BaseModel


class ChannelCreate(BaseModel):
    link: str


class ChannelUpdate(BaseModel):
    auto_download: bool | None = None
    filter_type: str | None = None
    max_file_size: int | None = None
    allowed_extensions: str | None = None
    download_path: str | None = None
    download_by_channel: int | None = None
    download_by_media_type: int | None = None
    sync_limit: int | None = None


class ChannelResponse(BaseModel):
    id: int
    account_id: int | None = None
    telegram_id: int
    title: str
    username: str | None = None
    photo_url: str | None = None
    auto_download: bool = False
    filter_type: str = "all"
    max_file_size: int = 0
    allowed_extensions: str = ""
    download_path: str = ""
    download_by_channel: int = 0
    download_by_media_type: int = 0
    sync_limit: int = 0
    created_at: str
    updated_at: str
