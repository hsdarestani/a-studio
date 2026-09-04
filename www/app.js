(() => {
  "use strict";

  const API = "https://studio.aplus-solution.de/api/mobile";
  const WEB = "https://studio.aplus-solution.de";
  const root = document.getElementById("app");
  const state = {
    token: localStorage.getItem("astudio_token") || "",
    route: "projects",
    selectedProject: null,
    me: null,
  };

  const escapeHtml = (value = "") => String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

  const errorText = (code) => ({
    authentication_required: "Bitte melden Sie sich erneut an.",
    invalid_credentials: "E-Mail oder Passwort ist nicht korrekt.",
    project_not_found: "Das Projekt wurde nicht gefunden.",
    message_required: "Bitte beschreiben Sie Ihre Anfrage.",
    message_too_long: "Die Anfrage ist zu lang.",
    confirmation_required: "Bitte bestätigen Sie die Kontolöschung.",
  }[code] || "Etwas ist schiefgelaufen. Bitte versuchen Sie es erneut.");

  async function api(path, options = {}) {
    const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
    if (state.token) headers.Authorization = `Bearer ${state.token}`;
    const response = await fetch(`${API}${path}`, { ...options, headers });
    let body = {};
    try { body = await response.json(); } catch (_) {}
    if (response.status === 401) {
      setToken("");
      showAuth();
      throw new Error(errorText("authentication_required"));
    }
    if (!response.ok || body.ok === false) throw new Error(errorText(body.error));
    return body;
  }

  function setToken(token) {
    state.token = token || "";
    if (state.token) localStorage.setItem("astudio_token", state.token);
    else localStorage.removeItem("astudio_token");
  }

  function brand() {
    return `<div class="brand"><div class="brandmark">A+</div><div><b>A+ Studio</b><small>Kundenprojekte</small></div></div>`;
  }

  function shell(content, active = state.route) {
    const tabs = [["projects", "⌂", "Projekte"], ["account", "◎", "Konto"]];
    root.innerHTML = `
      <div class="shell">
        <header class="topbar">${brand()}<button class="iconbtn" data-refresh aria-label="Aktualisieren">↻</button></header>
        <main class="content">${content}</main>
        <nav class="tabbar">
          ${tabs.map(([route, icon, label]) => `<button data-route="${route}" class="${active === route ? "active" : ""}"><span>${icon}</span><small>${label}</small></button>`).join("")}
        </nav>
      </div>`;
    root.querySelectorAll("[data-route]").forEach((el) => el.addEventListener("click", () => navigate(el.dataset.route)));
    root.querySelector("[data-refresh]")?.addEventListener("click", () => render());
  }

  function loading(title = "A+ Studio") {
    shell(`<div class="eyebrow">A+ SOLUTION</div><h1>${escapeHtml(title)}</h1><div class="loading">Wird geladen…</div>`);
  }

  function showError(error, retry = true) {
    shell(`<div class="eyebrow">VERBINDUNG</div><h1>Das hat nicht geklappt.</h1><div class="notice error">${escapeHtml(error.message)}</div>${retry ? '<button class="btn primary" data-retry>Erneut versuchen</button>' : ""}`);
    root.querySelector("[data-retry]")?.addEventListener("click", () => render());
  }

  function showAuth(message = "") {
    root.innerHTML = `
      <main class="auth"><section class="auth-card">
        ${brand()}<div class="hero-orb"></div>
        <div class="eyebrow">KUNDENZUGANG</div>
        <h1>Status. Abstimmung. Fortschritt.</h1>
        <p class="muted">A+ Studio ist der mobile Zugang für bestehende A+ Solution Kundenprojekte. Sehen Sie Projektfortschritte und stimmen Sie offene Punkte mit dem Projektteam ab.</p>
        ${message ? `<div class="notice error">${escapeHtml(message)}</div>` : ""}
        <form id="auth-form" class="form">
          <label>E-Mail<input name="email" type="email" autocomplete="email" required></label>
          <label>Passwort<input name="password" type="password" autocomplete="current-password" required></label>
          <button class="btn primary" type="submit">Anmelden</button>
        </form>
        <button class="btn secondary full" id="demo-mode">Demo ansehen</button>
        <p class="muted" style="margin-top:16px">Der mobile Zugang wird für bestehende Kundenkonten bereitgestellt.</p>
        <div class="legal"><a href="${WEB}/mobile/privacy/" target="_blank" rel="noopener">Datenschutz</a><a href="${WEB}/mobile/terms/" target="_blank" rel="noopener">Bedingungen</a><a href="${WEB}/mobile/support/" target="_blank" rel="noopener">Support</a></div>
      </section></main>`;

    document.getElementById("demo-mode").addEventListener("click", showDemo);
    document.getElementById("auth-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
      const button = event.currentTarget.querySelector("button[type=submit]");
      button.disabled = true;
      button.textContent = "Bitte warten…";
      try {
        const data = await api("/login/", { method: "POST", body: JSON.stringify(payload) });
        setToken(data.token);
        state.me = data.user;
        state.route = "projects";
        await render();
      } catch (error) { showAuth(error.message); }
    });
  }

  function showDemo() {
    root.innerHTML = `
      <main class="auth"><section class="auth-card demo-card">
        ${brand()}<div class="eyebrow">REVIEW DEMO</div><h1>Mobile Projektkoordination.</h1>
        <p class="muted">Diese vollständig lokale Demo zeigt den Funktionsumfang ohne Anmeldung.</p>
        <div class="card"><span class="status active">In Bearbeitung</span><h3>Standorteröffnung Westend</h3><p>Kundenprojekt · zuletzt heute aktualisiert</p></div>
        <div class="card"><h2>Aktuelle Abstimmung</h2><div class="chat"><div class="bubble user"><small>Kunde</small><div>Bitte den Termin für die nächste Abstimmung auf Donnerstag verschieben.</div></div><div class="bubble assistant"><small>Projektteam</small><div>Anfrage erfasst · Status: zur Prüfung.</div></div></div></div>
        <div class="card"><h2>Projektübersicht</h2><p>Fortschritt, Beschreibung und offene Abstimmungspunkte sind an einem Ort verfügbar.</p></div>
        <button class="btn primary full" id="demo-back">Zur Anmeldung</button>
      </section></main>`;
    document.getElementById("demo-back").addEventListener("click", () => showAuth());
  }

  async function navigate(route) {
    state.route = route;
    if (route !== "project") state.selectedProject = null;
    await render();
  }

  async function loadMe() {
    if (!state.me) state.me = (await api("/me/")).user;
    return state.me;
  }

  function statusLabel(status) {
    return ({
      planning: "Planung", active: "In Bearbeitung", review: "Abstimmung", completed: "Abgeschlossen",
      paused: "Pausiert", attention: "Klärung erforderlich", proposed: "Zur Prüfung", approved: "Freigegeben",
      done: "Erledigt", rejected: "Abgelehnt", failed: "Klärung erforderlich",
    }[status] || "In Bearbeitung");
  }

  async function renderProjects() {
    loading("Ihre Projekte");
    const data = await api("/dashboard/");
    shell(`
      <section class="hero"><div class="eyebrow">KUNDENBEREICH</div><h1>${escapeHtml(data.organization.name)}</h1><p>Projektfortschritt und Abstimmung mit dem A+ Solution Projektteam – kompakt mobil.</p><div class="metrics"><div><b>${data.projects.length}</b><span>Projekte</span></div><div><b>${data.projects.filter((p) => p.status !== "completed").length}</b><span>Aktiv</span></div></div></section>
      <div class="section-head"><h2>Projekte</h2></div>
      <section class="stack">${data.projects.length ? data.projects.map((project) => `<button class="project-card" data-project="${project.id}"><div><span class="status ${escapeHtml(project.status)}">${escapeHtml(statusLabel(project.status))}</span><h3>${escapeHtml(project.name)}</h3><p>${escapeHtml(project.business_type)}</p></div><div class="arrow">›</div></button>`).join("") : `<div class="empty"><div class="empty-icon">✦</div><h3>Keine Projekte zugeordnet</h3><p>Projekte erscheinen hier, sobald sie Ihrem Kundenkonto durch das A+ Solution Projektteam zugeordnet wurden.</p></div>`}</section>
    `, "projects");
    root.querySelectorAll("[data-project]").forEach((el) => el.addEventListener("click", async () => { state.selectedProject = el.dataset.project; state.route = "project"; await render(); }));
  }

  function renderRequests(items) {
    if (!items?.length) return '<p class="muted">Noch keine Abstimmungspunkte erfasst.</p>';
    return `<div class="submission-list">${items.map((item) => `<div><b>${escapeHtml(item.title)}</b><span>${escapeHtml(statusLabel(item.status))}</span></div>`).join("")}</div>`;
  }

  async function renderProject() {
    if (!state.selectedProject) return navigate("projects");
    loading("Projekt");
    const project = (await api(`/projects/${state.selectedProject}/`)).project;
    shell(`
      <button class="textbtn back" data-route="projects">‹ Zurück zu Projekten</button><div class="eyebrow">PROJEKT</div><h1>${escapeHtml(project.name)}</h1><p class="lead">${escapeHtml(project.business_type)}</p>
      <div class="card"><div class="detail-row"><span>Status</span><b>${escapeHtml(statusLabel(project.status))}</b></div><div class="detail-row"><span>Sprache</span><b>${escapeHtml((project.language || "de").toUpperCase())}</b></div></div>
      <div class="card"><h2>Projektbeschreibung</h2><p>${escapeHtml(project.description || "Keine Beschreibung hinterlegt.")}</p></div>
      <div class="card"><h2>Abstimmung</h2>${renderRequests(project.requests)}<form id="request-form" class="form" style="margin-top:18px"><label>Frage, Feedback oder Abstimmungspunkt<textarea name="message" rows="5" required placeholder="Was möchten Sie mit dem Projektteam abstimmen?"></textarea></label><button class="btn primary" type="submit">Anfrage senden</button></form></div>
    `, "projects");

    document.getElementById("request-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = event.currentTarget.querySelector("button");
      const message = new FormData(event.currentTarget).get("message");
      button.disabled = true;
      button.textContent = "Wird gesendet…";
      try {
        await api(`/projects/${state.selectedProject}/chat/`, { method: "POST", body: JSON.stringify({ message }) });
        await renderProject();
      } catch (error) { button.disabled = false; button.textContent = "Anfrage senden"; alert(error.message); }
    });
  }

  async function renderAccount() {
    const me = await loadMe();
    shell(`
      <div class="eyebrow">KONTO</div><h1>${escapeHtml(me.name)}</h1>
      <div class="card"><div class="detail-row"><span>E-Mail</span><b>${escapeHtml(me.email)}</b></div><div class="detail-row"><span>Kundenbereich</span><b>${escapeHtml(me.organization.name)}</b></div></div>
      <div class="card"><h2>Mobile Nutzung</h2><p>Dieser mobile Zugang dient der Koordination bereits bestehender Kundenprojekte und enthält keine Käufe oder Abonnements.</p></div>
      <div class="card link-list"><a href="${WEB}/mobile/privacy/" target="_blank" rel="noopener">Datenschutz <span>›</span></a><a href="${WEB}/mobile/terms/" target="_blank" rel="noopener">Bedingungen <span>›</span></a><a href="${WEB}/mobile/support/" target="_blank" rel="noopener">Support <span>›</span></a></div>
      <button class="btn secondary full" id="logout">Abmelden</button><button class="textbtn danger full" id="delete-account">Konto dauerhaft löschen</button>
    `, "account");
    document.getElementById("logout").addEventListener("click", () => { setToken(""); state.me = null; showAuth(); });
    document.getElementById("delete-account").addEventListener("click", async () => {
      if (!window.confirm("Möchten Sie Ihr A+ Studio Konto dauerhaft löschen?")) return;
      try { await api("/account/delete/", { method: "POST", body: JSON.stringify({ confirmation: "DELETE" }) }); setToken(""); state.me = null; showAuth(); alert("Ihr Konto wurde gelöscht."); } catch (error) { alert(error.message); }
    });
  }

  async function render() {
    if (!state.token) return showAuth();
    try {
      if (state.route === "account") return await renderAccount();
      if (state.route === "project") return await renderProject();
      return await renderProjects();
    } catch (error) { showError(error); }
  }

  render();
})();
