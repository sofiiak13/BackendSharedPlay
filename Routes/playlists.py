from fastapi import APIRouter, Body, HTTPException
from Modules import Playlist, PlaylistUpdate
from firebase_admin import db

import datetime

router = APIRouter(
    prefix="/playlist",
    tags=["playlists"]
)

# -------------------- PLAYLIST METHODS --------------------
@router.post("", response_model=Playlist)
def create_playlist(playlist: Playlist = Body(...)):
    ref = db.reference(f"Playlists")
    new_ref = ref.push()
    new_id = new_ref.key

    playlist_dict = playlist.model_dump()
    playlist_dict["id"] = new_id
    owner = playlist_dict["owner"]
    playlist_dict["editors"] = [owner]
    playlist_dict["date_created"] = datetime.datetime.now().isoformat()
    playlist_dict["last_updated"] = datetime.datetime.now().isoformat()

    new_ref.set(playlist_dict)
    us_to_pl(owner, new_id)
    
    return playlist_dict

def us_to_pl(user_id: str, playlist_id: str):
    ref = db.reference(f"UserToPlaylists/{user_id}")
    ref.update({playlist_id: True})
    return "Successful mapping User to Playlist."


@router.get("/{playlist_id}", response_model=Playlist)
def get_playlist(playlist_id: str):
    ref = db.reference(f"Playlists/{playlist_id}")
    data = ref.get()
    if not data:
        raise HTTPException(status_code=404, detail="Playlist not found")
    data["id"] = playlist_id
    return Playlist(**data)


@router.patch("/{playlist_id}", response_model=Playlist)
def patch_playlist(playlist_id: str, update: PlaylistUpdate = Body(...)):
    # Only include fields that the user actually sent
    update_dict = update.model_dump(exclude_unset=True)

    ref = db.reference(f"Playlists/{playlist_id}")
    existing = ref.get()

    if not existing:
        raise HTTPException(status_code=404, detail="Playlist not found")

    # Merge editors if provided
    if "editors" in update_dict and update_dict["editors"]:
        existing_editors = existing.get("editors", [])
        new_editors = update_dict["editors"]
        update_dict["editors"] = list(set(existing_editors + new_editors))

    # Always update id and timestamp server-side
    update_dict["id"] = playlist_id
    update_dict["last_updated"] = datetime.datetime.now().isoformat()

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
def delete_playlist(playlist_id: str):
    ref = db.reference(f"Playlists/{playlist_id}")
    data = ref.get()
    if not data:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    ref.delete()

    for editor in data["editors"]: remove_pl_from(editor, playlist_id)
    remove_pl_map(playlist_id)
    return {"message": f"Playlist {playlist_id} deleted successfully"}


@router.get("/{user_id}/playlists")
def get_all_playlists_for(user_id: str):
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