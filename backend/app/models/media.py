from pydantic import BaseModel


class MediaFileResponse(BaseModel):
    id: int
    task_id: str | None = None
    channel_id: int | None = None
    filename: str
    file_path: str
    file_size: int = 0
    media_type: str
    thumbnail_path: str | None = None
    created_at: str


class MediaListResponse(BaseModel):
    files: list[MediaFileResponse]
    total: int
