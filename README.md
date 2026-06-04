# ArUco-Quest

## 概要
Meta Quest 3 で ArUco を動かすプロジェクトです。  
ZED-mini というステレオカメラを Meta Quest 3 の前面に固定してください。  
また、PC と Meta Quest 3 は必ず同じ Wi-Fi に接続してください。

### 関連プロジェクト

- [ArUco-Quest v2](https://github.com/kohama-yujin/ArUco-Quest-v2)  
  立体視表示と深度オクルージョンに対応しています
  
## 使用機器
- PC
- Meta Quest 3
- ZED-mini

## バージョン
- Windows 11
- Python 3.13.2
- CUDA 12.8
- ZED_SDK_Windows_cuda12.8_tensorrt10.9_v5.0.3
- Unity Hub 3.13.0
- Unity 6.1 (6000.1.12f1)
- MQDH (Meta Quest Developer Hub)

## 環境構築
### 仮想環境の作成 & 有効化
```
cd ArUco-Quest
python -m venv venv
.\venv\Scripts\activate
```
> ```
> .\.venv\Scripts\activate : このシステムではスクリプトの実行が無
> 効になっているため、ファイル \.venv\Scripts\Activate.ps1 を読み込むことができません。詳細については、「about_Execution_Policies」(https://go.microsoft.com/fwlink/?) を参照してください。
> 発生場所 行:1 文字:1
> + .\.venv\Scripts\activate
> + ~~~~~~~~~~~~~~~~~~~~~~~~
>     + CategoryInfo          : セキュリティ エラー: (: ) []、PSSecurityEx    ception
>     + FullyQualifiedErrorId : UnauthorizedAccess
> ```
> 上記のようなエラーが出た場合、PowerShellを管理者として実行し、以下のコマンドを叩いてください。
> ```
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```
> そして再度以下を実行すると仮想環境を有効化できると思います。
> ```
> .\venv\Scripts\activate
> ```

### ライブラリをインストール
```
pip install -r requirements.txt
```
> `Installing collected packages: ~~` が表示されたあとラグがありますが、`(venv) PS C:\Users\~~>`になるまで待ってください。

### CUDAのインストール  
1. Visual Studio のインストール
    - [Visual Studio](https://visualstudio.microsoft.com/ja/downloads/) から`Community`版をダウンロード
    - インストール時に「ワークロード」から`C++によるデスクトップ開発`を選択
1. [CUDA Toolkit 12.8](https://developer.nvidia.com/cuda-12-8-0-download-archive?target_os=Windows&target_arch=x86_64&target_version=11&target_type=exe_local)を開き、`cuda_12.8.x_xxx.exe`をダウンロード
1. ダウンロードした`cuda_12.8.x_xxx.exe`を管理者権限で実行し、指示に従ってインストール
1. PCを再起動
1. 再起動後、以下を実行し、`CUDA Verwsion: 12.9`となっていれば成功
```
nvidia-smi
```

### ZED SDK のインストール  
1. [ZED SDK](https://www.stereolabs.com/en-jp/developers/release)を開き、`CUDA 12 - TensorRT 10`の`ZED SDK for Windows 10/11 5.1`をダウンロード
1. ダウンロードした`~~.exe`を実行してSDKをインストールし、PCを再起動
1. 再起動後、以下を実行し、PythonAPIをインストール
```
cd .\ZED_SDK
python .\get_python_api.py
```

### WebRTC通信のポート開放
1. 「セキュリティが強化された Windows Defender ファイアウォール」を開く
1. 「受信の規則」を開き、右側ペインの「新しい規則」をクリック
1. 「ポート」を選択し「次へ」
1. 以下を個別に設定
    - 名前：websocket用
        - 「TCP」を選択し、特定のローカルポートに`5555`と入力して「次へ」
    - 名前：WebRTC用
        - 「UDP」を選択し、特定のローカルポートに`1024-65535`と入力して「次へ」
1. 「接続を許可する」を選択して「次へ」
1. 「プライベート」のみを選択して「次へ」
1. 設定した名前を入力

### Unity のインストール
1. [Unity をダウンロード](https://unity.com/ja/download)を開き、ダウンロード
1. Unity Hub をインストール
1. Unity Hub を開き、`Projects > Add > Add project from disk` で、このリポジトリの`UnityAR`フォルダを追加

### MQDH のインストール
1. [MQDHのダウンロード](https://developers.meta.com/horizon/downloads/package/oculus-developer-hub-win/?locale=ja_JP)を開き、ダウンロード
1. 解凍し、インストール

## テスト
### シグナリングサーバーを起動
```
cd ..\ArUco
python .\main.py
```
`Launch the signaling server...`と出力された状態で待機
### AR開始
1. Unity Hub を開き、`UnityAR`を開く
1. 左側の`Hierarchy`ウィンドウから`WebRTCReceiver`を選択
1. 右側の`Inspector`ウィンドウで以下の項目を入力
    - Signaling IP
        - PCのIPv4アドレス
    - Target Quad
        - `Hierarchy`ウィンドウの`Main Camera`横の「‣」を展開
        - `CaptureBackground`をドラッグ&ドロップ
    - Target Camera
        - `Hierarchy`ウィンドウの`Main Camera`をドラッグ&ドロップ
    - Z（カメラから映像までの距離）
        - 1（任意）
1. 上にある『 ▶ 』で起動

## 実行
### アプリ（apkファイル）を作成
1. Unity Hub を開き、`UnityAR`を開く
2. `File`の`Build Profiles`を開き、`Platforms`の`Android`を選択
3. 右下の`Switch Platform`をクリック
4. 終わり次第、右下の`Build`をクリックし、このリポジトリの`APK`フォルダに`apk`ファイルを作成
### アプリ（apkファイル）を Meta Quest 3 にインストール
1. MQDHを開き、`Device manager`で Meta Quest 3 が`Active`となっていることを確認
2. `Apps`の`Add Build`で先ほど作成した`apk`ファイルを選択
### シグナリングサーバーを起動
```
cd ..\ArUco
python .\main.py
```
`Launch the signaling server...`と出力された状態で待機
### AR開始
1. Meta Quest 3 を被る
2. MQDHの`Apps`から、アプリの右側にある「…」を選択し`Launch App`で起動
