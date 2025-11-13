from pydantic import BaseModel
from typing import Optional

class Song(BaseModel):
    id: Optional[str] = None        
    yt_id: Optional[str] = None 
    title: Optional[str] = None
    artist: Optional[str] = None
    added_by: Optional[str] = None
    link: Optional[str] = None
    playlist_id: Optional[str] = None
    date_added: Optional[str] = None
    date_released: Optional[str] = None