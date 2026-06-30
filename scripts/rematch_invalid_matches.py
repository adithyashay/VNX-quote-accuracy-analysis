import argparse
import os

from src.database.postgres_matcher import match_unmatched_postgres_quotes_to_delayed
from src.database.writer import insert_matched_quote_rows


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Reprocess recent unmatched or invalid/wide matched VNX rows after "
            "the delayed/reference feed has had time to catch up."
        )
    )
    parser.add_argument(
        "--lookback-hours",
        type=int,
        default=336,
        help="How far back to scan VNX rows. Default: 336 hours / 14 days.",
    )
    parser.add_argument(
        "--valid-window-seconds",
        type=int,
        default=60,
        help="Maximum timestamp gap for a valid match. Default: 60.",
    )
    parser.add_argument(
        "--delayed-padding-seconds",
        type=int,
        default=900,
        help="Delayed/reference lookup padding around VNX rows. Default: 900.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write rematched rows back to PostgreSQL. Without this, preview only.",
    )
    parser.add_argument(
        "--sync-replica",
        action="store_true",
        help=(
            "Also write rematched rows to MATCHED_REPLICA_DATABASE_URL. "
            "Requires --apply."
        ),
    )

    return parser.parse_args()


def main():
    args = parse_args()

    matched_df = match_unmatched_postgres_quotes_to_delayed(
        valid_window_seconds=args.valid_window_seconds,
        lookback_hours=args.lookback_hours,
        delayed_padding_seconds=args.delayed_padding_seconds,
    )

    if matched_df.empty:
        print("No rows need rematching for the selected lookback window.")
        return

    valid_rows = matched_df[
        (matched_df["valid_match"] == True)
        & (matched_df["time_gap_seconds"] <= args.valid_window_seconds)
    ]
    invalid_rows = matched_df[
        (matched_df["valid_match"] != True)
        | (matched_df["time_gap_seconds"] > args.valid_window_seconds)
    ]

    print("Rematch candidate rows:", len(matched_df))
    print("Rows valid after rematch:", len(valid_rows))
    print("Rows still invalid/wide:", len(invalid_rows))
    print("Symbols in candidates:", matched_df["symbol"].nunique())
    print("Earliest VNX time:", matched_df["vnx_time"].min())
    print("Latest VNX time:", matched_df["vnx_time"].max())

    if not args.apply:
        print("Preview only. Re-run with --apply to write results.")
        return

    local_inserted = insert_matched_quote_rows(matched_df)
    print("Local matched rows upserted:", local_inserted)

    if args.sync_replica:
        replica_url = os.getenv("MATCHED_REPLICA_DATABASE_URL")

        if not replica_url:
            raise ValueError(
                "MATCHED_REPLICA_DATABASE_URL is required for --sync-replica."
            )

        replica_inserted = insert_matched_quote_rows(
            matched_df,
            database_url=replica_url,
        )
        print("Replica matched rows upserted:", replica_inserted)


if __name__ == "__main__":
    main()
