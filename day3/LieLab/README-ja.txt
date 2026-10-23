Lie Lab 配布パッケージ
=====================

【画面を渡したい場合】
site/dist/ がWebサイトのHTML・CSS・JavaScript一式です。
このフォルダをHTTPS対応の静的ホスティングへ置くと、カメラ録画・保存が使えます。
カメラにはブラウザの許可とHTTPSまたはlocalhostが必要です。
ファイルをダブルクリックするだけではカメラ機能を使えない場合があります。
公開版での動画解析には、別途解析サーバーが必要です。
同梱画面は公開URL上ではローカル解析への案内を表示する構成です。

【動画を解析したい場合】
Python 3.11、OpenFaceのFeatureExtraction実行ファイル・必要なモデル・ライブラリが別途必要です。
OpenFace本体と学習用の裁判動画は、このZIPには含めていません。

1. Python 3.11で仮想環境を作成して有効化する。
   python3.11 -m venv .venv
   source .venv/bin/activate
   （Windows: .venv\Scripts\activate）
2. 必要な依存をインストールする。
   pip install -r requirements-temporal-lock.txt
   pip install -r requirements-minirocket-lock.txt
3. config.yaml の openface_binary を、配布先PCにインストールした
   FeatureExtraction実行ファイルのパスへ変更する。
   絶対パスでも指定できます。
4. このREADMEのあるフォルダで起動する。
   python -m src.web
5. http://127.0.0.1:8765/ をブラウザで開く。

既存のMacで開発中のアプリを起動している場合は、ポート重複を避けるため
python -m src.web --port 8766 でも起動できます。
このサーバーはlocalhost専用です。外部公開するための認証・HTTPS・負荷対策は含みません。
第三者のPCでのOpenFaceの導入・動作は未検証です。

【内容】
site/dist/       Web画面。2質問モード、録画、結果ページ。
src/             Python解析サーバーと既存の特徴量・モデル処理。
models/          SVM・GRU・MiniRocketの学習済みモデル。
requirements*    依存パッケージと再現用バージョン。
config.yaml      動作設定。
licenses/        元プロジェクトのライセンス・著作権表記。

【取り扱い】
録画は音声なし。解析時の動画・抽出データはMac内の一時フォルダで処理し、終了後に削除します。
結果メタデータはサーバーのメモリ、結果ページ表示用JSONは同じタブのsessionStorageに保持します。
判定はエンタメ・研究用の参考結果で、嘘や真実の証明ではありません。
joblib等のモデルは信頼できるものだけを読み込んでください。
OpenFaceを用いた利用には同梱の非商用研究利用等の条件を確認してください。
依存ソフトには各ソフトの利用条件が適用されます。
