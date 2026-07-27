(() => {
  document.querySelectorAll('.flash').forEach(el => setTimeout(() => { el.style.opacity = '0'; setTimeout(() => el.remove(), 250); }, 5500));

  const workspace = document.querySelector('.project-workspace');
  const form = document.getElementById('chat-form');
  if (!workspace || !form) return;

  const stream = document.getElementById('chat-stream');
  const frame = document.getElementById('preview-frame');
  const credits = document.getElementById('credits-count');
  const submit = form.querySelector('button[type="submit"]');
  const textarea = form.querySelector('textarea');
  const csrf = form.querySelector('[name="csrfmiddlewaretoken"]').value;

  const scrollDown = () => { stream.scrollTop = stream.scrollHeight; };
  scrollDown();

  const escapeHtml = value => String(value || '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  const renderText = value => escapeHtml(value).replace(/\n/g, '<br>');

  function addMessage(role, content, id = '', working = false) {
    const article = document.createElement('article');
    article.className = `chat-message ${role}${working ? ' working' : ''}`;
    if (id) article.dataset.messageId = id;
    article.innerHTML = `<div class="message-author">${role === 'assistant' ? 'A+ Builder' : 'You'}</div><div class="message-content">${renderText(content)}</div><small>now</small>`;
    stream.appendChild(article);
    scrollDown();
    return article;
  }

  async function poll(messageId, article) {
    const url = `${window.location.pathname}messages/${messageId}/`;
    for (let attempt = 0; attempt < 180; attempt++) {
      await new Promise(resolve => setTimeout(resolve, 2000));
      const response = await fetch(url, {headers: {'X-Requested-With': 'XMLHttpRequest'}});
      if (!response.ok) continue;
      const data = await response.json();
      if (credits) credits.textContent = data.credits;
      if (data.status === 'done' || data.status === 'failed') {
        article.classList.remove('working');
        article.querySelector('.message-content').innerHTML = renderText(data.content);
        article.querySelector('small').textContent = data.status === 'failed' ? 'failed safely' : 'just now';
        if (data.metadata && data.metadata.preview_url) {
          const link = document.createElement('a');
          link.className = 'inline-action';
          link.href = data.metadata.preview_url;
          link.target = '_blank';
          link.textContent = 'Open preview ↗';
          article.insertBefore(link, article.querySelector('small'));
          if (frame) frame.src = `${data.metadata.preview_url}?v=${Date.now()}`;
        }
        submit.disabled = false;
        textarea.disabled = false;
        textarea.focus();
        scrollDown();
        return;
      }
    }
    article.classList.remove('working');
    article.querySelector('.message-content').textContent = 'The build is still running. Refresh this page to see the latest status.';
    submit.disabled = false;
    textarea.disabled = false;
  }

  form.addEventListener('submit', async event => {
    event.preventDefault();
    const value = textarea.value.trim();
    if (!value) return;
    addMessage('user', value);
    textarea.value = '';
    textarea.disabled = true;
    submit.disabled = true;
    const assistant = addMessage('assistant', 'Working on your request…', '', true);
    try {
      const body = new FormData();
      body.append('message', value);
      body.append('csrfmiddlewaretoken', csrf);
      const response = await fetch(form.action, {method: 'POST', body, headers: {'X-Requested-With': 'XMLHttpRequest'}});
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Could not start the build');
      assistant.dataset.messageId = data.assistant_message_id;
      poll(data.assistant_message_id, assistant);
    } catch (error) {
      assistant.classList.remove('working');
      assistant.querySelector('.message-content').textContent = error.message;
      submit.disabled = false;
      textarea.disabled = false;
    }
  });

  textarea.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });
})();
