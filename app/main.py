from fastapi import FastAPI

app = FastAPI(title="Inventário Server")

@app.get("/")
def home():
    return {"status": "ok"}