import requests
import csv
from io import StringIO

def fetch_lotto_results(output_path):
    """
    Downloads UK National Lottery results and extracts 6 main balls per draw,
    formatted as tab-separated two-digit numbers.
    """
    url = "https://www.national-lottery.co.uk/results/lotto/draw-history/csv"

    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ Failed to fetch draw history: {e}")
        return

    csv_data = response.text
    reader = csv.reader(StringIO(csv_data))

    lines = []
    header_skipped = False

    for row in reader:
        if not header_skipped:
            header_skipped = True
            continue

        # Extract columns B to G (Main Ball 1–6)
        try:
            balls = row[1:7]  # Columns B to G
            if len(balls) != 6:
                continue

            balls = [int(b) for b in balls]  # Convert to int
            formatted = "\t".join(f"{b:02}" for b in balls)  # Two-digit format
            lines.append(formatted)
        except (ValueError, IndexError):
            continue

    if not lines:
        print("❌ No valid lines found in data.")
        return

    # Reverse to have most recent draws first
    lines.reverse()

    try:
        with open(output_path, "w") as f:
            for line in lines:
                f.write(line + "\n")
        print(f"✅ Wrote {len(lines)} draws to {output_path}")
    except IOError as e:
        print(f"❌ Failed to save output file: {e}")


if __name__ == "__main__":
    fetch_lotto_results("lotto_results.lot")
