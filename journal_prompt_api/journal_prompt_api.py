"Main routing file for the API"
from fastapi import FastAPI

api = FastAPI()


@api.get("/")
def read_root() -> dict[str, str]:
    "Declare a welcome message at root"
    return {"message": "This is the Journal Prompt API"}
