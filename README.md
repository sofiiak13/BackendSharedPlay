# BackendSharedPlay

This repository contains the backend REST API for the SharedPlay mobile application (you may see app frontend here https://github.com/sofiiak13/SharedPlay).
It handles authentication, data persistence, and business logic within the app.

## Responsibilities

- User authentication and authorization (through Google account only)
- CRUD methods for User, Playlist, Song and Comment entities
- Request validation and error handling
- Communication with a real-time database
- Imitates SQL-like structure in a non-SQL environment

## Tech Stack

- **Language:** Python 
- **Framework:** FastAPI
- **Database:** Firebase Realtime DB
- **Authentication:** Firebase Admin SDK
- **Hosting Server:** Railway
