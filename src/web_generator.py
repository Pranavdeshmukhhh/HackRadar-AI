"""
Web Dashboard Generator for HackRadar-AI.
Compiles scraped hackathon events into a modern, responsive, high-performance
single-page application hosted on GitHub Pages (docs/index.html & docs/hackathons.json).
"""

from __future__ import annotations

import os
import json
from datetime import datetime, timezone
from typing import List, Dict, Any

from .models import HackathonEvent


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>HackRadar-AI | 24/7 Autonomous Hackathon Radar</title>
  <meta name="description" content="Autonomous 24/7 intelligence monitor & opportunity radar for developers. Scans Unstop, Devfolio, Devpost, HackerEarth, and MLH with Nagpur & Solo prioritization.">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #07090e;
      --card-bg: rgba(18, 24, 38, 0.7);
      --card-hover: rgba(28, 38, 60, 0.85);
      --border: rgba(255, 255, 255, 0.08);
      --border-accent: rgba(99, 102, 241, 0.4);
      --text: #f1f5f9;
      --text-muted: #94a3b8;
      --primary: #6366f1;
      --primary-glow: rgba(99, 102, 241, 0.35);
      --amber: #f59e0b;
      --amber-glow: rgba(245, 158, 11, 0.25);
      --emerald: #10b981;
      --emerald-glow: rgba(16, 185, 129, 0.25);
      --cyan: #06b6d4;
      --purple: #a855f7;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      background-color: var(--bg);
      background-image: 
        radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.15) 0px, transparent 50%),
        radial-gradient(at 100% 0%, rgba(245, 158, 11, 0.1) 0px, transparent 50%),
        radial-gradient(at 50% 100%, rgba(16, 185, 129, 0.1) 0px, transparent 50%);
      background-attachment: fixed;
      color: var(--text);
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      min-height: 100vh;
      line-height: 1.5;
    }

    header {
      padding: 3rem 1.5rem 2rem;
      max-width: 1280px;
      margin: 0 auto;
      text-align: center;
    }

    .badge-pill {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.35rem 0.9rem;
      background: rgba(99, 102, 241, 0.15);
      border: 1px solid var(--border-accent);
      border-radius: 9999px;
      font-size: 0.85rem;
      font-weight: 600;
      color: #c7d2fe;
      margin-bottom: 1rem;
      box-shadow: 0 0 20px var(--primary-glow);
    }

    .pulse-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background-color: var(--emerald);
      box-shadow: 0 0 10px var(--emerald);
      animation: pulse 2s infinite;
    }

    @keyframes pulse {
      0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
      70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
      100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
    }

    h1 {
      font-family: 'Outfit', sans-serif;
      font-size: clamp(2.2rem, 5vw, 3.8rem);
      font-weight: 800;
      letter-spacing: -0.02em;
      background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 50%, #94a3b8 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      margin-bottom: 0.75rem;
    }

    .subtitle {
      font-size: 1.15rem;
      color: var(--text-muted);
      max-width: 720px;
      margin: 0 auto 2rem;
    }

    /* Stats Grid */
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
      max-width: 1100px;
      margin: 0 auto 2.5rem;
    }

    .stat-card {
      background: var(--card-bg);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border);
      border-radius: 1rem;
      padding: 1.25rem;
      text-align: center;
      transition: transform 0.2s, border-color 0.2s;
    }

    .stat-card:hover {
      transform: translateY(-2px);
      border-color: rgba(255, 255, 255, 0.2);
    }

    .stat-num {
      font-family: 'Outfit', sans-serif;
      font-size: 2rem;
      font-weight: 700;
      color: #fff;
    }

    .stat-label {
      font-size: 0.85rem;
      color: var(--text-muted);
      margin-top: 0.25rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    /* Controls: Search, Filters, Sort */
    .controls-container {
      max-width: 1280px;
      margin: 0 auto 2rem;
      padding: 0 1.5rem;
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .search-row {
      display: flex;
      gap: 1rem;
      flex-wrap: wrap;
    }

    .search-input-wrap {
      flex: 1;
      min-width: 280px;
      position: relative;
    }

    .search-input {
      width: 100%;
      padding: 0.9rem 1.2rem 0.9rem 2.8rem;
      background: var(--card-bg);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      color: #fff;
      font-size: 1rem;
      outline: none;
      transition: border-color 0.2s, box-shadow 0.2s;
    }

    .search-input:focus {
      border-color: var(--primary);
      box-shadow: 0 0 15px var(--primary-glow);
    }

    .search-icon {
      position: absolute;
      left: 1rem;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-muted);
      font-size: 1.1rem;
    }

    .sort-select {
      padding: 0.9rem 1.2rem;
      background: var(--card-bg);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      color: #fff;
      font-size: 0.95rem;
      outline: none;
      cursor: pointer;
    }

    .filter-pills {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
    }

    .pill-btn {
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--border);
      color: var(--text-muted);
      padding: 0.45rem 1rem;
      border-radius: 9999px;
      font-size: 0.85rem;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s;
    }

    .pill-btn:hover {
      background: rgba(255, 255, 255, 0.1);
      color: #fff;
    }

    .pill-btn.active {
      background: var(--primary);
      border-color: var(--primary);
      color: #fff;
      box-shadow: 0 0 15px var(--primary-glow);
    }

    .pill-btn.nagpur.active {
      background: var(--amber);
      border-color: var(--amber);
      box-shadow: 0 0 15px var(--amber-glow);
    }

    .pill-btn.solo.active {
      background: var(--emerald);
      border-color: var(--emerald);
      box-shadow: 0 0 15px var(--emerald-glow);
    }

    /* Grid */
    main {
      max-width: 1280px;
      margin: 0 auto;
      padding: 0 1.5rem 5rem;
    }

    .cards-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
      gap: 1.5rem;
    }

    .event-card {
      background: var(--card-bg);
      backdrop-filter: blur(14px);
      border: 1px solid var(--border);
      border-radius: 1.2rem;
      padding: 1.5rem;
      display: flex;
      flex-direction: column;
      position: relative;
      overflow: hidden;
      transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.25s, box-shadow 0.25s;
    }

    .event-card:hover {
      transform: translateY(-4px);
      border-color: rgba(255, 255, 255, 0.2);
      box-shadow: 0 12px 30px rgba(0, 0, 0, 0.5);
    }

    .event-card.nagpur-card {
      border-color: rgba(245, 158, 11, 0.4);
      background: linear-gradient(180deg, rgba(245, 158, 11, 0.05) 0%, var(--card-bg) 40%);
    }

    .card-top {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 0.8rem;
    }

    .score-badge {
      display: inline-flex;
      align-items: center;
      gap: 0.25rem;
      padding: 0.3rem 0.7rem;
      border-radius: 0.5rem;
      font-size: 0.85rem;
      font-weight: 700;
      font-family: 'Outfit', sans-serif;
    }

    .score-high {
      background: rgba(245, 158, 11, 0.15);
      border: 1px solid rgba(245, 158, 11, 0.4);
      color: #fbbf24;
    }

    .score-mid {
      background: rgba(99, 102, 241, 0.15);
      border: 1px solid rgba(99, 102, 241, 0.4);
      color: #a5b4fc;
    }

    .source-tag {
      font-size: 0.75rem;
      text-transform: uppercase;
      font-weight: 700;
      letter-spacing: 0.05em;
      color: var(--text-muted);
    }

    .card-title {
      font-family: 'Outfit', sans-serif;
      font-size: 1.25rem;
      font-weight: 700;
      color: #fff;
      line-height: 1.3;
      margin-bottom: 0.5rem;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    .card-org {
      font-size: 0.9rem;
      color: var(--cyan);
      font-weight: 500;
      margin-bottom: 0.75rem;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .meta-row {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      margin-bottom: 1rem;
    }

    .tag {
      display: inline-flex;
      align-items: center;
      gap: 0.3rem;
      font-size: 0.75rem;
      padding: 0.25rem 0.6rem;
      border-radius: 0.4rem;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border);
      color: #e2e8f0;
    }

    .tag.solo {
      background: rgba(16, 185, 129, 0.15);
      border-color: rgba(16, 185, 129, 0.4);
      color: #34d399;
      font-weight: 600;
    }

    .tag.nagpur {
      background: rgba(245, 158, 11, 0.15);
      border-color: rgba(245, 158, 11, 0.4);
      color: #fbbf24;
      font-weight: 600;
    }

    .tag.online {
      background: rgba(6, 182, 212, 0.15);
      border-color: rgba(6, 182, 212, 0.4);
      color: #67e8f9;
    }

    .reasons-box {
      background: rgba(0, 0, 0, 0.25);
      border-radius: 0.5rem;
      padding: 0.6rem 0.8rem;
      margin-bottom: 1rem;
      font-size: 0.8rem;
      color: var(--text-muted);
      border-left: 3px solid var(--primary);
    }

    .reasons-box.nagpur-accent {
      border-left-color: var(--amber);
    }

    .card-footer {
      margin-top: auto;
      padding-top: 1rem;
      border-top: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .deadline-badge {
      font-size: 0.8rem;
      color: #cbd5e1;
    }

    .apply-btn {
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      background: var(--primary);
      color: #fff;
      text-decoration: none;
      padding: 0.55rem 1.1rem;
      border-radius: 0.6rem;
      font-size: 0.85rem;
      font-weight: 600;
      transition: background 0.2s, box-shadow 0.2s;
    }

    .apply-btn:hover {
      background: #4f46e5;
      box-shadow: 0 0 15px var(--primary-glow);
    }

    .no-results {
      grid-column: 1 / -1;
      text-align: center;
      padding: 4rem 1rem;
      color: var(--text-muted);
    }

    footer {
      text-align: center;
      padding: 3rem 1.5rem;
      color: var(--text-muted);
      font-size: 0.9rem;
      border-top: 1px solid var(--border);
    }

    footer a {
      color: var(--primary);
      text-decoration: none;
    }
  </style>
</head>
<body>

  <header>
    <div class="badge-pill">
      <span class="pulse-dot"></span>
      <span>24/7 Continuous Web Scanner Active</span>
    </div>
    <h1>🛰️ HackRadar-AI</h1>
    <p class="subtitle">Autonomous 24/7 intelligence monitor & opportunity radar for engineers, coders, and hackathon competitors — prioritizing Nagpur, Solo eligibility, and AI tracks.</p>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-num" id="stat-total">0</div>
        <div class="stat-label">Total Verified Hackathons</div>
      </div>
      <div class="stat-card">
        <div class="stat-num" id="stat-nagpur" style="color: var(--amber)">0</div>
        <div class="stat-label">Nagpur & Vidarbha Regionals</div>
      </div>
      <div class="stat-card">
        <div class="stat-num" id="stat-solo" style="color: var(--emerald)">0</div>
        <div class="stat-label">Solo Eligible (1 Member)</div>
      </div>
      <div class="stat-card">
        <div class="stat-num" id="stat-ai" style="color: var(--purple)">0</div>
        <div class="stat-label">AI & Software Tracks</div>
      </div>
    </div>
  </header>

  <div class="controls-container">
    <div class="search-row">
      <div class="search-input-wrap">
        <span class="search-icon">🔍</span>
        <input type="text" id="searchInput" class="search-input" placeholder="Search by name, college (VNIT, IIIT), track, or host...">
      </div>
      <select id="sortSelect" class="sort-select">
        <option value="score">Sort: Highest Match Score</option>
        <option value="deadline">Sort: Ending Soonest</option>
        <option value="solo">Sort: Solo Friendly First</option>
      </select>
    </div>

    <div class="filter-pills">
      <button class="pill-btn active" data-filter="all">All Opportunities</button>
      <button class="pill-btn nagpur" data-filter="nagpur">📍 Nagpur & Vidarbha Priority</button>
      <button class="pill-btn solo" data-filter="solo">👤 Solo Eligible</button>
      <button class="pill-btn" data-filter="ai">🤖 AI / GenAI Tracks</button>
      <button class="pill-btn" data-filter="online">🌐 Online / Virtual</button>
      <button class="pill-btn" data-filter="inperson">🏢 In-Person / On-Campus</button>
    </div>
  </div>

  <main>
    <div class="cards-grid" id="cardsGrid"></div>
  </main>

  <footer>
    <p>Powered by <strong>HackRadar-AI</strong> • Scrapes Unstop, Devfolio, Devpost, HackerEarth & MLH every hour 24/7.</p>
    <p style="margin-top: 0.5rem;"><a href="https://github.com/Pranavdeshmukhhh/HackRadar-AI" target="_blank">View GitHub Repository</a> • <a href="https://github.com/Pranavdeshmukhhh/HackRadar-AI/blob/main/HACKATHONS.md" target="_blank">Markdown Dashboard</a></p>
  </footer>

  <!-- Embedded JSON Dataset -->
  <script id="hackathons-data" type="application/json">
__DATA_JSON__
  </script>

  <script>
    let rawEvents = [];
    let currentFilter = 'all';

    function init() {
      try {
        const dataElement = document.getElementById('hackathons-data');
        if (dataElement && dataElement.textContent.trim()) {
          rawEvents = JSON.parse(dataElement.textContent);
        }
      } catch (err) {
        console.error("Failed to parse embedded hackathons data:", err);
      }

      // If embedded empty, fetch dynamically
      if (!rawEvents || rawEvents.length === 0) {
        fetch('hackathons.json')
          .then(r => r.json())
          .then(data => {
            rawEvents = data;
            render();
          })
          .catch(err => console.error("Could not fetch hackathons.json", err));
      } else {
        render();
      }

      setupEvents();
    }

    function setupEvents() {
      document.getElementById('searchInput').addEventListener('input', () => renderCards());
      document.getElementById('sortSelect').addEventListener('change', () => renderCards());

      document.querySelectorAll('.pill-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          document.querySelectorAll('.pill-btn').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          currentFilter = btn.getAttribute('data-filter');
          renderCards();
        });
      });
    }

    function render() {
      updateStats();
      renderCards();
    }

    function updateStats() {
      document.getElementById('stat-total').textContent = rawEvents.length;
      document.getElementById('stat-nagpur').textContent = rawEvents.filter(e => e.is_nagpur_local).length;
      document.getElementById('stat-solo').textContent = rawEvents.filter(e => e.solo_allowed).length;
      document.getElementById('stat-ai').textContent = rawEvents.filter(e => {
        const text = (e.title + ' ' + (e.tracks || []).join(' ')).toLowerCase();
        return text.includes('ai') || text.includes('machine learning') || text.includes('software');
      }).length;
    }

    function renderCards() {
      const grid = document.getElementById('cardsGrid');
      const search = document.getElementById('searchInput').value.trim().toLowerCase();
      const sort = document.getElementById('sortSelect').value;

      let filtered = rawEvents.filter(e => {
        // Filter by tab
        if (currentFilter === 'nagpur' && !e.is_nagpur_local) return false;
        if (currentFilter === 'solo' && !e.solo_allowed) return false;
        if (currentFilter === 'online' && e.mode !== 'Online') return false;
        if (currentFilter === 'inperson' && e.mode === 'Online') return false;
        if (currentFilter === 'ai') {
          const text = (e.title + ' ' + (e.tracks || []).join(' ')).toLowerCase();
          if (!text.includes('ai') && !text.includes('ml') && !text.includes('software')) return false;
        }

        // Search match
        if (search) {
          const searchable = [
            e.title,
            e.organizer,
            e.venue,
            e.source,
            (e.tracks || []).join(' '),
            (e.matched_reasons || []).join(' ')
          ].join(' ').toLowerCase();

          if (!searchable.includes(search)) return false;
        }

        return true;
      });

      // Sorting
      if (sort === 'score') {
        filtered.sort((a, b) => (b.score || 0) - (a.score || 0));
      } else if (sort === 'deadline') {
        filtered.sort((a, b) => {
          const d1 = a.registration_deadline ? new Date(a.registration_deadline).getTime() : 9999999999999;
          const d2 = b.registration_deadline ? new Date(b.registration_deadline).getTime() : 9999999999999;
          return d1 - d2;
        });
      } else if (sort === 'solo') {
        filtered.sort((a, b) => (b.solo_allowed ? 1 : 0) - (a.solo_allowed ? 1 : 0));
      }

      if (filtered.length === 0) {
        grid.innerHTML = `
          <div class="no-results">
            <h3>No matching hackathons found</h3>
            <p style="margin-top:0.5rem">Try adjusting your filters or search keywords.</p>
          </div>
        `;
        return;
      }

      grid.innerHTML = filtered.map(e => {
        const isNagpur = e.is_nagpur_local;
        const scoreClass = (e.score >= 80) ? 'score-high' : 'score-mid';
        const soloBadge = e.solo_allowed ? `<span class="tag solo">👤 Solo Eligible</span>` : `<span class="tag">👥 Team of ${e.min_team_size}-${e.max_team_size || 'N'}</span>`;
        const nagpurTag = isNagpur ? `<span class="tag nagpur">📍 Nagpur & Vidarbha</span>` : '';
        const modeTag = `<span class="tag online">${e.mode === 'Online' ? '🌐 Virtual' : (e.mode === 'Hybrid' ? '⚡ Hybrid' : '🏢 In-Person')}</span>`;
        
        let deadlineStr = 'Registration Open';
        if (e.registration_deadline) {
          try {
            const dt = new Date(e.registration_deadline);
            deadlineStr = `Ends: ${dt.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}`;
          } catch (_) {
            deadlineStr = `Ends: ${e.registration_deadline}`;
          }
        }

        const reasons = (e.matched_reasons || []).slice(0, 3).map(r => `• ${r}`).join('<br>');

        return `
          <div class="event-card ${isNagpur ? 'nagpur-card' : ''}">
            <div class="card-top">
              <span class="source-tag">${e.source}</span>
              <span class="score-badge ${scoreClass}">★ ${e.score} pts</span>
            </div>

            <h2 class="card-title" title="${escapeHtml(e.title)}">${escapeHtml(e.title)}</h2>
            <div class="card-org">${escapeHtml(e.organizer || e.venue || 'Organizer TBA')}</div>

            <div class="meta-row">
              ${nagpurTag}
              ${soloBadge}
              ${modeTag}
            </div>

            ${reasons ? `<div class="reasons-box ${isNagpur ? 'nagpur-accent' : ''}">${reasons}</div>` : ''}

            <div class="card-footer">
              <span class="deadline-badge">📅 ${deadlineStr}</span>
              <a href="${escapeHtml(e.url)}" target="_blank" rel="noopener noreferrer" class="apply-btn">Apply Now 🚀</a>
            </div>
          </div>
        `;
      }).join('');
    }

    function escapeHtml(str) {
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
    }

    window.addEventListener('DOMContentLoaded', init);
  </script>
</body>
</html>
"""


def generate_web_dashboard(events: List[HackathonEvent], output_dir: str = "docs") -> str:
    """
    Generate interactive HTML dashboard & JSON dataset for GitHub Pages hosting.
    Returns path to generated index.html.
    """
    os.makedirs(output_dir, exist_ok=True)
    dict_events = [e.to_dict() for e in events]

    # 1. Output docs/hackathons.json
    json_path = os.path.join(output_dir, "hackathons.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(dict_events, f, indent=2, ensure_ascii=False)

    # 2. Output docs/index.html with embedded JSON
    html_content = HTML_TEMPLATE.replace(
        "__DATA_JSON__",
        json.dumps(dict_events, ensure_ascii=False)
    )

    html_path = os.path.join(output_dir, "index.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return html_path
