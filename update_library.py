import os
import json
import requests

ADS_DEV_KEY = os.environ.get("ADS_DEV_KEY")
LIBRARY_ID = "O622yT9iQCKJDhjyd2028w"  # Your ADS Library ID

if not ADS_DEV_KEY:
    print("Error: ADS_DEV_KEY environment variable not set.")
    exit(1)

headers = {
    "Authorization": f"Bearer {ADS_DEV_KEY}",
    "Content-Type": "application/json"
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

print(f"Retrieved {len(all_bibcodes)} bibcodes from library.")

# 2. Fetch Detailed Metadata for All Bibcodes
print("2. Fetching detailed metadata from ADS Search API...")
search_url = "https://api.adsabs.harvard.edu/v1/search/query"
fields_to_fetch = "bibcode,title,bibstem,property,year,pubdate,pub,citation_count,citation,keyword,facility,instrument,grant"

detailed_records = []
chunk_size = 1000  # Query bibcodes in safe POST chunks

for i in range(0, len(all_bibcodes), chunk_size):
    chunk_bibcodes = all_bibcodes[i:i + chunk_size]
    bibcode_query = "bibcode:(" + " OR ".join(chunk_bibcodes) + ")"
    
    payload = {
        "q": bibcode_query,
        "fl": fields_to_fetch,
        "rows": len(chunk_bibcodes)
    }
    
    query_resp = requests.post(search_url, headers=headers, json=payload)
    if query_resp.status_code == 200:
        docs = query_resp.json().get("response", {}).get("docs", [])
        detailed_records.extend(docs)
        print(f"   Fetched {len(detailed_records)} / {len(all_bibcodes)} detailed records...")
    else:
        print(f"   Warning: Failed chunk fetch ({query_resp.status_code}): {query_resp.text}")

# 3. Calculate Summary Statistics
total_citations = sum(doc.get("citation_count", 0) for doc in detailed_records)
avg_citations = round(total_citations / len(detailed_records), 1) if detailed_records else 0

# Calculate H-Index locally from records
citation_list = sorted([doc.get("citation_count", 0) for doc in detailed_records], reverse=True)
h_index = 0
for idx, count in enumerate(citation_list):
    if count >= idx + 1:
        h_index = idx + 1
    else:
        break

# 4. Save to docs/data.json
os.makedirs("docs", exist_ok=True)
output_data = {
    "num_documents": len(all_bibcodes),
    "metrics": {
        "total_papers": len(all_bibcodes),
        "total_citations": total_citations,
        "h_index": h_index,
        "avg_citations": avg_citations
    },
    "papers": detailed_records
}

with open("docs/data.json", "w") as f:
    json.dump(output_data, f, indent=2)

print(f"Successfully exported {len(detailed_records)} rich records to docs/data.json!")
