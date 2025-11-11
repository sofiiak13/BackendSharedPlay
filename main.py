from fastapi import FastAPI, HTTPException, Body
import firebase_admin
import json
from firebase_admin import credentials, db
from dotenv import load_dotenv
import os
from googleapiclient.discovery import build
from urllib.parse import urlparse, parse_qs
import datetime
import re

from Entities import User, Playlist, Song, Comment, Reaction
from Entities import UserUpdate, PlaylistUpdate, CommentUpdate

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

@app.get("/")
def home():
    return {"message": "Welcome to SharedPlay API"}

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
    user_dict["date_joined"] = datetime.datetime.now().isoformat()

    new_ref.set(user_dict)
    return user_dict


@app.get("/user/{user_id}", response_model=User)
def get_user(user_id: str):
    ref = db.reference(f"Users/{user_id}")
    data = ref.get()

    if not data:
        raise HTTPException(status_code=404, detail="User not found")

    return User(**data)


@app.patch("/user/{user_id}", response_model=User)
def patch_user(user_id: str, update: UserUpdate = Body(...)):
    # Only include fields the client actually sent
    update_dict = update.model_dump(exclude_unset=True)

    ref = db.reference(f"Users/{user_id}")
    existing = ref.get()
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    
    if "friends" in update_dict and update_dict["friends"]:
        existing_friends = existing.get("friends", [])
        new_friends = update_dict["friends"]
        update_dict["friends"] = list(set(existing_friends + new_friends))

    update_dict["id"] = user_id

    # Update only the provided fields
    ref.update(update_dict)

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

@app.get("/user/{user_id}/playlists")
def get_all_playlists_from(user_id: str):
    ref = db.reference(f"UserToPlaylists/{user_id}")
    data = ref.get()
    all_playlists = []
    for playlist_id in data:
        try: 
            all_playlists.append(get_playlist(playlist_id))
        except HTTPException:
            all_playlists.append({"playlist_id": "Not_found"})

    return all_playlists

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
    playlist_dict["date_created"] = datetime.datetime.now().isoformat()
    playlist_dict["last_updated"] = datetime.datetime.now().isoformat()

    new_ref.set(playlist_dict)
    us_to_pl(owner, new_id)
    
    return playlist_dict

def us_to_pl(user_id: str, playlist_id: str):
    ref = db.reference(f"UserToPlaylists/{user_id}")
    ref.update({playlist_id: True})
    return "Successful mapping User to Playlist."


@app.get("/playlist/{playlist_id}", response_model=Playlist)
def get_playlist(playlist_id: str):
    ref = db.reference(f"Playlists/{playlist_id}")
    data = ref.get()
    if not data:
        raise HTTPException(status_code=404, detail="Playlist not found")
    data["id"] = playlist_id
    return Playlist(**data)

@app.get("/playlist/{playlist_id}/songs")
def get_all_songs_from(playlist_id: str):
    ref = db.reference(f"PlaylistToSongs/{playlist_id}")
    data = ref.get()
    all_songs = []
    for song_id in data:
        try: 
            all_songs.append(get_song(song_id))
        except HTTPException:
            all_songs.append({"song_id": "Not_found"})

    return all_songs

@app.patch("/playlist/{playlist_id}", response_model=Playlist)
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
    ref = db.reference(f"Songs")
    new_ref = ref.push()
    new_id = new_ref.key

    data = get_yt_data(url)

    new_song = Song(id=new_id,
                    yt_id=data["yt_id"],
                    title=data["title"],
                    artist=data["channel"],
                    added_by=user_id,
                    link=url, 
                    playlist_id=playlist_id,
                    date_added = datetime.datetime.now().isoformat(),
                    date_released = data["date_released"]
                    )

    song_dict = new_song.model_dump()
    new_ref.set(song_dict)
    pl_to_song(playlist_id, new_id)

    return song_dict

def pl_to_song(playlist_id: str, song_id: str):
    ref = db.reference(f"PlaylistToSongs/{playlist_id}")
    ref.update({song_id: True})
    return

@app.get("/song/{song_id}", response_model=Song)
def get_song(song_id: str):
    ref = db.reference(f"Songs/{song_id}")
    data = ref.get()
    if not data:
        raise HTTPException(status_code=404, detail="Song not found")
    data["id"] = song_id
    return Song(**data)

