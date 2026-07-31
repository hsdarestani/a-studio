(() => {
  const workspace = document.querySelector('.project-workspace');
  const form = document.getElementById('chat-form');
  if (!workspace || !form) return;
  window.ASTUDIO_WORKFLOW_V2 = true;

  const de = (document.documentElement.lang || 'de').toLowerCase().startsWith('de');
  const t = de ? {
    queued:'Anfrage eingereiht', analyzing:'Anforderung wird analysiert', planning:'Änderung wird geplant', preparing:'Build wird vorbereitet',
    building:'App wird erstellt', validating:'Build wird geprüft', syncing:'Quellcode wird synchronisiert', finishing:'Vorschau wird finalisiert',
    ready:'Vorschau bereit', failed:'Build fehlgeschlagen', live:'Live', elapsed:'vergangen',
    title:'Dein Build läuft', saved:'Deine Anfrage ist gespeichert. Du musst sie nicht erneut senden.',
    queuedText:'Anfrage eingereiht. A+ Builder bereitet den Build vor.', preview:'Vorschau öffnen ↗',
    duplicate:'Dieser Build läuft bereits. Die nächste Anfrage kannst du senden, sobald er fertig ist.',
    store:'Store-Anfragen & Status →', note:'Optionale Notiz für A+ Solution', error:'Der Build konnte nicht gestartet werden.'
  } : {
    queued:'Request queued', analyzing:'Analyzing requirement', planning:'Planning change', preparing:'Preparing build',
    building:'Building app', validating:'Validating build', syncing:'Syncing source code', finishing:'Finalizing preview',
    ready:'Preview ready', failed:'Build failed', live:'Live', elapsed:'elapsed',
    title:'Your build is running', saved:'Your request is saved. You do not need to send it again.',
    queuedText:'Request queued. A+ Builder is preparing the build.', preview:'Open preview ↗',
    duplicate:'This build is already running. You can send the next request when it is ready.',
    store:'Store requests & status →', note:'Optional note for A+ Solution', error:'Could not start the build.'
  };
  const labels = {queued:t.queued,analyzing:t.analyzing,planning:t.planning,preparing:t.preparing,building:t.building,validating:t.validating,syncing:t.syncing,finishing:t.finishing,ready:t.ready,failed:t.failed};
  const stream = document.getElementById('chat-stream');
  const frame = document.getElementById('preview-frame');
  const credits = document.getElementById('credits-count');
  const textarea = form.querySelector('textarea');
  const submit = form.querySelector('button[type="submit"]');
  const csrf = form.querySelector('[name="csrfmiddlewaretoken"]').value;
  const originalTitle = document.title;
  let timer = null, busyStart = null, pollingId = null;

  const esc = s => String(s || '').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  const text = s => esc(s).replace(/\n/g,'<br>');
  const wait = ms => new Promise(r=>setTimeout(r,ms));
  const elapsed = start => { const s=Math.max(0,Math.floor((Date.now()-start)/1000)); return `${String(Math.floor(s/60)).padStart(2,'0')}:${String(s%60).padStart(2,'0')}`; };
  const previewUrl = (url,version=Date.now()) => { const u=new URL(url,location.origin); u.searchParams.set('preview','1'); u.searchParams.set('v',String(version)); return u.toString(); };

  let lock = document.getElementById('build-lock');
  if (!lock) {
    lock = document.createElement('div'); lock.id='build-lock'; lock.className='build-lock hidden';
    lock.innerHTML=`<span class="build-lock-dot"></span><div><strong>${t.title}</strong><small>${t.saved}</small></div><time>00:00</time>`;
    form.prepend(lock);
  }
  function busy(on,start=Date.now()){
    if(on){busyStart=start;form.classList.add('busy');lock.classList.remove('hidden');textarea.disabled=true;submit.disabled=true;document.title=`⏳ ${originalTitle}`;clearInterval(timer);const tick=()=>lock.querySelector('time').textContent=elapsed(busyStart);tick();timer=setInterval(tick,1000);}
    else{form.classList.remove('busy');lock.classList.add('hidden');textarea.disabled=false;submit.disabled=false;document.title=originalTitle;clearInterval(timer);timer=null;busyStart=null;textarea.focus();}
  }
  function progress(article,stage='queued',percent=5,start=Date.now()){
    let box=article.querySelector('.build-progress');
    if(!box){box=document.createElement('div');box.className='build-progress';box.innerHTML=`<div class="build-progress-head"><strong></strong><b></b></div><div class="build-progress-track"><i></i></div><div class="build-progress-meta"><span>${t.live}</span><time></time></div><small>${t.saved}</small>`;article.querySelector('.message-content').insertAdjacentElement('afterend',box);}
    const p=Math.max(0,Math.min(100,Number(percent)||0));box.querySelector('strong').textContent=labels[stage]||t.building;box.querySelector('b').textContent=`${p}%`;box.querySelector('i').style.width=`${Math.max(5,p)}%`;box.dataset.start=String(start);box.querySelector('time').textContent=`${elapsed(start)} ${t.elapsed}`;
  }
  setInterval(()=>document.querySelectorAll('.build-progress').forEach(b=>{const s=Number(b.dataset.start||Date.now());b.querySelector('time').textContent=`${elapsed(s)} ${t.elapsed}`;}),1000);

  function add(role,content){const a=document.createElement('article');a.className=`chat-message ${role}`;a.innerHTML=`<div class="message-author">${role==='assistant'?'A+ Builder':(de?'Du':'You')}</div><div class="message-content">${text(content)}</div><small>${de?'jetzt':'now'}</small>`;stream.appendChild(a);stream.scrollTop=stream.scrollHeight;return a;}
  function finish(article,data){article.classList.remove('working');article.querySelector('.build-progress')?.remove();article.querySelector('.message-content').innerHTML=text(data.content);if(credits)credits.textContent=data.credits;if(data.metadata?.preview_url){const u=previewUrl(data.metadata.preview_url,data.metadata.version);let a=article.querySelector('.inline-action');if(!a){a=document.createElement('a');a.className='inline-action';a.target='_blank';a.rel='noopener';article.insertBefore(a,article.querySelector('small'));}a.href=u;a.textContent=t.preview;if(frame)frame.src=u;}busy(false);setTimeout(()=>location.reload(),700);}
  async function poll(id,article,start=Date.now()){
    if(!id||pollingId===id)return;pollingId=id;busy(true,start);article.classList.add('working');progress(article,'queued',5,start);
    const url=`${location.pathname}messages/${id}/`;
    for(let i=0;i<300;i++){await wait(i<40?1500:3000);try{const r=await fetch(url,{headers:{'X-Requested-With':'XMLHttpRequest'},cache:'no-store'});if(!r.ok)continue;const d=await r.json();const p=d.metadata?.progress||{};progress(article,p.stage||(d.status==='queued'?'queued':'building'),p.percent||(d.status==='queued'?5:55),start);if(d.status==='done'||d.status==='failed'){pollingId=null;finish(article,d);return;}}catch(_e){}}
  }
  async function resume(){const last=[...stream.querySelectorAll('.chat-message.assistant[data-message-id]')].pop();if(!last)return;try{const r=await fetch(`${location.pathname}messages/${last.dataset.messageId}/`,{headers:{'X-Requested-With':'XMLHttpRequest'},cache:'no-store'});if(!r.ok)return;const d=await r.json();if(d.status==='queued'||d.status==='working')poll(last.dataset.messageId,last,Date.now());}catch(_e){}}

  form.addEventListener('submit',async e=>{
    e.preventDefault();e.stopImmediatePropagation();if(submit.disabled)return;const v=textarea.value.trim();if(!v)return;add('user',v);textarea.value='';const a=add('assistant',t.queuedText);const start=Date.now();busy(true,start);progress(a,'queued',5,start);
    try{const body=new FormData();body.append('message',v);body.append('csrfmiddlewaretoken',csrf);const r=await fetch(form.action,{method:'POST',body,headers:{'X-Requested-With':'XMLHttpRequest'}});const d=await r.json();if(r.status===409&&d.active_message_id){a.querySelector('.message-content').textContent=t.duplicate;setTimeout(()=>location.reload(),500);return;}if(!r.ok)throw new Error(d.error||t.error);a.dataset.messageId=d.assistant_message_id;poll(d.assistant_message_id,a,start);}catch(err){a.querySelector('.build-progress')?.remove();a.querySelector('.message-content').textContent=err.message;busy(false);}
  },true);
  textarea.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();form.requestSubmit();}},true);

  const storeForm=document.querySelector('.store-request');
  if(storeForm){if(!storeForm.querySelector('textarea[name="notes"]')){const n=document.createElement('textarea');n.name='notes';n.rows=2;n.maxLength=4000;n.placeholder=t.note;storeForm.insertBefore(n,storeForm.querySelector('button'));}const link=document.createElement('a');link.className='store-requests-link';link.href=`${location.pathname}store-submissions/`;link.textContent=t.store;storeForm.insertAdjacentElement('afterend',link);}
  resume();
})();
