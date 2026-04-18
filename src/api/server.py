import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.stream import router as stream_router

app = FastAPI(title="Manga/Anime Streaming API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "HEAD"],
    allow_headers=["*"],
)

app.include_router(stream_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
