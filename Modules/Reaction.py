from pydantic import BaseModel
from typing import Optional

class Reaction(BaseModel):
    id: Optional[str] = None
    emoji: Optional[str] = None
    author: Optional[str] = None
    comment_id: Optional[str] = None