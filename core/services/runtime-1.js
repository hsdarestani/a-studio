(() => {
const spec = window.APP_SPEC || {};
const app = spec.app || {}, sections = Array.isArray(spec.sections) ? spec.sections : [];
const backend = spec.backend || {};
const esc = value => String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
const items = value => Array.isArray(value) ? value : [];
const lang = String(app.language || 'de').toLowerCase();
const copy = lang.startsWith('de') ? {
  home:'Start', quiz:'Quiz', results:'Ergebnisse', profile:'Profil', favorites:'Favoriten', account:'Konto',
  install:'Installieren', start:'Quiz starten', back:'Zurück', next:'Weiter', finish:'Ergebnisse anzeigen',
  retake:'Quiz wiederholen', yourProfile:'Dein Profil', topMatches:'Deine besten Matches',
  noResults:'Beantworte zuerst das Quiz, um persönliche Empfehlungen zu erhalten.',
  noFavorites:'Noch keine Favoriten. Markiere Empfehlungen mit dem Herz.',
  match:'Match', xp:'XP', level:'Level', completed:'Beantwortet', traits:'Profilmerkmale',
  saved:'Gespeichert', explorer:'Entdecker', curator:'Kurator', expert:'Kenner',
  login:'Anmelden', signup:'Konto erstellen', logout:'Abmelden', email:'E-Mail', password:'Passwort', name:'Name',
  signedIn:'Angemeldet als', authNeeded:'Bitte melde dich an, um Daten sicher zu speichern.',
  savedRemote:'Sicher gespeichert.', requestFailed:'Das hat nicht funktioniert. Bitte erneut versuchen.',
  uploading:'Datei wird sicher hochgeladen…'
} : {
  home:'Home', quiz:'Quiz', results:'Results', profile:'Profile', favorites:'Favorites', account:'Account',
  install:'Install', start:'Start quiz', back:'Back', next:'Next', finish:'Show results',
  retake:'Retake quiz', yourProfile:'Your profile', topMatches:'Your best matches',
  noResults:'Complete the quiz first to unlock personalized recommendations.',
  noFavorites:'No favorites yet. Save recommendations with the heart.',
  match:'match', xp:'XP', level:'Level', completed:'Answered', traits:'Profile traits',
  saved:'Saved', explorer:'Explorer', curator:'Curator', expert:'Connoisseur',
  login:'Log in', signup:'Create account', logout:'Log out', email:'Email', password:'Password', name:'Name',
  signedIn:'Signed in as', authNeeded:'Please sign in to store data securely.',
  savedRemote:'Saved securely.', requestFailed:'That did not work. Please try again.',
  uploading:'Uploading file securely…'
};
const quiz = sections.find(section => section.type === 'recommendation_quiz');
const hero = sections.find(section => section.type === 'hero') || {};
const standardSections = sections.filter(section => !['hero','recommendation_quiz'].includes(section.type));
const backendFeatures = new Set(items(backend.features).map(String));
const backendBase = String(backend.api_base || '').replace(/\/+$/,'');
const hasAuth = backendFeatures.has('auth') && !!backendBase;
const hasDatabase = backendFeatures.has('database') && !!backendBase;
const hasStorage = backendFeatures.has('storage') && !!backendBase;
const storageKey = `astudio:${String(app.title || 'app').toLowerCase().replace(/[^a-z0-9]+/g,'-')}:state-v2`;
const tokenKey = `${storageKey}:backend-token`;
const blankState = {view:'home', step:0, answers:{}, profile:{}, results:[], favorites:[], xp:0, backendProfile:null};
let state = loadState();
let backendToken = localStorage.getItem(tokenKey) || '';
let deferredPrompt;

function loadState(){
  try { return {...blankState, ...JSON.parse(localStorage.getItem(storageKey) || '{}')}; }
  catch (_) { return {...blankState}; }
}
function saveState(){ localStorage.setItem(storageKey, JSON.stringify(state)); }
function setBackendSession(token,user){
  backendToken = String(token || '');
  if(backendToken) localStorage.setItem(tokenKey, backendToken); else localStorage.removeItem(tokenKey);
  state.backendProfile = user || null;
  saveState();
}
function clearBackendSession(){ setBackendSession('', null); }
async function backendRequest(path, options={}){
  if(!backendBase) throw new Error('backend_unavailable');
  const headers = {...(options.headers || {})};
  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;
  if(options.body && !isFormData && !headers['Content-Type']) headers['Content-Type'] = 'application/json';
  if(backendToken) headers.Authorization = `Bearer ${backendToken}`;
  const response = await fetch(`${backendBase}${path}`, {...options, headers});
  const contentType = String(response.headers.get('content-type') || '');
  const payload = contentType.includes('application/json') ? await response.json().catch(() => ({})) : {};
  if(response.status === 401 && backendToken) clearBackendSession();
  if(!response.ok) throw new Error(payload.error || `http_${response.status}`);
  return payload;
}
async function uploadManagedFile(file){
  if(!hasStorage || !(file instanceof File) || !file.size) return null;
  const body = new FormData(); body.append('file', file, file.name);
  const payload = await backendRequest('/files/', {method:'POST', body});
  return payload.file || null;
}
function collectionName(value, fallback){
  const clean = String(value || fallback || 'submissions').toLowerCase().replace(/[^a-z0-9_-]+/g,'-').replace(/^-+|-+$/g,'').slice(0,80);
  return /^[a-z]/.test(clean) ? clean : `data-${clean || 'item'}`.slice(0,80);
}
function toast(message){
  const old = document.querySelector('.toast'); if(old) old.remove();
  const node = document.createElement('div'); node.className='toast'; node.textContent=message;
  document.body.appendChild(node); setTimeout(() => node.remove(), 2200);
}
function levelInfo(){
  const xp = Number(state.xp || 0);
  if(xp >= 700) return {number:3, label:copy.expert};
  if(xp >= 350) return {number:2, label:copy.curator};
  return {number:1, label:copy.explorer};
}
function formFieldMarkup(field){
  const type = String(field.type || 'text').toLowerCase();
  const name = esc(field.name || field.label);
  const required = field.required ? 'required' : '';
  if(type === 'file'){
    const accept = esc(field.accept || 'image/jpeg,image/png,image/webp,application/pdf,text/plain,text/csv');
    return `<label>${esc(field.label)}<input name="${name}" type="file" accept="${accept}" ${required}></label>`;
  }
  return `<label>${esc(field.label)}<input name="${name}" type="${esc(type)}" ${required}></label>`;
}
function standardSection(section, index){
  const id = esc(section.id || section.type || `section-${index}`);
  const title = section.title ? `<h2>${esc(section.title)}</h2>` : '';
  if(['services','products'].includes(section.type)) return `<section id="${id}">${title}<div class="grid">${items(section.items).map(item => `<article class="card"><span class="pill">${esc(item.category || (section.type === 'products' ? 'Product' : 'Service'))}</span><h3>${esc(item.title)}</h3><p>${esc(item.text || item.description)}</p>${item.price ? `<div class="price">${esc(item.price)}</div>` : ''}</article>`).join('')}</div></section>`;
  if(section.type === 'booking') return `<section id="${id}">${title}<p>${esc(section.text || '')}</p><form class="booking" data-local-form data-backend-collection="${esc(collectionName(section.collection,'bookings'))}"><label>${esc(section.name_label || 'Name')}<input name="name" required></label><label>${esc(section.service_label || 'Service')}<select name="service">${items(section.services).map(item => `<option>${esc(item.title || item)}</option>`).join('')}</select></label><label>${esc(section.date_label || 'Preferred date')}<input name="date" type="date" required></label>${items(section.fields).map(formFieldMarkup).join('')}<button class="primary-button">${esc(section.button || 'Request appointment')}</button></form></section>`;
  if(section.type === 'gallery') return `<section id="${id}">${title}<div class="gallery">${items(section.items).map((item,n) => `<div class="gallery-item" aria-label="${esc(item.title || `Image ${n+1}`)}">${esc(item.emoji || '✦')}</div>`).join('')}</div></section>`;
  if(section.type === 'testimonials') return `<section id="${id}">${title}<div class="grid">${items(section.items).map(item => `<blockquote class="card"><p>“${esc(item.text)}”</p><strong>${esc(item.name)}</strong></blockquote>`).join('')}</div></section>`;
  if(section.type === 'faq') return `<section id="${id}" class="faq">${title}${items(section.items).map(item => `<details><summary>${esc(item.question)}</summary><p>${esc(item.answer)}</p></details>`).join('')}</section>`;
  if(section.type === 'loyalty') return `<section id="${id}">${title}<div class="card"><span class="pill">${esc(section.label || 'Member benefits')}</span><h3>${esc(section.headline || 'Your loyalty card')}</h3><p>${esc(section.text || '')}</p><div class="price">${esc(section.points || '0 points')}</div></div></section>`;
  if(section.type === 'form') return `<section id="${id}">${title}<form class="contact-form" data-local-form data-backend-collection="${esc(collectionName(section.collection,'submissions'))}">${items(section.fields).map(formFieldMarkup).join('')}<button class="primary-button">${esc(section.button || 'Send')}</button></form></section>`;
  if(section.type === 'contact') return `<section id="${id}">${title}<div class="grid"><div class="card"><h3>${esc(section.company || app.title)}</h3><p>${esc(section.address || '')}</p>${section.phone ? `<p><a href="tel:${esc(section.phone)}">${esc(section.phone)}</a></p>` : ''}${section.email ? `<p><a href="mailto:${esc(section.email)}">${esc(section.email)}</a></p>` : ''}</div></div></section>`;
  return `<section id="${id}" class="${section.type === 'notice' ? 'notice' : ''}">${title}<p>${esc(section.text || section.description || '')}</p></section>`;
}