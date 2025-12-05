from pydantic import BaseModel

class Invitation(BaseModel):
    id: str
    playlist_id: str
    created_by: str
    expires_at: str