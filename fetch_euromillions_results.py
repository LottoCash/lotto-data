# fetch_euromillions_results.py
import requests
import csv
from io import StringIO
import os
import subprocess

def update_previous_draws_file(local_filepath, source_url=None):
    """
    Updates the euromillions_results.lot file in the GitHub repo by fetching all historical draws
    from the UK National Lottery website and appending any new draws.

    - Each line has 7 tab-separated numbers: 5 main balls and 2 lucky stars (formatted as 2-digit strings).
    - Draws are sorted newest first.
    """
    if source_url is None:
        source_url = "https://www.national-lottery.co.uk/results/euromillions/draw-history/csv"

    # Load existing lines
    try:
        with open(local_filepath, 'r') as f:
            local_lines = f.read().splitlines()
        local_draws = set(local_lines)
    except FileNotFoundError:
        local_lines = []
        local_draws = set()

    # Download and parse CSV
    response = requests.get(source_url)
    response.raise_for_status()
    remote_csv = StringIO(response.text)
    reader = csv.reader(remote_csv)

    header = next(reader, None)  # Skip header
    new_draws = []

    for row in reader:
        # Expect at least: Date, 5 main balls, 2 lucky stars, (Millionaire Maker)
        if len(row) < 8:
            continue  # skip malformed lines
        try:
            # Columns B–F → 5 main balls (index 1‑5)
            main_balls = [int(row[i]) for i in range(1, 6)]
            # Columns G–H → 2 lucky stars (index 6‑7)
            lucky_stars = [int(row[i]) for i in range(6, 8)]
        except ValueError:
            continue

        # Keep main balls sorted; stars sorted, then combine
        formatted = '\t'.join(f"{n:02}" for n in (sorted(main_balls) + sorted(lucky_stars)))
        if formatted not in local_draws:
            new_draws.append(formatted)

    if not new_draws:
        print("No new draws found.")
        return 0

    # Write new draws first
    updated_lines = new_draws + local_lines
    with open(local_filepath, 'w') as f:
        for line in updated_lines:
            f.write(line + '\n')

    print(f"✅ Appended {len(new_draws)} new draw(s) at top of the file.")

    # Automatically stage, commit, and push if run in GitHub Actions
    if os.getenv("GITHUB_ACTIONS"):
        subprocess.run(["git", "config", "user.name", "github-actions"], check=True)
        subprocess.run(["git", "config", "user.email", "github-actions@github.com"], check=True)
        subprocess.run(["git", "add", local_filepath], check=True)
        subprocess.run(["git", "diff", "--cached", "--quiet"]) or subprocess.run([
            "git", "commit", "-m", "🔄 Auto-update euromillions_results.lot"
        ], check=True)
        subprocess.run(["git", "push"], check=True)

    return len(new_draws)


if __name__ == "__main__":
    update_previous_draws_file("euromillions_results.lot")
