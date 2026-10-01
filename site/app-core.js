/* 风路书核心计算引擎 · 静态版（与服务端 build_plan/render_roadbook 同逻辑） */
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
