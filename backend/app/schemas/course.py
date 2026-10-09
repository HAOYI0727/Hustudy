from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
class CourseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200); description: Optional[str] = Field(default=None, max_length=5000)
class CourseUpdate(CourseCreate): pass
class CourseResponse(BaseModel):
    id: str; user_id: str; name: str; description: Optional[str]; created_at: datetime; updated_at: datetime
