"""
github_analyzer.py
-------------------
Core backend logic for the GitHub Repo Analyzer project.

Responsibilities:
    1. Call GitHub's public REST API to fetch repository data for a user.
    2. Load the data into a Pandas DataFrame.
    3. Sort and summarize the data (stars, forks, languages, etc.)

This module has NO Flask/web code in it on purpose - it can be imported
by the Flask app (app.py) OR run directly from the command line (see
the __main__ block at the bottom).
"""

import requests
import pandas as pd
from datetime import datetime


GITHUB_API_URL = "https://api.github.com"


class GitHubUserNotFoundError(Exception):
    """Raised when the requested GitHub username does not exist."""
    pass


class GitHubAPIError(Exception):
    """Raised for any other GitHub API related error (rate limits, etc.)."""
    pass


def fetch_repos(username: str, token: str = None, per_page: int = 100) -> list:
    """
    Fetch ALL public repositories for a given GitHub username.

    GitHub paginates results, so we loop through pages until there is
    no more data left ("pagination" pattern).

    Parameters
    ----------
    username : str
        The GitHub username to look up.
    token : str, optional
        A GitHub personal access token. Not required for public data,
        but if provided it raises the API rate limit from 60/hr to 5000/hr.
    per_page : int
        How many repos to request per page (GitHub max is 100).

    Returns
    -------
    list of dict
        Raw JSON repo objects as returned by the GitHub API.
    """
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    all_repos = []
    page = 1

    # First, make sure the user actually exists.
    user_check = requests.get(f"{GITHUB_API_URL}/users/{username}", headers=headers)
    if user_check.status_code == 404:
        raise GitHubUserNotFoundError(f"GitHub user '{username}' was not found.")
    if user_check.status_code == 403:
        raise GitHubAPIError("GitHub API rate limit exceeded. Try again later or use a token.")
    if user_check.status_code != 200:
        raise GitHubAPIError(f"Unexpected error checking user (status {user_check.status_code}).")

    while True:
        params = {"per_page": per_page, "page": page, "type": "owner", "sort": "updated"}
        response = requests.get(
            f"{GITHUB_API_URL}/users/{username}/repos",
            headers=headers,
            params=params,
        )

        if response.status_code == 403:
            raise GitHubAPIError("GitHub API rate limit exceeded. Try again later or use a token.")
        if response.status_code != 200:
            raise GitHubAPIError(f"GitHub API returned status {response.status_code}.")

        page_data = response.json()
        if not page_data:
            break

        all_repos.extend(page_data)
        page += 1

        # Safety valve - stop after 1000 repos so we never loop forever.
        if page > 10:
            break

    return all_repos


def build_dataframe(repos: list) -> pd.DataFrame:
    """
    Convert the raw GitHub API repo list (list of dicts) into a clean
    Pandas DataFrame with only the columns we care about.
    """
    if not repos:
        return pd.DataFrame(
            columns=[
                "name", "description", "language", "stars", "forks",
                "watchers", "open_issues", "size_kb", "created_at",
                "updated_at", "url", "is_fork", "archived",
            ]
        )

    records = []
    for repo in repos:
        records.append({
            "name": repo.get("name"),
            "description": repo.get("description") or "No description",
            "language": repo.get("language") or "Unknown",
            "stars": repo.get("stargazers_count", 0),
            "forks": repo.get("forks_count", 0),
            "watchers": repo.get("watchers_count", 0),
            "open_issues": repo.get("open_issues_count", 0),
            "size_kb": repo.get("size", 0),
            "created_at": repo.get("created_at"),
            "updated_at": repo.get("updated_at"),
            "url": repo.get("html_url"),
            "is_fork": repo.get("fork", False),
            "archived": repo.get("archived", False),
        })

    df = pd.DataFrame(records)

    # Convert date strings into real datetime objects for later use.
    for col in ("created_at", "updated_at"):
        df[col] = pd.to_datetime(df[col], errors="coerce")

    return df


