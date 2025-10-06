from pydantic import BaseModel
from typing import Optional, List

class User(BaseModel):
    id: str
    email: Optional[str] = None
    name: Optional[str] = None
    password: Optional[str] = None
    friends: List[str] = []

# think about what happens if someone deletes a playlist?
class Playlist(BaseModel):
    id: str
    name: Optional[str] = None
    owner: Optional[str] = None
    editors: List[str] = []             # maybe unneccesary if have same rights as editors
    date_created: Optional[str] = None
    last_updated: Optional[str] = None

class Song(BaseModel):
    id: str
    title: Optional[str] = None
    artist: Optional[str] = None
    added_by: Optional[str] = None

class Comment(BaseModel):
    id: str
    text: Optional[str] = None
    author: Optional[str] = None
    date: Optional[str] = None
    prev: Optional[str] = None

class Reaction(BaseModel):
    id: str
    emoji: Optional[str] = None
    author: Optional[str] = None
    date: Optional[str] = None