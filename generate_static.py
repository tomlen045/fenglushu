#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""风路书静态化生成器：烘 data.js + 产出可公网部署的纯静态 site/
静态版 = 全部输入组合在浏览器本地计算（数据锚定同源），无需后端。
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import app  # 复用同源数据库 ROUTES/BIKES/STYLES，禁二次维护

SITE = os.path.join(BASE, "site")
os.makedirs(SITE, exist_ok=True)

# ---------- 1. data.js ----------
data = {"routes": app.ROUTES, "bikes": app.BIKES, "styles": app.STYLES}
with open(os.path.join(SITE, "data.js"), "w", encoding="utf-8") as f:
    f.write("/* 风路书静态数据 · 与服务端 app.py 同源烘出，禁手改 */\n")
    f.write("(typeof window!=='undefined'?window:globalThis).FLS_DATA=")
    f.write(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    f.write(";\n")
print("data.js:", os.path.getsize(os.path.join(SITE, "data.js")), "bytes")

# ---------- 2. app-core.js（纯计算，node 可直接断言） ----------
CORE = r"""/* 风路书核心计算引擎 · 静态版（与服务端 build_plan/render_roadbook 同逻辑） */
(function (g) {
  'use strict';
  function D() { return g.FLS_DATA; }
  function r1(x) { return Math.round(x * 10) / 10; }

  g.flsRange = function (bikeKey) {
    var b = D().bikes[bikeKey];
    if (!b) return null;
    return { bike: b.name, tank_l: b.tank, consum: b.consum, range_km: r1(b.tank / b.consum * 100) };
  };

  g.flsBuildPlan = function (routeKey, bikeKey, style, days) {
    var r = D().routes[routeKey];
    var rng = g.flsRange(bikeKey);
    if (!r || !rng) return null;
    if (!days || days <= 0) days = r.days;
    var now = new Date();
    var dateStr = now.getFullYear() + '年' + (now.getMonth() + 1) + '月' + now.getDate() + '日';
    var plan = {
      route: r.name, slogan: r.slogan, bike: rng.bike, range_km: rng.range_km,
      style: D().styles[style] || style, total_km: r.length_km, days: days,
      daily_avg: Math.round(r.length_km / days), legs: r.legs, hazards: r.hazards,
      redlines: [], ai_questions: [], date: dateStr
    };
    r.hazards.forEach(function (h) { if (h[2] >= 4) plan.redlines.push({ level: h[2], tag: h[0], text: h[1] }); });
    plan.redlines.sort(function (a, b) { return b.level - a.level; });
    plan.ai_questions = [
      '我' + dateStr + '出发，' + r.name + '沿线最近一周有没有塌方/施工/交通管制？哪些垭口在下雪？',
      '我的车是' + rng.bike + '，满油续航约' + rng.range_km + '公里，' + r.name + '沿线两座加油站之间的最长间隔是多少？会断油吗？',
      '我住平原，第一次上5000m+垭口，' + r.name.slice(0, 4) + '线上哪些天会睡在3500m以上？高反预警和药物时间表？',
      '现在这个月份，' + r.name + '全线还在开放窗口期内吗？今年封路时间和每日通行时段？'
    ];
    return plan;
  };

  g.flsRenderMd = function (p) {
    var L = [];
    L.push('# ' + p.route + ' · 风路书', '');
    L.push('> ' + p.slogan, '');
    L.push('- **总里程**：' + p.total_km + ' km　**建议天数**：' + p.days + ' 天　**日均**：' + p.daily_avg + ' km');
    L.push('- **座驾**：' + p.bike + '　**满油续航**：' + p.range_km + ' km');
    L.push('- **骑行风格**：' + p.style);
    L.push('- **生成日期**：' + p.date, '');
    L.push('## 逐日行程', '');
    L.push('| 天 | 区段 | 里程km | 宿点海拔m | 要点 |');
    L.push('|---|---|---|---|---|');
    p.legs.forEach(function (l) { L.push('| ' + l[0] + ' | ' + l[1] + ' | ' + l[2] + ' | ' + l[3] + ' | ' + l[4] + ' |'); });
    L.push('', '## 红线与风险（出发前必读）');
    p.redlines.forEach(function (rd) { L.push('- ' + (rd.level >= 5 ? '🔴' : '🟠') + ' 【' + rd.tag + '】' + rd.text); });
    L.push('', '## AI 路况问题清单（出发前3天，逐条问 AI 路况助手）');
    p.ai_questions.forEach(function (q, i) { L.push((i + 1) + '. ' + q); });
    L.push('', '## 装备核对清单');
    ['链条油+便携补胎', '防雨三件套', '高原药物（红景天/布洛芬/便携氧）', '甘油输液管（高海拔手工加油）',
     '防水驮包+绑带', '行车记录仪/手机支架', '保暖内胆+护具', '备钥匙+证件复印件'
    ].forEach(function (it) { L.push('- [ ] ' + it); });
    L.push('', '---', '*风路书 FengLuShu · 数据锚定2025-2026公开信源，路况以出行当日官方通报为准*');
    return L.join('\n');
  };
})(typeof window !== 'undefined' ? window : globalThis);
if (typeof module !== 'undefined') {
  module.exports = { flsRange: globalThis.flsRange, flsBuildPlan: globalThis.flsBuildPlan, flsRenderMd: globalThis.flsRenderMd };
}
"""
with open(os.path.join(SITE, "app-core.js"), "w", encoding="utf-8") as f:
    f.write(CORE)
print("app-core.js written")

# ---------- 3. index.html（静态 UI） ----------
INDEX = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>风路书 FengLuShu · 60秒生成摩旅路书</title>
<style>
:root{--bg:#0a0f1a;--card:#111827;--line:#1f2a3d;--tx:#e5edf7;--dim:#8ba0b8;--acc:#ffb02e;--ok:#2dd4a7;--red:#ff5a5a}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--tx);font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;
 background-image:linear-gradient(rgba(255,255,255,.025) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.025) 1px,transparent 1px);
 background-size:36px 36px;min-height:100vh;padding:32px 16px}
