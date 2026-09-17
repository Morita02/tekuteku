# Render無料プランで試す

このフォルダーはOneDrive版アプリから作成した公開用コピーです。
既存のアカウント、投稿、アップロード画像、バックアップは含めていません。
元のアプリはそのまま残っています。

## 公開手順（Blueprint）

1. GitHubで新しい非公開リポジトリを作成します。
2. このフォルダーの中身をリポジトリのルートにアップロードしてコミットします。
   `app.py`、`requirements.txt`、`render.yaml`、`routes`、`templates`、`static`が
   同じ階層になるようにします。ZIPファイル自体を置くのではなく、展開した中身を置きます。
3. https://dashboard.render.com/ を開き、「New」→「Blueprint」を選択します。
4. GitHubを接続し、作成したリポジトリを選択します。
5. 設定ファイル `render.yaml` を使用します。Web ServiceのプランがFreeであること、
   ディスクや有料データベースが含まれていないことを確認して作成します。
6. デプロイがLiveになったら、表示される `https://...onrender.com` を開きます。
7. 「登録」でテスト用アカウントを新規作成します。投稿、画像、地図、設定を試します。

`SECRET_KEY`はBlueprintが自動生成します。ソースコードに秘密鍵を記入する必要はありません。
初期管理者は作成しません。以前の管理者アカウントも含まれていません。

## Web Serviceを手動作成する場合

- Language: Python
- Instance Type: Free
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn --workers 1 --threads 2 --bind 0.0.0.0:$PORT app:app`
- Health Check Path: `/healthz`
- Environment Variables:
  - `PYTHON_VERSION`: `3.13.7`
  - `SECRET_KEY`: 十分に長いランダムな秘密文字列（Generateを利用できる場合は自動生成）
  - `TEKUTEKU_DATA_DIR`: `/tmp/tekuteku-data`
  - `DEMO_MODE`: `1`
  - `TZ`: `Asia/Tokyo`

## 無料版の制約

15分間アクセスがないとサービスが休止します。再アクセス時の起動には時間がかかります。
休止・再起動・再デプロイのたびに、SQLiteのアカウント・投稿とアップロード画像は失われます。
テストデータだけで利用してください。月間利用枠にも上限があります。
支払い方法を登録済みの場合、帯域やビルド時間の超過分は課金される場合があるため、
RenderのBillingで利用上限も確認してください。

継続運用には永続ストレージなどの構成変更が必要です。
現在のデータ設定はSQLite専用です。PostgreSQLに切り替える場合はスキーマ更新処理も変更が必要です。

## 公開用コピーの変更内容

- Gunicornによる起動とRenderのポート指定、ヘルスチェックを追加。
- RenderではSECRET_KEY未設定時に起動を停止。
- HTTPS用Cookie設定とプロキシ対応を追加。
- 通常フォームと地図の更新リクエストにCSRF対策を追加。
- データと画像の保存先を環境変数で指定可能に変更。
- アップロード画像は指定保存先から配信。パストラバーサル防止とsandboxヘッダーを適用。
- 無料試用版の案内と検索エンジン向けnoindexを追加。
- 元アプリのソース、ローカルデータは変更なし。

## 参照

- https://render.com/docs/deploy-flask
- https://render.com/docs/blueprint-spec
- https://render.com/docs/free
