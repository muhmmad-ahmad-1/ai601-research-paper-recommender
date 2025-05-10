import json
import os
from src.storage.zilliz_storage import ZillizStorage

# Load paper JSON file
with open("input.json", "r", encoding="utf-8") as f:
    paper_data = json.load(f)

# Initialize ZillizStorage
zilliz = ZillizStorage(
    uri="https://in03-f83094c3a6039fc.serverless.gcp-us-west1.cloud.zilliz.com",
    token="202ef9fdae30c34d333b6b4cb4c6ca86eef7f6ed0ebef38064e36db837728f7ae7c3ba7a04ad9e21b3d8ee31d5aa2c4470262574",
    collection_name=os.getenv("ZILLIZ_COLLECTION_NAME", "papers")
)

# Parse and clean up citations from LaTeX format
raw_citations = paper_data.get("citations", "")
citations_list = []

if isinstance(raw_citations, str) and "\\bibitem" in raw_citations:
    raw = raw_citations.replace("\\begin{thebibliography}{100}", "").replace("\\end{thebibliography}", "")
    entries = raw.split("\\bibitem")
    for entry in entries:
        entry = entry.strip()
        if entry:
            citations_list.append(entry)

# Final parsed paper dictionary
parsed_paper = {
    "paper_id": paper_data.get("paper_id", ""),
    "paper_url": paper_data.get("paper_url", ""),
    "title": paper_data.get("title", ""),
    "year": paper_data.get("year", ""),
    "abstract": paper_data.get("abstract", ""),
    "citations": citations_list,
    "authors": paper_data.get("authors", []),
    "sections": paper_data.get("sections", []),
}

# Store the paper as chunks
chunk_ids = zilliz.store_paper(parsed_paper)
print(f"Stored paper in {len(chunk_ids)} chunks.")

# Search similar papers
query = parsed_paper["abstract"]
similar_papers = zilliz.search_papers(query=query, limit=5)

print("Similar papers found:")
for p in similar_papers:
    print(f"- {p['title']} - {p['paper_url']} (Score: {p['score']:.4f})")

# # Retrieve all chunks for a specific paper
paper_id = parsed_paper["paper_id"]
chunks = zilliz.get_all_chunks_for_paper(paper_id)
print(f"Retrieved {len(chunks)} chunks for paper {paper_id}.")
