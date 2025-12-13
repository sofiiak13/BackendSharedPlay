from fastapi import APIRouter, Body, HTTPException, Depends
from Modules import Playlist, PlaylistUpdate
from Modules.Invitation import Invitation
from firebase_admin import db
import uuid
from datetime import datetime, timedelta, timezone
from auth import get_current_user

router = APIRouter(
    prefix="/playlist",
    tags=["playlists"]
)

# -------------------- PLAYLIST METHODS --------------------
@router.post("", response_model=Playlist)
def create_playlist(playlist: Playlist = Body(...), uid: str = Depends(get_current_user)):
    ref = db.reference(f"Playlists")
    new_ref = ref.push()
    new_id = new_ref.key

    playlist_dict = playlist.model_dump()
    playlist_dict["id"] = new_id
    owner = uid
    playlist_dict["owner"] = owner
    playlist_dict["editors"] = [owner]
    playlist_dict["date_created"] = datetime.now().isoformat()
    playlist_dict["last_updated"] = datetime.now().isoformat()

    new_ref.set(playlist_dict)
    us_to_pl(owner, new_id)
    
    return playlist_dict

def us_to_pl(user_id: str, playlist_id: str):
    ref = db.reference(f"UserToPlaylists/{user_id}")
    ref.update({playlist_id: True})
    return "Successful mapping User to Playlist."


@router.get("/{playlist_id}", response_model=Playlist)
def get_playlist(playlist_id: str, _: str = Depends(get_current_user)):
    ref = db.reference(f"Playlists/{playlist_id}")
    data = ref.get()
    if not data:
        raise HTTPException(status_code=404, detail="Playlist not found")
    data["id"] = playlist_id
    return Playlist(**data)


@router.patch("/{playlist_id}", response_model=Playlist)
def patch_playlist(playlist_id: str, update: PlaylistUpdate = Body(...), _: str = Depends(get_current_user)):
    # Only include fields that the user actually sent
    update_dict = update.model_dump(exclude_unset=True)

    ref = db.reference(f"Playlists/{playlist_id}")
    existing = ref.get()

    if not existing:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    print(update_dict)

    # Merge editors if provided
    if "new_editor" in update_dict:
        new_editor_id = update_dict["new_editor"]
        if new_editor_id not in existing["editors"]:
            existing["editors"].append(new_editor_id)
            update_dict["editors"] = existing["editors"]
            print("Combined editors", update_dict["editors"])
            us_to_pl(new_editor_id, playlist_id)            # if there is a new editor create user to pl entry

    # Always update id and timestamp server-side
    update_dict["id"] = playlist_id
    update_dict["last_updated"] = datetime.now().isoformat()

    # Update only specified fields
    ref.update(update_dict)

    updated_data = ref.get()
    return Playlist(**updated_data)


def remove_pl_from(user_id: str, playlist_id: str):
    '''Removes playlist mapping from UserToPlaylists relationship.'''
    ref = db.reference(f"UserToPlaylists/{user_id}/{playlist_id}")
    data = ref.get()
    if not data:
        raise HTTPException(status_code=404, detail="Playlist not found in User to Playlist mapping")
    ref.delete()

def remove_pl_map(playlist_id: str):
    '''Removes playlist mapping from PlaylistToSongs relationship.'''
    ref = db.reference(f"PlaylistToSongs/{playlist_id}")
    data = ref.get()
    if not data:
        raise HTTPException(status_code=404, detail="Playlist not found in Playlist to Song mapping")
    ref.delete()


@router.delete("/{playlist_id}")
def delete_playlist(playlist_id: str, _: str = Depends(get_current_user)):
    ref = db.reference(f"Playlists/{playlist_id}")
    data = ref.get()
    if not data:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    ref.delete()

    for editor in data["editors"]: remove_pl_from(editor, playlist_id)
    remove_pl_map(playlist_id)
    return {"message": f"Playlist {playlist_id} deleted successfully"}


@router.get("/{user_id}/playlists")
def get_all_playlists_for(user_id: str, _: str = Depends(get_current_user)):
    ref = db.reference(f"UserToPlaylists/{user_id}")
    data = ref.get()
    all_playlists = []
    
    if data == None:
        return all_playlists
    
    for playlist_id in data:
        try: 
            all_playlists.append(get_playlist(playlist_id))
        except HTTPException:
            print("Playlist", playlist_id, "not found in mapping. Must have be deleted earlier.")

    return all_playlists

# ---Invitation to playlist methods---

@router.post("/{playlist_id}/invites", response_model=Invitation)
def create_invite(playlist_id: str, user_id: str, _: str = Depends(get_current_user)):
    playlist_ref = db.reference(f"Playlists/{playlist_id}")
    playlist = playlist_ref.get()

    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    if user_id not in playlist.get("editors", []):
        raise HTTPException(
            status_code=410, 
            detail="This user doesn't have permission to share the playlist."
        )

    invite_id = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(days=3)

    invitation = {
        "id": invite_id,
        "playlist_id": playlist_id,
        "created_by": user_id,
        "expires_at": expires_at.isoformat()
    }
        
    db.reference(f"Invites/{invite_id}").set(invitation)

    return invitation

@router.get("/invites/{invite_id}", response_model=Invitation)
def validate_invite(invite_id: str, _: str = Depends(get_current_user)):
    invite_ref = db.reference(f"Invites/{invite_id}")
    invite = invite_ref.get()

    if not invite:
        raise HTTPException(status_code=404, detail="Invalid invite")

    invite_expires_at = datetime.fromisoformat(invite["expires_at"])

    if invite_expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Invite expired")

    return invite


@router.post("/{playlist_id}/editors")
def add_editor(playlist_id: str, user_id: str, _: str = Depends(get_current_user)):
    playlist_ref = db.reference(f"Playlists/{playlist_id}")
    playlist = playlist_ref.get()

    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    

    patch_playlist(playlist_id, PlaylistUpdate(new_editor=user_id))

    return {"message": f"Editor {user_id} added successfully."}