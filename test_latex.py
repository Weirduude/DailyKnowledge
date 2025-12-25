#!/usr/bin/env python3
"""Test LaTeX URL generation."""
import urllib.request
import re

# Read the preview file
with open("email_preview.html", "r", encoding="utf-8") as f:
    content = f.read()

# Find all latex URLs
urls = re.findall(r'https://latex\.codecogs\.com/svg\.latex\?[^"]+', content)
print(f"Found {len(urls)} LaTeX URLs\n")

# Test first 5
for i, url in enumerate(urls[:5]):
    print(f"{i+1}. {url[:70]}...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        response = urllib.request.urlopen(req, timeout=10)
        data = response.read()
        print(f"   ✅ OK: {len(data)} bytes")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
