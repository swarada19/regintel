from typing import Literal

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from explore_fda import fetch_recalls
from llm import get_llm, invoke_with_retry
from prompts import RECALL_ASSESSMENT_PROMPT

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
    classification: str


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
            classification=r.get("classification", ""),
        )
        for r in raw_recalls
    ]


class RecallAssessment(BaseModel):
    summary: str = Field(description="two-sentence plain-English summary for a patient")
    severity: Literal["high", "medium", "low"]
    affected_population: str = Field(
        description="who is at risk, or 'not specified' if the record does not say"
    )
    root_cause_category: Literal[
        "contamination",
        "sterility_failure",
        "labeling_error",
        "potency_deviation",
        "packaging_defect",
        "stability_failure",
        "cgmp_deviation",
        "other",
    ] = Field(
        description=(
            "the underlying failure that caused the recall. Choose 'other' when no "
            "listed category is a clear fit — do not force an approximate match."
        )
    )


# Built once at import rather than per request — each construction opens its own
# HTTP client, and neither the model nor the schema varies between calls.
assessment_llm = get_llm(temperature=0).with_structured_output(RecallAssessment)


@app.post("/summarize-recall", response_model=RecallAssessment)
def summarize_recall(recall: Recall) -> RecallAssessment:
    messages = RECALL_ASSESSMENT_PROMPT.format_messages(
        product_description=recall.product_description,
        reason_for_recall=recall.reason_for_recall,
        classification=recall.classification,
        status=recall.status,
    )

    try:
        return invoke_with_retry(assessment_llm, messages)
    except Exception as error:
        # The model failed twice, or the call failed for a reason retrying won't fix.
        # 502 rather than 500: the fault is upstream, not in this service.
        raise HTTPException(
            status_code=502, detail=f"Could not assess this recall: {error}"
        ) from error