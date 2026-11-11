from fastapi import FastAPI

from app.routers import auth, customers, enquiries, users

app = FastAPI(title="Business Ops API")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(customers.router)
app.include_router(enquiries.router)


@app.get("/")
def home():
    return {"message": "Business Ops API is running"}