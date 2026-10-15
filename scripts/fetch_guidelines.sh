#!/bin/sh
# Refresh UMN's Works guides (Google Docs) as text. Run from anywhere.
set -eu
cd "$(dirname "$0")/../docs/guidelines"
fetch() { curl -sSL "https://docs.google.com/document/d/$1/export?format=txt" -o "$2"; echo "fetched $2 ($(wc -c < "$2") bytes)"; }
fetch 1GClloQM_E7iKP0kmy3F8cbcgdGrmFlNI quick-start.txt
fetch 1Cuy6jY2LcwtYFNRCYvsP_xyqQsG8yUC8 publications.txt
fetch 17wLYkWTzhTUhrOWBxO04HOiKSF0ItvxG grants.txt
fetch 1cjoM6ezjncO8RtjkLUkZ_BJL8n9gkqWr reports.txt
fetch 12WomJYix3IypmRZXSbxJBRj2HnPSdTON0h8v0BPXQdU new-interface-crosswalk.txt
date -u +%Y-%m-%d > fetched-on.txt
