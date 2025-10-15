from fastapi import FastAPI, HTTPException, Body
import firebase_admin
import json
from firebase_admin import credentials, db
from dotenv import load_dotenv
import os
from googleapiclient.discovery import build
from urllib.parse import urlparse, parse_qs

from Entities import User, Playlist, Song, Comment, Reaction

load_dotenv()

# Initialize Firebase
firebase_json = os.getenv("FIREBASE_SERVICE_ACCOUNT")

if firebase_json:
    # Running on Railway or with env var
    service_account_info = json.loads(firebase_json)
    cred = credentials.Certificate(service_account_info)
else:
    # Running locally
    cred = credentials.Certificate("serviceAccountKey.json")

firebase_admin.initialize_app(cred, {
    "databaseURL": "https://sharedplay-5eb60-default-rtdb.firebaseio.com"
})

# Initialize YouTube Data API
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

app = FastAPI()


# -------------------- USER METHODS --------------------
@app.post("/user/", response_model=User)
def create_user(user: User = Body(...)):
    ref = db.reference("Users")

    # Generate a unique push key using firebase
    new_ref = ref.push()
    new_id = new_ref.key

    # Add the ID into the user object
    user_dict = user.model_dump()   # Pydantic v2
    user_dict["id"] = new_id
    
    new_ref.set(user_dict)

    initialize_us_to_pl(new_id)
    return user_dict

def initialize_us_to_pl(user_id: str):
    ref = db.reference(f"UserToPlaylists/{user_id}")
    ref.set({})
    return 

@app.get("/user/{user_id}", response_model=User)
def get_user(user_id: str):
    ref = db.reference(f"Users/{user_id}")
    data = ref.get()

    if not data:
        raise HTTPException(status_code=404, detail="User not found")

    return User(**data)


@app.patch("/user/{user_id}", response_model=User)
def patch_user(user_id: str, update: User = Body(...)):
    # to avoid updating the id
    update["id"] = user_id
    ref = db.reference(f"Users/{user_id}")
    existing = ref.get()
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")

    # Only update fields that are not None
    ref.update({k: v for k, v in update.model_dump().items() if v is not None})

    updated_data = ref.get()
    return User(**updated_data)


def remove_us_map(user_id: str):
    ref = db.reference(f"UserToPlaylists/{user_id}")
    data = ref.get()
    if not data:
        raise HTTPException(status_code=404, detail="User not found in User to Playlist mapping")
    ref.delete()


@app.delete("/user/{user_id}")
def delete_user(user_id: str):
    ref = db.reference(f"Users/{user_id}")

    # Fetch the user first to see if it exists
    data = ref.get()

    if not data:
        raise HTTPException(status_code=404, detail="User not found")
    
    data = ref.delete()
    return {"message": f"User {user_id} deleted successfully"}


# -------------------- PLAYLIST METHODS --------------------
@app.post("/playlist/", response_model=Playlist)
def create_playlist(owner: str, playlist: Playlist = Body(...)):
    ref = db.reference(f"Playlists")
    new_ref = ref.push()
    new_id = new_ref.key

    playlist_dict = playlist.model_dump()
    playlist_dict["id"] = new_id
    playlist_dict["owner"] = owner
    playlist_dict["editors"] = [owner]

    new_ref.set(playlist_dict)
    initialize_pl_to_song(new_id)
    
    return playlist_dict

def us_to_pl(user_id: str, playlist_id: str):
    ref = db.reference(f"UserToPlaylists/{user_id}")
    ref.update({playlist_id: True})
    return

def initialize_pl_to_song(playlist_id: str):
    ref = db.reference(f"PlaylistToSongs/{playlist_id}")
    ref.set({})
    return 

@app.get("/playlist/{playlist_id}", response_model=Playlist)
def get_playlist(playlist_id: str):
    ref = db.reference(f"Playlists/{playlist_id}")
    data = ref.get()
    if not data:
        raise HTTPException(status_code=404, detail="Playlist not found")
    data["id"] = playlist_id
    return Playlist(**data)

