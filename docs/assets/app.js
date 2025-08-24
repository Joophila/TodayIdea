let rawData=null, REPO_PATH=null;
function esc(s){return (s||'').replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[m]))}
function formatCitations(html, id){return (html||'').replace(/\[(\d+)\]/g,(_,n)=>`<sup class="cite"><a href="#ev_${id}_${n}">[${n}]</a></sup>`)}
async function loadConfig(){try{const r=await fetch('config.json?cache='+Date.now()); const c=await r.json(); REPO_PATH=c.repo_path||null;}catch(e){}}
function updateNow(){ if(!REPO_PATH){alert('docs/config.json에서 repo_path 설정'); return;} window.open(`https://github.com/${REPO_PATH}/actions/workflows/update.yml`,'_blank');}
function renderToday(d){const el=document.getElementById('todayBody'); if(!d||!d.ideas||!d.ideas.length){el.textContent='데이터 없음';return;} const top=d.ideas[0], id='today';
  el.innerHTML=`<div class="grid cols-2"><div>
  <div class="badge">${esc(top.category||'generic')}</div><h3>${esc(top.one_liner||top.title)}</h3>
  <div class="small">설명</div><p>${formatCitations(esc(top.summary||''),id)}</p>
  <div class="small">왜 지금</div><p>${formatCitations(esc(top.why_now||''),id)}</p>
  <div class="small">진입 전략</div><p>${formatCitations(esc((top.gtm_tactics||[]).join(' · ')),id)}</p>
  </div><div><div class="chart-box"><canvas id="todayChart" height="160"></canvas></div>
  <div class="small">커뮤니티 상위</div><ul class="small">${(top.community_top||[]).slice(0,6).map(x=>`<li><a href="${x.url}" target="_blank">${esc(x.title||x.url)}</a></li>`).join('')}</ul></div></div>
  <div class="small">Evidence</div><ol>${(top.evidence||[]).map((e,i)=>`<li id="ev_${id}_${i+1}"><a href="${e.url}" target="_blank">${esc(e.title||e.url)}</a></li>`).join('')}</ol>`;
  if(top.trend_series&&top.trend_series.length&&window.Chart){const ctx=document.getElementById('todayChart'); new Chart(ctx,{type:'line',data:{labels:top.trend_series.map(p=>p.date),datasets:[{label:'검색 지수',data:top.trend_series.map(p=>p.value)}]},options:{responsive:true,plugins:{legend:{display:false}},scales:{x:{display:false}}}})}
}
function renderList(d){const list=document.getElementById('ideasList'); const f=(document.getElementById('filterInput').value||'').toLowerCase(); const c=document.getElementById('categorySel').value||'';
  let items=(d.ideas||[]).slice().filter(it=>(!c||it.category===c)&& (it.title+it.category+(it.tags||[]).join(',')).toLowerCase().includes(f));
  if(items.length===0){list.innerHTML='<div class="card">검색 조건에 맞는 아이디어가 없습니다.</div>';return;}
  list.innerHTML=items.map((it,idx)=>{const id=`i${idx}`; return `<article class="card idea-card"><header><div><div class="badge">${esc(it.category||'generic')}</div><strong>${esc(it.title)}</strong></div><div class="small">순위 ${idx+1}</div></header>
  <div class="body"><div class="grid cols-3"><div><div class="small">한줄 요약</div><p>${formatCitations(esc(it.one_liner||'알 수 없습니다'),id)}</p>
  <div class="small">설명</div><p>${formatCitations(esc(it.summary||'알 수 없습니다'),id)}</p><div class="small">왜 지금</div><p>${formatCitations(esc(it.why_now||'알 수 없습니다'),id)}</p></div>
  <div><div class="small">진입 전략</div><p>${formatCitations(esc((it.gtm_tactics||[]).join(' · ')||'알 수 없습니다'),id)}</p><div class="small">시장</div><p>${formatCitations(esc(it.market||'확실하지 않음'),id)}</p>
  <div class="small">리스크</div><p>${formatCitations(esc(it.risks||'확실하지 않음'),id)}</p><div class="small">검증 단계</div><p>${formatCitations(esc((it.validation_steps||[]).join(' · ')||'확실하지 않음'),id)}</p></div>
  <div><div class="chart-box"><canvas id="chart_${idx}" height="120"></canvas></div><div class="small">커뮤니티 상위</div>
  <ul class="small">${(it.community_top||[]).slice(0,5).map(x=>`<li><a href="${x.url}" target="_blank">${esc(x.title||x.url)}</a></li>`).join('')}</ul>
  <div class="small">Evidence</div><ol>${(it.evidence||[]).map((e,i)=>`<li id="ev_${id}_${i+1}"><a href="${e.url}" target="_blank">${esc(e.title||e.url)}</a></li>`).join('')}</ol></div></div></div></article>`}).join('');
  if(window.Chart){items.forEach((it,idx)=>{const el=document.getElementById('chart_'+idx); if(el&&it.trend_series&&it.trend_series.length){new Chart(el,{type:'line',data:{labels:it.trend_series.map(p=>p.date),datasets:[{label:'검색 지수',data:it.trend_series.map(p=>p.value)}]},options:{responsive:true,plugins:{legend:{display:false}},scales:{x:{display:false}}}})}})}
}
async function loadData(){await loadConfig(); const r=await fetch('ideas.json?cache='+Date.now()); const data=await r.json(); rawData=data;
  document.getElementById('lastUpdated').textContent='Last updated: '+(data.generated_at||''); const cats=[...new Set((data.ideas||[]).map(x=>x.category||'generic'))];
  const sel=document.getElementById('categorySel'); sel.innerHTML='<option value="">모든 카테고리</option>'+cats.map(c=>`<option>${c}</option>`).join('');
  renderToday(data); renderList(data);
}
window.addEventListener('DOMContentLoaded',()=>{document.getElementById('manualBtn').addEventListener('click', ()=>updateNow()); document.getElementById('reloadBtn').addEventListener('click', loadData);
  document.getElementById('filterInput').addEventListener('input', ()=>renderList(rawData||{ideas:[]})); document.getElementById('categorySel').addEventListener('change', ()=>renderList(rawData||{ideas:[]})); loadData();});
