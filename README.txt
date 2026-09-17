【アプリ名】
てくてく秋田

【アプリの概要】
秋田県内の「場所への投稿」「イベント情報」「道路状況」を、地図と
タイムラインで共有する Web アプリケーションである。登録した場所と投稿を
結び付け、地域の情報を種類ごとに探せるようにしている。

【主な機能】
・場所への投稿、イベント情報、道路状況の 3 種類の投稿・閲覧
・ホーム画面で投稿種別ごとに切り替えて表示
・カテゴリー選択、キーワード検索、画像（最大 5 枚）添付、いいね、返信
・イベントの開催日時・期限の設定、期限切れイベントの非表示
・地図表示、場所の登録、場所リスト、種類別フィルター
・投稿と場所の紐付け、現在地表示、出発地・到着地を選ぶルート案内
・アカウント登録、ログイン、表示名・パスワード変更、投稿者本人の編集・削除
・投稿に応じたアカウントレベルの上昇、設定画面でのレベルインジケーター表示
・管理者による投稿削除、外部イベント候補の承認後公開

【動作環境・使用言語】
OS: Windows 10 / 11
言語: Python 3.10 以上、HTML / CSS / JavaScript
Web フレームワーク: Flask 3.0 以上
データベース: SQLite
ブラウザ: Google Chrome または Microsoft Edge の最新版
ネットワーク: 初回のライブラリ導入時、および地図・住所取得・経路案内の利用時に必要

【必要ライブラリ】
Flask 3.0 以上
Flask-SQLAlchemy 3.1 以上
Requests 2.31 以上
Werkzeug 3.0 以上
※ requirements.txt を使用して導入する。

【インストール方法】
1. PowerShell を開き、展開した tekuteku フォルダーへ移動する。
   cd "<展開先フォルダー>"
2. 仮想環境を作成する。
   python -m venv .venv
3. PowerShell の実行ポリシーで止まる場合は、同じ画面で次を一度だけ実行する。
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
4. 仮想環境を有効化する。
   .\.venv\Scripts\activate
5. ライブラリを導入する。
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt

【起動方法】
1. 仮想環境を有効化済みの PowerShell で、次を実行する。
   python app.py

起動後は通常ブラウザが自動で開く。開かない場合は、ブラウザで
http://127.0.0.1:5000 を開く。終了時は PowerShell で Ctrl + C を押す。

python が認識されない場合は py app.py を試す。仮想環境の Python を
直接実行する場合の先頭は ..venv ではなく .\.venv である。
例: & ".\.venv\Scripts\python.exe" app.py

【基本操作】
1. 「登録」からアカウントを作成してログインする。
2. ホームで投稿の種類を切り替えて閲覧する。
3. 「投稿」画面から投稿種別を選び、必要事項を入力して投稿する。
   イベントでは期限を設定できる。
4. 「地図」画面で地図上をクリックして場所を登録する。登録済み場所は投稿先に選べる。
5. 現在地を表示する場合はブラウザの位置情報利用を許可する。ルート案内では
   出発地点、到着地点の順に地図または場所マーカーを選択する。
6. ログイン後、「設定」画面の「アカウント」で現在のレベルとインジケーターを確認する。

【アカウントレベル・インジケーター】
・新規アカウントは Lv.1 から始まり、投稿するたびにレベルが 1 上がる。
・設定画面には現在のレベルを数値とバー型のインジケーターで表示する。
・バーは 10 レベルごとの区間で、次の目標までの進み具合を示す。
  例: Lv.12 では Lv.10 ～ Lv.20 の区間を表示し、バーは 20% になる。
  「次の目標 Lv.20 まであと8投稿」のように、目標と残り投稿数も表示する。
・Lv.10、Lv.20 などの区切りに達すると、次の区間に切り替わり、バーは 0% から始まる。
  レベル自体は下がらず、上限は設けていない。
・レベルは表示専用で、設定画面から直接変更することはできない。

【使用時の注意事項】
・位置情報はブラウザの許可を得た場合だけ取得する。
・地図、住所の逆引き、経路案内は外部サービスに依存するため、ネットワーク未接続時、
  利用制限時、障害時には利用できない。
・投稿画像は PNG / JPG / JPEG / GIF、最大 5 枚、アプリ全体の受信上限は 16 MB である。
・公開運用時は SECRET_KEY を環境変数に設定し、バックアップ・アクセス制御を別途行う。

【既知の不具合・制限】
・現時点で再現手順が確立したアプリ固有の不具合は確認されていない。
・多数同時接続時および大量データ保存時の性能は未検証である。
・OpenStreetMap、Nominatim、OSRM の公開サービスが停止または利用制限された場合、
  地図表示、住所取得、経路案内の一部または全部を利用できない。

【使用した外部ライブラリ・サービス・データ】
名称: Flask
用途: Web フレームワーク
出典: https://flask.palletsprojects.com/
ライセンス: BSD-3-Clause

名称: Flask-SQLAlchemy
用途: SQLite の操作
出典: https://flask-sqlalchemy.palletsprojects.com/
ライセンス: BSD-3-Clause

名称: Requests
用途: HTTP 通信
出典: https://requests.readthedocs.io/
ライセンス: Apache License 2.0

名称: Werkzeug
用途: Web ユーティリティ
出典: https://werkzeug.palletsprojects.com/
ライセンス: BSD-3-Clause

名称: Leaflet
用途: 地図表示
出典: https://leafletjs.com/
ライセンス: BSD-2-Clause

名称: Leaflet Routing Machine
用途: 経路表示の画面部品
出典: https://www.liedman.net/leaflet-routing-machine/
ライセンス: ISC License

名称: Bootstrap Icons
用途: 画面内のアイコン
出典: https://icons.getbootstrap.com/
ライセンス: MIT License

名称: OpenStreetMap
用途: 地図データ・地図タイル
出典: https://www.openstreetmap.org/
ライセンス: Open Database License (ODbL) 1.0。地図画面に著作権表示を行う。

名称: Nominatim
用途: 緯度・経度から住所を取得する逆ジオコーディング
出典: https://nominatim.openstreetmap.org/
ライセンス・利用条件: 基礎データは OpenStreetMap の ODbL 1.0。
https://operations.osmfoundation.org/policies/nominatim/ の利用方針を遵守する。

名称: OSRM 公開サーバー
用途: 自動車経路の検索
出典: https://project-osrm.org/
ライセンス・利用条件: OSRM は BSD-2-Clause。公開サーバーは利用条件を確認して使用する。

【同梱音声】
static/audio/click.mp3 
用途: ボタン押下時の効果音
出典: https://soundeffect-lab.info/sound/button
ライセンス・利用条件: 効果音ラボ利用規約に従う。商用利用可、クレジット表記不要。
音声ファイル単体の再配布および効果音を主目的とするコンテンツでの配布は禁止。

【Render無料試用版】
公開手順は RENDER_DEPLOY.md を参照。
このコピーには既存アカウント・投稿・画像は含まれない。
無料版は休止・再起動・再デプロイ時にデータが失われる。
