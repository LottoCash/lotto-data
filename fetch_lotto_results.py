import requests
import csv
from io import StringIO
import os
import subprocess
import re


DEFAULT_OFFICIAL_CSV = "https://www.national-lottery.co.uk/results/lotto/draw-history/csv"
FALLBACK_BEATLOTTERY = "https://www.beatlottery.co.uk/lotto/draw-history"


class UpdaterSourceError(RuntimeError):
    pass


def _fetch_text(url: str, timeout: int = 30) -> requests.Response:
    # Use a common desktop Chrome UA (custom UAs can get served JS-only / blocked pages)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9",
        "Connection": "keep-alive",
    }
    r = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
    r.raise_for_status()
    return r


def _looks_like_planned_upgrades(resp: requests.Response) -> bool:
    ct = (resp.headers.get("Content-Type") or "").lower()
    body_head = (resp.text or "")[:1200].lower()
    url = (resp.url or "").lower()

    # If it's HTML (or looks like HTML) and not obviously CSV
    looks_html = ("text/html" in ct) or body_head.lstrip().startswith("<!doctype") or body_head.lstrip().startswith("<html")

    return (
        "planned upgrades" in body_head
        or "online services unavailable" in body_head
        or "cdn-national-lottery.co.uk/planned_upgrades" in url
        or (looks_html and "drawnumber" not in body_head and "draw-number" not in body_head)
    )


def _parse_official_csv(text: str) -> list[str]:
    remote_csv = StringIO(text)
    reader = csv.reader(remote_csv)
    header = next(reader, None)  # Skip header

    draws = []
    for row in reader:
        # Expected: date/draw-number columns + balls etc. But we only need 6 main balls.
        if len(row) < 7:
            continue
        try:
            main_balls = [int(row[i]) for i in range(1, 7)]
        except ValueError:
            continue

        formatted = "\t".join(f"{n:02}" for n in sorted(main_balls))
        draws.append(formatted)

    if not draws:
        raise UpdaterSourceError("Official CSV parsed but produced 0 draws (unexpected format?)")

    return draws


def _parse_beatlottery_html(html: str) -> list[str]:
    """
    Robust parser:
    - Remove scripts/styles
    - Strip HTML tags -> plain text
    - Normalise whitespace
    - Find patterns: 6 numbers + BONUS + bonus number
    """
    # Remove script/style blocks (common place for a ton of unrelated numbers)
    html = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    html = re.sub(r"(?is)<style.*?>.*?</style>", " ", html)

    # Convert HTML entities we care about
    html = html.replace("&nbsp;", " ").replace("&#160;", " ")

    # Strip tags
    text = re.sub(r"(?s)<[^>]*>", " ", html)

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # Now search across the entire visible text
    # Supports both "07 25 27 46 52 59 BONUS 40" and "7 25 27 46 52 59 BONUS 40"
    pattern = re.compile(
        r"\b(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+BONUS\s+(\d{1,2})\b",
        re.IGNORECASE,
    )
    matches = pattern.findall(text)

    if not matches:
        raise UpdaterSourceError(
            "BeatLottery HTML parsed but found 0 draws. "
            f"Visible text head was: {text[:500]!r}"
        )

    draws = []
    seen = set()
    for m in matches:
        main6 = [int(x) for x in m[:6]]
        formatted = "\t".join(f"{n:02}" for n in sorted(main6))
        if formatted not in seen:
            seen.add(formatted)
            draws.append(formatted)

    if not draws:
        raise UpdaterSourceError("BeatLottery parsing produced 0 unique draws after filtering")

    return draws


def update_previous_draws_file(local_filepath, source_url=None) -> int:
    """
    Updates the lotto_results.lot file by fetching historical draws and prepending any new ones.

    Each line: 6 tab-separated main ball numbers (2-digit strings), bonus excluded.
    """
    if source_url is None:
        source_url = DEFAULT_OFFICIAL_CSV

    # Load existing lines
    try:
        with open(local_filepath, "r") as f:
            local_lines = f.read().splitlines()
        local_draws = set(local_lines)
    except FileNotFoundError:
        local_lines = []
        local_draws = set()

    # Try official CSV first
    remote_draws = None
    try:
        resp = _fetch_text(source_url)
        if _looks_like_planned_upgrades(resp):
            raise UpdaterSourceError(
                f"Official source returned planned-upgrades HTML (final URL: {resp.url})"
            )
        remote_draws = _parse_official_csv(resp.text)
        print(f"✅ Official CSV source OK (final URL: {resp.url})")
    except Exception as e:
        print(f"⚠️ Official source failed: {e}")
        print(f"➡️ Falling back to BeatLottery HTML: {FALLBACK_BEATLOTTERY}")
        resp2 = _fetch_text(FALLBACK_BEATLOTTERY)
        remote_draws = _parse_beatlottery_html(resp2.text)
        print("✅ Fallback source OK (BeatLottery HTML)")

    # Determine new draws (preserve "newest first" by keeping remote order)
    new_draws = []
    for formatted in remote_draws:
        if formatted not in local_draws:
            new_draws.append(formatted)

    if not new_draws:
        print("No new draws found.")
        return 0

    # Write new draws first
    updated_lines = new_draws + local_lines
    with open(local_filepath, "w") as f:
        for line in updated_lines:
            f.write(line + "\n")

    print(f"✅ Appended {len(new_draws)} new draw(s) at top of the file.")

    return len(new_draws)


if __name__ == "__main__":
    update_previous_draws_file("lotto_results.lot")




