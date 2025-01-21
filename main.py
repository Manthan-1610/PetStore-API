from fastapi import FastAPI
from .routers import pets, users, store

app = FastAPI()

app.include_router(pets.router)
app.include_router(users.router)
app.include_router(store.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)