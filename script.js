// script.js
// Handles form submission, calls the Flask /api/analyze endpoint,
// and renders the summary cards, Chart.js charts, and repo table.

const form = document.getElementById("analyze-form");
const runBtn = document.getElementById("run-btn");
const statusLine = document.getElementById("status-line");
const resultsSection = document.getElementById("results");
const emptyState = document.getElementById("empty-state");
const exportBtn = document.getElementById("export-btn");

let languageChartInstance = null;
let starsChartInstance = null;
let currentUsername = null;

// A small fixed palette so the charts match the site's dark/violet/teal theme.
const CHART_PALETTE = [
  "#7c5cff", "#2dd9c4", "#ffb454", "#ff6b6b", "#a996ff",
  "#5fd0ff", "#f472b6", "#8b8fff", "#4ade80", "#facc15",
];

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const username = document.getElementById("username").value.trim();
  const sortBy = document.getElementById("sort_by").value;
  const ascending = document.getElementById("ascending").value === "true";
  const token = document.getElementById("token").value.trim();

  if (!username) return;

  runBtn.disabled = true;
  runBtn.textContent = "running...";
  setStatus(`fetching repositories for '${username}' from GitHub API...`, "");

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, sort_by: sortBy, ascending, token }),
    });

    const data = await response.json();

    if (!response.ok || !data.success) {
      setStatus(`error: ${data.error || "something went wrong"}`, "error");
      resultsSection.classList.add("hidden");
      emptyState.classList.remove("hidden");
      return;
    }

    currentUsername = data.username;
    setStatus(`done — analyzed ${data.repo_count} repositories for '${data.username}'.`, "success");
    renderResults(data);
  } catch (err) {
    setStatus(`network error: ${err.message}`, "error");
  } finally {
    runBtn.disabled = false;
    runBtn.textContent = "run \u203a";
  }
});

exportBtn.addEventListener("click", () => {
  if (!currentUsername) return;
  window.location.href = `/api/export/${encodeURIComponent(currentUsername)}`;
});

function setStatus(msg, cls) {
  statusLine.textContent = "> " + msg;
  statusLine.className = "status-line " + (cls || "");
}

function renderResults(data) {
  emptyState.classList.add("hidden");
  resultsSection.classList.remove("hidden");

  renderSummary(data.summary);
  renderLanguageChart(data.summary.language_distribution);
  renderStarsChart(data.repos);
  renderTable(data.repos);
}

function renderSummary(summary) {
  document.getElementById("stat-repos").textContent = summary.total_repos;
  document.getElementById("stat-stars").textContent = summary.total_stars.toLocaleString();
  document.getElementById("stat-forks").textContent = summary.total_forks.toLocaleString();
  document.getElementById("stat-avg").textContent = summary.average_stars;
  document.getElementById("stat-lang").textContent = summary.most_used_language || "-";

  const topRepoEl = document.getElementById("stat-top-repo");
  if (summary.top_repo_by_stars) {
    topRepoEl.textContent = `${summary.top_repo_by_stars.name} (${summary.top_repo_by_stars.stars}\u2605)`;
    topRepoEl.onclick = () => window.open(summary.top_repo_by_stars.url, "_blank");
  } else {
    topRepoEl.textContent = "-";
    topRepoEl.onclick = null;
  }
}

function renderLanguageChart(languageDistribution) {
  const ctx = document.getElementById("languageChart").getContext("2d");
  const entries = Object.entries(languageDistribution || {}).sort((a, b) => b[1] - a[1]);

  const labels = entries.map(([lang]) => lang);
  const values = entries.map(([, count]) => count);

  if (languageChartInstance) languageChartInstance.destroy();

  languageChartInstance = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: CHART_PALETTE,
        borderColor: "#1b1a29",
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "right",
          labels: { color: "#e9e7f3", font: { family: "JetBrains Mono", size: 11 }, boxWidth: 12 },
        },
      },
    },
  });
}

function renderStarsChart(repos) {
  const ctx = document.getElementById("starsChart").getContext("2d");
  const top = [...repos].sort((a, b) => b.stars - a.stars).slice(0, 8);

  if (starsChartInstance) starsChartInstance.destroy();

  starsChartInstance = new Chart(ctx, {
    type: "bar",
    data: {
      labels: top.map((r) => r.name),
      datasets: [{
        label: "stars",
        data: top.map((r) => r.stars),
        backgroundColor: "#7c5cff",
        borderRadius: 4,
      }],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#928fae" }, grid: { color: "#2d2b42" } },
        y: { ticks: { color: "#e9e7f3", font: { family: "JetBrains Mono", size: 11 } }, grid: { display: false } },
      },
    },
  });
}

function renderTable(repos) {
  const tbody = document.getElementById("repo-table-body");
  tbody.innerHTML = "";

  repos.forEach((repo) => {
    const tr = document.createElement("tr");

    const updated = repo.updated_at ? repo.updated_at.split("T")[0].split(" ")[0] : "-";

    tr.innerHTML = `
      <td><a href="${repo.url}" target="_blank" rel="noopener">${escapeHtml(repo.name)}</a></td>
      <td><span class="lang-pill">${escapeHtml(repo.language || "Unknown")}</span></td>
      <td>${repo.stars.toLocaleString()}</td>
      <td>${repo.forks.toLocaleString()}</td>
      <td>${repo.open_issues.toLocaleString()}</td>
      <td>${updated}</td>
    `;
    tbody.appendChild(tr);
  });
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}
