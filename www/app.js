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
    valid_email_required: "Bitte geben Sie eine gültige E-Mail-Adresse ein.",
    email_exists: "Für diese E-Mail existiert bereits ein Konto.",
    profile_fields_required: "Name und Unternehmen werden benötigt.",
    weak_password: "Bitte wählen Sie ein stärkeres Passwort.",
    invalid_project: "Bitte prüfen Sie die Projektdaten.",
    project_not_found: "Das Projekt wurde nicht gefunden.",
    message_required: "Bitte beschreiben Sie Ihre Anfrage.",
    message_too_long: "Die Anfrage ist zu lang.",
    confirmation_required: "Bitte bestätigen Sie die Kontolöschung.",
    mobile_companion_only: "Diese Aktion ist in der mobilen Begleit-App nicht verfügbar.",
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
    if (!response.ok || body.ok === false) {
      const err = new Error(errorText(body.error));
      err.details = body.details || body.fields || null;
      throw err;
    }
    return body;
  }

  function setToken(token) {
    state.token = token || "";
    if (state.token) localStorage.setItem("astudio_token", state.token);
    else localStorage.removeItem("astudio_token");
  }

  function brand() {
    return `<div class="brand"><div class="brandmark">A+</div><div><b>A+ Studio</b><small>Projektbegleitung</small></div></div>`;
  }

  function shell(content, active = state.route) {
    const tabs = [
      ["projects", "⌂", "Projekte"],
      ["new", "+", "Neu"],
      ["account", "◎", "Konto"],
    ];
    root.innerHTML = `
      <div class="shell">
        <header class="topbar">${brand()}<button class="iconbtn" data-refresh aria-label="Aktualisieren">↻</button></header>
        <main class="content">${content}</main>
        <nav class="tabbar">
          ${tabs.map(([route, icon, label]) => `
            <button data-route="${route}" class="${active === route ? "active" : ""}">
              <span>${icon}</span><small>${label}</small>
            </button>`).join("")}
        </nav>
      </div>`;
    root.querySelectorAll("[data-route]").forEach((el) => el.addEventListener("click", () => navigate(el.dataset.route)));
    root.querySelector("[data-refresh]")?.addEventListener("click", () => render());
  }

  function loading(title = "A+ Studio") {
    shell(`<div class="eyebrow">A+ SOLUTION</div><h1>${escapeHtml(title)}</h1><div class="loading">Wird geladen…</div>`);
  }

  function showError(error, retry = true) {
    shell(`
      <div class="eyebrow">VERBINDUNG</div>
      <h1>Das hat nicht geklappt.</h1>
      <div class="notice error">${escapeHtml(error.message)}</div>
      ${retry ? '<button class="btn primary" data-retry>Erneut versuchen</button>' : ""}`);
    root.querySelector("[data-retry]")?.addEventListener("click", () => render());
  }

  function showAuth(mode = "login", message = "") {
    const signup = mode === "signup";
    root.innerHTML = `
      <main class="auth">
        <section class="auth-card">
          ${brand()}
          <div class="hero-orb"></div>
          <div class="eyebrow">${signup ? "BEGLEITKONTO ERSTELLEN" : "WILLKOMMEN ZURÜCK"}</div>
          <h1>${signup ? "Ihr Projekt immer im Blick." : "Status. Abstimmung. Fortschritt."}</h1>
          <p class="muted">A+ Studio ist die mobile Begleit-App für Softwareprojekte mit A+ Solution. Sie verwalten Projektbriefings, Änderungswünsche und den aktuellen Bearbeitungsstatus.</p>
          ${message ? `<div class="notice error">${escapeHtml(message)}</div>` : ""}
          <form id="auth-form" class="form">
            ${signup ? `
              <label>Vollständiger Name<input name="full_name" autocomplete="name" required></label>
              <label>Unternehmen<input name="company_name" autocomplete="organization" required></label>` : ""}
            <label>E-Mail<input name="email" type="email" autocomplete="email" required></label>
            <label>Passwort<input name="password" type="password" autocomplete="${signup ? "new-password" : "current-password"}" minlength="8" required></label>
            <button class="btn primary" type="submit">${signup ? "Konto erstellen" : "Anmelden"}</button>
          </form>
          ${signup ? "" : '<button class="btn secondary full" id="demo-mode">Demo ansehen</button>'}
          <button class="textbtn" id="auth-switch">${signup ? "Schon registriert? Anmelden" : "Noch kein Begleitkonto? Konto erstellen"}</button>
          <div class="legal">
            <a href="${WEB}/privacy/" target="_blank" rel="noopener">Datenschutz</a>
            <a href="${WEB}/terms/" target="_blank" rel="noopener">Bedingungen</a>
            <a href="${WEB}/support/" target="_blank" rel="noopener">Support</a>
          </div>
        </section>
      </main>`;

    document.getElementById("auth-switch").addEventListener("click", () => showAuth(signup ? "login" : "signup"));
    document.getElementById("demo-mode")?.addEventListener("click", showDemo);
    document.getElementById("auth-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const form = new FormData(event.currentTarget);
      const payload = Object.fromEntries(form.entries());
      const button = event.currentTarget.querySelector("button[type=submit]");
      button.disabled = true;
      button.textContent = "Bitte warten…";
      try {
        const data = await api(signup ? "/signup/" : "/login/", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        setToken(data.token);
        state.me = data.user;
        state.route = "projects";
        await render();
      } catch (error) {
        showAuth(mode, error.message);
      }
    });
  }

  function showDemo() {
    root.innerHTML = `
      <main class="auth">
        <section class="auth-card demo-card">
          ${brand()}
          <div class="eyebrow">REVIEW DEMO</div>
          <h1>Mobile Projektbegleitung.</h1>
          <p class="muted">Diese vollständig lokale Demo zeigt den Funktionsumfang der mobilen App ohne Konto.</p>
          <div class="card">
            <span class="status building">In Umsetzung</span>
            <h3>Luna Booking</h3>
            <p>Softwareprojekt für einen lokalen Salon · zuletzt heute aktualisiert</p>
          </div>
          <div class="card">
            <h2>Änderungswünsche</h2>
            <div class="chat">
              <div class="bubble user"><small>Kunde</small><div>Bitte die Terminübersicht auf dem Tablet übersichtlicher gestalten.</div></div>
              <div class="bubble assistant"><small>Projektteam</small><div>Anfrage erfasst · Status: zur Prüfung.</div></div>
            </div>
          </div>
          <div class="card">
            <h2>Veröffentlichungsstatus</h2>
            <p>Freigaben und Store-Status können eingesehen werden. Die mobile App erstellt, lädt oder führt keinen Programmcode aus.</p>
          </div>
          <button class="btn primary full" id="demo-back">Zur Anmeldung</button>
        </section>
      </main>`;
    document.getElementById("demo-back").addEventListener("click", () => showAuth("login"));
  }

  async function navigate(route) {
    state.route = route;
    if (route !== "project") state.selectedProject = null;
    await render();
  }

  async function loadMe() {
    if (!state.me) {
      const data = await api("/me/");
      state.me = data.user;
    }
    return state.me;
  }

  function statusLabel(status) {
    return ({
      draft: "Briefing",
      building: "In Umsetzung",
      preview: "Interne Abnahme",
      live: "Veröffentlicht",
      paused: "Pausiert",
      error: "Klärung erforderlich",
      proposed: "Zur Prüfung",
      approved: "Freigegeben",
      done: "Erledigt",
      rejected: "Abgelehnt",
      failed: "Klärung erforderlich",
      requested: "Angefragt",
      eligibility: "Prüfung",
      accounts: "Kontenprüfung",
      preparing: "Vorbereitung",
      submitted: "Eingereicht",
      review: "In Prüfung",
    }[status] || status || "–");
  }

  async function renderProjects() {
    loading("Ihre Projekte");
    const data = await api("/dashboard/");
    shell(`
      <section class="hero">
        <div class="eyebrow">WORKSPACE</div>
        <h1>${escapeHtml(data.organization.name)}</h1>
        <p>Projektstatus, Briefings und Änderungswünsche – kompakt in einer mobilen Begleit-App.</p>
        <div class="metrics">
          <div><b>${data.projects.length}</b><span>Projekte</span></div>
          <div><b>${data.projects.filter((project) => project.status !== "live").length}</b><span>Aktiv</span></div>
        </div>
      </section>
      <div class="section-head"><h2>Projekte</h2><button class="smallbtn" data-route="new">+ Neu</button></div>
      <section class="stack">
        ${data.projects.length ? data.projects.map((project) => `
          <button class="project-card" data-project="${project.id}">
            <div>
              <span class="status ${project.status}">${escapeHtml(statusLabel(project.status))}</span>
              <h3>${escapeHtml(project.name)}</h3>
              <p>${escapeHtml(project.business_type)}</p>
            </div>
            <div class="arrow">›</div>
          </button>`).join("") : `
          <div class="empty">
            <div class="empty-icon">✦</div>
            <h3>Noch kein Projektraum</h3>
            <p>Legen Sie ein Briefing an, um Anforderungen und Abstimmung mit dem A+ Projektteam zu organisieren.</p>
            <button class="btn primary" data-route="new">Projekt anlegen</button>
          </div>`}
      </section>
    `, "projects");
    root.querySelectorAll("[data-project]").forEach((el) => el.addEventListener("click", async () => {
      state.selectedProject = el.dataset.project;
      state.route = "project";
      await render();
    }));
  }

  async function renderNewProject() {
    await loadMe();
    shell(`
      <div class="eyebrow">PROJEKTBRIEFING</div>
      <h1>Neuen Projektraum anlegen</h1>
      <p class="lead">Erfassen Sie Ziel, Branche und Anforderungen für die Zusammenarbeit mit dem A+ Projektteam.</p>
      <form id="project-form" class="form card">
        <label>Projektname<input name="name" required maxlength="160" placeholder="z. B. Luna Booking"></label>
        <label>Branche / Geschäftstyp<input name="business_type" required maxlength="120" placeholder="z. B. Friseursalon"></label>
        <label>Ziel & Anforderungen<textarea name="description" rows="7" required placeholder="Wer nutzt das Produkt? Welches Problem soll gelöst werden? Welche Anforderungen sind wichtig?"></textarea></label>
        <label>Projektsprache<select name="language"><option value="de">Deutsch</option><option value="en">English</option></select></label>
        <div class="notice">Die mobile App dient ausschließlich der Projektkoordination. Sie erstellt, lädt, installiert oder führt keinen Programmcode und keine anderen Apps aus.</div>
        <button class="btn primary" type="submit">Projekt anlegen</button>
      </form>
    `, "new");
    document.getElementById("project-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = event.currentTarget.querySelector("button");
      button.disabled = true;
      button.textContent = "Projekt wird angelegt…";
      const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
      try {
        const data = await api("/projects/", { method: "POST", body: JSON.stringify(payload) });
        state.selectedProject = data.project.id;
        state.route = "project";
        await render();
      } catch (error) {
        button.disabled = false;
        button.textContent = "Projekt anlegen";
        alert(error.message);
      }
    });
  }

  function renderChangeRequests(items) {
    if (!items?.length) {
      return '<p class="muted">Noch keine Änderungswünsche erfasst.</p>';
    }
    return `<div class="submission-list">${items.map((item) => `
      <div>
        <b>${escapeHtml(item.title)}</b>
        <span>${escapeHtml(statusLabel(item.status))}</span>
      </div>
    `).join("")}</div>`;
  }

  function renderStoreStatus(items) {
    if (!items?.length) {
      return '<p class="muted">Noch kein Veröffentlichungsstatus vorhanden.</p>';
    }
    return `<div class="submission-list">${items.map((item) => `
      <div>
        <b>${item.platform === "both" ? "Apple + Google" : item.platform === "ios" ? "Apple App Store" : "Google Play"}</b>
        <span>${escapeHtml(statusLabel(item.status))}</span>
      </div>
    `).join("")}</div>`;
  }

  async function renderProject() {
    if (!state.selectedProject) return navigate("projects");
    loading("Projekt");
    const data = await api(`/projects/${state.selectedProject}/`);
    const project = data.project;
    shell(`
      <div class="project-title">
        <div>
          <span class="status ${project.status}">${escapeHtml(statusLabel(project.status))}</span>
          <h1>${escapeHtml(project.name)}</h1>
          <p>${escapeHtml(project.business_type)}</p>
        </div>
      </div>

      <section class="card">
        <div class="section-head"><h2>Projektstatus</h2><span class="pill">${escapeHtml(statusLabel(project.status))}</span></div>
        <p>${escapeHtml(project.description)}</p>
        <div class="notice">Technische Builds, ausführbarer Code und App-Previews sind kein Bestandteil dieser mobilen App.</div>
      </section>

      <section class="card">
        <div class="section-head"><h2>Änderungswünsche</h2><span class="pill">Projektteam</span></div>
        ${renderChangeRequests(project.change_requests)}
        <form id="request-form" class="chat-form">
          <textarea name="message" rows="4" maxlength="12000" required placeholder="Beschreiben Sie Ihre Änderung, Frage oder Priorität für das Projektteam."></textarea>
          <button class="btn primary" type="submit">Anfrage senden</button>
        </form>
      </section>

      <section class="card">
        <div class="section-head"><h2>Veröffentlichungsstatus</h2><span class="pill">Nur Status</span></div>
        ${renderStoreStatus(project.store_submissions)}
        <p class="muted">Store-Einreichungen werden außerhalb dieser mobilen App vom Projektteam verwaltet.</p>
      </section>
    `, "projects");

    document.getElementById("request-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = event.currentTarget.querySelector("button");
      const message = new FormData(event.currentTarget).get("message");
      button.disabled = true;
      button.textContent = "Wird gesendet…";
      try {
        await api(`/projects/${project.id}/chat/`, {
          method: "POST",
          body: JSON.stringify({ message }),
        });
        await renderProject();
      } catch (error) {
        alert(error.message);
        button.disabled = false;
        button.textContent = "Anfrage senden";
      }
    });
  }

  async function renderAccount() {
    const me = await loadMe();
    shell(`
      <div class="eyebrow">KONTO</div>
      <h1>${escapeHtml(me.name)}</h1>
      <section class="card profile">
        <div><small>E-Mail</small><b>${escapeHtml(me.email)}</b></div>
        <div><small>Workspace</small><b>${escapeHtml(me.organization.name)}</b></div>
      </section>
      <section class="card">
        <h2>Über diese App</h2>
        <p class="muted">A+ Studio für iOS ist eine kostenlose Begleit-App zur Projektkoordination. In der App gibt es keine Käufe, Abonnements, Credits oder Freischaltungen.</p>
      </section>
      <section class="card">
        <h2>Hilfe & Rechtliches</h2>
        <div class="linklist">
          <a href="${WEB}/privacy/" target="_blank" rel="noopener">Datenschutzerklärung <span>›</span></a>
          <a href="${WEB}/terms/" target="_blank" rel="noopener">Nutzungsbedingungen <span>›</span></a>
          <a href="${WEB}/support/" target="_blank" rel="noopener">Support <span>›</span></a>
          <a href="${WEB}/account-deletion/" target="_blank" rel="noopener">Kontolöschung im Web <span>›</span></a>
        </div>
      </section>
      <section class="card danger-zone">
        <h2>Konto löschen</h2>
        <p>Dadurch werden Ihr Konto und Ihre persönlichen A+ Studio Workspaces inklusive Projekten dauerhaft gelöscht. Gesetzlich erforderliche Nachweise können nur im notwendigen Umfang aufbewahrt werden.</p>
        <button class="btn danger" id="delete-account">Konto dauerhaft löschen</button>
      </section>
      <button class="btn secondary full" id="logout">Abmelden</button>
    `, "account");

    document.getElementById("logout").addEventListener("click", () => {
      state.me = null;
      setToken("");
      showAuth();
    });
    document.getElementById("delete-account").addEventListener("click", async () => {
      const first = confirm("Möchten Sie Ihr A+ Studio Konto wirklich dauerhaft löschen?");
      if (!first) return;
      const confirmation = prompt('Zur Bestätigung bitte "DELETE" eingeben.');
      if (confirmation !== "DELETE") return;
      try {
        await api("/account/delete/", {
          method: "POST",
          body: JSON.stringify({ confirmation }),
        });
        state.me = null;
        setToken("");
        root.innerHTML = `<main class="auth"><section class="auth-card">${brand()}<div class="eyebrow">KONTO GELÖSCHT</div><h1>Ihre Löschung wurde abgeschlossen.</h1><p class="muted">Sie können die App jetzt schließen oder ein neues Konto erstellen.</p><button class="btn primary" id="restart">Zur Anmeldung</button></section></main>`;
        document.getElementById("restart").addEventListener("click", () => showAuth());
      } catch (error) {
        alert(error.message);
      }
    });
  }

  async function render() {
    if (!state.token) return showAuth();
    try {
      if (state.route === "new") return await renderNewProject();
      if (state.route === "project") return await renderProject();
      if (state.route === "account") return await renderAccount();
      return await renderProjects();
    } catch (error) {
      if (state.token) showError(error);
    }
  }

  render();
})();
