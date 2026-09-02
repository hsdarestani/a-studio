function resultsMarkup(favoritesOnly=false){
  const results = state.results?.length ? state.results : (Object.keys(state.answers || {}).length ? calculateResults() : []);
  const visible = favoritesOnly ? results.filter(item => items(state.favorites).includes(item._id)) : results;
  if(!visible.length) return `<section class="empty-state"><h2>${favoritesOnly?copy.noFavorites:copy.noResults}</h2><button class="primary-button" data-action="start-quiz">${copy.start}</button></section>`;
  return `${favoritesOnly?'':`<section class="result-hero"><span class="eyebrow">${copy.yourProfile}</span><h1>${esc(quiz?.result_title || copy.topMatches)}</h1><p class="lead">${esc(quiz?.result_intro || 'Your answers were compared with every option in the catalog.')}</p></section>`}<section><div class="match-list">${visible.slice(0,favoritesOnly?50:6).map(resultCard).join('')}</div>${favoritesOnly?'':`<button class="secondary-button" data-action="retake" style="margin-top:18px">${esc(quiz?.restart_label || copy.retake)}</button>`}</section>`;
}
function profileMarkup(){
  const profile = state.profile && Object.keys(state.profile).length ? state.profile : calculateProfile();
  const values = Object.values(profile).map(Number), max = Math.max(1,...values), level = levelInfo();
  return `<section><div class="profile-grid"><div><span class="pill">${copy.yourProfile}</span><h2>${copy.traits}</h2>${Object.keys(profile).length ? Object.entries(profile).sort((a,b)=>b[1]-a[1]).map(([trait,value]) => `<div class="trait"><div class="trait-head"><span>${esc(traitLabel(trait))}</span><span>${Math.round((Number(value)/max)*100)}%</span></div><div class="trait-track"><div class="trait-fill" style="width:${Math.round((Number(value)/max)*100)}%"></div></div></div>`).join('') : `<p>${copy.noResults}</p>`}</div><div class="card"><div class="level-orb"><div><small>${copy.level} ${level.number}</small>${esc(level.label)}</div></div><h3 style="margin-top:18px">${Number(state.xp || 0)} ${copy.xp}</h3><p>${Object.keys(state.answers || {}).length}/${items(quiz?.questions).length} ${copy.completed}</p><button class="secondary-button" data-action="retake">${copy.retake}</button></div></div></section>`;
}
function accountMarkup(){
  if(!hasAuth) return '';
  if(backendToken && state.backendProfile){
    const user = state.backendProfile || {};
    return `<section class="account-shell"><span class="pill">${copy.account}</span><h1>${copy.signedIn}</h1><div class="account-profile card"><div class="account-avatar">${esc(String(user.display_name || user.email || 'A').slice(0,1).toUpperCase())}</div><div><h3>${esc(user.display_name || user.email || '')}</h3><p>${esc(user.email || '')}</p></div></div><button class="secondary-button" data-backend-logout>${copy.logout}</button></section>`;
  }
  return `<section class="account-shell"><span class="pill">${copy.account}</span><h1>${copy.account}</h1><div class="auth-grid"><form class="auth-card card" data-backend-login><h3>${copy.login}</h3><label>${copy.email}<input type="email" name="email" autocomplete="email" required></label><label>${copy.password}<input type="password" name="password" autocomplete="current-password" minlength="8" required></label><button class="primary-button">${copy.login}</button></form><form class="auth-card card" data-backend-signup><h3>${copy.signup}</h3><label>${copy.name}<input name="display_name" autocomplete="name"></label><label>${copy.email}<input type="email" name="email" autocomplete="email" required></label><label>${copy.password}<input type="password" name="password" autocomplete="new-password" minlength="8" maxlength="128" required></label><button class="primary-button">${copy.signup}</button></form></div></section>`;
}
function pageMarkup(){
  if(state.view === 'account' && hasAuth) return accountMarkup();
  if(!quiz) return `<section class="hero"><h1>${esc(hero.title || app.title)}</h1><p class="lead">${esc(hero.text || app.tagline)}</p></section>${standardSections.map(standardSection).join('')}`;
  if(state.view === 'quiz') return quizMarkup();
  if(state.view === 'results') return resultsMarkup(false);
  if(state.view === 'profile') return profileMarkup();
  if(state.view === 'favorites') return resultsMarkup(true);
  return `<div class="experience-home">${heroMarkup()}</div>${standardSections.map(standardSection).join('')}`;
}
function navMarkup(){
  const entries = [];
  if(quiz) entries.push(['home',copy.home],['quiz',copy.quiz],['results',copy.results],['profile',copy.profile],['favorites',copy.favorites]);
  else if(hasAuth) entries.push(['home',copy.home]);
  if(hasAuth) entries.push(['account',copy.account]);
  if(!entries.length) return '';
  return `<nav class="bottom-nav">${entries.map(([view,label]) => `<button data-view="${view}" class="${state.view===view?'active':''}">${esc(label)}</button>`).join('')}</nav>`;
}
function render(){
  const level = levelInfo();
  const xp = quiz ? `<span class="xp-chip">${Number(state.xp || 0)} ${copy.xp} · ${esc(level.label)}</span>` : '';
  const accountAction = hasAuth ? `<button class="account-button" data-view="account" aria-label="${esc(copy.account)}">${backendToken?'●':'○'}</button>` : '';
  document.getElementById('app').innerHTML = `<header class="topbar"><div class="brand"><div class="brand-mark">A+</div><span>${esc(app.title || 'App')}</span></div><div class="top-actions">${xp}${accountAction}<button id="install" class="install hidden">${copy.install}</button></div></header><main>${pageMarkup()}</main>${navMarkup()}`;
  bind(); window.scrollTo({top:0,behavior:'smooth'});
}
async function handleBackendAuth(form, path){
  const button = form.querySelector('button');
  if(button) button.disabled = true;
  try{
    const data = Object.fromEntries(new FormData(form).entries());
    const payload = await backendRequest(path,{method:'POST',body:JSON.stringify(data)});
    setBackendSession(payload.token,payload.user);
    state.view='home'; saveState(); toast(copy.savedRemote); render();
  }catch(error){
    const code = String(error?.message || '');
    if(code==='email_in_use') toast(lang.startsWith('de')?'Diese E-Mail ist bereits registriert.':'This email is already registered.');
    else if(code==='invalid_credentials') toast(lang.startsWith('de')?'E-Mail oder Passwort stimmt nicht.':'Email or password is incorrect.');
    else toast(copy.requestFailed);
  }finally{
    if(button) button.disabled = false;
  }
}
async function managedFormPayload(form){
  const output = {};
  for(const [key,value] of new FormData(form).entries()){
    if(typeof File !== 'undefined' && value instanceof File){
      if(!value.size) continue;
      if(!hasStorage) throw new Error('storage_not_enabled');
      toast(copy.uploading);
      const uploaded = await uploadManagedFile(value);
      output[key] = uploaded ? {
        file_id: uploaded.id,
        name: uploaded.name,
        content_type: uploaded.content_type,
        size: uploaded.size,
        download_path: uploaded.download_path
      } : null;
    }else if(Object.prototype.hasOwnProperty.call(output,key)){
      output[key] = Array.isArray(output[key]) ? [...output[key], value] : [output[key], value];
    }else{
      output[key] = value;
    }
  }
  return output;
}
function bind(){
  document.querySelectorAll('[data-view]').forEach(button => button.addEventListener('click', () => {state.view=button.dataset.view;saveState();render();}));
  document.querySelectorAll('[data-action="start-quiz"]').forEach(button => button.addEventListener('click', () => {state.view='quiz';state.step=Math.min(Object.keys(state.answers || {}).length,Math.max(0,items(quiz?.questions).length-1));saveState();render();}));
  document.querySelectorAll('[data-answer]').forEach(button => button.addEventListener('click', () => {const question=items(quiz?.questions)[state.step];if(!question)return;state.answers={...state.answers,[question.id]:button.dataset.answer};calculateProfile();saveState();render();}));
  document.querySelectorAll('[data-action="quiz-back"]').forEach(button => button.addEventListener('click', () => {state.step=Math.max(0,state.step-1);saveState();render();}));
  document.querySelectorAll('[data-action="quiz-next"]').forEach(button => button.addEventListener('click', () => {const questions=items(quiz?.questions),question=questions[state.step];if(!question||!state.answers?.[question.id])return;if(state.step>=questions.length-1){calculateResults();state.view='results';}else{state.step+=1;}saveState();render();}));
  document.querySelectorAll('[data-action="retake"]').forEach(button => button.addEventListener('click', () => {const savedProfile=state.backendProfile;state={...blankState,view:'quiz',favorites:state.favorites||[],backendProfile:savedProfile};saveState();render();}));
  document.querySelectorAll('[data-favorite]').forEach(button => button.addEventListener('click', () => {const id=button.dataset.favorite,current=new Set(items(state.favorites));current.has(id)?current.delete(id):current.add(id);state.favorites=[...current];saveState();toast(copy.saved);render();}));
  document.querySelectorAll('[data-local-form]').forEach(form => form.addEventListener('submit', async event => {
    event.preventDefault();
    const needsRemote = hasDatabase || (hasStorage && !!form.querySelector('input[type="file"]'));
    if(!needsRemote){toast(lang.startsWith('de')?'Danke! Deine Anfrage wurde gespeichert.':'Thanks! Your request was saved.');form.reset();return;}
    if(!backendToken){state.view='account';saveState();render();toast(copy.authNeeded);return;}
    const button=form.querySelector('button');if(button)button.disabled=true;
    try{
      const data=await managedFormPayload(form);
      if(hasDatabase){
        const collection=collectionName(form.dataset.backendCollection,'submissions');
        await backendRequest(`/records/${encodeURIComponent(collection)}/`,{method:'POST',body:JSON.stringify({data})});
      }
      toast(copy.savedRemote);form.reset();
    }catch(_){toast(copy.requestFailed);}finally{if(button)button.disabled=false;}
  }));
  document.querySelector('[data-backend-login]')?.addEventListener('submit',event=>{event.preventDefault();handleBackendAuth(event.currentTarget,'/auth/login/');});
  document.querySelector('[data-backend-signup]')?.addEventListener('submit',event=>{event.preventDefault();handleBackendAuth(event.currentTarget,'/auth/signup/');});
  document.querySelector('[data-backend-logout]')?.addEventListener('click',()=>{clearBackendSession();state.view='home';saveState();render();});
  document.getElementById('install')?.addEventListener('click', async () => {if(deferredPrompt){deferredPrompt.prompt();await deferredPrompt.userChoice;deferredPrompt=null;}});
  if(deferredPrompt) document.getElementById('install')?.classList.remove('hidden');
}
window.addEventListener('beforeinstallprompt', event => {event.preventDefault();deferredPrompt=event;document.getElementById('install')?.classList.remove('hidden');});
render();
if(hasAuth && backendToken && !state.backendProfile){
  backendRequest('/auth/me/').then(payload=>{state.backendProfile=payload.user;saveState();if(state.view==='account')render();}).catch(()=>clearBackendSession());
}
if('serviceWorker' in navigator){
  window.addEventListener('load', async () => {
    const previewMode = location.pathname.includes('/preview/') || new URLSearchParams(location.search).has('preview');
    if(previewMode){
      const registrations = await navigator.serviceWorker.getRegistrations();
      await Promise.all(registrations.filter(registration => location.href.startsWith(registration.scope)).map(registration => registration.unregister()));
      if('caches' in window){
        const prefix = String(window.APP_CACHE_PREFIX || '');
        const keys = await caches.keys();
        await Promise.all(keys.filter(key => prefix && key.startsWith(prefix)).map(key => caches.delete(key)));
      }
      return;
    }
    const version = encodeURIComponent(String(window.APP_BUILD_VERSION || '1'));
    navigator.serviceWorker.register(`sw.js?v=${version}`);
  });
}
})();