@app.patch("/playlist/{playlist_id}", response_model=Playlist)
def patch_playlist(playlist_id: str, update: Playlist = Body(...)):
    update_dict = update.model_dump()
    update_dict["id"] = playlist_id
    ref = db.reference(f"Playlists/{playlist_id}")
    existing = ref.get()

    if update_dict["editors"]:
        existing["editors"] = list(set(existing["editors"] + update_dict["editors"]))

    if not existing:
        raise HTTPException(status_code=404, detail="Playlist not found")
    ref.update({k: v for k, v in update_dict.items() if v is not None})
    
    updated_data = ref.get()
    return Playlist(**updated_data)

def remove_pl_from(user_id: str, playlist_id: str):
    ref = db.reference(f"UserToPlaylists/{user_id}/{playlist_id}")
    data = ref.get()
    if not data:
        raise HTTPException(status_code=404, detail="Playlist not found in User to Playlist mapping")
    ref.delete()

def remove_pl_map(playlist_id: str):
    ref = db.reference(f"PlaylistToSongs/{playlist_id}")
    data = ref.get()
    if not data:
        raise HTTPException(status_code=404, detail="Playlist not found in Playlist to Song mapping")
    ref.delete()


@app.delete("/playlist/{playlist_id}")
def delete_playlist(playlist_id: str):
    ref = db.reference(f"Playlists/{playlist_id}")
    data = ref.get()
    if not data:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    ref.delete()

    for editor in data["editors"]: remove_pl_from(editor, playlist_id)
    remove_pl_map(playlist_id)
    return {"message": f"Playlist {playlist_id} deleted successfully"}


# -------------------- SONG METHODS --------------------
@app.post("/song/", response_model=Song)
def create_song(url: str, playlist_id: str, user_id: str):
    '''
    Inserts new song into playlist using information extracted from url.
    
    url: string, YouTube link to the song
    playlist_id: str, id of the playlist we want to insert to
    user_id: str, id of the user who added this song
    '''
    data = get_yt_data(url)

    new_song = Song(id=data["id"],
                    title=data["title"],
                    artist=data["channel"],
                    added_by=user_id,
                    link=url, 
                    playlist_id=playlist_id)

    add_song(new_song)
    pl_to_song(playlist_id, data["id"])

def pl_to_song(playlist_id: str, song_id: str):
    ref = db.reference(f"PlaylistToSongs/{playlist_id}")
    ref.update({song_id: True})
    return

def add_song(song: Song = Body(...)):
    song_dict = song.model_dump()
    song_id = song_dict.get("id")  

    if not song_id:
        raise HTTPException(status_code=400, detail="Song 'id' (YouTube ID) is required")

    new_ref = db.reference("Songs").child(song_id)
    new_ref.set(song_dict)

    return song_dict

@app.get("/song/{song_id}", response_model=Song)
def get_song(song_id: str):
    ref = db.reference(f"Songs/{song_id}")
    data = ref.get()
    if not data:
        raise HTTPException(status_code=404, detail="Song not found")
    data["id"] = song_id
    return Song(**data)

@app.patch("/song/{song_id}", response_model=Song)
def patch_song(song_id: str, update: Song = Body(...)):
    update_dict = update.model_dump()
    update_dict["id"] = song_id
    ref = db.reference(f"Songs/{song_id}")
    existing = ref.get()
    if not existing:
        raise HTTPException(status_code=404, detail="Song not found")
    ref.update({k: v for k, v in update_dict.items() if v is not None})
    updated_data = ref.get()
    return Song(**updated_data)

def remove_song_from(playlist_id: str, song_id: str):
    ref = db.reference(f"PlaylistToSongs/{playlist_id}/{song_id}")
    data = ref.get()
    if not data:
        raise HTTPException(status_code=404, detail="Song not found in mapping")
    ref.delete()

@app.delete("/song/{song_id}")
def delete_song(song_id: str):
    ref = db.reference(f"Songs/{song_id}")
    data = ref.get()
    if not data:
        raise HTTPException(status_code=404, detail="Song not found")
    ref.delete()
    remove_song_from(data["playlist_id"], song_id)
    return {"message": f"Song {song_id} deleted successfully"}


# -------------------- COMMENT METHODS --------------------
@app.post("/comment/", response_model=Comment)
def create_comment(comment: Comment = Body(...)):
    ref = db.reference(f"Comments")
    new_ref = ref.push()
    new_id = new_ref.key

    comment_dict = comment.model_dump()
    comment_dict["id"] = new_id

    new_ref.set(comment_dict)
    return comment_dict

