from pydantic import BaseModel
from typing import Optional

class Comment(BaseModel):
    id: Optional[str] = None
    text: Optional[str] = None
    author: Optional[str] = None
    date_created: Optional[str] = None
    prev: Optional[str] = None
    song_id: Optional[str] = None
    edited: bool = False
    depth: Optional[int] = None
    
class CommentUpdate(BaseModel):
    text: Optional[str] 
    edited: bool 