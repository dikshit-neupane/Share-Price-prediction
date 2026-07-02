# main.py — add this
from fastapi import FastAPI
from signup import router as signup_router
from login import router as login_router

app = FastAPI()

app.include_router(signup_router)
app.include_router(login_router)