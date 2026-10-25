import argparse
from rfp.db import init_db, load_criteria

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create and seed the SQLite RFP database.")
    parser.add_argument("--db", default="data/rfp.sqlite")
    args = parser.parse_args()
    init_db(args.db)
    print(f"Initialized {args.db}: {len(load_criteria(args.db))} active criteria")
