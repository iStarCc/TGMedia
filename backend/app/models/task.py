from pydantic import BaseModel


class TaskResponse(BaseModel):
    id: str
    account_id: int | None = None
    channel_id: int | None = None
    message_id: int | None = None
    chat_id: int = 0
    filename: str
    file_size: int = 0
    downloaded: int = 0
    media_type: str
    status: str = "pending"
    speed: float = 0
    error: str | None = None
    file_path: str | None = None
    started_at: str | None = None
    created_at: str
    updated_at: str

    @property
    def progress(self) -> float:
        if self.file_size <= 0:
            return 0.0
        return min(self.downloaded / self.file_size, 1.0)


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]
    total: int
