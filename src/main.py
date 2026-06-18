import logging
import random
import sys
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app_name = "backsanta"
port = 7070
matches: dict[str, str] = {}
random_gen = random.Random()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(f"{app_name}.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(app_name)



class NamesWrapper(BaseModel):
    names: dict[str, list[str]]


class NameTokenPair(BaseModel):
    name: str
    token: str


def validate_exclusions(names: dict[str, list[str]]) -> None:
    all_names_set = set(names.keys())
    for name, exclusions in names.items():
        current_exclusion_set = set(exclusions)
        current_exclusion_set.add(name)
        if all_names_set == current_exclusion_set:
            raise HTTPException(status_code=400, detail=f"Exclude list for {name} contains all names")


def generate_matches(names: dict[str, list[str]]) -> list[NameTokenPair]:
    validate_exclusions(names)
    matches.clear()

    participants: list[NameTokenPair] = []
    for _ in range(10):
        participants.clear()
        names_taken: list[str] = []

        for name, excludes in names.items():
            draw_pool: set[str] = set(names.keys())
            draw_pool.discard(name)
            for exclude in excludes:
                draw_pool.discard(exclude)
            for taken in names_taken:
                draw_pool.discard(taken)

            if not draw_pool:
                logger.info(f"For name {name} there are no options to draw from\n")
                continue

            target = random_gen.choice(list(draw_pool))
            names_taken.append(target)

            token = str(uuid.uuid4())
            matches[token] = target

            participants.append(NameTokenPair(name=name, token=token))

        if len(participants) == len(names):
            return participants

    raise HTTPException(status_code=500, detail="could not generate valid pairings after 10 attempts")


def find_target(token: str) -> str:
    target = matches.pop(token, None)
    if target is None:
        raise HTTPException(status_code=400, detail="token not found")
    return target




@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    logger.info(f"{app_name} server starting on :{port}")
    yield
    logger.info(f"{app_name} server shutting down")


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": exc.status_code,
            "type": exc.__class__.__name__,
            "detail": exc.detail,
        },
    )


@app.post("/matches")
async def generate_links(body: NamesWrapper) -> list[NameTokenPair]:
    return generate_matches(body.names)


@app.get("/matches/{token}")
async def find_match(token: str) -> dict[str, str]:
    return {"target": find_target(token)}


@app.delete("/matches", status_code=204)
async def clear_matches() -> None:
    matches.clear()
    return None


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=port, log_config=None)


if __name__ == "__main__":
    main()
