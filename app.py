import streamlit as st
import pandas as pd
import os
from estimation_app_constructor import ListingData
import requests
# Add st_aggrid import
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

st.set_page_config(layout="wide")

# --- Refresh Data Button and DataFrame Caching ---
REFRESH_LABEL = "Refresh Data"
refresh_clicked = st.button(REFRESH_LABEL)

# Session state key for dataframe
DF_SESSION_KEY = "listing_df"

def load_data(force_refresh=False):
    ld = ListingData([
        "Millburn, NJ",
        "Maplewood, NJ",
        "New Providence, NJ",
        "Chatham, NJ",
        "Summit, NJ"
    ], force_refresh=force_refresh)
    return pd.read_csv(ld.csv_path)

if refresh_clicked or DF_SESSION_KEY not in st.session_state:
    # On button click or first load, fetch fresh (if requested) or cached data
    st.session_state[DF_SESSION_KEY] = load_data(force_refresh=refresh_clicked)

df = st.session_state[DF_SESSION_KEY]

DISPLAY_COLUMNS = [
    "mls_id",
    "full_street_line",
    "town_searched",
    "list_price",
    "status",
    "estimated_price",
    "sold_price",
    "last_sold_date",
    "favorite"
]


# Town filter selectbox
town_options = df["town_searched"].dropna().unique()
selected_town = st.selectbox("Filter by Town", ["All"] + list(town_options))

# Filter by selected town
if selected_town != "All":
    df = df[df["town_searched"] == selected_town]

# Sort the dataframe before splitting into groups
df['status_order'] = df['status'].map({'for_sale': 0, 'pending': 1, 'sold': 2})
df = df.sort_values(by=['status_order', 'list_price'], ascending=[True, True])
df = df.drop(columns=['status_order'])

## 'favorite' column will be loaded directly from CSV, not session state

# Split into groups after filtering
active_no_estimate = df[(df['status'].isin(['for_sale', 'pending'])) & (df['estimated_price'].isna())]
active_with_estimate = df[(df['status'].isin(['for_sale', 'pending'])) & (df['estimated_price'].notna())]
sold = df[df['status'] == 'sold']

# Streamlit UI
st.title("Real Estate Listings")

st.header("Active or Under Contract (No Estimate)")
# AgGrid display for active_no_estimate
gb_no_est = GridOptionsBuilder.from_dataframe(active_no_estimate[DISPLAY_COLUMNS])
gb_no_est.configure_selection(
    selection_mode="single",
    use_checkbox=False
)
gb_no_est.configure_column("mls_id", hide=True)
grid_options_no_est = gb_no_est.build()
grid_response_no_est = AgGrid(
    active_no_estimate[DISPLAY_COLUMNS],
    gridOptions=grid_options_no_est,
    update_mode=GridUpdateMode.SELECTION_CHANGED,
    height=300,
    fit_columns_on_grid_load=True
)
selected_rows_no_est = grid_response_no_est['selected_rows']
if selected_rows_no_est is not None and len(selected_rows_no_est) > 0:
    st.session_state.selected_id = selected_rows_no_est.iloc[0]['mls_id']

st.header("Active or Under Contract (With Estimate)")
# AgGrid display for active_with_estimate
gb_with_est = GridOptionsBuilder.from_dataframe(active_with_estimate[DISPLAY_COLUMNS])
gb_with_est.configure_selection(
    selection_mode="single",
    use_checkbox=False
)
gb_with_est.configure_column("mls_id", hide=True)
grid_options_with_est = gb_with_est.build()
grid_response_with_est = AgGrid(
    active_with_estimate[DISPLAY_COLUMNS],
    gridOptions=grid_options_with_est,
    update_mode=GridUpdateMode.SELECTION_CHANGED,
    height=300,
    fit_columns_on_grid_load=True
)
selected_rows_with_est = grid_response_with_est['selected_rows']
if selected_rows_with_est is not None and len(selected_rows_with_est) > 0:
    st.session_state.selected_id = selected_rows_with_est.iloc[0]['mls_id']

st.header("Sold Listings")
# AgGrid display for sold
gb_sold = GridOptionsBuilder.from_dataframe(sold[DISPLAY_COLUMNS])
gb_sold.configure_selection(
    selection_mode="single",
    use_checkbox=False
)
gb_sold.configure_column("mls_id", hide=True)
grid_options_sold = gb_sold.build()
grid_response_sold = AgGrid(
    sold[DISPLAY_COLUMNS],
    gridOptions=grid_options_sold,
    update_mode=GridUpdateMode.SELECTION_CHANGED,
    height=300,
    fit_columns_on_grid_load=True
)
selected_rows_sold = grid_response_sold['selected_rows']
if selected_rows_sold is not None and len(selected_rows_sold) > 0:
    st.session_state.selected_id = selected_rows_sold.iloc[0]['mls_id']

# Center the Clear Selection button
cols = st.columns([1, 2, 1])
with cols[1]:
    if st.button("Clear Selection"):
        st.session_state.selected_id = None

# Listing detail viewer
st.header("Listing Details")

