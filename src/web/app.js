'use strict';
const $ = id => document.getElementById(id);
let market = null, range = '3M', selectedUnit = 'oz', points = [], cursor = 0, pending = false, lastSuccess = 0;
const money = n => Number.isFinite(n) ? new Intl.NumberFormat('en-US', {style:'currency',currency:'USD',maximumFractionDigits:2}).format(n) : '—';
const factor = () => selectedUnit === 'g' ? 1 / 31.1034768 : 1;
const dateLabel = value => new Date(value).toLocaleDateString(undefined,{month:'short',day:'numeric',year:'numeric'});
const stampLabel = value => new Date(value).toLocaleString(undefined,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit',timeZoneName:'short'});
const signed = n => `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`;

async function refresh() {
  if (pending) return;
  pending = true; $('refresh').disabled = true;
  try {
    const response = await fetch('/api/market', {signal:AbortSignal.timeout(20000),cache:'no-store'});
    if (!response.ok) throw new Error('Market feed temporarily unavailable');
    const data = await response.json();
    if (!Number.isFinite(data.price) || !data.history?.length) throw new Error('Incomplete quote');
    market = data; lastSuccess = Date.now(); render();
  } catch (_) {
    $('notice').hidden = false;
    $('notice').textContent = market ? 'Connection interrupted. Showing the last received prices; they may be out of date. Retrying automatically.' : 'The market feed is temporarily unavailable. Retrying automatically — or select Refresh data.';
    $('feedStatus').textContent = '● Feed unavailable'; $('feedStatus').className = 'feed-pill warning';
    if (!market) $('chartEmpty').textContent = 'Waiting for the market provider';
  } finally {pending = false; $('refresh').disabled = false;}
}

function render() {
  const f = factor();
  $('price').textContent = money(market.price * f); $('priceUnit').textContent = `USD / ${selectedUnit}`;
  for (const [id,key] of [['previous','previous_close'],['high','high'],['low','low']]) $(id).textContent = money(market[key]*f);
  $('change').textContent = `${market.change >= 0 ? '↗' : '↘'} ${money(Math.abs(market.change)*f)} (${signed(market.change_percent)})`;
  $('change').className = market.change >= 0 ? 'positive' : 'negative';
  $('feedStatus').textContent = market.stale ? '● Older quote' : '● Feed connected';
  $('feedStatus').className = `feed-pill${market.stale ? ' warning' : ''}`;
  $('notice').hidden = !market.stale;
  $('notice').textContent = market.feed_status === 'refresh_failed' ? 'Provider refresh failed. Showing the last successful quote. We will keep retrying.' : 'The latest available quote is older than 20 minutes. The market may be closed or the provider delayed. Check the quote timestamp below.';
  $('quoteTime').textContent = `Quote: ${stampLabel(market.quote_time)}`;
  $('download').disabled = false; $('chartEmpty').hidden = true;
  chart(); scenario(); calculator(); history();
}

function visiblePoints() {
  if (range === '1D') return market.intraday;
  const rows = market.history;
  const days = {'1W':7,'1M':30,'3M':90,'1Y':365,ALL:Infinity}[range];
  const cutoff = new Date(rows.at(-1).date).getTime() - days*86400000;
  return rows.filter(row => new Date(row.date).getTime() >= cutoff);
}

function chart() {
  if (!market) return;
  points = visiblePoints(); cursor = points.length-1;
  const svg = $('priceChart'), f = factor(), W = 900, H = 320, left = 20, right = 92, top = 24, bottom = 42;
  const prices = points.map(p=>p.close*f);
  let min = Math.min(...prices), max = Math.max(...prices), pad = Math.max((max-min)*.2, max*.0005);
  min-=pad; max+=pad;
  const x = i => left + i / Math.max(points.length-1,1)*(W-left-right);
  const y = value => top + (max-value)/(max-min)*(H-top-bottom);
  let markup = '<defs><linearGradient id="fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stop-color="#dcb56c" stop-opacity=".22"/><stop offset="100%" stop-color="#dcb56c" stop-opacity="0"/></linearGradient></defs>';
  for(let i=0;i<5;i++) {
    const value = min+(max-min)*i/4, yy=y(value);
    markup+=`<line x1="${left}" y1="${yy}" x2="${W-right}" y2="${yy}" stroke="#303236" stroke-dasharray="3 6"/><text x="${W-right+16}" y="${yy+4}" fill="#8c9296" font-size="11" font-family="sans-serif">${money(value)}</text>`;
  }
  const path=points.map((p,i)=>`${i===0?'M':'L'}${x(i).toFixed(2)},${y(p.close*f).toFixed(2)}`).join(' ');
  markup+=`<path d="${path} L${x(points.length-1)},${H-bottom} L${left},${H-bottom} Z" fill="url(#fill)"/><path d="${path}" fill="none" stroke="#e6bf79" stroke-width="2.4" stroke-linejoin="round"/>`;
  const ticks=Math.min(6,points.length);
  for(let i=0;i<ticks;i++) {
    const idx=Math.round(i/Math.max(ticks-1,1)*(points.length-1)), date=new Date(points[idx].date);
    const label=range==='1D'?date.toLocaleTimeString(undefined,{hour:'2-digit',minute:'2-digit'}):date.toLocaleDateString(undefined,{month:'short',day:'numeric'});
    markup+=`<text x="${x(idx)}" y="${H-14}" text-anchor="${i===0?'start':i===ticks-1?'end':'middle'}" fill="#8c9296" font-size="11" font-family="sans-serif">${label}</text>`;
  }
  markup+=`<circle cx="${x(points.length-1)}" cy="${y(prices.at(-1))}" r="4" fill="#e6bf79" stroke="#191b1e" stroke-width="2"/>`;
  svg.innerHTML=markup;
  svg.setAttribute('aria-label',`Gold futures ${range} chart, from ${money(prices[0])} to ${money(prices.at(-1))} per ${selectedUnit}.`);
  const change=(points.at(-1).close/points[0].close-1)*100;
  $('chartSubtitle').textContent=`${dateLabel(points[0].date)} – ${dateLabel(points.at(-1).date)} · ${signed(change)} over this period`;
  $('tooltip').hidden=true;
}
function showPoint(index) {
  if(!points.length) return;
  cursor=Math.max(0,Math.min(points.length-1,index));
  $('tooltip').textContent=`${range==='1D'?stampLabel(points[cursor].date):dateLabel(points[cursor].date)} · ${money(points[cursor].close*factor())} / ${selectedUnit}`;
  $('tooltip').hidden=false;
}
function scenario() {
  const days=Number($('horizon').value); $('horizonValue').textContent=`${days} ${days===1?'day':'days'}`;
  if(!market) return;
  const rows=market.history.slice(-61), returns=rows.slice(1).map((row,i)=>Math.log(row.close/rows[i].close));
  const mean=returns.reduce((a,b)=>a+b,0)/returns.length;
  const vol=Math.sqrt(returns.reduce((a,b)=>a+(b-mean)**2,0)/(returns.length-1));
  const width=1.96*vol*Math.sqrt(days), price=market.price*factor();
  $('scenarioLow').textContent=money(price*Math.exp(-width)); $('scenarioMid').textContent=money(price); $('scenarioHigh').textContent=money(price*Math.exp(width));
}
function calculator() {
  const weight=Number($('weight').value);
  $('value').textContent=market && $('weight').value!=='' && weight>=0 && weight<=1000000 ? money(market.price*weight/($('weightUnit').value==='g'?31.1034768:1)):'—';
}
function history() {
  const rows=market.history;
  $('historyRows').replaceChildren(...rows.slice(-5).reverse().map(row=>{
    const idx=rows.indexOf(row), prior=rows[idx-1], change=prior?(row.close/prior.close-1)*100:0;
    const tr=document.createElement('tr');
    [dateLabel(row.date),money(row.open),money(row.high),money(row.low),money(row.close),signed(change)].forEach((value,i)=>{
      const td=document.createElement('td');td.textContent=value;if(i===5) td.className=change>=0?'positive':'negative';tr.append(td);
    });return tr;
  }));
}
$('refresh').addEventListener('click',refresh);
$('unit').addEventListener('change',e=>{selectedUnit=e.target.value;if(market) render();});
document.querySelectorAll('[data-range]').forEach(button=>button.addEventListener('click',()=>{
  range=button.dataset.range;document.querySelectorAll('[data-range]').forEach(b=>{b.classList.toggle('selected',b===button);b.setAttribute('aria-pressed',String(b===button));});chart();
}));
$('chart').addEventListener('pointermove',e=>{const box=$('priceChart').getBoundingClientRect();showPoint(Math.round(((e.clientX-box.left)/box.width*900-20)/788*(points.length-1)));});
$('chart').addEventListener('pointerleave',()=>$('tooltip').hidden=true);
$('chart').addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();showPoint(cursor+(e.key==='ArrowRight'?1:-1));}});
$('horizon').addEventListener('input',scenario);
$('weight').addEventListener('input',calculator);$('weightUnit').addEventListener('change',calculator);
$('download').addEventListener('click',()=>{
  if(!market)return;
  const csv='date,open_usd_per_oz,high_usd_per_oz,low_usd_per_oz,close_usd_per_oz\n'+market.history.map(r=>[r.date,r.open,r.high,r.low,r.close].join(',')).join('\n');
  const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));
  const a=document.createElement('a');a.href=url;a.download='auric-gold-futures-history.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
document.querySelectorAll('.nav-link').forEach(link=>link.addEventListener('click',()=>{document.querySelectorAll('.nav-link').forEach(a=>a.classList.toggle('active',a===link));}));
setInterval(()=>{
  $('clock').textContent=new Date().toLocaleTimeString(undefined,{hour:'2-digit',minute:'2-digit',timeZoneName:'short'});
  const seconds=lastSuccess?Math.max(0,60-Math.floor((Date.now()-lastSuccess)/1000)):0;
  $('countdown').textContent=pending?'Checking…':seconds?`Next check in ${seconds}s`:'Every 60 seconds';
},1000);
setInterval(()=>{if(!document.hidden)refresh();},60000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh();});
refresh();