.wrap{max-width:920px;margin:0 auto}
.badge{display:inline-block;border:1px solid var(--acc);color:var(--acc);font-size:12px;padding:3px 10px;border-radius:99px;letter-spacing:2px}
h1{font-size:34px;margin:14px 0 6px}
h1 .glow{color:var(--acc);text-shadow:0 0 18px rgba(255,176,46,.55)}
.sub{color:var(--dim);font-size:15px;line-height:1.7}
.stats{display:flex;gap:12px;margin:22px 0}
.stat{flex:1;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.stat b{display:block;font-size:26px;color:var(--acc);text-shadow:0 0 12px rgba(255,176,46,.4)}
.stat span{font-size:12px;color:var(--dim)}
.sec{margin-top:26px}
.sec h2{font-size:15px;color:var(--dim);letter-spacing:3px;margin-bottom:12px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px}
.rc{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;cursor:pointer;transition:.15s}
.rc:hover{border-color:var(--acc)}
.rc.on{border-color:var(--acc);box-shadow:0 0 0 1px var(--acc),0 8px 24px rgba(255,176,46,.12)}
.rc b{font-size:16px}
.rc p{font-size:12px;color:var(--dim);margin-top:6px;line-height:1.6}
.rc .meta{margin-top:10px;font-size:12px;color:var(--acc)}
.row{display:flex;gap:12px;flex-wrap:wrap;margin-top:12px}
.chip{background:var(--card);border:1px solid var(--line);border-radius:99px;padding:8px 16px;font-size:13px;cursor:pointer;color:var(--dim)}
.chip.on{border-color:var(--acc);color:var(--acc)}
.chip:hover{border-color:var(--acc)}
.gen{margin-top:26px;width:100%;padding:16px;font-size:17px;font-weight:700;letter-spacing:4px;
 background:linear-gradient(135deg,#ffb02e,#ff8a3d);color:#1a1206;border:none;border-radius:14px;cursor:pointer}
#out{margin-top:26px;display:none}
.panel{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:20px;margin-bottom:14px}
.panel h3{font-size:14px;color:var(--acc);letter-spacing:2px;margin-bottom:12px}
.redline{display:flex;gap:10px;padding:10px 0;border-bottom:1px dashed var(--line);font-size:13.5px;line-height:1.6}
.redline:last-child{border:none}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:8px 6px;border-bottom:1px solid var(--line);text-align:left}
th{color:var(--dim);font-weight:400}
td:first-child{color:var(--acc)}
.q{display:flex;align-items:flex-start;gap:10px;padding:10px 0;border-bottom:1px dashed var(--line)}
.q:last-child{border:none}
.q p{flex:1;font-size:13.5px;line-height:1.7}
.q button{flex-shrink:0;background:none;border:1px solid var(--acc);color:var(--acc);border-radius:8px;padding:4px 10px;font-size:12px;cursor:pointer}
.dl{display:inline-block;margin-top:14px;color:var(--ok);border:1px solid var(--ok);border-radius:10px;padding:8px 18px;text-decoration:none;font-size:14px;cursor:pointer}
.foot{margin-top:30px;color:var(--dim);font-size:12px;text-align:center;line-height:1.8}
</style>
</head>
<body>
<div class="wrap">
  <span class="badge">风路书 FENGLUSHU · 纯静态版</span>
  <h1>60秒生成<span class="glow">摩旅路书</span></h1>
  <p class="sub">垭口海拔 · 封路红线 · 加油节点 · 高反日程 —— 按你的车和假期排好，出发前还送一份「问 AI 的路况问题清单」。<br>数据锚定 2025-2026 官方通报（独库封路窗口 / 川藏垭口海拔 / 加油站布点），全部计算在你手机本地完成。</p>
  <div class="stats">
    <div class="stat"><b id="st-route">0</b><span>锚定路线</span></div>
    <div class="stat"><b id="st-red">0</b><span>红线提示（选中路线）</span></div>
    <div class="stat"><b id="st-bike">0</b><span>热门中大排车型库</span></div>
  </div>
  <div class="sec"><h2>① 选路线</h2><div class="cards" id="routes"></div></div>
  <div class="sec"><h2>② 选座驾（决定满油续航）</h2><div class="row" id="bikes"></div></div>
  <div class="sec"><h2>③ 骑行风格与天数</h2>
    <div class="row" id="styles"></div>
    <div class="row"><span style="color:var(--dim);font-size:13px;align-self:center">总天数</span>
      <input id="days" type="number" min="1" max="30" value="12" style="background:var(--card);border:1px solid var(--line);color:var(--tx);border-radius:8px;padding:8px 12px;width:90px;font-size:14px"></div>
  </div>
  <button class="gen" onclick="gen()">生 成 路 书</button>
  <div id="out"></div>
  <div class="foot">风路书 FengLuShu · 路况封路信息以出行当日官方通报为准 · 数据锚定2025-2026公开信源</div>
</div>
<script src="data.js"></script>
<script src="app-core.js"></script>
<script>
let route=null,bike=null,style='easy';
function render(){
  const M=window.FLS_DATA;
  document.getElementById('st-route').textContent=Object.keys(M.routes).length;
  document.getElementById('st-bike').textContent=Object.keys(M.bikes).length;
  const rc=document.getElementById('routes');let i=0;
  for(const k in M.routes){const r=M.routes[k];
    const d=document.createElement('div');d.className='rc'+(i==0?' on':'');if(i==0)route=k;
    d.innerHTML='<b>'+r.name+'</b><p>'+r.slogan+'</p><div class="meta">'+r.length_km+' km · 建议'+r.days+'天</div>';
    d.onclick=()=>{route=k;[...rc.children].forEach(c=>c.classList.remove('on'));d.classList.add('on');
      document.getElementById('days').value=r.days;};
    rc.appendChild(d);i++;}
  document.getElementById('st-red').textContent=M.routes[route].hazards.filter(h=>h[2]>=4).length;
  const bk=document.getElementById('bikes');let j=0;
  for(const k in M.bikes){const b=M.bikes[k];
    const c=document.createElement('div');c.className='chip'+(j==0?' on':'');if(j==0)bike=k;
    c.textContent=b.name+' · 油箱'+b.tank+'L';
    c.onclick=()=>{bike=k;[...bk.children].forEach(x=>x.classList.remove('on'));c.classList.add('on');};
    bk.appendChild(c);j++;}
  const st=document.getElementById('styles');let s=0;
  for(const k in M.styles){const c=document.createElement('div');c.className='chip'+(s==0?' on':'');
    c.textContent=M.styles[k];
    c.onclick=()=>{style=k;[...st.children].forEach(x=>x.classList.remove('on'));c.classList.add('on');};
    st.appendChild(c);s++;}
}
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function gen(){
  const days=parseInt(document.getElementById('days').value||'0');
  const p=window.flsBuildPlan(route,bike,style,days);
  if(!p){alert('数据异常');return;}
  document.getElementById('st-red').textContent=p.redlines.length;
  let h='<div class="panel"><h3>✳ 行程概要</h3><p style="font-size:14px;line-height:2">'
   +'路线：<b style="color:var(--acc)">'+esc(p.route)+'</b><br>'
   +'总里程 <b style="color:var(--acc)">'+p.total_km+'</b> km · '+p.days+' 天 · 日均 '+p.daily_avg+' km<br>'
   +'座驾：'+esc(p.bike)+' · 满油续航 <b style="color:var(--ok)">'+p.range_km+'</b> km · 风格：'+esc(p.style)+'</p>'
   +'<a class="dl" onclick="dlmd()" >⬇ 下载完整路书 .md</a></div>';
  h+='<div class="panel"><h3>🚨 红线与风险（按严重度排序）</h3>';
  p.redlines.forEach(r=>{h+='<div class="redline"><span>'+(r.level>=5?'🔴':'🟠')+'</span><div><b>【'+esc(r.tag)+'】</b>'+esc(r.text)+'</div></div>';});
  h+='</div>';
  h+='<div class="panel"><h3>📅 逐日行程</h3><table><tr><th>天</th><th>区段</th><th>km</th><th>宿点海拔</th><th>要点</th></tr>';
  p.legs.forEach(l=>{h+='<tr><td>'+esc(l[0])+'</td><td>'+esc(l[1])+'</td><td>'+l[2]+'</td><td>'+l[3]+'m</td><td>'+esc(l[4])+'</td></tr>';});
  h+='</table></div>';
  h+='<div class="panel"><h3>🤖 出发前3天 · 问 AI 路况助手的问题清单</h3>';
  p.ai_questions.forEach((q,i)=>{h+='<div class="q"><p>'+(i+1)+'. '+esc(q)+'</p><button onclick="copyq(this)">复制</button></div>';});
  h+='</div>';
  const out=document.getElementById('out');out.innerHTML=h;out.style.display='block';
  out.scrollIntoView({behavior:'smooth'});
  window.__lastPlan=p;
}
function dlmd(){
  const p=window.__lastPlan;if(!p)return;
  const md=window.flsRenderMd(p);
  const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([md],{type:'text/markdown;charset=utf-8'}));
  a.download='fenglushu.md';a.click();URL.revokeObjectURL(a.href);
}
function copyq(btn){const p=btn.parentElement.querySelector('p').textContent.replace(/^\d+\.\s/,'');
  navigator.clipboard.writeText(p).then(()=>{btn.textContent='已复制';setTimeout(()=>btn.textContent='复制',1500);});}
render();
</script>
</body>
</html>
"""
with open(os.path.join(SITE, "index.html"), "w", encoding="utf-8") as f:
    f.write(INDEX)
print("index.html:", os.path.getsize(os.path.join(SITE, "index.html")), "bytes")
print("STATIC SITE READY ->", SITE)
