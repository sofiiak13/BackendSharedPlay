from pydantic import BaseModel
from typing import Optional

class Reaction(BaseModel):
    id: Optional[str] = None    #id is optional because it's being set on backend upon creation
    emoji: str
    author: str
    comment_id: str