from fastapi import FastAPI

app = FastAPI(title="Business Ops API")


@app.get("/")
def home():
    return {"message": "Business Ops API is running"}