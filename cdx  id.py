import requests

API_KEY = "AIzaSyAwTr2Dl7ApQC_gOuHsQBx-6p1tn5lJVbU"

payload = {
  "title": "FactRadar Medical Search",
  "description": "Search restricted to medical institutions",
  "language": "en",
  "sitesToSearch": [
    {"siteUrl": "cdc.gov"},
    {"siteUrl": "who.int"},
    {"siteUrl": "nih.gov"},
    {"siteUrl": "mayoclinic.org"},
    {"siteUrl": "hopkinsmedicine.org"},
    {"siteUrl": "yalemedicine.org"}
  ]
}

resp = requests.post(
    f"https://programmablesearchengine.googleapis.com/v1/cses?key={API_KEY}",
    json=payload
)

print(resp.json())
