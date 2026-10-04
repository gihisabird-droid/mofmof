# セットアップ(約5分)
1. GitHubで新しいリポジトリを作る(例: mofmof-feed / Public)
2. この中身(scripts, .github, docs, README)をそのままアップロード
3. Settings → Pages → Source: "Deploy from a branch" / Branch: main / Folder: /docs → Save
4. Actions タブ → "Build RSS" → Run workflow(初回の手動実行)
5. https://<ユーザー名>.github.io/<リポジトリ名>/feed.xml が開けば完成
6. Feedly で「+ Follow sources」にその URL を貼り付けて Follow
以降は3時間ごとに自動更新されます。
