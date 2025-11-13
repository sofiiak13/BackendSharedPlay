from pydantic import BaseModel
from typing import Optional, List

class Playlist(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    date_created: Optional[str] = None
    last_updated: Optional[str] = None
    owner: Optional[str] = None
    editors: List[str] = None             # maybe unneccesary if have same rights as editors

class PlaylistUpdate(BaseModel):
    name: Optional[str] = None
    owner: Optional[str] = None
    editors: Optional[List[str]] = None