from fastapi import FastAPI, HTTPException, Body
import firebase_admin
from firebase_admin import credentials, db

from Entities import User, Playlist, Song, Comment, Reaction

# Initialize Firebase
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    "databaseURL": "https://sharedplay-5eb60-default-rtdb.firebaseio.com"
})

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
