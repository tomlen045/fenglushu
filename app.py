#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""风路书 FengLuShu · 摩旅路书生成引擎
输入：路线 + 摩托车 + 骑行偏好 → 输出：逐日路书（海拔/里程/加油/高反/封路红线 + AI 路况问题清单）
红线数据（垭口海拔/封路窗口/加油点）来自 2025-2026 公开信源人工锚定，禁 Mock。
"""
import json
import os
import re
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
OUT_DIR = os.path.join(BASE, "output")
STATIC = os.path.join(BASE, "static")
for d in (DATA_DIR, OUT_DIR, STATIC):
    os.makedirs(d, exist_ok=True)

# ---------------- 真实锚定数据库 ----------------
ROUTES = {
    "g318": {
        "name": "川藏南线 G318（成都→拉萨）", "days": 12, "length_km": 2150,
        "start_alt": 500, "slogan": "此生必驾 · 眼睛在天堂身体在地狱",
        "legs": [
            ["D1", "成都→雅安", 149, 500, "泸定桥方向，出成都平原最后的大城市补给"],
            ["D2", "雅安→康定", 103, 2560, "二郎山隧道，进藏前整备链条与胎压"],
            ["D3", "康定→新都桥", 75, 3460, "翻折多山垭口4298m（康巴第一关），第一座4000m+"],
            ["D4", "新都桥→雅江", 74, 2600, "高尔寺山垭口4412m，短途适应日勿赶路"],
            ["D5", "雅江→理塘", 143, 4014, "剪子弯山4659m+卡子拉山4429m，世界高城过夜"],
            ["D6", "理塘→巴塘", 165, 2580, "海子山4685m，姊妹湖观景台"],
            ["D7", "巴塘→左贡", 264, 3780, "金沙江大桥进藏·宗拉山4170m+拉乌山4338m+东达山5008m"],
            ["D8", "左贡→八宿", 201, 3260, "业拉山4658m+怒江72拐，长下坡控速"],
            ["D9", "八宿→波密", 219, 2725, "安久拉山4325m+然乌湖，冰川之乡休整"],
            ["D10", "波密→林芝", 216, 2900, "通麦天险已改隧道，色季拉山4559m远眺南迦巴瓦"],
            ["D11", "林芝→工布江达", 147, 3400, "沿尼洋河，林拉公路吃油看表"],
            ["D12", "工布江达→拉萨", 273, 3650, "米拉山口5013m收官，布达拉宫打卡"],
        ],
        "hazards": [
            ["雨季7-8月", "通麦-波密段雨后塌方落石高发，出发前查当日路况", 4],
            ["全年", "折多山/东达山/米拉山突发降雪，备防雨保暖，垭口勿久留", 4],
            ["全年", "东达山5008m为全程最高点，含氧量约为海平面53%，当日禁酒", 5],
            ["全程", "318全线大部分国省道对摩托车开放，个别隧道禁摩需绕行预案", 3],
        ],
    },
    "duku": {
        "name": "独库公路 G217（独山子→库车）", "days": 3, "length_km": 561,
        "start_alt": 300, "slogan": "纵贯天山脊梁 · 中国最美公路",
        "legs": [
            ["D1", "独山子→乔尔玛", 180, 2300, "哈希勒根达坂3390m，老虎口悬崖弯道慢行"],
            ["D2", "乔尔玛→巴音布鲁克", 160, 2470, "那拉提草原段，注意牛羊横穿"],
            ["D3", "巴音布鲁克→库车", 221, 1100, "大小龙池+天山神秘大峡谷，长下坡"],
        ],
        "hazards": [
            ["封路窗口", "每年仅约6月初-10月上旬开放约4个月，10月中冬季封闭（2025年为10月10日20时）", 5],
            ["通行时段", "2026年起昼保通行夜保施工：乌苏驿-库如力段每日8-19时，19时后那拉提/乔尔玛入口禁止驶入", 5],
            ["加油", "全线仅5座加油站：独山子/乔尔玛/那拉提/巴音布鲁克/天山神秘大峡谷，见站就加", 5],
            ["车型确认", "2026年新疆公安厅官方通告明确：摩托车可以走独库，需持摩托车驾照；山区流动测速限速40/60km/h", 4],
            ["天气", "6月/9月垭口随时降雪，铁力买提达坂隧道前后常有暗冰", 4],
        ],
    },
    "u_expr": {
        "name": "独库北段闪电战（乌鲁木齐往返，2天）", "days": 2, "length_km": 700,
        "start_alt": 800, "slogan": "周末党专属 · 最小闭环体验天山",
        "legs": [
            ["D1", "乌鲁木齐→独山子→乔尔玛", 320, 2300, "凌晨出发赶8时开闸，独山子进山前满油"],
            ["D2", "乔尔玛→那拉提→独山子→乌鲁木齐", 380, 800, "原路返回，19时前务必出山"],
        ],
        "hazards": [
            ["时间红线", "8-19时开放，晚一分钟就困在山里，反程必须留足余量", 5],
            ["加油", "乔尔玛是中途唯一稳妥加油点，380km返程段无加油站", 4],
        ],
    },
    "bcc": {
        "name": "丙察察 G219 滇藏段（丙中洛→察瓦龙→察隅→波密）", "days": 4, "length_km": 640,
        "start_alt": 1750, "slogan": "国道烂路之王 · 勇士之路 · 一天翻四季",
        "legs": [
            ["D1", "丙中洛适应日", 0, 1750, "怒江第一湾/雾里村，低海拔起点是本线最大优势"],
            ["D2", "丙中洛→察瓦龙", 90, 1900, "上午过大流沙（察瓦龙南9km），严禁鸣笛勿停车；察瓦龙满油补给"],
            ["D3", "察瓦龙→察隅", 220, 2300, "翻雄珠拉4636/昌拉4490/益秀拉4706三垭口，8-10小时，目若村3700m午餐"],
            ["D4", "察隅→然乌→波密", 330, 2725, "德姆拉山+然乌湖，接上G318路书继续走"],
        ],
        "hazards": [
            ["施工管制", "2026年1月31日前丙中洛至察瓦龙段实行周一至周四封闭施工、周五至周日通行，出发前查官方通告（2026年8月计划全线铺装）", 5],
            ["大流沙", "察瓦龙以南约9km，200米沿江飞石区：上午通过、严禁鸣笛、勿停车拍照，雨后天晴最危险", 5],
            ["无信号无救援", "察察段约220km基本无地面通讯、救援滞后，必须组队+卫星通讯，车况胎况提前整备", 5],
            ["雨季", "6-8月塌方/滚石/泥石流高发，首选春末和秋季窗口", 4],
            ["边防证", "沿线毗邻中缅边境，需提前办理边防证", 4],
            ["路面", "察察段为碎石/炮弹坑非铺装路（2026年8月前），摩旅需拉力胎+护具拉满", 4],
        ],
    },
    "g219xl": {
        "name": "新藏线 G219 天路段（叶城→狮泉河）", "days": 4, "length_km": 1000,
        "start_alt": 1765, "slogan": "世界海拔最高公路 · 平均4500m · 5座5000m+达坂16个",
        "legs": [
            ["D1", "叶城→麻扎达坂→黑卡达坂→三十里营房", 360, 3700, "零公里出发当天连翻三个5000m级达坂，当晚睡3700m，最强高反日"],
            ["D2", "三十里营房→界山达坂→日土/班公湖", 410, 4250, "翻界山达坂5290m，穿越约255km无人区，出发必须满油"],
            ["D3", "日土→狮泉河", 230, 4350, "班公湖打卡，抵达阿里首府狮泉河休整补给"],
            ["D4", "狮泉河机动日（休整/转阿里大环线）", 0, 4350, "连续睡4000m+后强制休整天，高反没有英雄"],
        ],
        "hazards": [
            ["高反最强", "本线是进藏线高反之王：D1从1765m翻5000m级达坂直达3700m过夜，全程连续睡3700-4350m，出发前叶城住一晚+备药携氧", 5],
            ["加油", "三大补给点：叶城/三十里营房/狮泉河；D2约410km无人区段无加油站，三十里营房必须满油并留30%余量", 5],
            ["无人区", "数百公里无信号无救援无补给，组队出发+卫星通讯+帐篷食品药品冗余", 5],
            ["达坂冰雪", "界山达坂等5000m+达坂全年可能降雪，5-6月/9-10月为推荐窗口", 4],
            ["边防证", "阿里地区需边防证，户籍地或叶城提前办理", 4],
        ],
    },
    "duku_slow": {
        "name": "独库公路慢骑版（独山子→库车，4天深玩）", "days": 4, "length_km": 576,
        "start_alt": 300, "slogan": "同一条天山 · 把节奏降下来 · 草原深玩两整天",
        "legs": [
            ["D1", "独山子→乔尔玛", 180, 2300, "哈希勒根达坂3390m，老虎口慢行，乔尔玛住下看烈士陵园"],
            ["D2", "乔尔玛→那拉提", 90, 1300, "全程最短日：草原深玩，午后拍照不赶路"],
            ["D3", "那拉提→巴音布鲁克", 85, 2470, "天鹅湖日落，九曲十八弯等晚霞"],
            ["D4", "巴音布鲁克→库车", 221, 1100, "大小龙池+天山神秘大峡谷，长下坡收环"],
        ],
        "hazards": [
            ["封路窗口", "每年仅约6月初-10月上旬开放约4个月，出发前查当年官方通告", 5],
            ["通行时段", "2026年起昼保通行夜保施工：乌苏驿-库如力段每日8-19时；慢骑版每天里程短，但午后拍照仍勿误出山时间", 5],
            ["加油", "全线仅5座加油站：独山子/乔尔玛/那拉提/巴音布鲁克/天山神秘大峡谷，见站就加", 5],
            ["天气", "6月/9月垭口随时降雪，早晚温差大，慢骑版在山里时间更长保暖更要带足", 4],
        ],
    },
    "hainan": {
        "name": "环海南岛（环岛旅游公路988km，7天慢环）", "days": 7, "length_km": 900,
        "start_alt": 10, "slogan": "国家海岸一号风景道 · 无海拔焦虑 · 冬季摩旅天花板",
        "legs": [
            ["D1", "海口(绕城外围出发)→文昌", 90, 30, "骑楼老街起步，文昌椰林+铜鼓岭，注意海口主城区禁摩"],
            ["D2", "文昌→琼海·博鳌", 100, 20, "博鳌亚洲论坛会址，潭门渔港海鲜"],
            ["D3", "博鳌→万宁", 110, 30, "日月湾冲浪镇/石梅湾，滨海公路精华段"],
            ["D4", "万宁→陵水→三亚", 120, 20, "海棠湾收东线；三亚环岛旅游公路段已解除摩限行"],
            ["D5", "三亚休整→崖州", 60, 20, "休整日：南山/天涯海角，短骑到崖州古城"],
            ["D6", "崖州→东方", 170, 40, "转西线：莺歌海盐场，鱼鳞洲日落"],
            ["D7", "东方→儋州→海口", 250, 10, "西线北上收官，儋州千年古盐田，傍晚环岛闭合"],
        ],
        "hazards": [
            ["高速禁摩", "海南全省高速公路禁止摩托车通行（《海南省高速公路交通安全管理办法》），误入罚100记1分；导航可能把你引上G98，务必设置避开高速", 5],
            ["海口禁摩区", "海口主城区闭合区域（含海甸岛/新埠岛）禁摩，起点安排在绕城外围出发", 5],
            ["台风季", "5-10月为台风季（8-10月高发），出发前查台风路径；最佳窗口11月-次年4月", 5],
            ["三亚限行", "三亚主城仅环岛旅游公路段2023年12月起解除摩限行，其他区域（迎宾路/育新路/鹿回头等）仍限行", 4],
            ["烈日暴晒", "热带紫外线极强，避开14-16点暴骑，每小时补水，防晒拉满", 4],
        ],
    },
    "g109": {
        "name": "青藏线 G109（格尔木→拉萨，进藏线全家桶收官）", "days": 6, "length_km": 1140,
        "start_alt": 2815, "slogan": "天路 · 平均海拔4500m · 货运大动脉上骑在世界屋脊",
        "legs": [
            ["D1", "格尔木→西大滩→昆仑山口→五道梁", 270, 4420, "连爬昆仑山口4768m，当晚睡五道梁——全程最狠高反日"],
            ["D2", "五道梁→沱沱河→雁石坪", 210, 4700, "索南达杰保护站/长江源沱沱河，冻土波浪路开始"],
            ["D3", "雁石坪→唐古拉山口→安多→那曲", 250, 4507, "翻全线最高点唐古拉5231m（天下第一道班），藏北草原收高原段"],
            ["D4", "那曲→当雄", 165, 4200, "短途缓冲日，可支线纳木错扎西半岛"],
            ["D5", "当雄→羊八井→拉萨", 245, 3650, "念青唐古拉伴行，羊八井温泉，终于睡回3650m"],
            ["D6", "拉萨机动日", 0, 3650, "布达拉宫/大昭寺休整，与G318路书在此会师"],
        ],
        "hazards": [
            ["高反魔咒", "五道梁民谚「到了五道梁，哭爹又喊娘」：D1从2815m连爬到4400m+过夜，且全程无低海拔睡觉点（沱沱河4533/那曲4507/当雄4200）——格尔木住两晚适应+携氧备药再出发，症状加重立即搭车下撤", 5],
            ["货运大动脉", "G109是进藏货运主力，大货车络绎不绝且路窄仅容两车并行：遇货车提前靠边让行，绝对禁止夜路骑行，最迟19时到宿点（当地日照到20:30也别赌）", 5],
            ["冻土波浪路", "西大滩至那曲段冻土路基起伏开裂成波浪路（热棒路段），控速40-50，轮组/行李架螺栓每天出发前紧一遍", 5],
            ["冰雹天气", "7-9月午后常有冰雹/阵雪且天气瞬变：赶早出发午后收工，垭口不逗留", 4],
            ["提质改造施工", "2025年起格尔木至那曲段提质改造工程启动，沿线多处半幅通行，出发前查青海省交通运输厅/西藏交通路况通报", 4],
        ],
    },
}
# 车型库：油箱L / 百公里油耗L（摩友实测口径）→ 计算续航
BIKES = {
    "cf450sr":  {"name": "春风450SR",   "tank": 14.0, "consum": 3.8},
    "wl525r":   {"name": "无极525R",    "tank": 17.5, "consum": 4.2},
    "qj600":    {"name": "钱江赛600",   "tank": 18.0, "consum": 4.6},
    "cf800mt":  {"name": "春风800MT",   "tank": 19.0, "consum": 4.8},
    "nk800":    {"name": "春风800NK",   "tank": 15.0, "consum": 4.9},
}
STYLES = {"easy": "舒适骑", "photo": "摄影打卡", "hard": "赶路铁屁股"}
AQI_TAGS = ["风大", "暴晒", "低温", "雨季", "正常"]

# ---------------- 核心计算（纯函数，可断言） ----------------
def compute_range(bike_key):
    b = BIKES.get(bike_key)
    if not b:
        return None
    return {"bike": b["name"], "tank_l": b["tank"], "consum": b["consum"],
            "range_km": round(b["tank"] / b["consum"] * 100, 1)}


def build_plan(route_key, bike_key, style, days):
    r = ROUTES.get(route_key)
    if not r:
        return None
    rng = compute_range(bike_key)
    total_km = r["length_km"]
    plan = {
        "route": r["name"], "slogan": r["slogan"], "bike": rng["bike"],
        "range_km": rng["range_km"], "style": STYLES.get(style, style),
        "total_km": total_km, "days": days,
        "daily_avg": round(total_km / days, 0),
        "legs": r["legs"], "hazards": r["hazards"],
        "redlines": [],
        "ai_questions": [],
    }
    # 红线检查（真实锚定）
    for h in r["hazards"]:
        if h[2] >= 4:
            plan["redlines"].append({"level": h[2], "tag": h[0], "text": h[1]})
    # AI 路况问题清单（生成引擎按路线拼装，答案随出行日期动态化）
    plan["ai_questions"] = [
        "我%s出发，%s沿线最近一周有没有塌方/施工/交通管制？哪些垭口在下雪？" % (time.strftime("%Y年%m月%d日"), r["name"]),
        "我的车是%s，满油续航约%s公里，%s沿线两座加油站之间的最长间隔是多少？会断油吗？" % (rng["bike"], rng["range_km"], r["name"]),
        "我住平原，第一次上5000m+垭口，%s线上哪些天会睡在3500m以上？高反预警和药物时间表？" % (r["name"][:4],),
        "现在这个月份，%s全线还在开放窗口期内吗？今年封路时间和每日通行时段？" % r["name"],
    ]
    return plan


def render_roadbook(plan):
    """生成 Markdown 路书交付物"""
    L = []
    L.append("# %s · 风路书" % plan["route"])
    L.append("")
    L.append("> %s" % plan["slogan"])
    L.append("")
    L.append("- **总里程**：%s km　**建议天数**：%s 天　**日均**：%s km" % (
        plan["total_km"], plan["days"], plan["daily_avg"]))
    L.append("- **座驾**：%s　**满油续航**：%s km（油箱%sL / %sL百公里）" % (
        plan["bike"], plan["range_km"], "—", "—"))
    L.append("- **骑行风格**：%s" % plan["style"])
    L.append("- **生成日期**：%s" % time.strftime("%Y-%m-%d"))
    L.append("")
    L.append("## 逐日行程")
    L.append("")
    L.append("| 天 | 区段 | 里程km | 宿点海拔m | 要点 |")
    L.append("|---|---|---|---|---|")
    for leg in plan["legs"]:
        L.append("| %s | %s | %s | %s | %s |" % (leg[0], leg[1], leg[2], leg[3], leg[4]))
    L.append("")
    L.append("## 红线与风险（出发前必读）")
    for rd in sorted(plan["redlines"], key=lambda x: -x["level"]):
        bar = "🔴" if rd["level"] >= 5 else "🟠"
        L.append("- %s 【%s】%s" % (bar, rd["tag"], rd["text"]))
    L.append("")
    L.append("## AI 路况问题清单（出发前3天，逐条问 AI 路况助手）")
    for i, q in enumerate(plan["ai_questions"], 1):
        L.append("%d. %s" % (i, q))
    L.append("")
    L.append("## 装备核对清单")
    for item in ["链条油+便携补胎", "防雨三件套", "高原药物（红景天/布洛芬/便携氧）",
                 "甘油输液管（高海拔手工加油）", "防水驮包+绑带", "行车记录仪/手机支架",
                 "保暖内胆+护具", "备钥匙+证件复印件"]:
        L.append("- [ ] " + item)
    L.append("")
    L.append("---")
    L.append("*风路书 FengLuShu · 数据锚定2025-2026公开信源，路况以出行当日官方通报为准*")
    return "\n".join(L)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="text/html; charset=utf-8", extra=None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            with open(os.path.join(STATIC, "index.html"), encoding="utf-8") as f:
                return self._send(200, f.read())
        if path == "/api/meta":
            return self._send(200, json.dumps({
                "routes": {k: {"name": v["name"], "days": v["days"],
                               "length_km": v["length_km"], "slogan": v["slogan"]}
                           for k, v in ROUTES.items()},
                "bikes": BIKES, "styles": STYLES,
            }, ensure_ascii=False), "application/json; charset=utf-8")
        m = re.match(r"^/download/([0-9a-f-]{36})\.md$", path)
        if m:
            fp = os.path.join(OUT_DIR, m.group(1) + ".md")
            if os.path.exists(fp):
                with open(fp, "rb") as f:
                    return self._send(200, f.read(), "text/markdown; charset=utf-8",
                                      {"Content-Disposition": "attachment; filename=lu-book.md"})
        return self._send(404, "not found", "text/plain")

    def do_POST(self):
        if urlparse(self.path).path != "/api/generate":
            return self._send(404, "not found", "text/plain")
        try:
            n = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(n).decode("utf-8"))
            rk, bk = data.get("route", ""), data.get("bike", "")
            if rk not in ROUTES or bk not in BIKES:
                return self._send(400, json.dumps({"ok": False, "error": "route/bike 无效"}),
                                  "application/json; charset=utf-8")
            days = int(data.get("days") or 0) or ROUTES[rk]["days"]
            plan = build_plan(rk, bk, data.get("style", "easy"), days)
            pid = str(uuid.uuid4())
            md = render_roadbook(plan)
            with open(os.path.join(OUT_DIR, pid + ".md"), "w", encoding="utf-8") as f:
                f.write(md)
            with open(os.path.join(DATA_DIR, pid + ".json"), "w", encoding="utf-8") as f:
                json.dump({"id": pid, "created": time.strftime("%Y-%m-%d"),
                           "input": data, "plan": plan}, f, ensure_ascii=False, indent=1)
            return self._send(200, json.dumps({"ok": True, "id": pid, "plan": plan,
                                               "markdown": md,
                                               "download": "/download/%s.md" % pid},
                                              ensure_ascii=False),
                              "application/json; charset=utf-8")
        except Exception as e:
            return self._send(500, json.dumps({"ok": False, "error": str(e)}),
                              "application/json; charset=utf-8")


if __name__ == "__main__":
    port = int(os.environ.get("APP_PORT", "8666"))
    print("FengLuShu running at http://127.0.0.1:%d" % port)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
