from fastapi import FastAPI, HTTPException, Body
import firebase_admin
from firebase_admin import credentials, db
from dotenv import load_dotenv
import os
from googleapiclient.discovery import build
from urllib.parse import urlparse, parse_qs

from Entities import User, Playlist, Song, Comment, Reaction

# Initialize Firebase
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    "databaseURL": "https://sharedplay-5eb60-default-rtdb.firebaseio.com"
})

# Initialize YouTube Data API
load_dotenv()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

app = FastAPI()

# USER METHODS
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
    return user_dict


@app.get("/user/{user_id}", response_model=User)
def get_user(user_id: str):
    ref = db.reference(f"Users/{user_id}")
    data = ref.get()

    if not data:
        raise HTTPException(status_code=404, detail="User not found")

    return User(**data)


@app.patch("/user/{user_id}", response_model=User)
def patch_user(user_id: str, update: User = Body(...)):
    # in case user_id is missing in body
    update["id"] = user_id
    ref = db.reference(f"Users/{user_id}")
    existing = ref.get()
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")

    # Only update fields that are not None
    ref.update({k: v for k, v in update.model_dump().items() if v is not None})

    updated_data = ref.get()
    return User(**updated_data)


@app.delete("/user/{user_id}")
def delete_user(user_id: str):
    ref = db.reference(f"Users/{user_id}")

    # Fetch the user first to see if it exists
    data = ref.get()

    if not data:
        raise HTTPException(status_code=404, detail="User not found")
    
    data = ref.delete()
    return {"message": f"User {user_id} deleted successfully"}


# PLAYLIST METHODS
@app.get("/playlist/{user_id}/{playlist_id}", response_model=Playlist)
def get_playlist(user_id: str, playlist_id: str):
    ref = db.reference(f"Users/{user_id}/playlists/{playlist_id}")
    data = ref.get()

    if not data:
        raise HTTPException(status_code=404, detail="Playlist not found")

    data["id"] = playlist_id
    return Playlist(**data)


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
        "video_id": video_id,
        "title": item["snippet"]["title"],
        "channel": item["snippet"]["channelTitle"],
        "thumbnail": item["snippet"]["thumbnails"]["default"]["url"],
        "duration": item["contentDetails"]["duration"],
        "views": item["statistics"].get("viewCount")
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