# ShogiEloScript

Fetches ELO rating histories from [fesashogi.eu](https://fesashogi.eu) for a list of players and plots them on a single graph.

## Usage

```bash
pip install -r requirements.txt
python shogi_elo.py players.csv data/ [--html] [--refresh]
```

- `players.csv`: two columns, `FirstName,LastName`, one player per row
- `data/`: folder where per-player JSON caches and the output graph are stored
- `--html`: produce an interactive HTML graph (via Plotly) instead of a static PNG
- `--refresh`: re-fetch all player data from the server, ignoring the cache

Player data is cached in `data/` as JSON files; re-running the script will not re-fetch already cached players. Players for whom no tournament history was found are recorded in `data/no_history.json` and skipped in future runs unless `--refresh` is used.
