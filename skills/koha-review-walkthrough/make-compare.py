#!/usr/bin/env python3
"""Build compare/index.html: before and after videos side by side.

usage: make-compare.py <walkthrough-dir>

<walkthrough-dir> holds:
  scenarios.json        {"meta": {"title", "before_label", "after_label"},
                         "scenarios": {ID: {"title","pre","what","prefs",
                                            "section","tag","note"}}}
  before/<ID>/*.webm    recorded on the unpatched instance
  after/<ID>/*.webm     recorded on the patched instance
"tag" is same | differs | new (green / red / blue dot); "note" is what the
reviewer saw. Scenario order is the order in scenarios.json. When a scenario
folder holds several takes, the newest wins.
Open compare/index.html directly, or run `python3 -m http.server` in the
walkthrough dir and open /compare/ if the browser blocks local video.
"""
import glob, json, os, sys

if len(sys.argv) != 2 or not os.path.isdir(sys.argv[1]):
    sys.exit(__doc__)
ROOT = os.path.abspath(sys.argv[1])
cfg = json.load(open(f'{ROOT}/scenarios.json'))
meta = cfg.get('meta', {})
baseline = cfg.get('baselinePrefs', {})


def newest(side, sid):
    fs = sorted(glob.glob(f'{ROOT}/{side}/{sid}/*.webm'), key=os.path.getmtime)
    return os.path.relpath(fs[-1], f'{ROOT}/compare') if fs else None


items = []
for sid, sc in cfg['scenarios'].items():
    items.append({
        'id': sid,
        'title': sc.get('title', sid),
        'pre': sc.get('pre', ''),
        'what': sc.get('what', ''),
        'prefs': sc.get('prefs', {}),
        'before': newest('before', sid),
        'after': newest('after', sid),
        'tag': sc.get('tag', ''),
        'note': sc.get('note', ''),
        'section': sc.get('section', ''),
    })

