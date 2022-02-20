"Main routing file for the API"
import logging
import os
import secrets
from typing import cast

import databases
import sqlalchemy
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from sqlalchemy.sql.expression import func

logging.basicConfig(
    format="%(asctime)s, %(levelname)s:%(message)s", datefmt="%m/%d/%Y %I:%M:%S %p"
)

DATABASE_URL = os.environ["DATABASE_URL"]
OLD_POSTGRES_FORMAT = "postgres://"
if DATABASE_URL.startswith(OLD_POSTGRES_FORMAT):
    DATABASE_URL = "postgresql://" + DATABASE_URL[len(OLD_POSTGRES_FORMAT) :]

database = databases.Database(DATABASE_URL)

metadata = sqlalchemy.MetaData()

prompts = sqlalchemy.Table(
    "prompts",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("text", sqlalchemy.String),
)


engine = sqlalchemy.create_engine(DATABASE_URL)
metadata.create_all(engine)


class Prompt(BaseModel):
    "A journal prompt"
    id: int
    text: str


class PromptIn(BaseModel):
    "A new journal prompt"
    text: str


api = FastAPI()
security = HTTPBasic()


@api.on_event("startup")
async def startup() -> None:
    "Commands to run at api startup"
    await database.connect()


@api.on_event("shutdown")
async def shutdown() -> None:
    "Commands to run at api shutdown"
    await database.disconnect()


@api.get("/")
def read_root() -> dict[str, str]:
    "Declare a welcome message at root"
    return {"message": "This is the Journal Prompt API"}


@api.get("/random", response_model=Prompt)
async def random() -> Prompt | None:
    "Returns a random journal prompt"
    query = prompts.select().order_by(func.random())
    row = cast(Prompt | None, await database.fetch_one(query=query))
    return row


def authenticate(
    credentials: HTTPBasicCredentials = Depends(security),
) -> HTTPBasicCredentials:
    "Authenticates user and returns credentials used"
    correct_username = os.environ.get("AUTH_USERNAME", "")
    correct_password = os.environ.get("AUTH_PASSWORD", "")
    matching_username = secrets.compare_digest(credentials.username, correct_username)
    matching_password = secrets.compare_digest(credentials.password, correct_password)
    if (
        not correct_username
        or not correct_password
        or not (matching_username and matching_password)
    ):
        logging.error("Invalid username or password for user %s", credentials.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials


@api.post("/prompts/", response_model=Prompt)
async def create_prompt(
    prompt: PromptIn, credentials: HTTPBasicCredentials = Depends(authenticate)
) -> dict[str, str]:
    "Create a new prompt"
    logging.info(
        'User "%s" is creating a prompt with contents: "%s"',
        credentials.username,
        prompt,
    )
    query = prompts.insert().values(text=prompt.text.strip())
    last_record_id = await database.execute(query)
    logging.info("Created entry with id %d", last_record_id)
    return {**prompt.dict(), "id": last_record_id}
