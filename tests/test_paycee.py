"""Paycee. の自動テスト。
使い方: python3 tests/test_paycee.py [index.html のパス]
(Playwright と Chromium が必要。アプリの計算・入力・分析・期間の切り替えを、スマホ相当の画面で確かめる)
"""
import asyncio, json, os, sys, tempfile
from playwright.async_api import async_playwright

SRC = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "index.html"))
TMP = tempfile.mkdtemp()
# 本番と同じく、制限付きの枠(sandbox)の中で動かす
open(f"{TMP}/outer.html", "w").write('<!doctype html><style>body{margin:0}iframe{border:0;width:100vw;height:100vh}</style>'
                                     f'<iframe id=f sandbox="allow-scripts allow-same-origin" src="file://{SRC}"></iframe>')
FAILS = []
def ok(c, m):
    print(("✅ " if c else "❌ ") + m)
    if not c: FAILS.append(m)
def yen(n): return ("−" if n < -0.5 else "") + "¥" + format(abs(round(n)), ",")
def E(d, a, **k): return dict({"id": f"e{d}_{a}", "date": f"2026-10-{d:02d}", "amount": a, "type": "out", "group": "food", "cat": "", "memo": ""}, **k)
def state(**k):
    s = {"v": 3, "mode": "carry", "period": {"start": "2026-10-01", "end": "2026-10-31", "budget": 93000}, "expenses": [], "archives": [],
         "fixed": [], "goals": [], "savings": [], "autoKeys": [], "onboarded": True}
    s.update(k); return s

class App:
    def __init__(s, pw): s.pw = pw
    async def open(s, st=None, now="2026-10-10T20:00:00+09:00"):
        s.b = await s.pw.chromium.launch()
        s.ctx = await s.b.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True, accept_downloads=True)
        s.pg = await s.ctx.new_page(); s.errs = []; s.pg.on("pageerror", lambda e: s.errs.append(str(e)))
        await s.pg.clock.install(time=now)
        if st is not None:
            await s.pg.add_init_script("if(!sessionStorage.getItem('seed')){localStorage.clear();localStorage.setItem('paycee3'," + json.dumps(json.dumps(st)) + ");sessionStorage.setItem('seed','1')}")
        else:
            await s.pg.add_init_script("if(!sessionStorage.getItem('seed')){localStorage.clear();sessionStorage.setItem('seed','1')}")
        await s.pg.goto(f"file://{TMP}/outer.html"); await s.pg.clock.run_for(2800)
        return s
    @property
    def f(s): return [x for x in s.pg.frames if x.url.endswith("index.html") or x.url.endswith(".html") and x != s.pg.main_frame][0]
    async def tap(s, sel):
        l = s.f.locator(sel).first; await l.evaluate("e=>e.scrollIntoView({block:'center'})"); await l.tap(); await s.pg.clock.run_for(250)
    async def ev(s, js): return await s.f.evaluate(js)
    async def left(s): return await s.f.inner_text("#left")
    async def add(s, amount, kind="out", grp=None, date=None, memo=""):
        await s.tap(f"#kindSeg [data-kind={kind}]")
        if grp: await s.tap(f"[data-grp={grp}]")
        if date:
            if await s.f.is_hidden("#dateRow"): await s.tap("#moreBtn")
            await s.f.fill("#date", date); await s.f.dispatch_event("#date", "change")
        elif not await s.f.is_hidden("#dateRow"): await s.tap("#moreBtn")
        await s.f.fill("#amt", str(amount)); await s.f.fill("#memo", memo); await s.tap("#addBtn")
    async def close(s):
        if s.errs: ok(False, "JSエラー: " + "; ".join(s.errs))
        await s.b.close()

