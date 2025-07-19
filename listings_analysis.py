#%%
import pandas as pd

# Load the CSV
file_path = "millburn_maplewood_listings.csv"
df = pd.read_csv(file_path)

# Clean column names if needed (sometimes there are spaces)
df.columns = [col.strip() for col in df.columns]

# Display the column names to check which column is the sale price
print("Columns:", df.columns)

# Convert 'Sold Price' to numeric directly, removing $ and commas
df["Sold Price"] = (
    df["Sold Price"]
    .replace("[\$,]", "", regex=True)
    .astype(float)
)

# Filter rows with Sale Price between 1M and 1.3M
filtered_df = df[(df["Sold Price"] >= 1_000_000) & (df["Sold Price"] <= 1_300_000)]

# Show the filtered results
print(filtered_df)

# Optionally, save to a new CSV
filtered_df.to_csv(
    "/Users/andrewshedd/Coding_Projects/Home_Search/filtered_listings_1M_1_3M.csv",
    index=False
)
# %%