if "selected_id" not in st.session_state:
    st.session_state.selected_id = None

if st.session_state.selected_id:
    listing = df[df["mls_id"] == st.session_state.selected_id].iloc[0]

    st.subheader(f"{listing['full_street_line']}, {listing['city']}, {listing['state']} {listing['zip_code']}")

    # Favorite toggle button - now updates CSV and reloads data
    is_favorite = listing['favorite']
    if is_favorite:
        if st.button("Remove from Favorites"):
            ld = ListingData([])
            ld.update_favorite(listing["mls_id"], False)
            st.session_state[DF_SESSION_KEY] = pd.read_csv(ld.csv_path)
            st.rerun()
    else:
        if st.button("Add to Favorites"):
            ld = ListingData([])
            ld.update_favorite(listing["mls_id"], True)
            st.session_state[DF_SESSION_KEY] = pd.read_csv(ld.csv_path)
            st.rerun()

    st.subheader("Update Estimated Price")
    new_estimate = st.number_input("Enter new estimated price", min_value=0, value=int(listing["estimated_price"]) if pd.notna(listing["estimated_price"]) else 0, step=1000)
    if st.button("Save Estimated Price"):
        ld = ListingData([])
        ld.update_estimated_price(listing["mls_id"], new_estimate)
        st.session_state[DF_SESSION_KEY] = pd.read_csv(ld.csv_path)
        st.rerun()

    # Show details as markdown
    detail_text = """
    **MLS ID**: {mls}

    **Status**: {status}

    **Price**: ${price:,.0f}

    **Sold Price**: ${sold_price:,.0f}

    **Tax**: ${tax:,.0f}

    **Beds**: {beds}

    **Full Baths**: {full_baths}

    **Half Baths**: {half_baths}

    **Square Feet**: {sqft}

    **Year Built**: {year}

    **Lot Size (sqft)**: {lot}

    **Estimated Price**: {estimate}

    **Favorite**: {favorite}

    **AC Type**: {ac}

    **Siding Type**: {siding}

    **Property URL**: [{url}]({url})

    **Google Maps URL**: [{maps}]({maps})

    **Description**: {text}
    """.format(
        mls=listing["mls_id"],
        status=listing["status"],
        price=listing["list_price"] or 0,
        sold_price=listing["sold_price"] or 0,
        tax=listing["tax"] or 0,
        beds=listing["beds"],
        full_baths=listing["full_baths"],
        half_baths=listing["half_baths"],
        sqft=listing["sqft"],
        year=int(round(listing["year_built"])) if pd.notna(listing["year_built"]) else "",
        lot=int(round(listing["lot_sqft"])) if pd.notna(listing["lot_sqft"]) else "",
        estimate=listing["estimated_price"],
        favorite="Yes" if is_favorite else "No",
        ac=listing.get("ac_type", ""),
        siding=listing.get("siding_type", ""),
        url=listing["property_url"],
        maps=listing["google_maps_url"],
        text=listing["text"]
    )
    st.markdown(detail_text)

    # Show local photos in two-column layout
    if pd.notna(listing["local_photos"]):
        photo_paths = [p.strip() for p in str(listing["local_photos"]).split(",") if p.strip()]
        if photo_paths:
            # Display images in pairs using two columns
            for i in range(0, len(photo_paths), 2):
                cols = st.columns(2)
                # First image in the pair
                if os.path.exists(photo_paths[i]):
                    cols[0].image(photo_paths[i], use_container_width=True)
                else:
                    cols[0].write(f"Missing image: {photo_paths[i]}")
                # Second image in the pair, if it exists
                if i + 1 < len(photo_paths):
                    if os.path.exists(photo_paths[i + 1]):
                        cols[1].image(photo_paths[i + 1], use_container_width=True)
                    else:
                        cols[1].write(f"Missing image: {photo_paths[i + 1]}")


def download_and_cache_photos(self, photo_urls, listing_id, base_dir="cached_photos"):
    import concurrent.futures

    os.makedirs(base_dir, exist_ok=True)
    listing_dir = os.path.join(base_dir, str(listing_id))
    os.makedirs(listing_dir, exist_ok=True)

    # If photos already exist, skip downloading
    existing_files = sorted([
        os.path.join(listing_dir, f) for f in os.listdir(listing_dir)
        if os.path.isfile(os.path.join(listing_dir, f))
    ])
    if existing_files:
        return existing_files

    def download_image(url, dest_path, session):
        try:
            resp = session.get(url, timeout=10)
            resp.raise_for_status()
            with open(dest_path, "wb") as f:
                f.write(resp.content)
            return dest_path
        except Exception as e:
            print(f"Failed to download {url}: {e}")
            return None

    local_paths = []
    with requests.Session() as session:
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for idx, url in enumerate(photo_urls):
                ext = url.split("?")[0].split(".")[-1]
                filename = f"photo_{idx + 1}.{ext}"
                file_path = os.path.join(listing_dir, filename)
                futures.append(executor.submit(download_image, url, file_path, session))

            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    local_paths.append(result)

    return local_paths