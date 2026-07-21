import json
import requests


BASE_URL = "https://api.fda.gov/drug/enforcement.json"

def fetch_recalls (search: str, limit:int = 5)-> dict:
    """Fetch recalls matching a search query. Returns parsed JSON."""
    params = {"search": search, "limit": limit}
    response = requests.get(BASE_URL, params=params, timeout=10)
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    data = fetch_recalls('classification:"Class I"', limit=5)

    total = data["meta"]["results"]["total"]
    print(f"Total Class I recalls in openFDA: {total}\n")

    for r in data["results"]:
        print(f"Recall:  {r.get('recall_number', 'N/A')}")
        print(f"Product: {r.get('product_description', 'N/A')[:80]}")
        print(f"Reason:  {r.get('reason_for_recall', 'N/A')[:80]}")
        print(f"Date:    {r.get('recall_initiation_date', 'N/A')}")
        print("-" * 60)
    
    # Add this after the for-loop, still inside the __main__ block
    ongoing = sum(1 for r in data["results"] if r.get("status") == "Ongoing")
    completed = sum(1 for r in data["results"] if r.get("status") == "Completed")
    print(f"\nOngoing: {ongoing}, Completed: {completed}")