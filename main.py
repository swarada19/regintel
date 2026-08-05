import requests
from fastapi import FastAPI
from pydantic import BaseModel

from explore_fda import fetch_recalls

app = FastAPI()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/ping")
def ping() -> dict:
    return {"message": "pong"}


class Recall(BaseModel):
    recall_number: str
    product_description: str
    reason_for_recall: str
    recall_initiation_date: str
    status: str


@app.get("/recalls", response_model=list[Recall])
def get_recalls(drug: str, limit: int = 5):
    search = f'product_description:"{drug}"'

    try:
        data = fetch_recalls(search, limit=limit)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            data = {}
        else:
            raise

    raw_recalls = data.get("results", [])

    return [
        Recall(
            recall_number=r.get("recall_number", ""),
            product_description=r.get("product_description", ""),
            reason_for_recall=r.get("reason_for_recall", ""),
            recall_initiation_date=r.get("recall_initiation_date", ""),
            status=r.get("status", ""),
        )
        for r in raw_recalls
    ]