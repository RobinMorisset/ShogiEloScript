import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


BASE_URL = "https://fesashogi.eu/old/index.php"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ShogiEloScript/1.0)"}


def player_url(first: str, last: str) -> str:
    name = f"{first} {last}"
    return f"{BASE_URL}?mid=5&player={requests.utils.quote(name, encoding='latin-1')}"


def parse_date(raw: str) -> datetime:
    """Return the last date from a cell that may contain one or two dates."""
    parts = raw.strip().split()
    # Keep only tokens that look like dates (contain "-" and have digits)
    date_tokens = [p for p in parts if ("-" in p) and any(c.isdigit() for c in p)]
    last = date_tokens[-1]
    try:
        return datetime.strptime(last, "%Y-%m-%d")
    except ValueError:
        ValueError(f"Unrecognised date format: {last!r}")


def fetch_player_history(first: str, last: str) -> list[dict]:
    url = player_url(first, last)
    print(f"    GET {url}")
    resp = requests.get(url, headers=HEADERS, timeout=15)
    time.sleep(0.5)
    if not resp.ok:
        print(f"    HTTP {resp.status_code}, {len(resp.content)} bytes")
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    tables = soup.find_all("table")
    if len(tables) != 2:
        print(f"    Found {len(tables)} table(s) on the page (expected 2)")
    if len(tables) < 2:
        raise ValueError(f"Expected at least 2 tables, found {len(tables)}")

    tournament_table = tables[1]
    rows = tournament_table.find_all("tr")
    print(f"    Tournament table has {len(rows)} row(s) (including header)")

    history = []
    skipped = 0
    for row in rows[1:-1]:  # skip header and footer rows
        cols = [td.get_text(strip=True) for td in row.find_all("td")]
        if len(cols) == 0:
            continue
        if len(cols) < 4:
            print(f"    Skipping row (too few columns): {cols}")
            skipped += 1
            continue
        raw_date, raw_elo, raw_change = cols[1], cols[2], cols[3]
        try:
            date = parse_date(raw_date)
            elo = int(raw_elo.replace("*", ""))
            raw_change = raw_change.strip()
            change = int(raw_change.replace("+", "").replace("−", "-").replace("–", "-")) if raw_change else 0
            if elo + change == 1:
                continue
            history.append({"date": date.strftime("%Y-%m-%d"), "elo": elo + change})
        except (ValueError, IndexError) as e:
            print(f"    Skipping row (parse error: {e}): {cols}")
            skipped += 1
            continue

    if skipped:
        print(f"    Skipped {skipped} row(s)")

    history.sort(key=lambda x: x["date"])
    return history


def load_or_fetch(first: str, last: str, folder: Path) -> list[dict] | None:
    path = folder / f"{first}_{last}.json"
    if path.exists():
        print(f"  Loading cached data for {first} {last}")
        with path.open(encoding="utf-8") as f:
            return json.load(f)

    print(f"  Fetching data for {first} {last} ...")
    try:
        history = fetch_player_history(first, last)
        if not history:
            print(f"  WARNING: no tournament data found for {first} {last}")
            return None
        with path.open("w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
        print(f"  Saved {len(history)} entries to {path.name}")
        return history
    except Exception as e:
        print(f"  ERROR fetching {first} {last}: {e}")
        return None


def plot(players: dict[str, list[dict]], output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(12, 6))

    sorted_players = sorted(players.items(), key=lambda x: x[1][-1]["elo"], reverse=True)

    for name, history in sorted_players:
        dates = [datetime.fromisoformat(e["date"]) for e in history]
        elos = [e["elo"] for e in history]
        ax.plot(dates, elos, marker="o", markersize=3, label=name)

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    fig.autofmt_xdate()

    ax.set_xlabel("Date")
    ax.set_ylabel("ELO rating")
    ax.set_title("Shogi ELO history")
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    print(f"\nGraph saved to {output_path}")


def main():
    if len(sys.argv) != 3:
        print("Usage: python shogi_elo.py players.csv output_folder/")
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    folder = Path(sys.argv[2])
    folder.mkdir(parents=True, exist_ok=True)

    players: dict[str, list[dict]] = {}

    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)

    for i, row in enumerate(rows):
        if len(row) < 2:
            continue
        first = " ".join(w.capitalize() for w in row[0].strip().split())
        last = " ".join(w.capitalize() for w in row[1].strip().split())
        history = load_or_fetch(first, last, folder)
        if history:
            players[f"{first} {last}"] = history

    if not players:
        print("No data to plot.")
        sys.exit(1)

    plot(players, folder / "elo_history.png")


if __name__ == "__main__":
    main()
