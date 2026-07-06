# GitHub Repo Analyzer

A full-stack Python project that calls GitHub's public REST API, fetches
repository stats (stars, forks, language, etc.) for any GitHub user, loads
the data into a **Pandas DataFrame**, and sorts/summarizes it — with both
a web frontend and a command-line interface.

## Project Structure

```
github-repo-analyzer/
├── app.py                 # Flask backend (web server + JSON API)
├── github_analyzer.py     # Core logic: GitHub API calls + Pandas processing
├── requirements.txt       # Python dependencies
├── templates/
│   └── index.html         # Frontend page
└── static/
    ├── style.css           # Frontend styling (dark "terminal" theme)
    └── script.js            # Frontend logic (fetch + Chart.js rendering)
```

## How it works

1. **Backend / data layer (`github_analyzer.py`)**
   - `fetch_repos(username, token)` calls `GET /users/{username}/repos` on the
     GitHub REST API, paging through results until all repos are collected.
   - `build_dataframe(repos)` loads the raw JSON into a **Pandas DataFrame**
     with clean columns: `name`, `description`, `language`, `stars`, `forks`,
     `watchers`, `open_issues`, `size_kb`, `created_at`, `updated_at`, `url`.
   - `sort_repos(df, sort_by, ascending)` sorts the DataFrame by any column
     (stars, forks, name, dates, etc.) using `DataFrame.sort_values`.
   - `summarize(df)` uses Pandas aggregation (`sum`, `mean`, `value_counts`,
     `idxmax`) to compute total stars/forks, average stars, the most-used
     language, language distribution, and the top starred repo.
   - `analyze_user(...)` ties it all together and is reused by both the web
     app and the CLI.

2. **Web backend (`app.py`)**
   - Flask app with:
     - `GET /` — serves the frontend page
     - `POST /api/analyze` — accepts `{ username, sort_by, ascending, token }`
       as JSON and returns the sorted repo list + summary stats as JSON
     - `GET /api/export/<username>` — downloads the last analyzed data as CSV

3. **Frontend (`templates/index.html`, `static/`)**
   - A single page with a "terminal"-styled input where you type a username.
   - Calls `/api/analyze` with `fetch()`, then renders:
     - Summary stat cards (total repos, stars, forks, avg stars, top language,
       top repo)
     - Two **Chart.js** charts: a language-distribution doughnut chart and a
       top-8-repos-by-stars bar chart
     - A sortable, scrollable repo table
     - A "Export CSV" button that downloads the analyzed data

## Setup & Running the Web App

```bash
# 1. (Recommended) create a virtual environment
python -m venv venv
source venv/bin/activate      # on Windows: venv\Scripts\activate

# 2. install dependencies
pip install -r requirements.txt

# 3. run the Flask app
python app.py
```

Then open **http://127.0.0.1:5000** in your browser, type a GitHub
username (e.g. `torvalds`, `octocat`, `gvanrossum`), pick a sort option,
and click **run**.

> **Optional GitHub token:** GitHub's public API allows 60 requests/hour
> without authentication. If you hit a rate limit, generate a
> [personal access token](https://github.com/settings/tokens) (no scopes
> needed for public data) and paste it into the "token" field, or set it
> as an environment variable before running the app:
> `export GITHUB_TOKEN=ghp_xxxx`

## Using it from the command line (no web server needed)

`github_analyzer.py` can also be run directly:

```bash
python github_analyzer.py torvalds
python github_analyzer.py octocat --sort forks --asc
python github_analyzer.py gvanrossum --csv output.csv
```

Options:
- `--sort` : column to sort by (`stars`, `forks`, `name`, `updated_at`, `created_at`, `open_issues`)
- `--asc`  : sort ascending instead of descending
- `--token`: optional GitHub personal access token
- `--csv`  : save the results to a CSV file

## Example CLI output

```
Fetching repositories for 'octocat'...

=== Repository Table ===
         name language  stars  forks  open_issues
 Hello-World Python       2500    2100          0
     Spoon-Knife    HTML       12100   150300          0
       ...

=== Summary ===
total_repos: 8
total_stars: 3050
total_forks: 152600
average_stars: 381.25
most_used_language: HTML
...
```

## Possible extensions

- Add authentication so users can analyze their own private repos.
- Cache results in SQLite instead of an in-memory dict.
- Add a comparison mode for two usernames side-by-side.
- Add unit tests (`pytest`) for `github_analyzer.py` using `responses` or `unittest.mock` to mock the GitHub API.
