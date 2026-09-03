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
    invalid_project: "Bitte prüfen Sie die Projektdaten.",
    project_not_found: "Das Projekt wurde nicht gefunden.",
    message_required: "Bitte beschreiben Sie Ihren Änderungswunsch.",
    message_too_long: "Der Änderungswunsch ist zu lang.",
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
    return `<div class="brand"><div class="brandmark">A+</div><div><b>A+ Studio</b><small>Cloud App Builder</small></div></div>`;
  }

  function shell(content, active = state.route) {
    const tabs = [["projects", "⌂", "Projekte"], ["new", "+", "Neue App"], ["account", "◎", "Konto"]];
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
        <div class="eyebrow">CLOUD APP BUILDER</div>
        <h1>Idee beschreiben. App in der Cloud erstellen.</h1>
        <p class="muted">A+ Studio erstellt neue App-Projekte auf der A+ Cloud-Infrastruktur. Die iOS-App selbst lädt, installiert oder führt keinen generierten App-Code aus.</p>
        ${message ? `<div class="notice error">${escapeHtml(message)}</div>` : ""}
        <form id="auth-form" class="form">
          <label>E-Mail<input name="email" type="email" autocomplete="email" required></label>
          <label>Passwort<input name="password" type="password" autocomplete="current-password" required></label>
          <button class="btn primary" type="submit">Anmelden</button>
        </form>
        <button class="btn secondary full" id="demo-mode">Demo ansehen</button>
        <p class="muted" style="margin-top:16px">Konten werden außerhalb der iOS-App eingerichtet. Bestehende Nutzer können neue App-Projekte direkt mobil starten.</p>
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
        ${brand()}<div class="eyebrow">REVIEW DEMO</div><h1>App-Erstellung über die Cloud.</h1>
        <p class="muted">Diese lokale Demo zeigt den iOS-Workflow ohne Konto.</p>
        <div class="card"><span class="status generating">Generierung läuft</span><h3>Luna Booking</h3><p>Idee: Termin-App für einen lokalen Salon.</p></div>
        <div class="card"><h2>1. Projekt anlegen</h2><p>Name, Branche, Zielgruppe und gewünschte Funktionen werden an A+ Studio Cloud gesendet.</p></div>
        <div class="card"><h2>2. Serverseitige Erstellung</h2><p>Generierung, Build und Verarbeitung passieren ausschließlich auf der A+ Cloud-Infrastruktur.</p></div>
        <div class="card"><h2>3. Status & Änderungen</h2><p>Die iOS-App zeigt den Projektstatus und nimmt Änderungswünsche entgegen. Generierter App-Code wird in dieser iOS-App weder ausgeführt noch installiert oder als andere App gestartet.</p></div>
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
      queued: "In Warteschlange",
      generating: "Cloud-Generierung",
      generated: "Erstellt",
      deployed: "Bereitgestellt",
      paused: "Pausiert",
      attention: "Klärung erforderlich",
      proposed: "Zur Prüfung",
      approved: "Freigegeben",
      done: "Erledigt",
      rejected: "Abgelehnt",
      failed: "Klärung erforderlich",
    }[status] || "In Bearbeitung");
  }

  async function renderProjects() {
    loading("Ihre App-Projekte");
    const data = await api("/dashboard/");
    shell(`
      <section class="hero"><div class="eyebrow">CLOUD APP BUILDER</div><h1>${escapeHtml(data.organization.name)}</h1><p>Neue Apps starten, Cloud-Generierung verfolgen und Änderungswünsche verwalten.</p><div class="metrics"><div><b>${data.projects.length}</b><span>App-Projekte</span></div><div><b>${data.projects.filter((p) => ["queued", "generating"].includes(p.status)).length}</b><span>In Erstellung</span></div></div></section>
      <div class="section-head"><h2>Projekte</h2><button class="smallbtn" data-route="new">+ Neue App</button></div>
      <section class="stack">${data.projects.length ? data.projects.map((project) => `<button class="project-card" data-project="${project.id}"><div><span class="status ${escapeHtml(project.status)}">${escapeHtml(statusLabel(project.status))}</span><h3>${escapeHtml(project.name)}</h3><p>${escapeHtml(project.business_type)}</p></div><div class="arrow">›</div></button>`).join("") : `<div class="empty"><div class="empty-icon">✦</div><h3>Noch kein App-Projekt</h3><p>Beschreiben Sie Ihre Idee. A+ Studio startet daraus die serverseitige Erstellung.</p><button class="btn primary" data-route="new">Erste App starten</button></div>`}</section>
    `, "projects");
    root.querySelectorAll("[data-project]").forEach((el) => el.addEventListener("click", async () => { state.selectedProject = el.dataset.project; state.route = "project"; await render(); }));
  }

  async function renderNewProject() {
    await loadMe();
    shell(`
      <div class="eyebrow">NEUES APP-PROJEKT</div><h1>Was soll entstehen?</h1>
      <p class="lead">Beschreiben Sie das Produkt. A+ Studio sendet die Angaben an die Cloud und startet dort die App-Erstellung.</p>
      <form id="project-form" class="form card">
        <label>App-Name<input name="name" required maxlength="160" placeholder="z. B. Luna Booking"></label>
        <label>Branche / Geschäftstyp<input name="business_type" required maxlength="120" placeholder="z. B. Friseursalon"></label>
        <label>Ziel & Funktionen<textarea name="description" rows="7" required placeholder="Wer nutzt die App? Welches Problem soll sie lösen? Welche Kernfunktionen werden benötigt?"></textarea></label>
        <label>Sprache<select name="language"><option value="de">Deutsch</option><option value="en">English</option></select></label>
        <div class="notice">Die technische Generierung und Verarbeitung findet auf der A+ Studio Cloud-Infrastruktur statt. Die iOS-App führt den erzeugten App-Code nicht lokal aus.</div>
        <button class="btn primary" type="submit">App-Erstellung starten</button>
      </form>
    `, "new");
    document.getElementById("project-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = event.currentTarget.querySelector("button");
      button.disabled = true;
      button.textContent = "Cloud-Projekt wird gestartet…";
      try {
        const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
        const data = await api("/projects/", { method: "POST", body: JSON.stringify(payload) });
        state.selectedProject = data.project.id;
        state.route = "project";
        await render();
      } catch (error) {
        button.disabled = false;
        button.textContent = "App-Erstellung starten";
        alert(error.message);
      }
    });
  }

  function renderRequests(items) {
    if (!items?.length) return '<p class="muted">Noch keine Änderungswünsche erfasst.</p>';
    return `<div class="submission-list">${items.map((item) => `<div><b>${escapeHtml(item.title)}</b><span>${escapeHtml(statusLabel(item.status))}</span></div>`).join("")}</div>`;
  }

  async function renderProject() {
    if (!state.selectedProject) return navigate("projects");
    loading("App-Projekt");
    const project = (await api(`/projects/${state.selectedProject}/`)).project;
    shell(`
      <button class="textbtn back" data-route="projects">‹ Zurück zu Projekten</button><div class="eyebrow">APP-PROJEKT</div><h1>${escapeHtml(project.name)}</h1><p class="lead">${escapeHtml(project.business_type)} · Version ${escapeHtml(project.version)}</p>
      <div class="card"><div class="detail-row"><span>Cloud-Status</span><b>${escapeHtml(statusLabel(project.status))}</b></div><div class="detail-row"><span>Sprache</span><b>${escapeHtml((project.language || "de").toUpperCase())}</b></div></div>
      <div class="card"><h2>Produktbeschreibung</h2><p>${escapeHtml(project.description || "Keine Beschreibung hinterlegt.")}</p></div>
      <div class="card"><h2>Änderungswünsche</h2>${renderRequests(project.requests)}<form id="request-form" class="form" style="margin-top:18px"><label>Was soll an der App geändert werden?<textarea name="message" rows="5" required placeholder="Beschreiben Sie die gewünschte Anpassung."></textarea></label><button class="btn primary" type="submit">Änderungswunsch senden</button></form></div>
      <div class="notice">Aus Apple-Sicherheitsgründen wird die erzeugte Anwendung in der iOS-App nicht als ausführbare Fremd-App gestartet, installiert oder heruntergeladen.</div>
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
      } catch (error) { button.disabled = false; button.textContent = "Änderungswunsch senden"; alert(error.message); }
    });
  }

  async function renderAccount() {
    const me = await loadMe();
    shell(`
      <div class="eyebrow">KONTO</div><h1>${escapeHtml(me.name)}</h1>
      <div class="card"><div class="detail-row"><span>E-Mail</span><b>${escapeHtml(me.email)}</b></div><div class="detail-row"><span>Workspace</span><b>${escapeHtml(me.organization.name)}</b></div></div>
      <div class="card"><h2>Mobile Nutzung</h2><p>Die iOS-App steuert App-Projekte in der A+ Studio Cloud. Generierung erfolgt serverseitig; lokales Ausführen, Installieren oder Verteilen generierter Apps ist nicht Bestandteil der iOS-App.</p></div>
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
      if (state.route === "new") return await renderNewProject();
      if (state.route === "project") return await renderProject();
      return await renderProjects();
    } catch (error) { showError(error); }
  }

  render();
})();
