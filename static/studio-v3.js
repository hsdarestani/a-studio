(() => {
  const workspace = document.querySelector('.project-workspace[data-builder-mode="code_agent"]');
  if (!workspace) return;

  const urls = {
    manifest: workspace.dataset.codeManifestUrl || '',
    file: workspace.dataset.codeFileUrl || '',
    save: workspace.dataset.codeSaveUrl || '',
    changes: workspace.dataset.codeChangesUrl || '',
    diffBase: workspace.dataset.codeDiffBase || '',
  };
  const panels = [...document.querySelectorAll('[data-v3-panel]')];
  const tabs = [...document.querySelectorAll('[data-v3-tab]')];
  const fileList = document.querySelector('[data-v3-file-list]');
  const editor = document.querySelector('[data-v3-editor]');
  const pathLabel = document.querySelector('[data-v3-editor-path]');
  const saveButton = document.querySelector('[data-v3-save]');
  const editorStatus = document.querySelector('[data-v3-editor-status]');
  const changesList = document.querySelector('[data-v3-changes]');
  const preview = document.getElementById('preview-frame');
  const versionNode = document.querySelector('.project-state span:last-child');
  let selectedPath = '';
  let originalContent = '';
  let currentVersion = Number(workspace.dataset.projectVersion || 1);

  function csrfToken() {
    const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  }

  function setStatus(text, type = '') {
    if (!editorStatus) return;
    editorStatus.textContent = text || '';
    editorStatus.dataset.type = type;
  }

  function switchPanel(name) {
    tabs.forEach(tab => tab.classList.toggle('active', tab.dataset.v3Tab === name));
    panels.forEach(panel => { panel.hidden = panel.dataset.v3Panel !== name; });
    if (name === 'code') loadManifest();
    if (name === 'changes') loadChanges();
  }

  tabs.forEach(tab => tab.addEventListener('click', () => switchPanel(tab.dataset.v3Tab)));

  async function jsonFetch(url, options = {}) {
    const response = await fetch(url, {credentials: 'same-origin', ...options});
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error || `http_${response.status}`);
    return payload;
  }

  function renderFileList(files) {
    if (!fileList) return;
    fileList.innerHTML = '';
    (files || []).forEach(item => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'v3-file-button';
      button.textContent = item.path;
      button.title = `${item.path} · ${item.size || 0} bytes`;
      button.dataset.path = item.path;
      button.classList.toggle('active', item.path === selectedPath);
      button.addEventListener('click', () => loadFile(item.path));
      fileList.appendChild(button);
    });
  }

  async function loadManifest() {
    if (!urls.manifest || !fileList) return;
    try {
      const payload = await jsonFetch(urls.manifest);
      currentVersion = Number(payload.version || currentVersion);
      renderFileList(payload.files || []);
      if (!selectedPath && payload.entry) await loadFile(payload.entry);
    } catch (error) {
      fileList.innerHTML = `<div class="v3-ide-empty">${error.message}</div>`;
    }
  }

  async function loadFile(path) {
    if (!urls.file || !editor) return;
    setStatus('Loading…');
    try {
      const payload = await jsonFetch(`${urls.file}?path=${encodeURIComponent(path)}`);
      selectedPath = payload.path;
      originalContent = payload.content || '';
      editor.value = originalContent;
      if (pathLabel) pathLabel.textContent = selectedPath;
      if (saveButton) saveButton.disabled = true;
      document.querySelectorAll('.v3-file-button').forEach(button => button.classList.toggle('active', button.dataset.path === selectedPath));
      setStatus(`v${payload.version}`);
    } catch (error) {
      setStatus(error.message, 'error');
    }
  }

  editor?.addEventListener('input', () => {
    if (saveButton) saveButton.disabled = !selectedPath || editor.value === originalContent;
    setStatus(editor.value === originalContent ? `v${currentVersion}` : 'Unsaved changes');
  });

  editor?.addEventListener('keydown', event => {
    if (event.key === 'Tab') {
      event.preventDefault();
      const start = editor.selectionStart;
      const end = editor.selectionEnd;
      editor.value = `${editor.value.slice(0, start)}  ${editor.value.slice(end)}`;
      editor.selectionStart = editor.selectionEnd = start + 2;
      editor.dispatchEvent(new Event('input'));
    }
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 's') {
      event.preventDefault();
      if (saveButton && !saveButton.disabled) saveButton.click();
    }
  });

  saveButton?.addEventListener('click', async () => {
    if (!selectedPath || saveButton.disabled) return;
    saveButton.disabled = true;
    setStatus('Saving & rebuilding preview…');
    try {
      const payload = await jsonFetch(urls.save, {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken()},
        body: JSON.stringify({path: selectedPath, content: editor.value}),
      });
      originalContent = editor.value;
      currentVersion = Number(payload.version || currentVersion + 1);
      workspace.dataset.projectVersion = String(currentVersion);
      setStatus(`Saved · v${currentVersion}`, 'success');
      if (versionNode) versionNode.textContent = `Version ${currentVersion}`;
      if (preview) {
        const url = new URL(payload.preview_url || preview.src, window.location.origin);
        url.searchParams.set('preview', '1');
        url.searchParams.set('v', String(currentVersion));
        preview.src = url.toString();
      }
      await loadManifest();
    } catch (error) {
      setStatus(`Save failed · ${error.message}`, 'error');
      saveButton.disabled = false;
    }
  });

  async function loadChanges() {
    if (!urls.changes || !changesList) return;
    changesList.innerHTML = '<div class="v3-ide-empty">Loading revisions…</div>';
    try {
      const payload = await jsonFetch(urls.changes);
      const changes = payload.changes || [];
      if (!changes.length) {
        changesList.innerHTML = '<div class="v3-ide-empty">No code revisions yet.</div>';
        return;
      }
      changesList.innerHTML = '';
      changes.forEach(item => {
        const card = document.createElement('article');
        card.className = 'v3-change-card';
        const files = [...(item.changed_files || []), ...(item.deleted_files || []).map(path => `deleted: ${path}`)];
        card.innerHTML = `<header><div><h4></h4><small></small></div><button type="button" class="v3-diff-button">View diff</button></header><p></p><div class="v3-change-files"></div><pre class="v3-diff-view" hidden></pre>`;
        card.querySelector('h4').textContent = item.title || 'Code revision';
        card.querySelector('small').textContent = `${item.version ? `v${item.version} · ` : ''}${new Date(item.created_at).toLocaleString()}`;
        card.querySelector('p').textContent = item.description || '';
        const fileWrap = card.querySelector('.v3-change-files');
        files.forEach(path => {
          const span = document.createElement('span'); span.textContent = path; fileWrap.appendChild(span);
        });
        const diffButton = card.querySelector('.v3-diff-button');
        const diffView = card.querySelector('.v3-diff-view');
        diffButton.addEventListener('click', async () => {
          if (!diffView.hidden) { diffView.hidden = true; diffButton.textContent = 'View diff'; return; }
          diffButton.disabled = true;
          try {
            const url = `${urls.diffBase}${item.id}/`;
            const diffPayload = await jsonFetch(url);
            diffView.textContent = diffPayload.diff || 'No textual diff available.';
            diffView.hidden = false;
            diffButton.textContent = 'Hide diff';
          } catch (error) {
            diffView.textContent = error.message;
            diffView.hidden = false;
          } finally { diffButton.disabled = false; }
        });
        changesList.appendChild(card);
      });
    } catch (error) {
      changesList.innerHTML = `<div class="v3-ide-empty">${error.message}</div>`;
    }
  }

  document.querySelector('[data-v3-refresh-preview]')?.addEventListener('click', () => {
    if (!preview) return;
    const url = new URL(preview.src, window.location.origin);
    url.searchParams.set('v', `${currentVersion}-${Date.now()}`);
    preview.src = url.toString();
  });
})();
