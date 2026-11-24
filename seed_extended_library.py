import os
import requests

LIBRARY_ID = "O622yT9iQCKJDhjyd2028w"
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
# --- 1. The Latest Airtight Query (With Expanded Hale/Facility Title & Abstract Catchers) ---
ztf_clause = 'abs:("Zwicky Transient Facility" OR "ZTF") OR ack:("1440341" OR "2034437" OR "0965661" OR "1545949")'
iptf_clause = 'abs:("Intermediate Palomar Transient Factory" OR "iPTF") OR ack:("1313484")'
ptf_clause = 'abs:("Palomar Transient Factory") OR ack:("0838126") OR (abs:PTF AND (abs:transient OR abs:supernova OR abs:optical OR abs:survey))'

# Expanded Hale/Facility clause catching title/abstract observatory mentions + grants + official facility tags
hale_clause = (
    'abs:("Hale Telescope" OR "Palomar Observatory" OR "Palomar 200-inch" OR "P200") '
    'OR title:("Palomar" OR "Hale") '
    'OR ack:("Hale Telescope" OR "Palomar Observatory" OR "Caltech Optical Observatories" OR "P200") '
    'OR facility:"Palomar"'
)

# Restricted Instrument Clause: Requires instrument mention AND body context
base_instruments = (
    'abs:("Next Generation Palomar Spectrograph" OR "NGPS" OR "DBSP" OR "TripleSpec" '
    'OR "WIRC" OR "CHIMERA" OR "PARVI" OR "CWI" OR "ROBO-AO" OR "SED Machine" OR "SEDM")'
)
body_context_gate = '(body:Palomar OR body:telescope OR body:observatory OR body:spectrograph)'
restricted_instrument_clause = f"(({base_instruments}) AND {body_context_gate})"

# Robust Exclusions
exclusions = (
    'NOT abs:("pedotransfer" OR "soil water" OR "flash flood" OR "hill torrents" OR "hydrology" OR "pedology" '
    'OR "load frequency control" OR "power system" OR "microgrid" OR "electric vehicle" OR "lignosulfonate" OR "catalyst") '
    'NOT bibstem:("GCN" OR "ATel" OR "IAUC")'
)

# Final Combined Query
full_query = (
    f"(({ztf_clause}) OR ({iptf_clause}) OR ({ptf_clause}) OR ({restricted_instrument_clause}) OR ({hale_clause})) "
    f"AND database:astronomy AND property:refereed {exclusions}"
)

print("Fetching latest matching refereed astronomy papers from NASA ADS...")

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
