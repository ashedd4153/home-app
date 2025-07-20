import pandas as pd
from homeharvest import scrape_property
import os

class ListingData:
    def __init__(self, towns, min_price=900_000, max_price=1_500_000, csv_path="all_properties.csv", force_refresh=False):
        self.towns = towns if isinstance(towns, list) else [towns]
        self.min_price = min_price
        self.max_price = max_price
        self.csv_path = csv_path
        # Only fetch data if force_refresh is True or file does not exist
        if force_refresh or not os.path.exists(self.csv_path):
            self._fetch_data()

    def _fetch_data(self):
        
        frames = []
        for town in self.towns:
            for status, past_days in [("for_sale", 30), ("sold", 90), ("pending", 60)]:
                props = scrape_property(
                    location=town,
                    listing_type=status,
                    past_days=past_days,
                    property_type=["single_family"],
                )
                props["town_searched"] = town
                props["status"] = status
                frames.append(props)

        properties = pd.concat(frames, ignore_index=True).drop_duplicates(subset="mls_id").reset_index(drop=True)

        properties["estimated_price"] = None

        properties["list_price"] = pd.to_numeric(
            properties["list_price"].astype(str).str.replace(r"[\$,]", "", regex=True),
            errors="coerce",
        )
        properties = properties.dropna(subset=["list_price"])
        properties = properties[
            (properties["list_price"] >= self.min_price)
            & (properties["list_price"] <= self.max_price)
        ]

        properties["property_url"] = properties.apply(self.make_google_search_link, axis=1)
        properties["google_maps_url"] = properties.apply(self.make_google_maps_link, axis=1)
        properties["all_photos"] = (
            properties[["primary_photo", "alt_photos"]]
            .fillna("")
            .agg(", ".join, axis=1)
        )

        # Download photos and create local_photos column
        properties["local_photos"] = None
        for idx, row in properties.iterrows():
            photo_urls = [url.strip() for url in row["all_photos"].split(",") if url.strip()]
            local_paths = self.download_and_cache_photos(photo_urls, row["mls_id"])
            properties.at[idx, "local_photos"] = ", ".join(local_paths)




        csv_path = self.csv_path
        if os.path.exists(csv_path):
            old_df = pd.read_csv(csv_path)
        else:
            old_df = pd.DataFrame()

        if not old_df.empty:
            properties["mls_id"] = properties["mls_id"].astype(str)
            old_df["mls_id"] = old_df["mls_id"].astype(str)

            merged = pd.merge(
                properties,
                old_df,
                how="outer",
                on="mls_id",
                suffixes=("_new", None),
                indicator=True
            )

            prioritize_new_in_col_list = [
                "days_on_mls",
                "list_price",
                "list_price_min",
                "list_price_max",
                "list_date",
                "sold_price",
                "last_sold_date",
                "assessed_value",
                "estimated_value",
                "tax",
                "tax_history",
                "status"
            ]
            for col in merged.columns:
                if col.endswith("_new") == False and col not in ["mls_id", "_merge"]:
                    new_col = f"{col}_new"
                    if new_col not in merged.columns:
                        continue
                    if col in prioritize_new_in_col_list:
                        merged[col] = merged[new_col].combine_first(merged[col])
                    else:
                        merged[col] = merged[col].combine_first(merged[new_col])


            merged = merged.drop(columns=[c for c in merged.columns if c.endswith("_new")]).drop_duplicates(subset="mls_id").reset_index(drop=True)

            properties = merged
            if "_merge" in properties.columns:
                properties = properties.drop(columns="_merge")
        else:
            pass

        # Ensure 'favorite' column exists and defaults to False for all rows that don't already have a value
        if 'favorite' not in properties.columns:
            properties['favorite'] = False
        else:
            properties['favorite'] = properties['favorite'].fillna(False)

        properties.to_csv(csv_path, index=False)

        return properties

    @staticmethod
    def make_google_search_link(row):
        import urllib.parse
        address_parts = [
            str(row.get("full_street_line") or ""),
            str(row.get("city") or ""),
            str(row.get("state") or ""),
            str(row.get("zip_code") or "")
        ]
        address = " ".join(part for part in address_parts if part.strip())
        mls_id = row.get("mls_id", "")
        if address and mls_id:
            query = f"{address} MLS {mls_id}"
        elif address:
            query = address
        elif mls_id:
            query = f"MLS {mls_id}"
        else:
            return None
        encoded = urllib.parse.quote_plus(query)
        return f"https://www.google.com/search?q={encoded}"

    @staticmethod
    def make_google_maps_link(row):
        address_parts = [
            str(row.get("full_street_line") or ""),
            str(row.get("city") or ""),
            str(row.get("state") or ""),
            str(row.get("zip_code") or "")
        ]
        address = " ".join(part for part in address_parts if part.strip())
        if not address:
            return None
        address_str = address.replace(" ", "+")
        return f"https://www.google.com/maps/search/{address_str}"

    def download_and_cache_photos(self, photo_urls, listing_id, base_dir="cached_photos"):
        import requests
        os.makedirs(base_dir, exist_ok=True)
        listing_dir = os.path.join(base_dir, str(listing_id))
        os.makedirs(listing_dir, exist_ok=True)

        # If photos already exist, skip downloading
        existing_files = [
            os.path.join(listing_dir, f) for f in os.listdir(listing_dir)
            if os.path.isfile(os.path.join(listing_dir, f))
        ]
        if existing_files:
            return existing_files

        local_paths = []
        for idx, url in enumerate(photo_urls):
            print(f"Starting download {idx+1}/{len(photo_urls)}: {url}")
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
            except Exception as e:
                print(f"Failed to download {url}: {e}")
                continue

            ext = url.split("?")[0].split(".")[-1]
            filename = f"photo_{idx + 1}.{ext}"
            file_path = os.path.join(listing_dir, filename)

            with open(file_path, "wb") as f:
                f.write(response.content)

            print(f"Finished download {idx+1}/{len(photo_urls)}: {file_path}")

            local_paths.append(file_path)

        return local_paths




# Re-add update_estimated_price at the end of the ListingData class
    def update_estimated_price(self, mls_id, new_estimate):
        df = pd.read_csv(self.csv_path)
        df['mls_id'] = df['mls_id'].astype(str)
        mask = df['mls_id'] == str(mls_id)
        df.loc[mask, 'estimated_price'] = new_estimate
        df.to_csv(self.csv_path, index=False)

    def update_favorite(self, mls_id, favorite):
        df = pd.read_csv(self.csv_path)
        df['mls_id'] = df['mls_id'].astype(str)
        if 'favorite' not in df.columns:
            df['favorite'] = False
        mask = df['mls_id'] == str(mls_id)
        df.loc[mask, 'favorite'] = bool(favorite)
        df.to_csv(self.csv_path, index=False)