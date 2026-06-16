from pathlib import Path

from src.matcher import (
    match_all_vnx_quotes_to_delayed,
    normalize_matched_dataframe,
    save_matched_results,
)


PROCESSED_DIR = Path("data/processed")
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


print("Running VNX-driven incremental matcher...")
print("----------------------------------------")

matched_df = match_all_vnx_quotes_to_delayed(
    valid_window_seconds=60,
    incremental=True
)

print("New matched rows generated:", len(matched_df))

if matched_df.empty:
    print("No new unmatched VNX rows found.")
else:
    matched_df = normalize_matched_dataframe(matched_df)
    save_status = save_matched_results(matched_df)

    total_matches = len(matched_df)
    valid_matches = len(matched_df[matched_df["valid_match"] == True])
    invalid_matches = total_matches - valid_matches
    symbol_count = matched_df["symbol"].nunique()

    print("Save Status:", save_status["reason"])
    print("New rows saved:", save_status["saved_rows"])

    print()
    print("New Match Quality")
    print("-----------------")
    print("New Matches:", total_matches)
    print("Valid New Matches:", valid_matches)
    print("Invalid New Matches:", invalid_matches)
    print("Symbols in New Matches:", symbol_count)

    print()
    print("Top 20 Symbols in New Matches")
    print("-----------------------------")
    print(matched_df["symbol"].value_counts().head(20))
