Paycee.
=======

ペースいい、ペイシー。今日あといくら使えるかがわかる家計アプリ。
公開先: https://paycee.pages.dev/

- index.html … アプリ本体(build.py で paycee-claude.html から作る)
- sw.js / manifest.webmanifest / *.png … ホーム画面・オフライン用
- paycee-claude.html … 元になるファイル(Claude上の確認用の版)
- build.py … 元ファイルから独立版を作る
- tests/test_paycee.py … 自動テスト(`python3 tests/test_paycee.py index.html`)
