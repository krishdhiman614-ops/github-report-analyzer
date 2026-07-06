"""
app.py
------
Flask backend for the GitHub Repo Analyzer project.

Routes:
    GET  /                 -> Renders the main frontend page (index.html)
    POST /api/analyze      -> Accepts a username (JSON), returns repo data + summary as JSON
    GET  /api/export/<user>-> Downloads the analyzed repo data as a CSV file

Run with:
    python app.py
Then open http://127.0.0.1:5000 in your browser.
"""

import io
import os

from flask import Flask, render_template, request, jsonify, send_file

from github_analyzer import (
    analyze_user,
    GitHubUserNotFoundError,
    GitHubAPIError,
)

app = Flask(__name__)

# Simple in-memory cache so re-exporting a CSV doesn't require re-fetching
# from GitHub every single time within the same session.
_last_results_cache = {}


@app.route("/")
def index():
    """Serve the main frontend page."""
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    """
    Main API endpoint. Expects JSON body like:
        {
            "username": "torvalds",
            "sort_by": "stars",
            "ascending": false,
            "token": ""   (optional)
        }

    Returns JSON:
        {
            "success": true,
            "username": "...",
            "repos": [ {...}, {...}, ... ],
            "summary": { ... }
        }
    """
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    sort_by = data.get("sort_by", "stars")
    ascending = bool(data.get("ascending", False))
    token = data.get("token") or os.environ.get("GITHUB_TOKEN") or None

    if not username:
        return jsonify({"success": False, "error": "Please provide a GitHub username."}), 400

    try:
        df, summary = analyze_user(username, token=token, sort_by=sort_by, ascending=ascending)
    except GitHubUserNotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except GitHubAPIError as e:
        return jsonify({"success": False, "error": str(e)}), 429
    except Exception as e:  # noqa: BLE001 - want to surface any unexpected error to the UI
        return jsonify({"success": False, "error": f"Unexpected error: {e}"}), 500

    # Cache the dataframe (as records) for CSV export.
    _last_results_cache[username.lower()] = df

    # Convert DataFrame to a JSON-friendly list of dicts.
    # Dates need to be turned into strings since datetime objects aren't JSON serializable.
    df_json_ready = df.copy()
    for col in ("created_at", "updated_at"):
        df_json_ready[col] = df_json_ready[col].astype(str)

    repos = df_json_ready.to_dict(orient="records")

    return jsonify({
        "success": True,
        "username": username,
        "repo_count": len(repos),
        "repos": repos,
        "summary": summary,
    })


@app.route("/api/export/<username>")
def api_export(username):
    """Download the most recently analyzed data for a user as a CSV file."""
    df = _last_results_cache.get(username.lower())
    if df is None:
        return jsonify({"success": False, "error": "No cached data for this user. Analyze first."}), 404

    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    byte_buffer = io.BytesIO(buffer.getvalue().encode("utf-8"))
    byte_buffer.seek(0)

    return send_file(
        byte_buffer,
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"{username}_github_repos.csv",
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
