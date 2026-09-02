document.addEventListener("DOMContentLoaded", () => {
  let currentView = "landing"; // "landing" or "dashboard"
  let selectedTraceId = null;
  let autoRefreshInterval = null;
  let allTraces = [];
  let currentSearchQuery = "";
  let currentStatusFilter = "all";

  // DOM Elements - Navigation & Auth
  const navLogo = document.getElementById("nav-logo");
  const landingNavLinks = document.getElementById("landing-nav-links");
  const viewToggleBtn = document.getElementById("view-toggle-btn");
  const authModalBtn = document.getElementById("auth-modal-btn");
  const authBtnText = document.getElementById("auth-btn-text");
  const orgSwitcherContainer = document.getElementById("org-switcher-container");
  const orgSwitcher = document.getElementById("org-switcher");
  const authModal = document.getElementById("auth-modal");
  const closeAuthModal = document.getElementById("close-auth-modal");
  const googleLoginAction = document.getElementById("google-login-action");
  const apiKeyLoginAction = document.getElementById("api-key-login-action");

  // Wizard Elements
  const quickstartWizardBtn = document.getElementById("quickstart-wizard-btn");
  const wizardModal = document.getElementById("wizard-modal");
  const closeWizardModal = document.getElementById("close-wizard-modal");
  const fwButtons = document.querySelectorAll(".fw-btn");
  const wizardCodeSnippet = document.getElementById("wizard-code-snippet");
  const copySnippetBtn = document.getElementById("copy-snippet-btn");
  const fwFilename = document.getElementById("fw-filename");

  // Views
  const landingView = document.getElementById("landing-view");
  const dashboardView = document.getElementById("dashboard-view");

  // Search & Filter
  const traceSearchInput = document.getElementById("trace-search-input");
  const filterPills = document.querySelectorAll(".filter-pill");

  // Dashboard Elements
  const traceTableBody = document.getElementById("trace-table-body");
  const traceCountBadge = document.getElementById("trace-count-badge");
  const inspectorContent = document.getElementById("inspector-content");
  const inspectorActions = document.getElementById("inspector-actions");
  const runEvalBtn = document.getElementById("run-eval-btn");
  const evalModal = document.getElementById("eval-modal");
  const evalModalBody = document.getElementById("eval-modal-body");
  const closeModalBtn = document.getElementById("close-modal-btn");

  // Framework Code Snippets
  const snippets = {
    "fw-openai": `# Custom Python / OpenAI Integration
import os
from traceforge import trace

os.environ["TRACEFORGE_COLLECTOR_URL"] = "http://localhost:8000/api/v1/traces"

@trace("openai_agent_run", attributes={"user_id": "usr_9912"})
def main(prompt: str):
    with trace.span("llm_reasoning", span_type="llm", attributes={"model": "gpt-4o"}):
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
    return response`,

    "fw-anthropic": `# Anthropic Claude Integration
import os
from traceforge import trace

os.environ["TRACEFORGE_COLLECTOR_URL"] = "http://localhost:8000/api/v1/traces"

@trace("anthropic_agent_run", attributes={"provider": "anthropic"})
def main(prompt: str):
    with trace.span("claude_invocation", span_type="llm", attributes={"model": "claude-3-5-sonnet"}):
        msg = anthropic_client.messages.create(model="claude-3-5-sonnet", max_tokens=1000, messages=[{"role": "user", "content": prompt}])
    return msg`,

    "fw-langchain": `# LangChain Chain Instrumentation
import os
from traceforge import trace

os.environ["TRACEFORGE_COLLECTOR_URL"] = "http://localhost:8000/api/v1/traces"

with trace("langchain_retrieval_qa") as run:
    with run.span("vectorstore_retrieval", span_type="retrieval", attributes={"top_k": 5}):
        docs = vectorstore.similarity_search(query, k=5)
    
    with run.span("llm_chain", span_type="llm"):
        res = qa_chain.run(input_documents=docs, question=query)`,

    "fw-llamaindex": `# LlamaIndex Query Engine Instrumentation
import os
from traceforge import trace

os.environ["TRACEFORGE_COLLECTOR_URL"] = "http://localhost:8000/api/v1/traces"

with trace("llamaindex_query_engine") as run:
    with run.span("index_retrieval", span_type="retrieval"):
        nodes = retriever.retrieve(query_str)
    
    with run.span("synthesize_response", span_type="llm"):
        response = response_synthesizer.synthesize(query_str, nodes)`
  };

  // Check Auth Session
  checkUserSession();

  // Navigation Event Listeners
  navLogo.addEventListener("click", () => switchView("landing"));

  viewToggleBtn.addEventListener("click", () => {
    if (currentView === "landing") {
      switchView("dashboard");
    } else {
      switchView("landing");
    }
  });

  authModalBtn.addEventListener("click", () => openAuthModal());
  closeAuthModal.addEventListener("click", () => closeAuthModalWindow());

  // Wizard Listeners
  quickstartWizardBtn.addEventListener("click", () => {
    wizardModal.style.display = "flex";
  });
  closeWizardModal.addEventListener("click", () => {
    wizardModal.style.display = "none";
  });

  fwButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      fwButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const fwKey = btn.getAttribute("data-fw");
      wizardCodeSnippet.innerHTML = `<code>${escapeHtml(snippets[fwKey] || "")}</code>`;
      fwFilename.textContent = `${fwKey.replace("fw-", "")}_agent.py`;
    });
  });

  copySnippetBtn.addEventListener("click", () => {
    const text = wizardCodeSnippet.textContent;
    navigator.clipboard.writeText(text);
    copySnippetBtn.textContent = "✅ Copied!";
    setTimeout(() => { copySnippetBtn.textContent = "📋 Copy Code"; }, 2000);
  });

  document.querySelectorAll(".hero-auth-trigger").forEach((btn) => {
    btn.addEventListener("click", () => openAuthModal());
  });

  googleLoginAction.addEventListener("click", () => performLogin("Google User (Acme Corp)"));
  apiKeyLoginAction.addEventListener("click", () => performLogin("Dev User (API Key)"));

  // Search & Filter Listeners
  if (traceSearchInput) {
    traceSearchInput.addEventListener("input", (e) => {
      currentSearchQuery = e.target.value.toLowerCase().trim();
      renderFilteredTraces();
    });
  }

  filterPills.forEach((pill) => {
    pill.addEventListener("click", () => {
      filterPills.forEach((p) => p.classList.remove("active"));
      pill.classList.add("active");
      currentStatusFilter = pill.getAttribute("data-filter");
      renderFilteredTraces();
    });
  });

  // Functions
  function switchView(viewName) {
    currentView = viewName;
    if (viewName === "dashboard") {
      landingView.style.display = "none";
      dashboardView.style.display = "block";
      landingNavLinks.style.display = "none";
      orgSwitcherContainer.style.display = "block";
      viewToggleBtn.innerHTML = `<span class="icon">🌐</span> Product Landing`;
      fetchDashboardData();
      startAutoRefresh();
    } else {
      landingView.style.display = "block";
      dashboardView.style.display = "none";
      landingNavLinks.style.display = "flex";
      orgSwitcherContainer.style.display = "none";
      viewToggleBtn.innerHTML = `<span class="icon">📊</span> Console Dashboard`;
      stopAutoRefresh();
    }
  }

  function openAuthModal() {
    authModal.style.display = "flex";
  }

  function closeAuthModalWindow() {
    authModal.style.display = "none";
  }

  function performLogin(userName) {
    sessionStorage.setItem("traceforge_user", userName);
    checkUserSession();
    closeAuthModalWindow();
    switchView("dashboard");
  }

  function checkUserSession() {
    const user = sessionStorage.getItem("traceforge_user");
    if (user) {
      authBtnText.textContent = user;
    } else {
      authBtnText.textContent = "Continue with Google";
    }
  }

  function startAutoRefresh() {
    stopAutoRefresh();
    autoRefreshInterval = setInterval(fetchDashboardData, 5000);
  }

  function stopAutoRefresh() {
    if (autoRefreshInterval) {
      clearInterval(autoRefreshInterval);
      autoRefreshInterval = null;
    }
  }

  // Dashboard API Calls
  async function fetchDashboardData() {
    await Promise.all([fetchAnalyticsSummary(), fetchTraces()]);
    if (selectedTraceId) {
      fetchTraceDetails(selectedTraceId);
    }
  }

  async function fetchAnalyticsSummary() {
    try {
      const res = await fetch("/api/v1/analytics/summary");
      if (!res.ok) return;
      const data = await res.json();

      document.getElementById("stat-total-traces").textContent = data.total_traces;
      document.getElementById("stat-total-spans").textContent = `${data.total_spans} total spans executed`;

      document.getElementById("stat-pass-rate").textContent = `${data.pass_rate_percent.toFixed(1)}%`;
      document.getElementById("stat-eval-counts").textContent = `${data.passed_evaluations} passed / ${data.failed_evaluations} failed`;

      document.getElementById("stat-total-tokens").textContent = data.total_tokens.toLocaleString();
      document.getElementById("stat-total-cost").textContent = `Est. Cost: $${data.total_cost_usd.toFixed(4)} USD`;

      document.getElementById("stat-p50").textContent = `${data.p50_duration_ms.toFixed(1)}ms`;
      document.getElementById("stat-percentiles").textContent = `p90: ${data.p90_duration_ms.toFixed(1)}ms | p99: ${data.p99_duration_ms.toFixed(1)}ms`;
    } catch (err) {
      console.warn("Analytics fetch error:", err);
    }
  }

  async function fetchTraces() {
    try {
      const res = await fetch("/api/v1/traces?limit=50&offset=0");
      if (!res.ok) return;
      const data = await res.json();
      allTraces = data.items || [];
      renderFilteredTraces();
    } catch (err) {
      console.warn("Traces fetch error:", err);
    }
  }

  function renderFilteredTraces() {
    let filtered = allTraces.filter((t) => {
      // Status filter
      if (currentStatusFilter !== "all" && t.status !== currentStatusFilter) {
        return false;
      }
      // Search query
      if (currentSearchQuery) {
        const matchName = (t.name || "").toLowerCase().includes(currentSearchQuery);
        const matchId = (t.trace_id || "").toLowerCase().includes(currentSearchQuery);
        return matchName || matchId;
      }
      return true;
    });

    traceCountBadge.textContent = `${filtered.length} traces`;

    if (filtered.length === 0) {
      traceTableBody.innerHTML = `<tr><td colspan="5" class="empty-state">No matching traces captured yet. Run an agent execution to see live telemetry!</td></tr>`;
      return;
    }

    let html = "";
    filtered.forEach((item) => {
      const activeClass = item.trace_id === selectedTraceId ? "active-row" : "";
      const statusClass = item.status === "OK" ? "status-ok" : "status-error";
      const dateStr = new Date(item.start_time).toLocaleTimeString();
      const spansCount = (item.spans || []).length;
      const durationStr = item.duration_ms ? `${item.duration_ms.toFixed(1)}ms` : "N/A";

      html += `
        <tr class="${activeClass}" data-trace-id="${item.trace_id}">
          <td><span class="status-badge ${statusClass}">${item.status}</span></td>
          <td><strong>${escapeHtml(item.name)}</strong></td>
          <td>${durationStr}</td>
          <td>${spansCount}</td>
          <td style="color: var(--text-muted); font-size: 11px;">${dateStr}</td>
        </tr>
      `;
    });

    traceTableBody.innerHTML = html;

    // Click listener
    document.querySelectorAll("#trace-table-body tr").forEach((row) => {
      row.addEventListener("click", () => {
        const tId = row.getAttribute("data-trace-id");
        if (tId) {
          selectedTraceId = tId;
          document.querySelectorAll("#trace-table-body tr").forEach((r) => r.classList.remove("active-row"));
          row.classList.add("active-row");
          fetchTraceDetails(tId);
        }
      });
    });

    if (!selectedTraceId && filtered.length > 0) {
      selectedTraceId = filtered[0].trace_id;
      fetchTraceDetails(selectedTraceId);
    }
  }

  async function fetchTraceDetails(traceId) {
    try {
      const [traceRes, evalRes] = await Promise.all([
        fetch(`/api/v1/traces/${traceId}`),
        fetch(`/api/v1/traces/${traceId}/evaluations`)
      ]);

      if (!traceRes.ok) return;
      const trace = await traceRes.json();
      let evalsReport = null;
      if (evalRes.ok) {
        evalsReport = await evalRes.json();
      }

      inspectorActions.style.display = "flex";
      renderInspector(trace, evalsReport);
    } catch (err) {
      console.warn("Trace details error:", err);
    }
  }

  function renderInspector(trace, evalsReport) {
    const totalDuration = trace.duration_ms || 1.0;
    const spans = trace.spans || [];

    let evalBadgeHtml = "";
    if (evalsReport && evalsReport.total_evaluations > 0) {
      const st = evalsReport.overall_status;
      const cls = st === "PASS" ? "status-pass" : (st === "WARN" ? "status-warn" : "status-fail");
      evalBadgeHtml = `<span class="status-badge ${cls}">EVAL: ${st}</span>`;
    } else {
      evalBadgeHtml = `<span class="status-badge" style="background: rgba(255,255,255,0.1);">UNEVALUATED</span>`;
    }

    let html = `
      <div class="trace-meta-header">
        <div class="meta-item">
          <span class="meta-label">TRACE NAME</span>
          <span class="meta-val">${escapeHtml(trace.name)}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">TRACE ID</span>
          <span class="meta-val" style="font-size: 11px;">${trace.trace_id}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">DURATION</span>
          <span class="meta-val">${totalDuration.toFixed(2)}ms</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">EVALUATION</span>
          <div>${evalBadgeHtml}</div>
        </div>
      </div>

      <div class="waterfall-container">
        <div class="waterfall-header-row">
          <span>SPAN EXECUTION TREE</span>
          <span>TIMELINE RELATIVE TO ROOT</span>
        </div>
    `;

    spans.forEach((span) => {
      const spanDuration = span.duration_ms || 0.0;
      const stype = (span.span_type || "agent").toLowerCase();
      const stypeClass = `st-${stype}`;

      const rootStart = new Date(trace.start_time).getTime();
      const spanStart = new Date(span.start_time).getTime();
      const offsetPct = Math.max(0, Math.min(100, ((spanStart - rootStart) / totalDuration) * 100));
      const widthPct = Math.max(2, Math.min(100 - offsetPct, (spanDuration / totalDuration) * 100));

      const attrJson = JSON.stringify(span.attributes || {}, null, 2);

      html += `
        <div class="span-row" onclick="this.querySelector('.attr-box').style.display = (this.querySelector('.attr-box').style.display === 'none' ? 'block' : 'none')">
          <div class="span-info">
            <div class="span-title">
              <span class="span-type-tag ${stypeClass}">${stype}</span>
              <strong>${escapeHtml(span.name)}</strong>
            </div>
            <span style="font-family: var(--font-mono); font-size: 11px; color: var(--text-muted);">${spanDuration.toFixed(1)}ms</span>
          </div>
          <div class="span-bar-track">
            <div class="span-bar-fill" style="left: ${offsetPct}%; width: ${widthPct}%;"></div>
          </div>
          <div class="attr-box" style="display: none; margin-top: 8px;">${escapeHtml(attrJson)}</div>
        </div>
      `;
    });

    html += `</div>`;
    inspectorContent.innerHTML = html;
  }

  async function triggerEvaluation(traceId) {
    try {
      runEvalBtn.textContent = "⏳ Evaluating...";
      const res = await fetch(`/api/v1/evaluations/run/${traceId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_latency_ms: 3000, max_tokens: 2000, max_cost: 0.05 }),
      });
      runEvalBtn.innerHTML = "✨ Run Behavioral Evals";

      if (!res.ok) return;
      const report = await res.json();
      showEvalModal(report);
      fetchDashboardData();
    } catch (err) {
      runEvalBtn.innerHTML = "✨ Run Behavioral Evals";
      console.warn("Eval trigger error:", err);
    }
  }

  function showEvalModal(report) {
    const overall = report.overall_status;
    const cls = overall === "PASS" ? "status-pass" : (overall === "WARN" ? "status-warn" : "status-fail");

    let html = `
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
        <span style="font-size: 13px; color: var(--text-muted);">Trace ID: ${report.trace_id}</span>
        <span class="status-badge ${cls}" style="font-size: 14px; padding: 4px 12px;">OVERALL: ${overall}</span>
      </div>

      <div style="display: flex; flex-direction: column; gap: 12px;">
    `;

    (report.evaluations || []).forEach((ev) => {
      const eCls = ev.status === "PASS" ? "status-pass" : (ev.status === "WARN" ? "status-warn" : "status-fail");
      const detailsStr = JSON.stringify(ev.details || {}, null, 2);

      html += `
        <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--panel-border); padding: 14px; border-radius: 8px;">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
            <strong style="text-transform: uppercase; font-size: 13px; color: var(--accent-cyan);">${ev.eval_type}</strong>
            <span class="status-badge ${eCls}">Score: ${ev.score.toFixed(2)} | ${ev.status}</span>
          </div>
          <pre style="font-family: var(--font-mono); font-size: 11px; color: var(--text-muted); margin: 0;">${escapeHtml(detailsStr)}</pre>
        </div>
      `;
    });

    html += `</div>`;
    evalModalBody.innerHTML = html;
    evalModal.style.display = "flex";
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
});
