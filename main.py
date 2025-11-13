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
        