PAGE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--bg:#f6f7f9;--fg:#1d2733;--mut:#5c6b7a;--card:#fff;--line:#d7dde4;--before:#c77700;--after:#1b7fc4;--ok:#2a7f4f;--diff:#b3261e}
@media (prefers-color-scheme:dark){:root{--bg:#10161d;--fg:#e6ebf0;--mut:#9aa8b6;--card:#18212b;--line:#2b3744;--before:#ffb454;--after:#7fd1ff;--ok:#6fcf97;--diff:#ff8a80}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,sans-serif}
.app{display:grid;grid-template-columns:260px 1fr;min-height:100vh}
nav{border-right:1px solid var(--line);padding:12px;overflow:auto;max-height:100vh;position:sticky;top:0}
nav h1{font-size:16px;margin:4px 6px 10px}
nav button{display:flex;gap:8px;width:100%;text-align:left;background:none;border:0;color:inherit;padding:7px 8px;border-radius:6px;cursor:pointer;font:inherit}
nav button:hover{background:var(--card)}
nav button.on{background:var(--card);outline:2px solid var(--after)}
nav .id{font-weight:700;min-width:38px}
nav .t{flex:1;font-size:13px}
.dot{width:10px;height:10px;border-radius:50%;margin-top:5px;flex:none;background:var(--line)}
.sec{font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--mut);margin:14px 8px 4px;font-weight:700}.legend{font-size:12.5px;color:var(--mut);margin:0 6px 10px;line-height:1.9}.legend .dot{display:inline-block;margin:0 2px 0 0;vertical-align:middle}.dot.same{background:var(--ok)}.dot.differs{background:var(--diff)}.dot.new{background:var(--after)}
main{padding:14px 18px;min-width:0}
.bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:10px}
.bar button,.bar select{background:var(--card);color:inherit;border:1px solid var(--line);border-radius:6px;padding:6px 11px;font:inherit;cursor:pointer}
.bar button.on{border-color:var(--after);outline:1px solid var(--after)}
.bar .sp{flex:1}
h2{margin:2px 0 4px;font-size:20px}
.pre{color:var(--mut);margin:0 0 10px}
.vids{display:grid;gap:12px}
.vids.side{grid-template-columns:1fr 1fr}
.vids.seq,.vids.stack{grid-template-columns:1fr}
.pane{background:var(--card);border:1px solid var(--line);border-radius:8px;overflow:hidden}
.pane .lab{padding:6px 10px;font-weight:700;display:flex;justify-content:space-between}
.pane.b .lab{color:var(--before);border-bottom:3px solid var(--before)}
.pane.a .lab{color:var(--after);border-bottom:3px solid var(--after)}
video{width:100%;display:block;background:#000;aspect-ratio:16/9}
.none{aspect-ratio:16/9;display:grid;place-items:center;color:var(--mut);padding:20px;text-align:center}
.scrub{display:flex;gap:10px;align-items:center;margin:10px 0}
.scrub input{flex:1}
.scrub span{font-variant-numeric:tabular-nums;color:var(--mut);min-width:96px;text-align:right}
.note{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 14px;margin-top:6px}
.note b.tag{margin-right:6px}
.tag.same{color:var(--ok)}.tag.differs{color:var(--diff)}.tag.new{color:var(--after)}
code{background:var(--bg);padding:1px 5px;border-radius:4px}
.keys{color:var(--mut);font-size:12.5px;margin-top:10px}
@media(max-width:900px){.app{grid-template-columns:1fr}nav{position:static;max-height:none;border-right:0;border-bottom:1px solid var(--line)}.vids.side{grid-template-columns:1fr}}
</style></head><body>
<div class="app">
<nav><h1>__TITLE__</h1><div class="legend"><span class="dot same"></span> same outcome and flow &nbsp; <span class="dot differs"></span> outcome or flow differs &nbsp; <span class="dot new"></span> only possible after</div><div id="list"></div></nav>
<main>
 <div class="bar">
  <button id="bPlay">Play</button><button id="bRestart">Restart</button>
  <button id="mSide" class="on">Side by side</button><button id="mStack">Stacked (full width)</button><button id="mSeq">One after the other</button>
  <label>Speed <select id="spd"><option>0.5</option><option selected>1</option><option>1.5</option><option>2</option><option>3</option></select></label>
  <span class="sp"></span>
  <button id="bPrev">&larr; Prev</button><button id="bNext">Next &rarr;</button>
 </div>
 <h2 id="ttl"></h2><p class="pre" id="pre"></p>
 <div class="vids side" id="vids">
  <div class="pane b" id="pb"><div class="lab"><span>__BEFORE__</span><span id="db"></span></div><div id="slotB"></div></div>
  <div class="pane a" id="pa"><div class="lab"><span>__AFTER__</span><span id="da"></span></div><div id="slotA"></div></div>
 </div>
 <div class="scrub"><input type="range" id="scr" min="0" max="100" step="0.1" value="0"><span id="tm">0:00</span></div>
 <div class="note" id="note"></div>
 <div class="keys">Keys: <code>Space</code> play/pause, <code>R</code> restart, <code>S</code> cycle layout (side by side, stacked, one after the other), <code>&larr;</code>/<code>&rarr;</code> previous/next scenario, <code>[</code>/<code>]</code> speed.</div>
</main></div>
<script>
const ITEMS=__ITEMS__;
let cur=0,mode='side',seqStage='b',vb=null,va=null,playing=false,raf=0;
const $=id=>document.getElementById(id);
const fmt=t=>{t=Math.max(0,t||0);return Math.floor(t/60)+':'+String(Math.floor(t%60)).padStart(2,'0')};
const esc=s=>String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
function mk(src,slot){slot.innerHTML='';if(!src){slot.innerHTML='<div class="none">No recording for this scenario</div>';return null}
 const v=document.createElement('video');v.src=src;v.preload='auto';v.muted=true;v.playsInline=true;v.controls=false;slot.appendChild(v);return v}
function dur(){return Math.max(vb&&vb.duration||0,va&&va.duration||0)}
function seqDur(){return (vb&&vb.duration||0)+(va&&va.duration||0)}
function render(){
 const it=ITEMS[cur];
 document.querySelectorAll('#list button').forEach((b,i)=>b.classList.toggle('on',i===cur));
 $('ttl').textContent=it.id+': '+it.title;$('pre').textContent=it.pre+(it.what?'  '+it.what:'');
 const pf=Object.entries(it.prefs||{}).map(([k,v])=>'<code>'+esc(k)+' = '+esc(v)+'</code>').join(' ');
 $('note').innerHTML=(it.tag?'<b class="tag '+it.tag+'">'+({same:'Same behaviour',differs:'Different',new:'Only possible after'}[it.tag]||'')+'</b>':'')+esc(it.note||'No note.')+(pf?'<div style="margin-top:6px">Settings changed for this case: '+pf+'</div>':'');
 stop();seqStage='b';
 $('vids').className='vids '+mode;
 vb=mk(it.before,$('slotB'));va=mk(it.after,$('slotA'));
 $('pb').style.display=(mode==='seq'&&seqStage!=='b')?'none':'';$('pa').style.display=(mode==='seq'&&seqStage!=='a')?'none':'';
 [vb,va].forEach(v=>{if(v){v.playbackRate=+$('spd').value;v.addEventListener('loadedmetadata',upd);v.addEventListener('ended',onEnd)}});
 upd();
}
function setSeqView(){$('pb').style.display=(mode==='seq'&&seqStage!=='b')?'none':'';$('pa').style.display=(mode==='seq'&&seqStage!=='a')?'none':''}
function onEnd(){if(mode==='seq'&&seqStage==='b'&&va){seqStage='a';setSeqView();va.currentTime=0;if(playing)va.play()}else if(mode!=='seq'){if(vb&&va&&vb.ended&&va.ended)stop()}else if(mode==='seq'&&seqStage==='a'){stop()}}
function play(){playing=true;$('bPlay').textContent='Pause';
 if(mode!=='seq'){[vb,va].forEach(v=>v&&(v.ended&&(v.currentTime=0),v.play()))}
 else{const v=seqStage==='b'?vb:va;if(v)v.play()}
 loop()}
function stop(){playing=false;$('bPlay').textContent='Play';[vb,va].forEach(v=>v&&v.pause());cancelAnimationFrame(raf)}
function loop(){upd();if(playing)raf=requestAnimationFrame(loop)}
function upd(){
 $('db').textContent=vb?fmt(vb.duration):'';$('da').textContent=va?fmt(va.duration):'';
 if(mode!=='seq'){const d=dur()||1;const t=Math.max(vb&&vb.currentTime||0,va&&va.currentTime||0);$('scr').max=d;$('scr').value=t;$('tm').textContent=fmt(t)+' / '+fmt(d)}
 else{const bd=vb&&vb.duration||0;const t=(seqStage==='b'?(vb&&vb.currentTime||0):bd+(va&&va.currentTime||0));$('scr').max=seqDur()||1;$('scr').value=t;$('tm').textContent=fmt(t)+' / '+fmt(seqDur())}
}
$('scr').addEventListener('input',e=>{const t=+e.target.value;
 if(mode!=='seq'){[vb,va].forEach(v=>{if(v)v.currentTime=Math.min(t,v.duration||t)})}
 else{const bd=vb&&vb.duration||0;if(t<bd||!va){seqStage='b';setSeqView();if(vb)vb.currentTime=t;if(va)va.currentTime=0}else{seqStage='a';setSeqView();if(vb)vb.currentTime=bd;va.currentTime=t-bd}
  if(playing){const v=seqStage==='b'?vb:va;[vb,va].forEach(x=>x&&x!==v&&x.pause());v&&v.play()}}
 upd()});
function setMode(m){mode=m;$('mSide').classList.toggle('on',m==='side');$('mStack').classList.toggle('on',m==='stack');$('mSeq').classList.toggle('on',m==='seq');const was=playing;stop();seqStage='b';$('vids').className='vids '+mode;setSeqView();[vb,va].forEach(v=>v&&(v.currentTime=0));upd();if(was)play()}
function go(i){cur=(i+ITEMS.length)%ITEMS.length;render()}
function restart(){const was=playing;stop();seqStage='b';setSeqView();[vb,va].forEach(v=>v&&(v.currentTime=0));upd();if(was||true)play()}
$('bPlay').onclick=()=>playing?stop():play();$('bRestart').onclick=restart;
$('mSide').onclick=()=>setMode('side');$('mStack').onclick=()=>setMode('stack');$('mSeq').onclick=()=>setMode('seq');
$('bPrev').onclick=()=>go(cur-1);$('bNext').onclick=()=>go(cur+1);
$('spd').onchange=()=>[vb,va].forEach(v=>v&&(v.playbackRate=+$('spd').value));
addEventListener('keydown',e=>{if(e.target.tagName==='SELECT')return;
 if(e.code==='Space'){e.preventDefault();playing?stop():play()}
 else if(e.key==='r'||e.key==='R')restart();else if(e.key==='s'||e.key==='S')setMode(mode==='side'?'stack':mode==='stack'?'seq':'side');
 else if(e.key==='ArrowRight')go(cur+1);else if(e.key==='ArrowLeft')go(cur-1);
 else if(e.key===']'||e.key==='['){const s=$('spd');const i=Math.max(0,Math.min(s.options.length-1,s.selectedIndex+(e.key===']'?1:-1)));s.selectedIndex=i;s.onchange()}});
const L=$('list');let lastSec='';ITEMS.forEach((it,i)=>{if(it.section&&it.section!==lastSec){lastSec=it.section;const h=document.createElement('div');h.className='sec';h.textContent=it.section;L.appendChild(h)}const b=document.createElement('button');b.innerHTML='<span class="dot '+(it.tag||'')+'"></span><span class="id">'+it.id+'</span><span class="t">'+esc(it.title)+'</span>';b.onclick=()=>go(i);L.appendChild(b)});
render();
</script></body></html>
'''

os.makedirs(f'{ROOT}/compare', exist_ok=True)
html = (PAGE.replace('__ITEMS__', json.dumps(items))
        .replace('__TITLE__', meta.get('title', 'Before and after'))
        .replace('__BEFORE__', meta.get('before_label', 'BEFORE: unpatched'))
        .replace('__AFTER__', meta.get('after_label', 'AFTER: patched')))
open(f'{ROOT}/compare/index.html', 'w').write(html)
print('wrote compare/index.html with', len(items), 'scenarios;',
      'missing before:', [i['id'] for i in items if not i['before']],
      'missing after:', [i['id'] for i in items if not i['after']])
