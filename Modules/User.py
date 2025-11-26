from pydantic import BaseModel
from typing import Optional, List

class User(BaseModel):
    id: Optional[str] = None            #id is optional because it's being set on backend upon creation
    email: str
    name: str
    date_joined: Optional[str] = None
    friends: List[str] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    friends: List[str] = None