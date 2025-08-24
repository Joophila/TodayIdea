let rawData = null;

function esc(s){return (s||'').replace(/[&<>]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[m]))}

function renderToday(d){
  const el = document.getElementById('todayBody');
  if(!d || !d.ideas || !d.ideas.length){ el.textContent='데이터 없음'; return; }
  const top = d.ideas[0];
  const html = `
    <div class="grid cols-2">
      <div>
        <div class="badge">${esc(top.category||'generic')}</div>
        <h3>${esc(top.one_liner||top.title)}</h3>
        <p>${esc(top.summary||'')}</p>
        <div class="kv"><div class="k">점수</div><div class="v"><b>${top.score?.total ?? ''}</b> / 100</div></div>
        <div class="kv"><div class="k">왜 지금</div><div class="v">${esc(top.why_now||'알 수 없습니다')}</div></div>
        <div class="kv"><div class="k">진입 전략</div><div class="v">${esc(top.gtm_tactics||'알 수 없습니다')}</div></div>
      </div>
      <div>
        <div class="sec-title">트렌드(최근)</div>
        <div class="chart-box"><canvas id="todayChart" height="160"></canvas></div>
        <div class="sec-title">커뮤니티 반응</div>
        <ul class="source-list small">
          ${(top.community_top||[]).map(x=>`<li><a href="${x.url}" target="_blank">${esc(x.title||x.url)}</a> <span class="small">(${esc(x.source||'')})</span></li>`).join('')}
        </ul>
      </div>
    </div>
  `;
  el.innerHTML = html;
  if (top.trend_series && top.trend_series.length){
    const ctx = document.getElementById('todayChart');
    new Chart(ctx,{
      type:'line',
      data:{
        labels: top.trend_series.map(p=>p.date),
        datasets:[{label: '검색 지수', data: top.trend_series.map(p=>p.value)}]
      },
      options:{responsive:true, plugins:{legend:{display:false}}, scales:{x:{display:false}}}
    });
  }
}

function renderList(d){
  const list = document.getElementById('ideasList');
  const filter = (document.getElementById('filterInput').value||'').toLowerCase();
  const cat = document.getElementById('categorySel').value || '';
  let items = (d.ideas||[]).slice();
  items = items.filter(it => (!cat || it.category===cat) && (it.title+it.category+(it.tags||[]).join(',')).toLowerCase().includes(filter));
  list.innerHTML = items.map((it, idx)=>`
    <article class="card idea-card">
      <header>
        <div>
          <div class="badge">${esc(it.category||'generic')}</div>
          <strong>${esc(it.title)}</strong>
          <span class="small">· 점수 ${it.score?.total ?? ''}</span>
        </div>
        <div class="small">순위 ${idx+1}</div>
      </header>
      <div class="body">
        <div class="grid cols-3">
          <div>
            <div class="sec-title">한줄 요약</div>
            <p>${esc(it.one_liner||'알 수 없습니다')}</p>
            <div class="sec-title">설명</div>
            <p>${esc(it.summary||'알 수 없습니다')}</p>
            <div class="sec-title">왜 지금</div>
            <p>${esc(it.why_now||'알 수 없습니다')}</p>
          </div>
          <div>
            <div class="sec-title">진입 전략</div>
            <p>${esc(it.gtm_tactics||'알 수 없습니다')}</p>
            <div class="sec-title">시장</div>
            <p>${esc(it.market||'알 수 없습니다')}</p>
            <div class="sec-title">리스크</div>
            <p>${esc(it.risks||'알 수 없습니다')}</p>
          </div>
          <div>
            <div class="sec-title">트렌드</div>
            <div class="chart-box"><canvas id="chart_${idx}" height="120"></canvas></div>
            <div class="sec-title">커뮤니티 상위</div>
            <ul class="source-list small">
              ${(it.community_top||[]).slice(0,4).map(x=>`<li><a href="${x.url}" target="_blank">${esc(x.title||x.url)}</a> <span class="small">(${esc(x.source||'')})</span></li>`).join('')}
            </ul>
            <div class="sec-title">출처</div>
            <ul class="source-list small">
              ${(it.sources||[]).slice(0,5).map(s=>`<li><a href="${s.url}" target="_blank">${esc(s.title||s.url)}</a> <span class="small">(${esc(s.publisher||'' )})</span></li>`).join('')}
            </ul>
          </div>
        </div>
      </div>
    </article>
  `).join('');

  // attach charts
  items.forEach((it, idx)=>{
    const el = document.getElementById('chart_'+idx);
    if (el && it.trend_series && it.trend_series.length){
      new Chart(el,{
        type:'line',
        data:{
          labels: it.trend_series.map(p=>p.date),
          datasets:[{label: '검색 지수', data: it.trend_series.map(p=>p.value)}]
        },
        options:{responsive:true, plugins:{legend:{display:false}}, scales:{x:{display:false}}}
      });
    }
  });
}

async function loadData(){
  const res = await fetch('ideas.json?cache='+Date.now());
  const data = await res.json();
  rawData = data;
  document.getElementById('lastUpdated').textContent = 'Last updated: ' + (data.generated_at||'');
  // categories
  const cats = [...new Set((data.ideas||[]).map(x=>x.category||'generic'))];
  const sel = document.getElementById('categorySel');
  sel.innerHTML = '<option value="">모든 카테고리</option>' + cats.map(c=>`<option>${c}</option>`).join('');
  renderToday(data);
  renderList(data);
}

document.getElementById('reloadBtn').addEventListener('click', loadData);
document.getElementById('filterInput').addEventListener('input', ()=>renderList(rawData));
document.getElementById('categorySel').addEventListener('change', ()=>renderList(rawData));

loadData();
