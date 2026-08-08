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
    message_required: "Bitte geben Sie eine Nachricht ein.",
    message_too_long: "Die Nachricht ist zu lang.",
    preview_required: "Vor der Veröffentlichung muss ein erfolgreicher Preview-Build vorliegen.",
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
    return `<div class="brand"><div class="brandmark">A+</div><div><b>A+ Studio</b><small>AI Software Factory</small></div></div>`;
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
          <div class="eyebrow">${signup ? "KONTO ERSTELLEN" : "WILLKOMMEN ZURÜCK"}</div>
          <h1>${signup ? "Ihre nächste App beginnt hier." : "Bauen. Testen. Veröffentlichen."}</h1>
          <p class="muted">A+ Studio bringt Idee, AI-Builder, Preview und Veröffentlichung in einen klaren mobilen Workflow.</p>
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
          <button class="textbtn" id="auth-switch">${signup ? "Schon registriert? Anmelden" : "Noch kein Konto? Jetzt starten"}</button>
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
          <h1>So arbeitet A+ Studio.</h1>
          <p class="muted">Die Demo zeigt den mobilen Workflow ohne Konto. Für einen echten AI-Build kann anschließend kostenlos ein Konto mit Start-Credits erstellt werden.</p>
          <div class="card">
            <span class="status preview">Preview bereit</span>
            <h3>Luna Booking</h3>
            <p>Termin-App für einen lokalen Salon · Version 3</p>
          </div>
          <div class="card">
            <h2>AI Builder</h2>
            <div class="chat">
              <div class="bubble user"><small>Sie</small><div>Füge eine übersichtliche Wochenansicht für Termine hinzu.</div></div>
              <div class="bubble assistant"><small>A+ Studio</small><div>Die Wochenansicht ist vorbereitet. Der neue Preview-Build enthält Tagesnavigation, freie Slots und eine kompakte Terminübersicht.</div></div>
            </div>
          </div>
          <div class="card">
            <h2>Store Publishing</h2>
            <p>Nach Freigabe prüft A+ Metadaten, Signierung und Store-Compliance für Google Play und den App Store.</p>
          </div>
          <button class="btn primary full" id="demo-signup">Kostenlos ausprobieren</button>
          <button class="textbtn" id="demo-back">Zur Anmeldung</button>
        </section>
      </main>`;
    document.getElementById("demo-signup").addEventListener("click", () => showAuth("signup"));
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
      draft: "Entwurf",
      building: "Build läuft",
      preview: "Preview bereit",
      live: "Live",
      paused: "Pausiert",
      error: "Fehler",
      requested: "Angefragt",
      eligibility: "Prüfung",
      accounts: "Developer-Konten",
      preparing: "Vorbereitung",
      submitted: "Eingereicht",
      review: "In Prüfung",
      approved: "Freigegeben",
      rejected: "Abgelehnt",
    }[status] || status || "–");
  }

  async function renderProjects() {
    loading("Ihre Projekte");
    const data = await api("/dashboard/");
    shell(`
      <section class="hero">
        <div class="eyebrow">WORKSPACE</div>
        <h1>${escapeHtml(data.organization.name)}</h1>
        <p>Von der Idee zum installierbaren Produkt – mit Preview, Versionierung und A+ Publishing.</p>
        <div class="metrics">
          <div><b>${data.projects.length}</b><span>Projekte</span></div>
          <div><b>${Number(data.organization.credits) || 0}</b><span>Credits</span></div>
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
            <h3>Noch kein Projekt</h3>
            <p>Beschreiben Sie Ihre Idee. A+ Studio erstellt daraus den ersten Preview-Build.</p>
            <button class="btn primary" data-route="new">Erstes Projekt erstellen</button>
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
      <div class="eyebrow">NEUES PRODUKT</div>
      <h1>Was sollen wir bauen?</h1>
      <p class="lead">Geben Sie Kontext statt Technik vor. Der Builder erzeugt daraus die erste sichere App-Spezifikation und Preview.</p>
      <form id="project-form" class="form card">
        <label>App-Name<input name="name" required maxlength="160" placeholder="z. B. Luna Booking"></label>
        <label>Branche / Geschäftstyp<input name="business_type" required maxlength="120" placeholder="z. B. Friseursalon"></label>
        <label>Ziel & Funktionen<textarea name="description" rows="7" required placeholder="Wer nutzt die App? Was soll sie im Alltag lösen? Welche Kernfunktionen brauchen Sie?"></textarea></label>
        <label>Sprache<select name="language"><option value="de">Deutsch</option><option value="en">English</option></select></label>
        <div class="notice">Die Erstellung nutzt Ihre Studio-Credits. Käufe und Abos werden in dieser mobilen Version bewusst nicht angeboten.</div>
        <button class="btn primary" type="submit">Preview erstellen</button>
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
        button.textContent = "Preview erstellen";
        alert(error.message);
      }
    });
  }

  async function renderProject() {
    if (!state.selectedProject) return navigate("projects");
    loading("Projekt");
    const data = await api(`/projects/${state.selectedProject}/`);
    const project = data.project;
    const hasPreview = ["preview", "live"].includes(project.status);
    shell(`
      <div class="project-title">
        <div>
          <span class="status ${project.status}">${escapeHtml(statusLabel(project.status))}</span>
          <h1>${escapeHtml(project.name)}</h1>
          <p>${escapeHtml(project.business_type)} · Version ${project.version}</p>
        </div>
      </div>
      ${project.last_build_error ? `<div class="notice error">${escapeHtml(project.last_build_error)}</div>` : ""}
      <section class="card">
        <div class="section-head"><h2>Build</h2><span class="pill">${escapeHtml(statusLabel(project.status))}</span></div>
        <p>${escapeHtml(project.description)}</p>
        <div class="actions">
          ${project.preview_url ? `<a class="btn secondary" href="${escapeHtml(project.preview_url)}" target="_blank" rel="noopener">Preview öffnen</a>` : ""}
          ${project.live_url && project.status === "live" ? `<a class="btn secondary" href="${escapeHtml(project.live_url)}" target="_blank" rel="noopener">Live öffnen</a>` : ""}
          ${hasPreview ? '<button class="btn primary" data-publish>Live veröffentlichen</button>' : ""}
        </div>
      </section>

      <section class="card">
        <div class="section-head"><h2>AI Builder</h2><span class="pill">Chat</span></div>
        <div class="chat" id="chat-list">
          ${project.messages.length ? project.messages.map((message) => `
            <div class="bubble ${message.role === "user" ? "user" : "assistant"}">
              <small>${message.role === "user" ? "Sie" : "A+ Studio"}</small>
              <div>${escapeHtml(message.content)}</div>
              ${message.status === "working" || message.status === "queued" ? '<span class="working">In Arbeit…</span>' : ""}
            </div>`).join("") : '<p class="muted">Beschreiben Sie die nächste Änderung am Produkt.</p>'}
        </div>
        <form id="chat-form" class="chat-form">
          <textarea name="message" rows="3" maxlength="12000" required placeholder="z. B. Füge eine Terminübersicht mit Wochenansicht hinzu."></textarea>
          <button class="btn primary" type="submit">Änderung senden</button>
        </form>
      </section>

      <section class="card">
        <div class="section-head"><h2>Store Publishing</h2><span class="pill">Managed</span></div>
        <p>A+ prüft App-Qualität, Developer-Konten, Metadaten und Store-Compliance vor der Einreichung.</p>
        ${project.store_submissions.length ? `
          <div class="submission-list">${project.store_submissions.map((item) => `
            <div><b>${item.platform === "both" ? "Apple + Google" : item.platform === "ios" ? "Apple App Store" : "Google Play"}</b><span>${escapeHtml(statusLabel(item.status))}</span></div>
          `).join("")}</div>` : ""}
        <div class="actions">
          <button class="btn secondary" data-store="android">Google Play anfragen</button>
          <button class="btn secondary" data-store="ios">App Store anfragen</button>
          <button class="btn primary" data-store="both">Beide Stores</button>
        </div>
      </section>
    `, "projects");

    root.querySelector("[data-publish]")?.addEventListener("click", async (event) => {
      event.currentTarget.disabled = true;
      try {
        await api(`/projects/${project.id}/publish/`, { method: "POST", body: "{}" });
        alert("Publishing wurde gestartet.");
        await renderProject();
      } catch (error) {
        alert(error.message);
        event.currentTarget.disabled = false;
      }
    });

    root.querySelectorAll("[data-store]").forEach((button) => button.addEventListener("click", async () => {
      button.disabled = true;
      try {
        await api(`/projects/${project.id}/store-submission/`, {
          method: "POST",
          body: JSON.stringify({ platform: button.dataset.store }),
        });
        await renderProject();
      } catch (error) {
        alert(error.message);
        button.disabled = false;
      }
    }));

    document.getElementById("chat-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = event.currentTarget.querySelector("button");
      const message = new FormData(event.currentTarget).get("message");
      button.disabled = true;
      try {
        const queued = await api(`/projects/${project.id}/chat/`, {
          method: "POST",
          body: JSON.stringify({ message }),
        });
        await pollMessage(project.id, queued.assistant_message_id);
      } catch (error) {
        alert(error.message);
        button.disabled = false;
      }
    });
  }

  async function pollMessage(projectId, messageId) {
    for (let attempt = 0; attempt < 72; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 2500));
      try {
        const data = await api(`/projects/${projectId}/messages/${messageId}/`);
        if (["done", "failed"].includes(data.message.status)) {
          await renderProject();
          return;
        }
      } catch (_) {
        break;
      }
    }
    await renderProject();
  }

  async function renderAccount() {
    const me = await loadMe();
    shell(`
      <div class="eyebrow">KONTO</div>
      <h1>${escapeHtml(me.name)}</h1>
      <section class="card profile">
        <div><small>E-Mail</small><b>${escapeHtml(me.email)}</b></div>
        <div><small>Workspace</small><b>${escapeHtml(me.organization.name)}</b></div>
        <div><small>Plan</small><b>${escapeHtml(me.organization.plan)}</b></div>
        <div><small>Credits</small><b>${Number(me.organization.credits) || 0}</b></div>
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
