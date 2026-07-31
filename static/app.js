(() => {
  document.querySelectorAll('.flash').forEach(el => setTimeout(() => {
    el.style.opacity = '0';
    setTimeout(() => el.remove(), 250);
  }, 5500));
  if (!document.querySelector('.project-workspace')) return;
  const source = document.currentScript?.src || `${window.location.origin}/static/app.js`;
  const scriptUrl = new URL('workflow.js?v=20260731-1', source);
  const styleUrl = new URL('workflow.css?v=20260731-1', source);
  if (!document.querySelector('link[data-astudio-workflow]')) {
    const link = document.createElement('link'); link.rel = 'stylesheet'; link.href = styleUrl.toString(); link.dataset.astudioWorkflow = '1'; document.head.appendChild(link);
  }
  if (!document.querySelector('script[data-astudio-workflow]')) {
    const script = document.createElement('script'); script.src = scriptUrl.toString(); script.defer = true; script.dataset.astudioWorkflow = '1'; document.head.appendChild(script);
  }
})();
