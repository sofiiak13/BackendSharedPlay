from pydantic import BaseModel
from typing import Optional, List

class Playlist(BaseModel):
    id: Optional[str] = None        #id is optional because it's being set on backend upon creation
    name: str
    date_created: Optional[str] = None
    last_updated: Optional[str] = None
    owner: str
    editors: List[str] = None            

class PlaylistUpdate(BaseModel):
    name: Optional[str] = None
    owner: Optional[str] = None
    new_editor: Optional[str] = None