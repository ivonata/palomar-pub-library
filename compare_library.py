import os
import json
import requests

ADS_DEV_KEY = os.environ.get("ADS_DEV_KEY")
LIBRARY_ID = "O622yT9iQCKJDhjyd2028w"  # Your current Palomar Library ID

if not ADS_DEV_KEY:
    print("Error: ADS_DEV_KEY environment variable not set.")
    exit(1)

headers = {"Authorization": f"Bearer {ADS_DEV_KEY}"}

# 1. Fetch your current library's bibcodes
print("Fetching your current library bibcodes...")
my_bibcodes = set()
start = 0
while True:
    resp = requests.get(
        f"https://api.adsabs.harvard.edu/v1/biblib/libraries/{LIBRARY_ID}",
        headers=headers,
        params={"rows": 2000, "start": start}
    )
    data = resp.json()
    docs = data.get("documents", [])
    if isinstance(docs, dict):
        docs = docs.get("bibcodes", [])
    if not docs:
        break
    my_bibcodes.update(docs)
    if len(docs) < 2000:
        break
    start += 2000

print(f"Found {len(my_bibcodes)} papers in your library.")

# 2. Fetch all papers from your colleague's comprehensive query string
print("Fetching papers from your colleague's comprehensive query...")
colleague_query = (
    'property:refereed AND (facility:Palomar OR ack:"Palomar Observatory" OR abs:Palomar OR '
    '((abs:"Hale telescope" OR abs:"200-inch telescope" OR abs:DBSP OR abs:NGPS OR abs:TripleSpec '
    'OR abs:LFC OR abs:PFUEI OR abs:PHARO OR abs: PALAO OR abs:PALM-3000 OR abs:P3K OR abs:"Project 1640" '
    'OR abs:P1640 OR abs:WIRC OR abs:CHIMERA OR abs:PARVI OR abs:CWI OR abs:"East Arm Echelle" '
    'OR abs:"4shooter" OR abs:"oschin telescope" OR abs:"48-inch telescope" OR abs:"48-inch Schmidt" '
    'OR abs:"48-inch camera" OR abs:(POSS AND plate) OR abs:(NEAT AND asteroid) OR abs:"QUEST 2" '
    'OR abs:"QUEST II" OR abs:"Palomar quest" OR abs:(PTF AND transient) OR abs:(iPTF AND transient) '
    'OR abs:ZTF OR abs:"60-inch telescope" OR abs:"WINTER" OR abs:"18-inch Schmidt" OR abs:"18-inch camera" '
    'OR abs:"Gattini IR" OR abs:(PTI AND interferometry) OR abs:"ROBO-AO" OR abs:(SEDM AND 60-inch) '
    'OR abs:"SED Machine") AND (body:Palomar OR body:survey OR body:"wide field" OR body:telescope '
    'OR body:observatory))) year:1928-'
)

search_url = "https://api.adsabs.harvard.edu/v1/search/query"
colleague_papers = {}

rows = 2000
start = 0
while True:
    payload = {
        "q": colleague_query,
        "fl": "bibcode,year,title",
        "rows": rows,
        "start": start
    }
    resp = requests.get(search_url, headers=headers, params=payload)
    if resp.status_code != 200:
        print(f"Error querying ADS: {resp.text}")
        break
    
    results = resp.json().get("response", {}).get("docs", [])
    if not results:
        break
        
    for doc in results:
        colleague_papers[doc["bibcode"]] = doc
        
    start += rows
    if len(results) < rows:
        break

print(f"Found {len(colleague_papers)} papers matching your colleague's query.")

# 3. Find the difference
colleague_bibcodes = set(colleague_papers.keys())
missing_bibcodes = colleague_bibcodes - my_bibcodes

# 4. Group missing papers by publication year
year_distribution = {}
missing_details = []
for b in missing_bibcodes:
    doc = colleague_papers[b]
    yr = str(doc.get("year", "Unknown"))
    year_distribution[yr] = year_distribution.get(yr, 0) + 1
    
    # Safely extract title string if it's a list
    title_raw = doc.get("title", "No Title")
    title_str = title_raw[0] if isinstance(title_raw, list) else str(title_raw)
    
    missing_details.append({
        "bibcode": b,
        "year": yr,
        "title": title_str
    })

# Sort missing details by year descending
missing_details.sort(key=lambda x: x["year"], reverse=True)

# 5. Save output to a SEPARATE file (e.g., docs/missing_analysis.json)
# This keeps your dashboard data.json completely untouched!
os.makedirs("docs", exist_ok=True)
analysis_output = {
    "total_missing_count": len(missing_bibcodes),
    "year_distribution": dict(sorted(year_distribution.items(), key=lambda item: item[0])),
    "missing_papers": missing_details
}

output_filename = "docs/missing_analysis.json"
with open(output_filename, "w") as f:
    json.dump(analysis_output, f, indent=2)

print(f"Analysis successfully saved to {output_filename}!")
