from fastapi import FastAPI
import firebase_admin
import json
from firebase_admin import credentials
from dotenv import load_dotenv
import os

from Routes import songs, playlists, users, comments, reactions

load_dotenv()

# Initialize Firebase
firebase_json = os.getenv("FIREBASE_SERVICE_ACCOUNT")
database_url = os.getenv("FIREBASE_DATABASE_URL")

if firebase_json:
    # Running on Railway or with env var
    service_account_info = json.loads(firebase_json)
    cred = credentials.Certificate(service_account_info)
elif os.path.exists("serviceAccountKey.json"):
    # Running locally
    cred = credentials.Certificate("serviceAccountKey.json")
else:
    raise RuntimeError("Firebase credentials not found")

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        "databaseURL": database_url
    })

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Welcome to SharedPlay API"}

app.include_router(users.router)
app.include_router(playlists.router)
app.include_router(songs.router)
app.include_router(comments.router)
app.include_router(reactions.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
        