from fastapi import FastAPI
from .database import Base, engine
from . import models

app = FastAPI(title="Inventário Server")

Base.metadata.create_all(bind=engine)

@app.get("/")
def home():
    return {"status": "ok"}