## TODO: chnage to move song to pl? what else can we change?
@app.patch("/song/{song_id}", response_model=Song)
def patch_song(song_id: str, update: Song = Body(...)):
    update_dict = update.model_dump(exclude_unset=True)
    update_dict["id"] = song_id
    ref = db.reference(f"Songs/{song_id}")
    existing = ref.get()
    if not existing:
        raise HTTPException(status_code=404, detail="Song not found")
    
    ref.update(update_dict)
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
def create_comment(song_id: str, comment: Comment = Body(...)):
    ref = db.reference(f"Comments")
    new_ref = ref.push()
    new_id = new_ref.key

    comment_dict = comment.model_dump()
    comment_dict["id"] = new_id
    comment_dict["date"] = datetime.datetime.now().isoformat()
    comment_dict["song_id"] = song_id

    new_ref.set(comment_dict)
    song_to_comment(song_id, new_id)
    return comment_dict


def song_to_comment(song_id: str, comment_id: str):
    ref = db.reference(f"SongToComments/{song_id}")
    ref.update({comment_id: True})
    return "Successful mapping Song to Comment."


@app.get("/comment/{comment_id}", response_model=Comment)
def get_comment(comment_id: str):
    ref = db.reference(f"Comments/{comment_id}")
    data = ref.get()
    if not data:
        raise HTTPException(status_code=404, detail="Comment not found")
    data["id"] = comment_id
    return Comment(**data)

@app.patch("/comment/{comment_id}", response_model=Comment)
def patch_comment(comment_id: str, update: CommentUpdate = Body(...)):
    update_dict = update.model_dump(excude_unset = True)
    update_dict["id"] = comment_id
    update_dict["date"] = datetime.datetime.now().isoformat()
    ref = db.reference(f"Comments/{comment_id}")
    existing = ref.get()

    if not existing:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    ref.update(update_dict)
    
    updated_data = ref.get()
    return Comment(**updated_data)

@app.delete("/comment/{comment_id}")
def delete_comment(comment_id: str):
    ref = db.reference(f"Comments/{comment_id}")
    data = ref.get()
    if not data:
        raise HTTPException(status_code=404, detail="Comment not found")
    ref.delete()
    remove_comment_map(comment_id)
    return {"message": f"Comment {comment_id} deleted successfully"}

def remove_comment_map(comment_id: str):
    ref = db.reference(f"SongToComments/{comment_id}")
    data = ref.get()
    if not data:
        raise HTTPException(status_code=404, detail="Comment not found in Song to Comments mapping")
    ref.delete()

# -------------------- REACTION METHODS --------------------
@app.post("/reaction/", response_model=Reaction)
def create_reaction(comment_id: str, reaction: Reaction = Body(...)):
    ref = db.reference(f"Reactions")
    new_ref = ref.push()
    new_id = new_ref.key

    reaction_dict = reaction.model_dump()
    reaction_dict["id"] = new_id
    new_ref.set(reaction_dict)
    comment_to_reaction(comment_id, new_id)
    return reaction_dict

def comment_to_reaction(comment_id: str, reaction_id: str):
    ref = db.reference(f"SongToComments/{comment_id}")
    ref.update({reaction_id: True})
    return "Successful mapping Comment to Reactions."


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
    remove_reaction_map(reaction_id)
    return {"message": f"Reaction {reaction_id} deleted successfully"}


def remove_reaction_map(reaction_id: str):
    ref = db.reference(f"CommentToReaction/{reaction_id}")
    data = ref.get()
    if not data:
        raise HTTPException(status_code=404, detail="Reaction not found in Comment to Reactions mapping")
    ref.delete()

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

    channel = item["snippet"]["channelTitle"]
    match = re.search(r"(.+) - Topic", channel)
    
    if match:
        channel = match.group(1)
    
    video_info = {
        "yt_id": video_id,
        "title": item["snippet"]["title"],
        "channel": channel,
        "thumbnail": item["snippet"]["thumbnails"]["default"]["url"],
        "duration": item["contentDetails"]["duration"],
        "date_released": item["snippet"]["publishedAt"]
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

# TODO add date module to automatically update 


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
        