from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field
class JobStatus(str, Enum):
    QUEUED = "QUEUED"; RUNNING = "RUNNING"; SUCCEEDED = "SUCCEEDED"; FAILED = "FAILED"; CANCELLED = "CANCELLED"
class Locator(BaseModel):
    type: str = Field(pattern=r"^(slide|page|heading|docx_block)$")
    value: str
class Citation(BaseModel):
    version_id: str; chunk_id: str; locator: Locator; quote: str; quote_hash: Optional[str] = None; availability: str = "active"
class HealthResponse(BaseModel):
    status: str; service: str; environment: str; database: str
