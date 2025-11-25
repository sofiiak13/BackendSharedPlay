from pydantic import BaseModel
from typing import Optional

class Comment(BaseModel):
    id: Optional[str]                   #id is optional because it's being set on backend upon creation
    text: str
    author_id: str
    author: str
    date_created: Optional[str] = None
    prev: Optional[str] = None
    song_id: str
    edited: Optional[bool] = False
    depth: Optional[int] = 0
    