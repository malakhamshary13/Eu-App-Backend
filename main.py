from fastapi import FastAPI
from db.database import Base, engine
from modules.users.router import router as auth_router
from modules.users import models

Base.metadata.create_all(bind=engine)

app = FastAPI(title="EU App Backend API")

app.include_router(auth_router)

@app.get("/")
def root():
    return {"message": "API is running"}