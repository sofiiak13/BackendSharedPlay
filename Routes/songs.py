from fastapi import APIRouter, Body, HTTPException, Query, Depends
from Modules import Song
from firebase_admin import db

from urllib.parse import urlparse, parse_qs
import datetime
import re

from dotenv import load_dotenv
import os
from googleapiclient.discovery import build

from auth import get_current_user

router = APIRouter(
    prefix="/song",
    tags=["songs"]
)

load_dotenv()

# -------------------- SONG METHODS --------------------

@router.post("")
def create_song(
    url: str = Query(...),
    playlist_id: str = Query(...),
    user_id: str = Query(...),
    _: str = Depends(get_current_user)
):
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

@router.get("/{song_id}", response_model=Song)
def get_song(song_id: str, _: str = Depends(get_current_user)):
    ref = db.reference(f"Songs/{song_id}")
    data = ref.get()
    if not data:
        raise HTTPException(status_code=404, detail="Song not found")
    data["id"] = song_id
    return Song(**data)

## TODO: chnage to move song to pl? what else can we change?
# @router.patch("/{song_id}", response_model=Song)
# def patch_song(song_id: str, update: Song = Body(...)):
#     update_dict = update.model_dump(exclude_unset=True)
#     update_dict["id"] = song_id
#     ref = db.reference(f"Songs/{song_id}")
#     existing = ref.get()
#     if not existing:
#         raise HTTPException(status_code=404, detail="Song not found")
    
#     ref.update(update_dict)
#     updated_data = ref.get()
#     return Song(**updated_data)

def remove_song_from(playlist_id: str, song_id: str):
    ref = db.reference(f"PlaylistToSongs/{playlist_id}/{song_id}")
    data = ref.get()
    if not data:
        raise HTTPException(status_code=404, detail="Song not found in mapping")
    ref.delete()

@router.delete("/{song_id}")
def delete_song(song_id: str, _: str = Depends(get_current_user)):
    ref = db.reference(f"Songs/{song_id}")
    data = ref.get()
    if not data:
        raise HTTPException(status_code=404, detail="Song not found")
    ref.delete()
    remove_song_from(data["playlist_id"], song_id)
    return {"message": f"Song {song_id} deleted successfully"}


@router.get("/{playlist_id}/songs")
def get_all_songs_for(playlist_id: str, _: str = Depends(get_current_user)):
    ref = db.reference(f"PlaylistToSongs/{playlist_id}")
    data = ref.get()
    all_songs = []

    if data == None:
        return all_songs
    
    for song_id in data:
        try: 
            all_songs.append(get_song(song_id))
        except HTTPException:
            print("Song", song_id, "not found in mapping. Must have be deleted earlier.")

    return all_songs


# -------------------- YouTube Data --------------------

def get_youtube_client():
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise ValueError("Missing YOUTUBE_API_KEY in environment variables")
    return build("youtube", "v3", developerKey=api_key)


def get_yt_data(url: str):
    video_id = extract_video_id(url)
    if not video_id:
        return {"error": "Invalid YouTube URL"}

    youtube = get_youtube_client()
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