async def main():
    async with async_playwright() as pw:
        print("── 初回の設定ガイド")
        a = await App(pw).open()
        ok(not await a.f.is_hidden("#obGo"), "データがない状態で開くと、初回の設定ガイドが出る")
        await a.tap('#obCyc [data-cyc="pay"]'); await a.f.select_option("#obDay", "25")
        await a.f.fill("#obBud", "62000"); await a.tap("#obGo")
        p = await a.ev("S.period")
        ok(p["start"] == "2026-09-25" and p["end"] == "2026-10-24" and p["budget"] == 62000, f"給料日25日・62,000円 → 期間 {p['start']}〜{p['end']}")
        ok(await a.ev("S.cycleDay") == 25, "区切りの日(25日)が保存される")
        await a.close()

        print("── 入力と計算(繰越型・予算93,000円・31日・10/10)")
        a = await App(pw).open(state())
        ok(await a.left() == "¥30,000", f"支出なし → {await a.left()}")
        await a.add("１２００", grp="food", memo="ランチ"); ok(await a.left() == "¥28,800", f"全角で1,200円 → {await a.left()}")
        await a.f.fill("#amt", "300"); await a.f.press("#amt", "Enter"); await a.pg.clock.run_for(250)
        ok(await a.left() == "¥28,500", f"Enterで300円 → {await a.left()}")
        await a.add(5000, grp="fun", date="2026-10-05"); ok(await a.left() == "¥23,500", f"過去10/5に5,000円 → {await a.left()}")
        await a.add(12000, grp="fun", date="2026-10-28"); ok(await a.left() == "¥23,500", f"先の予定12,000円(繰越型)→ 変わらず {await a.left()}")
        await a.add(5000, kind="in", grp="extra", date="2026-10-25"); ok(await a.left() == "¥23,500", "先の収入 → 変わらず")
        await a.add(3000, kind="in", grp="extra"); ok(await a.left() == "¥26,500", f"今日の臨時収入3,000円 → {await a.left()}")
        await a.add(250000, kind="in", grp="salary"); await a.add(80000, grp="fixed")
        ok(await a.left() == "¥26,500", "給与・固定費 → 変わらず")
        await a.tap("[data-mode=avg]")
        exp = (93000 - 12000 + 3000 - 5000) / 22 - 1500
        ok(await a.left() == yen(exp), f"平均型 → {await a.left()}(期待 {yen(exp)})")
        await a.close()

        print("── 予算を途中で変える(変えた日から残りを均等に)")
        for spent, nb, want in [(2000, 124000, (124000 - 18000) / 22), (3000, 62000, (62000 - 27000) / 22)]:
            a = await App(pw).open(state(expenses=[E(d, spent) for d in range(1, 10)]))
            before = await a.ev("calcPeriod(S.period).allow.slice(0,9).map(Math.round)")
            await a.tap("nav.tabs [data-tab=set]"); await a.f.fill("#bud", str(nb)); await a.f.dispatch_event("#bud", "change"); await a.pg.clock.run_for(250)
            await a.tap("nav.tabs [data-tab=home]")
            ok(await a.left() == yen(want), f"9日で{spent*9:,}円 → {nb:,}円に変更 → {await a.left()}(期待 {yen(want)})")
            ok(before == await a.ev("calcPeriod(S.period).allow.slice(0,9).map(Math.round)"), "  変更前の日の枠は変わらない")
            await a.close()

        print("── ストリーク")
        a = await App(pw).open(state(expenses=[E(2, 4000), E(3, 3500), E(6, 12000)]))
        ok(await a.ev("streak()") == 4, f"枠内の日は続き、枠をこえた10/6で途切れる → {await a.ev('streak()')}日")
        await a.close()
        a = await App(pw).open(state(expenses=[E(2, 5000)]))
        await a.tap("nav.tabs [data-tab=set]"); await a.f.fill("#bud", "62000"); await a.f.dispatch_event("#bud", "change"); await a.pg.clock.run_for(250)
        ok(await a.ev("streak()") == 10, "予算を減らしても、変更前の日はさかのぼって判定し直さない")
        await a.close()

        print("── 分析タブ")
        a = await App(pw).open(state(expenses=[E(2, 4000), E(3, 2500), E(4, 200), E(5, 1000), E(6, 3000), E(7, 3001), E(28, 9000, planned=True)]))
        await a.tap("nav.tabs [data-tab=stats]")
        cal = {int(k): v for k, v in (await a.ev("[...document.querySelectorAll('#cal [data-day]')].reduce((o,b)=>(o[+b.dataset.day.slice(8)]=b.querySelector('.dot').className.split(' ')[1],o),{})")).items()}
        ok([cal[d] for d in (2, 3, 4, 5, 6, 7, 8, 28)] == ["over", "norm", "none", "small", "norm", "over", "none", "plan"], f"カレンダーの色(日割り3,000円基準)→ {[cal[d] for d in (2,3,4,5,6,7,8,28)]}")
        for cid in ["chPace", "chDaily", "chPer"]: ok(await a.f.locator(f"#{cid} svg").count() == 1, f"グラフ {cid}")
        txt = await a.f.inner_text("#chDaily"); ok("日割り 3,000" in txt and "↑" in txt, "日別グラフに日割りの線と、上端をこえた枠の↑")
        ok(await a.f.is_hidden("#flowCard"), "収入が未設定なら「お金の流れ」は出さない")
        ok(await a.f.locator("#rFrom").count() == 0, "期間別支出集計のカードは外した")
        await a.tap('[data-help="calendar"]'); ok("日割りの額" in await a.f.inner_text("#sheetBd"), "?で説明が開く")
        await a.close()

        print("── よく使う(ワンタップ入力)")
        a = await App(pw).open(state(expenses=[E(3, 800, memo="ランチ"), E(4, 800, memo="ランチ")]))
        ok("ランチ" in await a.f.inner_text("#quick"), "2回記録した組み合わせが候補に出る")
        await a.tap('#quick [data-q="0"]'); ok(await a.ev("S.expenses.filter(e=>e.date==='2026-10-10'&&e.amount===800).length") == 1, "候補をタップすると今日に記録")
        await a.f.fill("#amt", "450"); await a.tap("[data-grp=food]"); await a.f.fill("#memo", "コーヒー"); await a.tap("#qAdd")
        ok(await a.ev("S.quick.length") == 1 and "コーヒー" in await a.f.inner_text("#quick"), "「今の入力を登録」で追加できる")
        await a.close()

        print("── 期間の切り替わり")
        a = await App(pw).open(state(period={"start": "2026-09-25", "end": "2026-10-24", "budget": 62000}, cycleDay=25, expenses=[E(10, 5000)],
                                     goals=[{"id": "g1", "name": "車", "target": 4000000, "emoji": "🚗"}], saveGoal=50000), now="2026-10-26T09:00:00+09:00")
        ok(not await a.f.is_hidden("#modal"), "締め日を過ぎて開くと結果が出る")
        ok("早まります" in await a.f.inner_text("#mbox"), "余りを目標に入れると何日早まるかが出る")
        p = await a.ev("S.period"); ok(p["start"] == "2026-10-25" and p["end"] == "2026-11-24", f"給料日区切りで次の期間 {p['start']}〜{p['end']}")
        await a.close()

        print("── バックアップのお知らせ")
        a = await App(pw).open(state(expenses=[E(d, 500) for d in range(1, 7)]))
        local = await a.ev("LOCAL_DATA")
        if local:
            ok(not await a.f.is_hidden("#backupCard"), "記録が1週間以上たまり、未バックアップならお知らせが出る")
            await a.tap("#bkLater"); ok(await a.f.is_hidden("#backupCard"), "「あとで」で1週間消える")
        else:
            ok(await a.f.is_hidden("#backupCard"), "クラウド保存の版ではお知らせを出さない")
        await a.close()

    print(f"\n{'全て合格' if not FAILS else str(len(FAILS)) + '件の失敗'}")
    sys.exit(1 if FAILS else 0)

asyncio.run(main())
