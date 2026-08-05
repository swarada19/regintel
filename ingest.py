import json
from pathlib import Path

import requests
from langchain_core.documents import Document

from explore_fda import fetch_recalls

DATA_DIR = Path("data")
PDF_DIR = DATA_DIR / "pdfs"
CORPUS_PATH = DATA_DIR / "corpus.jsonl"

RECALL_LIMIT = 1000

# fda.gov's bot-detection blocks requests' default User-Agent with a 404
# "apology" page instead of the PDF, so a browser-like one is required.
DOWNLOAD_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}

# FDA guidance documents on drug manufacturing quality / CGMP — verified
GUIDANCE_PDFS = [
    ("cgmp-guidance-for-human-drugs", "https://www.fda.gov/media/88905/download"),
    (
        "process-validation-general-principles-and-practices",
        "https://www.fda.gov/files/drugs/published/Process-Validation--General-Principles-and-Practices.pdf",
    ),
    (
        "quality-systems-approach-to-pharmaceutical-cgmp-regulations",
        "https://www.fda.gov/media/71023/download",
    ),
    (
        "data-integrity-and-compliance-with-drug-cgmp-qa",
        "https://www.fda.gov/media/119267/download",
    ),
    (
        "q7-gmp-guidance-for-active-pharmaceutical-ingredients",
        "https://www.fda.gov/media/71518/download",
    ),
    ("compliance-program-7356-002f-api-inspections", "https://www.fda.gov/media/187860/download"),
]


def fetch_recall_documents(limit: int = RECALL_LIMIT) -> list[Document]:
    """Pull the most recent openFDA recalls, unfiltered, as Documents."""
    data = fetch_recalls(limit=limit, sort="recall_initiation_date:desc")
    raw_recalls = data.get("results", [])

    documents = []
    for r in raw_recalls:
        product = r.get("product_description", "")
        reason = r.get("reason_for_recall", "")
        documents.append(
            Document(
                page_content=f"{product}. Reason for recall: {reason}",
                metadata={
                    "source": "openfda",
                    "doc_type": "recall",
                    "recall_number": r.get("recall_number", ""),
                    "date": r.get("recall_initiation_date", ""),
                    "status": r.get("status", ""),
                    "classification": r.get("classification", ""),
                },
            )
        )
    return documents


def download_guidance_pdfs(pdfs: list[tuple[str, str]], dest_dir: Path) -> list[tuple[Path, str]]:
    """Download each (slug, url) pair to dest_dir. Returns [(local_path, url)]."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    downloaded = []
    for slug, url in pdfs:
        path = dest_dir / f"{slug}.pdf"
        response = requests.get(url, headers=DOWNLOAD_HEADERS, timeout=30)
        response.raise_for_status()
        path.write_bytes(response.content)
        downloaded.append((path, url))
    return downloaded


def pdf_to_documents(path: Path, url: str) -> list[Document]:
    """One Document per non-empty page of a guidance PDF."""
    from pypdf import PdfReader

    reader = PdfReader(path)
    documents = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if not text.strip():
            continue
        documents.append(
            Document(
                page_content=text,
                metadata={
                    "source": path.name,
                    "doc_type": "guidance",
                    "title": path.stem.replace("-", " "),
                    "page": page_number,
                    "url": url,
                },
            )
        )
    return documents


def write_corpus(documents: list[Document], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for doc in documents:
            f.write(json.dumps({"page_content": doc.page_content, "metadata": doc.metadata}))
            f.write("\n")


if __name__ == "__main__":
    print("Fetching recall records from openFDA...")
    recall_docs = fetch_recall_documents()
    print(f"  {len(recall_docs)} recall Documents")

    print("Downloading FDA guidance PDFs...")
    pdf_paths = download_guidance_pdfs(GUIDANCE_PDFS, PDF_DIR)
    print(f"  {len(pdf_paths)} PDFs downloaded to {PDF_DIR}/")

    print("Extracting guidance PDF text...")
    guidance_docs = []
    for path, url in pdf_paths:
        guidance_docs.extend(pdf_to_documents(path, url))
    print(f"  {len(guidance_docs)} guidance-page Documents")

    all_docs = recall_docs + guidance_docs
    write_corpus(all_docs, CORPUS_PATH)
    print(f"\nWrote {len(all_docs)} total Documents to {CORPUS_PATH}")
