import os
import json
import requests

ADS_DEV_KEY = os.environ.get("ADS_DEV_KEY")
LIBRARY_ID = "O622yT9iQCKJDhjyd2028w"  # Your ADS Library ID

if not ADS_DEV_KEY:
    print("Error: ADS_DEV_KEY environment variable not set.")
    exit(1)

headers = {
    "Authorization": f"Bearer {ADS_DEV_KEY}"
}

# 1. Fetch All Library Bibcodes (Paginated)
print("1. Fetching library bibcode list...")
all_bibcodes = []
start = 0
rows_per_page = 2000

while True:
    lib_resp = requests.get(
        f"https://api.adsabs.harvard.edu/v1/biblib/libraries/{LIBRARY_ID}",
        headers=headers,
        params={"rows": rows_per_page, "start": start}
    )
    if lib_resp.status_code != 200:
        print(f"Failed to fetch library bibcodes: {lib_resp.status_code}")
        exit(1)
        
    lib_data = lib_resp.json()
    page_bibcodes = lib_data.get("documents", [])
    if isinstance(page_bibcodes, dict):
        page_bibcodes = page_bibcodes.get("bibcodes", [])
        
    if not page_bibcodes:
        break
        
    all_bibcodes.extend(page_bibcodes)
    total_expected = lib_data.get("metadata", {}).get("num_documents", 0)
    
    if len(page_bibcodes) < rows_per_page or (total_expected > 0 and len(all_bibcodes) >= total_expected):
        break
    start += rows_per_page

print(f"Retrieved {len(all_bibcodes)} total bibcodes from library.")

# 2. Fetch Detailed Metadata Using BigQuery Endpoint
print("2. Querying ADS BigQuery API for complete paper metadata...")
bigquery_url = "https://api.adsabs.harvard.edu/v1/search/bigquery"
fields_to_fetch = "bibcode,title,bibstem,property,year,pubdate,pub,citation_count,citation,keyword,facility,instrument,grant"

payload_data = f"bibcode\n" + "\n".join(all_bibcodes)

params = {
    "q": "*:*",
    "fl": fields_to_fetch,
    "rows": len(all_bibcodes)
}

bq_headers = {
    "Authorization": f"Bearer {ADS_DEV_KEY}",
    "Content-Type": "big-query"
}

query_resp = requests.post(
    bigquery_url,
    headers=bq_headers,
    params=params,
    data=payload_data
)

detailed_records = []
if query_resp.status_code == 200:
    detailed_records = query_resp.json().get("response", {}).get("docs", [])
    print(f"Successfully retrieved metadata for {len(detailed_records)} papers!")
else:
    print(f"BigQuery endpoint failed ({query_resp.status_code}): {query_resp.text}")
    exit(1)

# 3. Calculate Refereed-Specific Summary Statistics
refereed_records = [
    doc for doc in detailed_records 
    if "REFEREED" in doc.get("property", [])
]

refereed_citations = sum(doc.get("citation_count", 0) for doc in refereed_records)
total_citations_all = sum(doc.get("citation_count", 0) for doc in detailed_records)

avg_refereed_citations = (
    round(refereed_citations / len(refereed_records), 1) 
    if refereed_records else 0
)

# Calculate H-Index specifically on refereed papers
ref_citation_list = sorted(
    [doc.get("citation_count", 0) for doc in refereed_records], 
    reverse=True
)
h_index = 0
for idx, count in enumerate(ref_citation_list):
    if count >= idx + 1:
        h_index = idx + 1
    else:
        break

# 4. Save Output to docs/data.json
os.makedirs("docs", exist_ok=True)
output_data = {
    "num_documents": len(all_bibcodes),
    "metrics": {
        "total_papers": len(all_bibcodes),
        "refereed_papers": len(refereed_records),
        "total_citations": refereed_citations,
        "all_citations": total_citations_all,
        "h_index": h_index,
        "avg_citations": avg_refereed_citations
    },
    "papers": detailed_records
}

with open("docs/data.json", "w") as f:
    json.dump(output_data, f, indent=2)

print(f"Export completed successfully to docs/data.json!")
