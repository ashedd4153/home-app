#%%
import requests
import pandas as pd
import os
from bs4 import BeautifulSoup

def fetch_listing_details_structured(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return {"ERROR": str(e)}

    soup = BeautifulSoup(response.text, "html.parser")

    details = {}

    # Also extract the basic fields in the top panel
    top_fields = soup.find_all("div", class_="report-sub-row")
    for tf in top_fields:
        label_tag = tf.find("div", class_="report-row-label")
        if label_tag:
            children = tf.find_all("div", class_="report-row-label")
            if len(children) == 2:
                key = children[0].get_text(strip=True).rstrip(":")
                value = children[1].get_text(strip=True)
                details[key] = value

    # Find all report sections
    sections = soup.find_all("div", class_="report-table")
    for section in sections:
        # Get section title if any
        section_title_tag = section.find("div", class_="section-title")
        section_title = section_title_tag.get_text(strip=True) if section_title_tag else ""

        # Find all rows
        rows = section.find_all("div", class_="report-row")
        for row in rows:
            labels = row.find_all("div", class_="report-row-label")
            for label_div in labels:
                label_tag = label_div.find("label")
                if label_tag:
                    key = label_tag.get_text(strip=True).rstrip(":")
                    label_tag.extract()
                    value = label_div.get_text(strip=True)
                    full_key = f"{section_title} - {key}" if section_title else key
                    details[full_key] = value

    return details

def main():
    df = pd.read_csv("listings.csv")

    all_records = []
    for idx, row in df.iterrows():
        url = row.get("Listing URL", "").strip()
        mls_number = str(row.get("MLS Number", "")).strip()

        if not url:
            print(f"No URL for MLS {mls_number}")
            continue

        print(f"Fetching details for MLS {mls_number}...")
        details = fetch_listing_details_structured(url)

        # Add MLS Number to details
        details["MLS Number"] = mls_number

        all_records.append(details)

    # Create DataFrame with all unique keys as columns
    combined_df = pd.DataFrame(all_records)

    output_file = "listings_with_details.csv"
    if os.path.exists(output_file):
        os.remove(output_file)

    combined_df.to_csv(output_file, index=False)
    print(f"Saved {len(combined_df)} records to {output_file}")

if __name__ == "__main__":
    main()

# %%
