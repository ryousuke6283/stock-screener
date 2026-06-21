# -*- coding: utf-8 -*-
"""AppTest で app.py を実機実行し、例外なし＆プリセット動作を検証する"""
from streamlit.testing.v1 import AppTest

at = AppTest.from_file("pages_screener.py", default_timeout=60).run()
assert not at.exception, f"起動時に例外: {at.exception}"

# 初期状態（条件なし）の件数を取得
total = int(at.metric[0].value.split()[0])
print(f"初期（条件なし）該当: {total} 件")
assert total == 726, f"初期件数が想定外: {total}"

# 「バリュー（割安）」プリセットボタンを押す
btn = next(b for b in at.button if b.label == "バリュー（割安）")
btn.click().run()
assert not at.exception, f"プリセット適用後に例外: {at.exception}"
value_n = int(at.metric[0].value.split()[0])
print(f"バリュー適用後: {value_n} 件 / 条件: {[s for s in at.caption]}")
assert value_n < total, "バリュー条件で件数が減っていない"

# 「グロース」も試す
at2 = AppTest.from_file("pages_screener.py", default_timeout=60).run()
g = next(b for b in at2.button if b.label == "グロース（成長）")
g.click().run()
assert not at2.exception
growth_n = int(at2.metric[0].value.split()[0])
print(f"グロース適用後: {growth_n} 件")

print("\nOK: AppTest 全チェック通過")
