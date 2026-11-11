from fastapi import FastAPI

from app.routers import auth, customers, users

app = FastAPI(title="Business Ops API")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(customers.router)


@app.get("/")
def home():
    return {"message": "Business Ops API is running"}