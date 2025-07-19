#%%


import numpy as np
import pandas as pd
import numpy_financial as npf

def search_zillow_address(address):
    import requests
    from bs4 import BeautifulSoup
    import re

    # Google search URL
    query = f"site:zillow.com {address}"
    google_url = f"https://www.google.com/search?q={query}"

    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(google_url, headers=headers)
    soup = BeautifulSoup(resp.text, "lxml")

    # Find the first Zillow link
    link = None
    for a in soup.find_all("a", href=True):
        href = a['href']
        if "zillow.com/homedetails" in href:
            # Google search links often start with /url?q=
            m = re.search(r"/url\?q=(https://www.zillow.com[^\&]+)", href)
            if m:
                link = m.group(1)
                break

    if not link:
        return {"link": None, "price": None}

    # Fetch the Zillow page
    zillow_resp = requests.get(link, headers=headers)
    zillow_soup = BeautifulSoup(zillow_resp.text, "lxml")

    # Parse price
    price = None
    price_span = zillow_soup.find("span", class_="ds-value")
    if price_span:
        price = price_span.get_text(strip=True)

    return {"link": link, "price": price}


result = search_zillow_address("430 Ridgewood Rd, Maplewood NJ")
print(result)

#%%