def sort_repos(df: pd.DataFrame, sort_by: str = "stars", ascending: bool = False) -> pd.DataFrame:
    """
    Sort the DataFrame by a given column.

    Parameters
    ----------
    sort_by : str
        One of: 'stars', 'forks', 'name', 'updated_at', 'created_at', 'open_issues'
    ascending : bool
        Sort order.
    """
    valid_columns = {"stars", "forks", "name", "updated_at", "created_at", "open_issues", "size_kb"}
    if sort_by not in valid_columns:
        sort_by = "stars"

    if df.empty:
        return df

    return df.sort_values(by=sort_by, ascending=ascending).reset_index(drop=True)


def summarize(df: pd.DataFrame) -> dict:
    """
    Produce summary statistics from the DataFrame using Pandas
    aggregation functions (sum, mean, idxmax, value_counts, etc.)

    Returns a plain dict so it's easy to convert to JSON for the frontend.
    """
    if df.empty:
        return {
            "total_repos": 0,
            "total_stars": 0,
            "total_forks": 0,
            "average_stars": 0,
            "average_forks": 0,
            "most_used_language": None,
            "language_distribution": {},
            "top_repo_by_stars": None,
            "most_recently_updated": None,
        }

    total_repos = int(len(df))
    total_stars = int(df["stars"].sum())
    total_forks = int(df["forks"].sum())
    average_stars = round(float(df["stars"].mean()), 2)
    average_forks = round(float(df["forks"].mean()), 2)

    language_counts = df["language"].value_counts()
    most_used_language = language_counts.idxmax() if not language_counts.empty else None
    language_distribution = language_counts.to_dict()

    top_repo_row = df.loc[df["stars"].idxmax()]
    top_repo_by_stars = {
        "name": top_repo_row["name"],
        "stars": int(top_repo_row["stars"]),
        "url": top_repo_row["url"],
    }

    most_recent_row = df.loc[df["updated_at"].idxmax()] if df["updated_at"].notna().any() else None
    most_recently_updated = None
    if most_recent_row is not None:
        most_recently_updated = {
            "name": most_recent_row["name"],
            "updated_at": str(most_recent_row["updated_at"]),
        }

    return {
        "total_repos": total_repos,
        "total_stars": total_stars,
        "total_forks": total_forks,
        "average_stars": average_stars,
        "average_forks": average_forks,
        "most_used_language": most_used_language,
        "language_distribution": language_distribution,
        "top_repo_by_stars": top_repo_by_stars,
        "most_recently_updated": most_recently_updated,
    }


def analyze_user(username: str, token: str = None, sort_by: str = "stars", ascending: bool = False):
    """
    Convenience function that ties everything together:
    fetch -> build DataFrame -> sort -> summarize.

    Returns (dataframe, summary_dict)
    """
    raw_repos = fetch_repos(username, token=token)
    df = build_dataframe(raw_repos)
    df_sorted = sort_repos(df, sort_by=sort_by, ascending=ascending)
    summary = summarize(df)
    return df_sorted, summary


# ---------------------------------------------------------------------------
# Command-line interface: lets you run this file directly, e.g.
#     python github_analyzer.py torvalds
# without needing the Flask web app at all.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="GitHub Repo Analyzer (CLI mode)")
    parser.add_argument("username", help="GitHub username to analyze")
    parser.add_argument("--sort", default="stars", help="Column to sort by (default: stars)")
    parser.add_argument("--asc", action="store_true", help="Sort ascending instead of descending")
    parser.add_argument("--token", default=None, help="Optional GitHub personal access token")
    parser.add_argument("--csv", default=None, help="Optional path to save results as CSV")
    args = parser.parse_args()

    try:
        print(f"Fetching repositories for '{args.username}'...")
        df, summary = analyze_user(args.username, token=args.token, sort_by=args.sort, ascending=args.asc)
    except GitHubUserNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except GitHubAPIError as e:
        print(f"API Error: {e}")
        sys.exit(1)

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 150)

    print("\n=== Repository Table ===")
    print(df[["name", "language", "stars", "forks", "open_issues"]].to_string(index=False))

    print("\n=== Summary ===")
    for key, value in summary.items():
        print(f"{key}: {value}")

    if args.csv:
        df.to_csv(args.csv, index=False)
        print(f"\nSaved results to {args.csv}")
