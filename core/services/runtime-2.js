function calculateProfile(){
  const profile = {};
  items(quiz?.questions).forEach(question => {
    const chosen = state.answers?.[question.id];
    const option = items(question.options).find(candidate => String(candidate.label) === String(chosen));
    Object.entries(option?.scores || {}).forEach(([trait, score]) => {
      profile[trait] = (profile[trait] || 0) + Number(score || 0);
    });
  });
  state.profile = profile;
  state.xp = Object.keys(state.answers || {}).length * Number(quiz?.xp_per_answer || 100);
  return profile;
}
function similarity(profile, traits){
  const keys = [...new Set([...Object.keys(profile || {}), ...Object.keys(traits || {})])];
  const dot = keys.reduce((sum,key) => sum + Number(profile[key] || 0) * Number(traits[key] || 0), 0);
  const a = Math.sqrt(keys.reduce((sum,key) => sum + Math.pow(Number(profile[key] || 0),2), 0));
  const b = Math.sqrt(keys.reduce((sum,key) => sum + Math.pow(Number(traits[key] || 0),2), 0));
  if(!a || !b) return 0;
  return Math.max(1, Math.min(99, Math.round((dot/(a*b))*100)));
}
function calculateResults(){
  const profile = calculateProfile();
  state.results = items(quiz?.catalog).map((item,index) => ({
    ...item, _id:`${item.brand || ''}-${item.model || index}`, match:similarity(profile,item.traits || {})
  })).sort((a,b) => b.match-a.match);
  saveState();
  return state.results;
}
function traitLabel(value){ return String(value || '').replace(/[-_]/g,' ').replace(/\b\w/g, letter => letter.toUpperCase()); }
function heroMarkup(){
  const level = levelInfo();
  return `<section class="hero"><span class="eyebrow">${esc(quiz?.title || app.title || 'A+ Experience')}</span><h1>${esc(hero.title || app.title)}</h1><p class="lead">${esc(hero.text || app.tagline || '')}</p><button class="cta" data-action="start-quiz">${esc(quiz?.start_label || copy.start)}</button></section>
  <section class="mission-card"><div class="mission-copy"><span class="pill">${copy.level} ${level.number}</span><h2>${esc(quiz?.intro || app.tagline || '')}</h2><p>${Object.keys(state.answers || {}).length ? `${Object.keys(state.answers).length}/${items(quiz?.questions).length} ${copy.completed}` : esc(app.tagline || '')}</p></div><div class="level-orb"><div><small>${copy.xp}</small>${Number(state.xp || 0)}</div></div></section>
  <div class="stat-grid"><div class="stat"><strong>${Object.keys(state.answers || {}).length}</strong><span>${copy.completed}</span></div><div class="stat"><strong>${Number(state.xp || 0)}</strong><span>${copy.xp}</span></div><div class="stat"><strong>${state.favorites?.length || 0}</strong><span>${copy.favorites}</span></div></div>`;
}
function quizMarkup(){
  const questions = items(quiz?.questions);
  if(!questions.length) return `<section class="empty-state"><h2>${copy.noResults}</h2></section>`;
  const step = Math.max(0, Math.min(Number(state.step || 0), questions.length-1));
  state.step = step;
  const question = questions[step], selected = state.answers?.[question.id];
  const progress = Math.round(((step+1)/questions.length)*100);
  return `<section class="quiz-shell"><div class="progress-head"><span>${step+1} / ${questions.length}</span><span>${Number(state.xp || 0)} ${copy.xp}</span></div><div class="progress-track"><div class="progress-bar" style="width:${progress}%"></div></div><div class="question-card"><span class="pill">${progress}%</span><h2>${esc(question.prompt)}</h2><p class="question-hint">${esc(question.hint || '')}</p><div class="option-grid">${items(question.options).map(option => `<button class="option ${String(selected)===String(option.label)?'selected':''}" data-answer="${esc(option.label)}"><span class="option-emoji">${esc(option.emoji || '✦')}</span><strong>${esc(option.label)}</strong></button>`).join('')}</div><div class="quiz-actions"><button class="secondary-button" data-action="quiz-back" ${step===0?'disabled':''}>${copy.back}</button><button class="primary-button" data-action="quiz-next" ${selected?'':'disabled'}>${step===questions.length-1?copy.finish:copy.next}</button></div></div></section>`;
}
function resultCard(item,index){
  const favorite = items(state.favorites).includes(item._id);
  return `<article class="match-card"><div class="match-rank">${esc(item.emoji || ['🥇','🥈','🥉'][index] || '✦')}</div><div><div class="match-head"><div><span class="pill">#${index+1}</span><h3>${esc([item.brand,item.model].filter(Boolean).join(' '))}</h3><p>${esc(item.subtitle || item.description || '')}</p></div><div class="match-score">${item.match}%<small> ${copy.match}</small></div></div>${item.description ? `<p>${esc(item.description)}</p>` : ''}<div class="note-list">${items(item.notes).map(note => `<span class="note">${esc(note)}</span>`).join('')}</div><div class="badge-list">${items(item.badges).map(badge => `<span class="badge">${esc(badge)}</span>`).join('')}</div></div><button class="favorite ${favorite?'active':''}" data-favorite="${esc(item._id)}" aria-label="${copy.favorites}">${favorite?'♥':'♡'}</button></article>`;
}
