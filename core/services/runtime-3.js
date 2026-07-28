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
function pageMarkup(){
  if(!quiz) return `<section class="hero"><h1>${esc(hero.title || app.title)}</h1><p class="lead">${esc(hero.text || app.tagline)}</p></section>${standardSections.map(standardSection).join('')}`;
  if(state.view === 'quiz') return quizMarkup();
  if(state.view === 'results') return resultsMarkup(false);
  if(state.view === 'profile') return profileMarkup();
  if(state.view === 'favorites') return resultsMarkup(true);
  return `<div class="experience-home">${heroMarkup()}</div>${standardSections.map(standardSection).join('')}`;
}
function navMarkup(){
  if(!quiz) return '';
  const entries = [['home',copy.home],['quiz',copy.quiz],['results',copy.results],['profile',copy.profile],['favorites',copy.favorites]];
  return `<nav class="bottom-nav">${entries.map(([view,label]) => `<button data-view="${view}" class="${state.view===view?'active':''}">${esc(label)}</button>`).join('')}</nav>`;
}
function render(){
  const level = levelInfo();
  document.getElementById('app').innerHTML = `<header class="topbar"><div class="brand"><div class="brand-mark">A+</div><span>${esc(app.title || 'App')}</span></div><div class="top-actions"><span class="xp-chip">${Number(state.xp || 0)} ${copy.xp} · ${esc(level.label)}</span><button id="install" class="install hidden">${copy.install}</button></div></header><main>${pageMarkup()}</main>${navMarkup()}`;
  bind(); window.scrollTo({top:0,behavior:'smooth'});
}
function bind(){
  document.querySelectorAll('[data-view]').forEach(button => button.addEventListener('click', () => {state.view=button.dataset.view;saveState();render();}));
  document.querySelectorAll('[data-action="start-quiz"]').forEach(button => button.addEventListener('click', () => {state.view='quiz';state.step=Math.min(Object.keys(state.answers || {}).length,Math.max(0,items(quiz?.questions).length-1));saveState();render();}));
  document.querySelectorAll('[data-answer]').forEach(button => button.addEventListener('click', () => {const question=items(quiz?.questions)[state.step];if(!question)return;state.answers={...state.answers,[question.id]:button.dataset.answer};calculateProfile();saveState();render();}));
  document.querySelectorAll('[data-action="quiz-back"]').forEach(button => button.addEventListener('click', () => {state.step=Math.max(0,state.step-1);saveState();render();}));
  document.querySelectorAll('[data-action="quiz-next"]').forEach(button => button.addEventListener('click', () => {const questions=items(quiz?.questions),question=questions[state.step];if(!question||!state.answers?.[question.id])return;if(state.step>=questions.length-1){calculateResults();state.view='results';}else{state.step+=1;}saveState();render();}));
  document.querySelectorAll('[data-action="retake"]').forEach(button => button.addEventListener('click', () => {state={...blankState,view:'quiz',favorites:state.favorites||[]};saveState();render();}));
  document.querySelectorAll('[data-favorite]').forEach(button => button.addEventListener('click', () => {const id=button.dataset.favorite,current=new Set(items(state.favorites));current.has(id)?current.delete(id):current.add(id);state.favorites=[...current];saveState();toast(copy.saved);render();}));
  document.querySelectorAll('[data-local-form]').forEach(form => form.addEventListener('submit', event => {event.preventDefault();toast(lang.startsWith('de')?'Danke! Deine Anfrage wurde gespeichert.':'Thanks! Your request was saved.');form.reset();}));
  document.getElementById('install')?.addEventListener('click', async () => {if(deferredPrompt){deferredPrompt.prompt();await deferredPrompt.userChoice;deferredPrompt=null;}});
  if(deferredPrompt) document.getElementById('install')?.classList.remove('hidden');
}
window.addEventListener('beforeinstallprompt', event => {event.preventDefault();deferredPrompt=event;document.getElementById('install')?.classList.remove('hidden');});
render();
if('serviceWorker' in navigator) window.addEventListener('load', () => navigator.serviceWorker.register('sw.js'));
})();
