from fastapi import FastAPI

from app.routers import auth, customers, enquiries, tasks, users

app = FastAPI(title="Business Ops API")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(customers.router)
app.include_router(enquiries.router)
app.include_router(tasks.router)


@app.get("/")
def home():
    return {"message": "Business Ops API is running"}