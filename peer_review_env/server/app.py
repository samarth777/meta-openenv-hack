# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""FastAPI application for the OpenReview score-prediction benchmark."""

from fastapi.responses import HTMLResponse

try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:  # pragma: no cover
    raise ImportError(
        "openenv is required for the web interface. Install dependencies with '\n    uv sync\n'"
    ) from e

try:
    from ..models import PeerReviewAction, PeerReviewObservation
    from .peer_review_env_environment import PeerReviewEnvironment
    from ..tasks import TASK_ORDER, TASKS
except ModuleNotFoundError:
    from models import PeerReviewAction, PeerReviewObservation
    from server.peer_review_env_environment import PeerReviewEnvironment
    from tasks import TASK_ORDER, TASKS


app = create_app(
    PeerReviewEnvironment,
    PeerReviewAction,
    PeerReviewObservation,
    env_name="peer_review_env",
    max_concurrent_envs=8,
)


_FRONTEND_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>OpenReview Score Prediction Benchmark</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0b1020;
      --panel: rgba(15, 23, 42, 0.88);
      --panel-2: rgba(30, 41, 59, 0.88);
      --text: #e5eefc;
      --muted: #94a3b8;
      --accent: #60a5fa;
      --accent-2: #22d3ee;
      --border: rgba(148, 163, 184, 0.22);
      --good: #34d399;
      --warn: #fbbf24;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
      background:
        radial-gradient(circle at top left, rgba(34, 211, 238, 0.14), transparent 28%),
        radial-gradient(circle at top right, rgba(96, 165, 250, 0.18), transparent 32%),
        linear-gradient(180deg, #020617 0%, #0f172a 100%);
      color: var(--text);
      min-height: 100vh;
    }
    a { color: var(--accent-2); }
    .wrap {
      max-width: 1360px;
      margin: 0 auto;
      padding: 24px;
    }
    .hero {
      display: grid;
      grid-template-columns: 1.25fr 0.75fr;
      gap: 18px;
      margin-bottom: 18px;
    }
    .card {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 20px;
      backdrop-filter: blur(16px);
      box-shadow: 0 24px 80px rgba(0, 0, 0, 0.35);
    }
    .hero-main {
      padding: 24px;
    }
    .eyebrow {
      color: var(--accent-2);
      font-size: 12px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      margin-bottom: 10px;
    }
    h1 {
      margin: 0 0 10px;
      font-size: clamp(2rem, 4vw, 3.3rem);
      line-height: 1;
    }
    .hero p {
      margin: 0;
      color: var(--muted);
      max-width: 70ch;
      line-height: 1.5;
    }
    .hero-side {
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      justify-content: center;
      background: linear-gradient(145deg, rgba(14, 165, 233, 0.12), rgba(15, 23, 42, 0.92));
    }
    .metric {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      padding: 10px 0;
      border-bottom: 1px solid rgba(148, 163, 184, 0.12);
    }
    .metric:last-child { border-bottom: 0; }
    .metric span:first-child { color: var(--muted); }
    .layout {
      display: grid;
      grid-template-columns: 360px minmax(0, 1fr);
      gap: 18px;
    }
    .sidebar, .content {
      display: flex;
      flex-direction: column;
      gap: 18px;
    }
    .section {
      padding: 18px;
    }
    .section h2 {
      margin: 0 0 14px;
      font-size: 1rem;
    }
    label {
      display: block;
      font-size: 0.9rem;
      color: var(--muted);
      margin-bottom: 8px;
    }
    select, input, button, textarea {
      width: 100%;
      border-radius: 12px;
      border: 1px solid rgba(148, 163, 184, 0.22);
      background: rgba(15, 23, 42, 0.82);
      color: var(--text);
      padding: 12px 14px;
      font: inherit;
    }
    input[type=range] {
      padding: 0;
      background: transparent;
      border: 0;
    }
    button {
      cursor: pointer;
      background: linear-gradient(135deg, var(--accent), var(--accent-2));
      color: #04111f;
      font-weight: 700;
      border: 0;
    }
    button.secondary {
      background: rgba(15, 23, 42, 0.88);
      color: var(--text);
      border: 1px solid rgba(148, 163, 184, 0.22);
    }
    .button-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }
    .range-row {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      align-items: center;
      margin-bottom: 14px;
    }
    .range-value {
      width: 56px;
      text-align: center;
      color: var(--accent-2);
      font-weight: 700;
    }
    .pill-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .pill {
      border-radius: 999px;
      border: 1px solid rgba(148, 163, 184, 0.18);
      padding: 6px 10px;
      color: var(--muted);
      font-size: 0.82rem;
    }
    .status {
      color: var(--muted);
      font-size: 0.92rem;
      min-height: 1.4em;
    }
    .score-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }
    .score-box {
      background: var(--panel-2);
      border: 1px solid rgba(148, 163, 184, 0.14);
      border-radius: 16px;
      padding: 14px;
    }
    .score-box .label {
      color: var(--muted);
      font-size: 0.82rem;
      margin-bottom: 8px;
    }
    .score-box .value {
      font-size: 1.5rem;
      font-weight: 800;
    }
    .feedback-list, .trace-list {
      display: grid;
      gap: 10px;
      max-height: 240px;
      overflow: auto;
    }
    .feedback-item, .trace-item {
      border-radius: 14px;
      background: rgba(15, 23, 42, 0.68);
      border: 1px solid rgba(148, 163, 184, 0.14);
      padding: 12px;
      color: var(--muted);
      line-height: 1.45;
    }
    .trace-item strong, .feedback-item strong { color: var(--text); }
    .markdown {
      white-space: pre-wrap;
      line-height: 1.55;
      color: #dbeafe;
      font-size: 0.95rem;
      max-height: 62vh;
      overflow: auto;
      padding-right: 4px;
    }
    .small {
      font-size: 0.84rem;
      color: var(--muted);
    }
    .top-links {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 14px;
    }
    .top-links a {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      text-decoration: none;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(15, 23, 42, 0.55);
      border: 1px solid rgba(148, 163, 184, 0.16);
    }
    @media (max-width: 980px) {
      .hero, .layout, .score-grid { grid-template-columns: 1fr; }
      .markdown { max-height: none; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <div class="card hero-main">
        <div class="eyebrow">OpenEnv x OpenReview</div>
        <h1>Peer Review Score Prediction</h1>
        <p>
          This Space serves a static OpenReview benchmark. Pick a paper, inspect the full markdown extracted from the PDF,
          and predict the mean human reviewer <code>rating</code> and <code>confidence</code>. Rewards come purely from score accuracy.
        </p>
        <div class="top-links">
          <a href="/docs" target="_blank" rel="noreferrer">API Docs</a>
          <a href="/openapi.json" target="_blank" rel="noreferrer">OpenAPI</a>
          <a href="/health" target="_blank" rel="noreferrer">Health</a>
        </div>
      </div>
      <div class="card hero-side">
        <div class="metric"><span>Runtime</span><strong>Static snapshot only</strong></div>
        <div class="metric"><span>Paper source</span><strong>OpenReview PDFs → markdown</strong></div>
        <div class="metric"><span>Targets</span><strong>Mean rating + confidence</strong></div>
        <div class="metric"><span>Tasks</span><strong>3 benchmark papers</strong></div>
      </div>
    </section>

    <section class="layout">
      <div class="sidebar">
        <div class="card section">
          <h2>Episode Control</h2>
          <label for="taskId">Task</label>
          <select id="taskId"></select>
          <div style="height: 12px"></div>
          <div class="button-row">
            <button id="resetBtn">Reset Task</button>
            <button id="stateBtn" class="secondary">Refresh State</button>
          </div>
          <div style="height: 14px"></div>
          <div class="pill-row" id="metaPills"></div>
          <div style="height: 12px"></div>
          <div class="status" id="statusText">Ready.</div>
        </div>

        <div class="card section">
          <h2>Predict Scores</h2>
          <label>Rating</label>
          <div class="range-row">
            <input id="ratingInput" type="range" min="1" max="10" step="0.1" value="5" />
            <div class="range-value" id="ratingValue">5.0</div>
          </div>
          <label>Confidence</label>
          <div class="range-row">
            <input id="confidenceInput" type="range" min="1" max="5" step="0.1" value="3" />
            <div class="range-value" id="confidenceValue">3.0</div>
          </div>
          <div class="button-row">
            <button id="stepBtn">Submit Prediction</button>
            <button id="finalizeBtn" class="secondary">Finalize</button>
          </div>
          <div style="height: 10px"></div>
          <div class="small">The app sends <code>{"action": {"rating", "confidence", "finalize"}}</code> to <code>/step</code>.</div>
        </div>

        <div class="card section">
          <h2>Feedback</h2>
          <div class="feedback-list" id="feedbackList"></div>
        </div>

        <div class="card section">
          <h2>Trace</h2>
          <div class="trace-list" id="traceList"></div>
        </div>
      </div>

      <div class="content">
        <div class="card section">
          <h2>Current Scores</h2>
          <div class="score-grid">
            <div class="score-box">
              <div class="label">Current Score</div>
              <div class="value" id="currentScore">0.00</div>
            </div>
            <div class="score-box">
              <div class="label">Best Score</div>
              <div class="value" id="bestScore">0.00</div>
            </div>
            <div class="score-box">
              <div class="label">Reward</div>
              <div class="value" id="attemptsRemaining">0</div>
            </div>
          </div>
          <div style="height: 12px"></div>
          <div class="pill-row" id="breakdownPills"></div>
        </div>

        <div class="card section">
          <h2 id="paperTitle">Paper</h2>
          <div class="small" id="paperObjective"></div>
          <div style="height: 14px"></div>
          <div class="markdown" id="paperMarkdown">Reset a task to load paper markdown.</div>
        </div>
      </div>
    </section>
  </div>

  <script>
    const TASK_OPTIONS = __TASK_OPTIONS__;

    const state = {
      observation: null,
      trace: [],
      lastReward: 0
    };

    const els = {
      taskId: document.getElementById('taskId'),
      resetBtn: document.getElementById('resetBtn'),
      stateBtn: document.getElementById('stateBtn'),
      stepBtn: document.getElementById('stepBtn'),
      finalizeBtn: document.getElementById('finalizeBtn'),
      ratingInput: document.getElementById('ratingInput'),
      confidenceInput: document.getElementById('confidenceInput'),
      ratingValue: document.getElementById('ratingValue'),
      confidenceValue: document.getElementById('confidenceValue'),
      statusText: document.getElementById('statusText'),
      currentScore: document.getElementById('currentScore'),
      bestScore: document.getElementById('bestScore'),
      attemptsRemaining: document.getElementById('attemptsRemaining'),
      feedbackList: document.getElementById('feedbackList'),
      traceList: document.getElementById('traceList'),
      paperTitle: document.getElementById('paperTitle'),
      paperObjective: document.getElementById('paperObjective'),
      paperMarkdown: document.getElementById('paperMarkdown'),
      metaPills: document.getElementById('metaPills'),
      breakdownPills: document.getElementById('breakdownPills')
    };

    function setStatus(text) {
      els.statusText.textContent = text;
    }

    function fmt(value) {
      return Number(value || 0).toFixed(2);
    }

    function updateSliderLabels() {
      els.ratingValue.textContent = Number(els.ratingInput.value).toFixed(1);
      els.confidenceValue.textContent = Number(els.confidenceInput.value).toFixed(1);
    }

    function initTaskOptions() {
      els.taskId.innerHTML = TASK_OPTIONS.map(task =>
        `<option value="${escapeHtml(task.id)}">${escapeHtml(task.label)}</option>`
      ).join('');
    }

    function renderObservation(obs) {
      if (!obs) return;
      state.observation = obs;
      els.paperTitle.textContent = obs.task_name || 'Paper';
      els.paperObjective.textContent = obs.objective || '';
      els.paperMarkdown.textContent = obs.paper_markdown || '';
      els.currentScore.textContent = fmt(obs.current_score);
      els.bestScore.textContent = fmt(obs.best_score);
      els.attemptsRemaining.textContent = fmt(state.lastReward);

      els.feedbackList.innerHTML = (obs.feedback || []).map(item =>
        `<div class="feedback-item"><strong>Feedback</strong><br>${escapeHtml(item)}</div>`
      ).join('') || '<div class="feedback-item">No feedback yet.</div>';

      const meta = obs.metadata || {};
      const metaPills = [
        `Difficulty: ${obs.difficulty}`,
        `Forum: ${meta.forum_id || 'n/a'}`,
        `Reviews: ${meta.review_count || 'n/a'}`,
        `Decision: ${meta.decision || 'n/a'}`
      ];
      els.metaPills.innerHTML = metaPills.map(item => `<div class="pill">${escapeHtml(item)}</div>`).join('');

      const breakdown = obs.score_breakdown || {};
      const entries = Object.entries(breakdown);
      els.breakdownPills.innerHTML = entries.length
        ? entries.map(([key, value]) => `<div class="pill">${escapeHtml(key)}: ${fmt(value)}</div>`).join('')
        : '<div class="pill">No score breakdown yet</div>';

      const rewardHint = `Attempts remaining: ${obs.attempts_remaining ?? 0}`;
      setStatus(`${rewardHint} · Current reward: ${fmt(state.lastReward)}`);
    }

    function renderTrace() {
      els.traceList.innerHTML = state.trace.map((item, idx) => `
        <div class="trace-item">
          <strong>Step ${idx + 1}</strong><br>
          rating=${fmt(item.action.rating)}, confidence=${fmt(item.action.confidence)}, finalize=${item.action.finalize}<br>
          reward=${fmt(item.reward)}, done=${String(item.done)}<br>
          rating_error=${fmt(item.breakdown.rating_error)}, confidence_error=${fmt(item.breakdown.confidence_error)}
        </div>
      `).join('') || '<div class="trace-item">No steps taken yet.</div>';
    }

    function escapeHtml(text) {
      return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }

    async function api(path, options = {}) {
      const response = await fetch(path, {
        headers: { 'Content-Type': 'application/json' },
        ...options
      });
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `HTTP ${response.status}`);
      }
      return response.json();
    }

    async function resetTask() {
      setStatus('Resetting task...');
      state.trace = [];
      renderTrace();
      const payload = { task_id: els.taskId.value };
      const result = await api('/reset', { method: 'POST', body: JSON.stringify(payload) });
      state.lastReward = result.reward ?? 0;
      renderObservation(result.observation);
      setStatus('Task ready. Read the paper markdown and submit a score prediction.');
    }

    async function refreshState() {
      setStatus('Refreshing state...');
      const result = await api('/state');
      setStatus(`Episode ${result.episode_id || 'n/a'} · step ${result.step_count}`);
    }

    async function submit(finalize) {
      if (!state.observation) {
        setStatus('Reset a task first.');
        return;
      }
      const action = {
        rating: Number(els.ratingInput.value),
        confidence: Number(els.confidenceInput.value),
        finalize
      };
      setStatus('Submitting prediction...');
      const result = await api('/step', {
        method: 'POST',
        body: JSON.stringify({ action })
      });
      state.lastReward = result.reward ?? 0;
      state.trace.unshift({
        action,
        reward: result.reward ?? 0,
        done: result.done,
        breakdown: result.observation.score_breakdown || {}
      });
      renderTrace();
      renderObservation(result.observation);
      setStatus(result.done ? 'Episode finished.' : 'Prediction submitted. You can revise and step again.');
    }

    els.ratingInput.addEventListener('input', updateSliderLabels);
    els.confidenceInput.addEventListener('input', updateSliderLabels);
    els.resetBtn.addEventListener('click', () => resetTask().catch(err => setStatus(err.message)));
    els.stateBtn.addEventListener('click', () => refreshState().catch(err => setStatus(err.message)));
    els.stepBtn.addEventListener('click', () => submit(false).catch(err => setStatus(err.message)));
    els.finalizeBtn.addEventListener('click', () => submit(true).catch(err => setStatus(err.message)));

    initTaskOptions();
    updateSliderLabels();
    resetTask().catch(err => setStatus(err.message));
  </script>
</body>
</html>
"""


@app.get("/", include_in_schema=False)
def root() -> HTMLResponse:
    task_options = [
        {
            "id": task_id,
            "label": f"{TASKS[task_id].difficulty.title()} · {TASKS[task_id].task_name}",
        }
        for task_id in TASK_ORDER
    ]
    return HTMLResponse(
        _FRONTEND_HTML.replace("__TASK_OPTIONS__", str(task_options).replace("'", '"'))
    )


def main(host: str = "0.0.0.0", port: int = 8000):
    """Run the FastAPI server locally."""
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    main(port=args.port)
