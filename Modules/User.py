from pydantic import BaseModel
from typing import Optional, List

class User(BaseModel):
    id: str          
    email: str
    name: str
    date_joined: Optional[str] = None
    friends: List[str] = []

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    friends: List[str] = []