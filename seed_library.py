import os
import requests

LIBRARY_ID = "dII2SaIMSymg02tSTUKTmA"
token = os.environ.get("ADS_DEV_KEY")

if not token:
    print("Error: ADS_DEV_KEY environment variable not found!")
    exit(1)

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# --- 1. Empty Existing Papers from Library (Clean Slate) ---
print(f"Emptying library {LIBRARY_ID} before re-seeding...")

# First, fetch all current bibcodes in the library
get_lib_resp = requests.get(
    f"https://api.adsabs.harvard.edu/v1/biblib/libraries/{LIBRARY_ID}",
    headers=headers
)

if get_lib_resp.status_code == 200:
    current_bibcodes = get_lib_resp.json().get("documents", [])
    if current_bibcodes:
        # Delete existing bibcodes in batches of 2000
        for i in range(0, len(current_bibcodes), 2000):
            batch = current_bibcodes[i:i + 2000]
            del_payload = {"bibcode": batch, "action": "empty"}
            requests.post(
                f"https://api.adsabs.harvard.edu/v1/biblib/documents/{LIBRARY_ID}",
                headers=headers,
                json=del_payload
            )
        print(" Library emptied successfully.")
    else:
        print(" Library was already empty.")

# --- 2. Build Airtight Search Query ---
ztf_clause = 'abs:("Zwicky Transient Facility" OR "ZTF") OR ack:("1440341" OR "2034437" OR "0965661" OR "1545949")'
iptf_clause = 'abs:("Intermediate Palomar Transient Factory" OR "iPTF") OR ack:("1313484")'

# Force PTF to match either full string, exact grant, or acronym paired strictly with astronomy terms
ptf_clause = 'abs:("Palomar Transient Factory") OR ack:("0838126") OR (abs:"PTF" AND abs:("survey" OR "transient" OR "supernova" OR "photometry" OR "telescope" OR "optical" OR "astronomy"))'

hale_clause = 'ack:("Hale Telescope" OR "Palomar Observatory" OR "Caltech Optical Observatories" OR "P200") OR facility:"Palomar"'

# Direct exclusions for false positive terms and non-astronomy domains
exclusions = 'NOT abs:("pedotransfer" OR "soil water" OR "flash flood" OR "hill torrents" OR "hydrology" OR "pedology") NOT bibstem:("GCN" OR "ATel" OR "IAUC")'

# Explicitly group target terms inside parenthetical scope before applying database and property filters
full_query = f"(({ztf_clause}) OR ({iptf_clause}) OR ({ptf_clause}) OR ({hale_clause})) AND database:astronomy AND property:refereed {exclusions}"

print("\nFetching all matching refereed astronomy papers from NASA ADS...")

all_bibcodes = []
start = 0
rows_per_page = 2000

while True:
    search_params = {
        "q": full_query,
        "fl": "bibcode",
        "rows": rows_per_page,
        "start": start
    }
    
    search_resp = requests.get(
        "https://api.adsabs.harvard.edu/v1/search/query",
        headers=headers,
        params=search_params
    )
    
    if search_resp.status_code != 200:
        print(f"Search failed: {search_resp.text}")
        exit(1)
        
    data = search_resp.json()["response"]
    docs = data["docs"]
    total_found = data["numFound"]
    
    bibcodes = [doc["bibcode"] for doc in docs if "bibcode" in doc]
    all_bibcodes.extend(bibcodes)
    
    print(f"  Retrieved {len(all_bibcodes)} of {total_found} bibcodes...")
    
    if len(all_bibcodes) >= total_found or len(docs) == 0:
        break
    start += rows_per_page

# --- 3. Push All Bibcodes in Batches ---
print(f"\nPushing {len(all_bibcodes)} astronomy papers into ADS library {LIBRARY_ID}...")

for i in range(0, len(all_bibcodes), 2000):
    batch = all_bibcodes[i:i + 2000]
    add_data = {
        "bibcode": batch,
        "action": "add"
    }
    
    push_resp = requests.post(
        f"https://api.adsabs.harvard.edu/v1/biblib/documents/{LIBRARY_ID}",
        headers=headers,
        json=add_data
    )
    
    if push_resp.status_code != 200:
        print(f"Failed batch push: {push_resp.status_code} - {push_resp.text}")
        exit(1)

print(f"\n Library re-seeding complete! Total papers in library: {len(all_bibcodes)}")
