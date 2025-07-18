# fetch_euromillions_results.py
#
# Downloads the full EuroMillions draw history from the UK National
# Lottery site, extracts 5 main balls + 2 lucky stars, and writes
# them (newest first) to euromillions_results.lot in tab-separated
# two-digit format, e.g. “04 11 17 25 41 02 07”

import requests, csv
from io import StringIO

CSV_URL = "https://www.national-lottery.co.uk/results/euromillions/draw-history/csv"

def fetch_euromillions_results(out_path: str = "euromillions_results.lot") -> int:
    try:
        resp = requests.get(CSV_URL)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"❌  Failed to fetch EuroMillions CSV: {e}")
        return 0

    reader = csv.reader(StringIO(resp.text))
    next(reader, None)  # skip header

    lines: list[str] = []
    for row in reader:
        if len(row) < 9:              # Date + 5 main + 2 stars + Millionaire Maker
            continue
        try:
            main  = [int(n) for n in row[1:6]]       # Ball 1–5
            stars = [int(n) for n in row[6:8]]       # Star 1–2
        except ValueError:
            continue

        formatted = "\t".join(f"{n:02}" for n in (main + stars))
        lines.append(formatted)

    if not lines:
        print("❌  No valid lines parsed.")
        return 0

    lines.reverse()        # newest first
    with open(out_path, "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"✅  Wrote {len(lines)} draws to {out_path}")
    return len(lines)


if __name__ == "__main__":
    fetch_euromillions_results()
