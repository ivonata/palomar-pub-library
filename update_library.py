import os
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

# --- 2. Build Airtight Search Query ---
ztf_clause = 'abs:("Zwicky Transient Facility" OR "ZTF") OR ack:("1440341" OR "2034437" OR "0965661" OR "1545949")'
iptf_clause = 'abs:("Intermediate Palomar Transient Factory" OR "iPTF") OR ack:("1313484")'

# Force PTF to match either full string, exact grant, or acronym paired strictly with astronomy terms
ptf_clause = 'abs:("Palomar Transient Factory") OR ack:("0838126")'

hale_clause = 'ack:("Hale Telescope" OR "Palomar Observatory" OR "Caltech Optical Observatories" OR "P200") OR facility:"Palomar"'

# Direct exclusions for false positive terms and non-astronomy domains
exclusions = 'NOT abs:("pedotransfer" OR "soil water" OR "flash flood" OR "hill torrents" OR "hydrology" OR "pedology") NOT bibstem:("GCN" OR "ATel" OR "IAUC")'

# Explicitly group target terms inside parenthetical scope before applying database and property filters
full_query = f"(({ztf_clause}) OR ({iptf_clause}) OR ({ptf_clause}) OR ({hale_clause})) AND database:astronomy AND property:refereed {exclusions}"

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
