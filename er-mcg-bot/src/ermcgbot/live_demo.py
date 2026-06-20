"""Generates a self-contained, animated 'live' demo of the screening bot.

Produces a single HTML file (no server, no dependencies, no network) that
simulates the ED trackboard filling up over time. As each synthetic patient
'arrives', the bot scans them with the same criteria logic used by the Python
engine and — for patients who meet criteria — fires a dry-run secure message
to the on-call physician. Open the file in any browser to watch it run.

Data and criteria are embedded from the same JSON the Python engine uses, so
the live demo and the backend never drift apart.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List

_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ED Admission-Screening Bot — Live Demo</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: system-ui, -apple-system, sans-serif;
         background: #0c1120; color: #e6ebf5; }
  .banner { background: #3a2e05; color: #ffd77a; border-bottom: 1px solid #6b5410;
            padding: 8px 16px; font-size: 13px; text-align: center; }
  header { padding: 14px 20px 0; }
  h1 { font-size: 20px; margin: 0; }
  .sub { color: #8a97b0; font-size: 13px; margin-top: 2px; }
  .controls { padding: 10px 20px; display: flex; gap: 10px; align-items: center; }
  button { background: #2563eb; color: #fff; border: 0; padding: 9px 16px;
           border-radius: 8px; font-size: 14px; cursor: pointer; font-weight: 600; }
  button.ghost { background: #1c2740; color: #cdd8ef; }
  button:disabled { opacity: .5; cursor: default; }
  .stats { display: flex; gap: 12px; padding: 4px 20px 14px; flex-wrap: wrap; }
  .stat { background: #131c33; border: 1px solid #213055; border-radius: 10px;
          padding: 10px 16px; min-width: 120px; }
  .stat .n { font-size: 26px; font-weight: 700; }
  .stat .l { color: #8a97b0; font-size: 12px; }
  .stat.flag .n { color: #34d399; }
  .grid { display: grid; grid-template-columns: 1.5fr 1fr; gap: 16px;
          padding: 0 20px 24px; align-items: start; }
  @media (max-width: 860px) { .grid { grid-template-columns: 1fr; } }
  .panel { background: #0f1830; border: 1px solid #1d2b4d; border-radius: 12px;
           overflow: hidden; }
  .panel h2 { font-size: 12px; text-transform: uppercase; letter-spacing: .06em;
              color: #8a97b0; margin: 0; padding: 12px 14px; background: #111c38;
              border-bottom: 1px solid #1d2b4d; }
  .board-row { display: grid; grid-template-columns: 56px 1fr auto;
               gap: 10px; align-items: center; padding: 10px 14px;
               border-bottom: 1px solid #15203c; animation: fadein .35s ease; }
  @keyframes fadein { from { opacity: 0; transform: translateY(6px);} to {opacity:1;} }
  .bed { background: #1c2740; border-radius: 6px; text-align: center;
         padding: 6px 0; font-weight: 700; font-size: 13px; color: #9fb3e0; }
  .who { font-size: 14px; } .who small { color: #8a97b0; display: block; font-size: 12px; }
  .pill { font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 999px; }
  .pill.scan { background: #3a2e05; color: #ffd77a; }
  .pill.clear { background: #16261c; color: #7fdca6; }
  .pill.flag { background: #34d399; color: #06281b; }
  .board-row.flagged { background: #0f2418; }
  .board-row.scanning { box-shadow: inset 3px 0 0 #ffd77a; }
  .feed, .msgs { max-height: 360px; overflow-y: auto; }
  .feed-item { padding: 8px 14px; border-bottom: 1px solid #15203c; font-size: 12px;
               color: #aeb9d2; animation: fadein .3s ease; }
  .feed-item .t { color: #5d6b88; }
  .msg { margin: 10px; border: 1px solid #234; border-radius: 10px; overflow: hidden;
         animation: fadein .35s ease; }
  .msg .head { background: #132a44; padding: 8px 12px; font-size: 12px;
               display: flex; justify-content: space-between; color: #bcd0ef; }
  .msg .body { padding: 10px 12px; font-size: 13px; white-space: pre-wrap;
               line-height: 1.4; }
  .msg .crit { color: #34d399; }
  .dry { font-size: 10px; color: #ffd77a; border: 1px solid #6b5410; border-radius: 4px;
         padding: 1px 6px; }
  .empty { padding: 16px; color: #5d6b88; font-size: 13px; }
</style>
</head>
<body>
  <div class="banner">DEMO &middot; synthetic data, no PHI &middot; criteria are illustrative (NOT MCG) &middot;
    messages are DRY-RUN, nothing is sent &middot; physician makes every decision</div>
  <header>
    <h1>ED Admission-Screening Bot — Live</h1>
    <div class="sub">Patients arrive on the trackboard; the bot scans each one and alerts the on-call physician.</div>
  </header>
  <div class="controls">
    <button id="start">&#9654; Start shift</button>
    <button id="reset" class="ghost">Reset</button>
    <button id="speed" class="ghost">Speed: 1&times;</button>
  </div>
  <div class="stats">
    <div class="stat"><div class="n" id="s-board">0</div><div class="l">On board</div></div>
    <div class="stat"><div class="n" id="s-scan">0</div><div class="l">Scanned</div></div>
    <div class="stat flag"><div class="n" id="s-flag">0</div><div class="l">Met criteria</div></div>
    <div class="stat"><div class="n" id="s-msg">0</div><div class="l">Alerts sent (dry-run)</div></div>
  </div>
  <div class="grid">
    <div class="panel">
      <h2>ED Trackboard</h2>
      <div id="board"><div class="empty">Press “Start shift” to begin…</div></div>
    </div>
    <div>
      <div class="panel" style="margin-bottom:16px;">
        <h2>Secure messages → on-call physician</h2>
        <div id="msgs" class="msgs"><div class="empty">No alerts yet.</div></div>
      </div>
      <div class="panel">
        <h2>Bot activity log</h2>
        <div id="feed" class="feed"><div class="empty">Idle.</div></div>
      </div>
    </div>
  </div>

<script>
const PATIENTS = __PATIENTS__;
const CRITERIA = __CRITERIA__;
const ONCALL   = __ONCALL__;

// --- criteria engine (mirrors src/ermcgbot/criteria_engine.py) ---
function getPath(obj, path){
  return path.split('.').reduce((o,k)=> (o && o[k] !== undefined) ? o[k] : undefined, obj);
}
const OPS = {
  '>=': (a,b)=> a!==undefined && a>=b, '>': (a,b)=> a!==undefined && a>b,
  '<=': (a,b)=> a!==undefined && a<=b, '<': (a,b)=> a!==undefined && a<b,
  '==': (a,b)=> a===b, '!=': (a,b)=> a!==b,
  'in': (a,b)=> Array.isArray(b) && b.includes(a),
  'not_in': (a,b)=> Array.isArray(b) && !b.includes(a),
  'exists': (a,b)=> (a!==undefined)===Boolean(b)
};
function cond(p,c){ return OPS[c.op](getPath(p,c.field), c.value); }
function desc(c){ return c.field+' '+c.op+' '+c.value; }
function matchRule(p, r){
  const hits=[];
  for(const c of (r.all_of||[])){ if(!cond(p,c)) return null; hits.push(desc(c)); }
  if(r.any_of && r.any_of.length){
    const any = r.any_of.filter(c=>cond(p,c));
    if(!any.length) return null;
    any.forEach(c=>hits.push(desc(c)));
  }
  if(!(r.all_of||[]).length && !(r.any_of||[]).length) return null;
  return {id:r.id,label:r.label,status:r.recommended_status,service:r.service,hits};
}
function screen(p){ return CRITERIA.rulesets.map(r=>matchRule(p,r)).filter(Boolean); }

// --- UI / simulation ---
const $=id=>document.getElementById(id);
let speed=1, timers=[], state={board:0,scan:0,flag:0,msg:0};
const SPEEDS=[1,2,4];

function clock(){ const d=new Date(); return d.toLocaleTimeString(); }
function bump(k,el){ state[k]++; $(el).textContent=state[k]; }
function feed(html){
  const f=$('feed'); if(f.querySelector('.empty')) f.innerHTML='';
  const d=document.createElement('div'); d.className='feed-item';
  d.innerHTML='<span class="t">'+clock()+'</span> &middot; '+html;
  f.prepend(d);
}
function reset(){
  timers.forEach(clearTimeout); timers=[];
  state={board:0,scan:0,flag:0,msg:0};
  ['s-board','s-scan','s-flag','s-msg'].forEach(i=>$(i).textContent='0');
  $('board').innerHTML='<div class="empty">Press “Start shift” to begin…</div>';
  $('msgs').innerHTML='<div class="empty">No alerts yet.</div>';
  $('feed').innerHTML='<div class="empty">Idle.</div>';
  $('start').disabled=false;
}
function addMessage(p, matches){
  const m=$('msgs'); if(m.querySelector('.empty')) m.innerHTML='';
  const primary=matches[0];
  const contact=ONCALL[primary.service]||{physician:'On-Call Hospitalist',handle:'hospitalist-oncall'};
  const crit=matches.map(x=>'  • '+x.label+' → recommend '+x.status).join('\n');
  const el=document.createElement('div'); el.className='msg';
  el.innerHTML='<div class="head"><span>To: '+contact.physician+' &lt;'+contact.handle+'&gt;</span>'
    +'<span class="dry">DRY-RUN</span></div>'
    +'<div class="body">'+p.name+'  MRN '+p.mrn+'  ('+p.age+p.sex+')  ·  '+p.bed+'\n'
    +p.chief_complaint+'\n<span class="crit">'+crit+'</span>\n\n'
    +'Reply ADMIT / DECLINE — decision support only.</div>';
  m.prepend(el);
}
function schedule(fn,ms){ const t=setTimeout(fn, ms/speed); timers.push(t); }

function run(){
  $('start').disabled=true;
  $('board').innerHTML='';
  feed('Bot online. Connecting to ED feed (simulated FHIR/ADT).');
  let delay=600;
  PATIENTS.patients.forEach((p,i)=>{
    schedule(()=>{
      // arrival
      const row=document.createElement('div'); row.className='board-row scanning';
      row.id='row-'+i;
      row.innerHTML='<div class="bed">'+p.bed+'</div>'
        +'<div class="who">'+p.name+'<small>'+p.chief_complaint+' · MRN '+p.mrn+'</small></div>'
        +'<div><span class="pill scan" id="pill-'+i+'">scanning…</span></div>';
      $('board').appendChild(row);
      bump('board','s-board');
      feed('Patient arrived: <b>'+p.name+'</b> ('+p.bed+') — scanning against criteria.');
      // scan completes shortly after arrival
      schedule(()=>{
        const matches=screen(p);
        bump('scan','s-scan');
        row.classList.remove('scanning');
        const pill=$('pill-'+i);
        if(matches.length){
          row.classList.add('flagged');
          pill.className='pill flag'; pill.textContent='MEETS CRITERIA';
          bump('flag','s-flag');
          feed('✅ <b>'+p.name+'</b> meets: '+matches.map(m=>m.label).join(', ')+' — alerting on-call.');
          schedule(()=>{ addMessage(p,matches); bump('msg','s-msg');
            feed('📨 Secure dry-run alert sent to '+(ONCALL[matches[0].service]||{physician:'on-call'}).physician+'.'); }, 500);
        } else {
          pill.className='pill clear'; pill.textContent='no criteria';
          feed('—  '+p.name+': no admission criteria met.');
        }
      }, 700);
    }, delay);
    delay += 1300;
  });
  schedule(()=>feed('Shift pass complete. '+state.flag+' of '+state.board+' patients flagged for admit review.'), delay+200);
}

$('start').onclick=run;
$('reset').onclick=reset;
$('speed').onclick=()=>{ speed=SPEEDS[(SPEEDS.indexOf(speed)+1)%SPEEDS.length];
  $('speed').textContent='Speed: '+speed+'×'; };
</script>
</body>
</html>
"""


def render_live_html(
    patients_raw: Dict[str, Any],
    criteria_raw: Dict[str, Any],
    on_call_raw: Dict[str, Any],
) -> str:
    """Build the animated demo by embedding the same JSON the engine uses."""
    return (
        _TEMPLATE.replace("__PATIENTS__", json.dumps(patients_raw))
        .replace("__CRITERIA__", json.dumps(criteria_raw))
        .replace("__ONCALL__", json.dumps(on_call_raw["on_call"]))
    )


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)
