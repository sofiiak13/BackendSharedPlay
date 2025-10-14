from pydantic import BaseModel
from typing import Optional, List

class User(BaseModel):
    id: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    password: Optional[str] = None
    friends: List[str] = []

# think about what happens if someone deletes a playlist?
class Playlist(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    date_created: Optional[str] = None
    last_updated: Optional[str] = None
    owner: Optional[str] = None
    editors: List[str] = []             # maybe unneccesary if have same rights as editors

class Song(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    artist: Optional[str] = None
    added_by: Optional[str] = None
    link: Optional[str] = None
    playlist_id: Optional[str] = None

class Comment(BaseModel):
    id: Optional[str] = None
    text: Optional[str] = None
    author: Optional[str] = None
    date: Optional[str] = None
    prev: Optional[str] = None
    song_id: Optional[str] = None

class Reaction(BaseModel):
    id: Optional[str] = None
    emoji: Optional[str] = None
    author: Optional[str] = None
    date: Optional[str] = None
    comment_id: Optional[str] = None