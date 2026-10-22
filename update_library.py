import os
import json
import requests

# 1. Replace with your actual ADS Library ID from your seed run
LIBRARY_ID = "O622yT9iQCKJDhjyd2028w"

# Fetch token securely from GitHub Secrets
token = os.environ.get("ADS_DEV_KEY")

if not token:
    print("Error: ADS_DEV_KEY environment variable not found!")
    exit(1)

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# 2. Build Airtight Search Clauses
ztf_clause = 'abs:("Zwicky Transient Facility" OR "ZTF") OR ack:("1440341" OR "2034437" OR "0965661" OR "1545949")'
iptf_clause = 'abs:("Intermediate Palomar Transient Factory" OR "iPTF") OR ack:("1313484")'

# Requires "PTF" to be full string, exact grant, or acronym strictly paired with astronomy terms
ptf_clause = 'abs:("Palomar Transient Factory") OR ack:("0838126") OR (abs:"PTF" AND abs:("survey" OR "transient" OR "supernova" OR "photometry" OR "telescope" OR "optical" OR "astronomy"))'

hale_clause = 'ack:("Hale Telescope" OR "Palomar Observatory" OR "Caltech Optical Observatories" OR "P200") OR facility:"Palomar"'

# Direct exclusions for false positive terms and non-astronomy domains
exclusions = 'NOT abs:("pedotransfer" OR "soil water" OR "flash flood" OR "hill torrents" OR "hydrology" OR "pedology") NOT bibstem:("GCN" OR "ATel" OR "IAUC")'

# Search query looking back 14 days with strict database, refereed, and scope constraints
recent_query = (
    f"(({ztf_clause}) OR ({iptf_clause}) OR ({ptf_clause}) OR ({hale_clause})) "
    f"AND database:astronomy AND property:refereed AND entdate:[NOW-14DAYS TO NOW] {exclusions}"
)

search_params = {
    "q": recent_query,
    "fl": "bibcode",
    "rows": 500
}

print("Checking NASA ADS for newly indexed papers from the past 14 days...")

response = requests.get(
    "https://api.adsabs.harvard.edu/v1/search/query",
    headers=headers,
    params=search_params
)

if response.status_code == 200:
    docs = response.json()["response"]["docs"]
    new_bibcodes = [doc["bibcode"] for doc in docs if "bibcode" in doc]
    
    print(f"Found {len(new_bibcodes)} matching paper(s) indexed recently.")
    
    if new_bibcodes:
        push_data = {"bibcode": new_bibcodes, "action": "add"}
        push_resp = requests.post(
            f"https://api.adsabs.harvard.edu/v1/biblib/documents/{LIBRARY_ID}",
            headers=headers,
            json=push_data
        )
        if push_resp.status_code == 200:
            print(f"Successfully appended {len(new_bibcodes)} paper(s) to ADS Library {LIBRARY_ID}.")
        else:
            print(f"Failed to update library: {push_resp.status_code} - {push_resp.text}")
    else:
        print("No new matching papers found this week. Library is up to date!")
else:
    print(f"ADS Query failed with status code {response.status_code}: {response.text}")
    exit(1)

# =====================================================================
# 3. Export FULL Library Contents (Paginated) to docs/data.json
# =====================================================================
print("\nFetching full library contents with pagination to update docs/data.json...")

all_bibcodes = []
start = 0
rows_per_page = 2000  # ADS maximum per request

while True:
    print(f"Fetching records starting at index {start}...")
    lib_resp = requests.get(
        f"https://api.adsabs.harvard.edu/v1/biblib/libraries/{LIBRARY_ID}",
        headers=headers,
        params={"rows": rows_per_page, "start": start}
    )
    
    if lib_resp.status_code != 200:
        print(f"Failed to fetch library contents: {lib_resp.status_code} - {lib_resp.text}")
        exit(1)
        
    lib_data = lib_resp.json()
    
    # Extract bibcodes from current page
    if isinstance(lib_data.get("documents"), list):
        page_bibcodes = lib_data["documents"]
    elif isinstance(lib_data.get("documents"), dict):
        page_bibcodes = lib_data["documents"].get("bibcodes", [])
    else:
        page_bibcodes = []
        
    if not page_bibcodes:
        break  # No more bibcodes returned
        
    all_bibcodes.extend(page_bibcodes)
    
    # Get total count reported by ADS metadata
    total_expected = lib_data.get("metadata", {}).get("num_documents", 0)
    
    # Break loop if we've collected all documents or page returned less than max
    if len(page_bibcodes) < rows_per_page or (total_expected > 0 and len(all_bibcodes) >= total_expected):
        break
        
    start += rows_per_page

# Save full aggregated set to docs/data.json
os.makedirs("docs", exist_ok=True)
with open("docs/data.json", "w") as f:
    json.dump({
        "num_documents": len(all_bibcodes),
        "bibcodes": all_bibcodes
    }, f, indent=2)

print(f"Successfully exported ALL {len(all_bibcodes)} bibcodes across pages to docs/data.json!")