@app.get("/comment/{comment_id}", response_model=Comment)
def get_comment(comment_id: str):
    ref = db.reference(f"Comments/{comment_id}")
    data = ref.get()
    if not data:
        raise HTTPException(status_code=404, detail="Comment not found")
    data["id"] = comment_id
    return Comment(**data)

@app.patch("/comment/{comment_id}", response_model=Comment)
def patch_comment(comment_id: str, update: Comment = Body(...)):
    update_dict = update.model_dump()
    update_dict["id"] = comment_id
    ref = db.reference(f"Comments/{comment_id}")
    existing = ref.get()

    if not existing:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    ref.update({k: v for k, v in update_dict.items() if v is not None})
    
    updated_data = ref.get()
    return Comment(**updated_data)

@app.delete("/comment/{comment_id}")
def delete_comment(comment_id: str):
    ref = db.reference(f"Comments/{comment_id}")
    data = ref.get()
    if not data:
        raise HTTPException(status_code=404, detail="Comment not found")
    ref.delete()
    return {"message": f"Comment {comment_id} deleted successfully"}


# -------------------- REACTION METHODS --------------------
@app.post("/reaction/", response_model=Reaction)
def create_reaction(reaction: Reaction = Body(...)):
    ref = db.reference(f"Reactions")
    new_ref = ref.push()
    new_id = new_ref.key

    reaction_dict = reaction.model_dump()
    reaction_dict["id"] = new_id
    new_ref.set(reaction_dict)
    return reaction_dict

@app.get("/reaction/{reaction_id}", response_model=Reaction)
def get_reaction(reaction_id: str):
    ref = db.reference(f"Reactions/{reaction_id}")
    data = ref.get()
    if not data:
        raise HTTPException(status_code=404, detail="Reaction not found")
    data["id"] = reaction_id
    return Reaction(**data)

@app.patch("/reaction/{reaction_id}", response_model=Reaction)
def patch_reaction(reaction_id: str, update: Reaction = Body(...)):
    update_dict = update.model_dump()
    update_dict["id"] = reaction_id
    ref = db.reference(f"Reactions/{reaction_id}")
    existing = ref.get()
    
    if not existing:
        raise HTTPException(status_code=404, detail="Reaction not found")
    
    ref.update({k: v for k, v in update_dict.items() if v is not None})
    updated_data = ref.get()
    return Reaction(**updated_data)

@app.delete("/reaction/{reaction_id}")
def delete_reaction(reaction_id: str):
    ref = db.reference(f"Reactions/{reaction_id}")
    data = ref.get()
    if not data:
        raise HTTPException(status_code=404, detail="Reaction not found")
    ref.delete()
    return {"message": f"Reaction {reaction_id} deleted successfully"}


# -------------------- YouTube Data --------------------
def get_yt_data(url: str):
    video_id = extract_video_id(url)
    if not video_id:
        return {"error": "Invalid YouTube URL"}

    request = youtube.videos().list(
        part="snippet,contentDetails,statistics",
        id=video_id
    )
    response = request.execute()
    
    if not response["items"]:
        return {"error": "Video not found"}
    else:
        print(response)

    item = response["items"][0]
    video_info = {
        "id": video_id,
        "title": item["snippet"]["title"],
        "channel": item["snippet"]["channelTitle"],
        "thumbnail": item["snippet"]["thumbnails"]["default"]["url"],
        "duration": item["contentDetails"]["duration"]
    }
    return video_info


def extract_video_id(url: str) -> str | None:
    """
    Extracts the video ID from a YouTube URL.
    Returns None if the URL is invalid.
    """
    parsed_url = urlparse(url)

    # Standard YouTube or YouTube Music
    if parsed_url.hostname in ["www.youtube.com", "youtube.com", "music.youtube.com"]:
        query = parse_qs(parsed_url.query)
        return query.get("v", [None])[0]

    # Shortened URL
    elif parsed_url.hostname == "youtu.be":
        return parsed_url.path.lstrip("/")

    return None




# add/remove friend

# add/remove editor

# TODO: get all playlists(user)
# get all songs(playlist)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
        