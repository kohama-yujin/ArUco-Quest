# ArUco-Quest

## 環境
- Windows 11
- CUDA 12.8
- ZED_SDK_Windows_cuda12.8_tensorrt10.9_v5.0.3
- Unity Hub 3.13.0
- Unity 6.1 (6000.1.12f1)
- MQDH (Meta Quest Developer Hub)

### 環境構築
1. 仮想環境の作成 & 有効化
```
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

2. ライブラリをインストール
```
pip install -r requirements.txt
```
> `Installing collected packages: ~~` が表示されたあとラグがありますが、`(venv) PS C:\Users\~~>`になるまで待ってください。

3. ZED SDK のインストール  
[ZED SDK](https://www.stereolabs.com/en-jp/developers/release)を開き、`CUDA 12 - TensorRT 10`の`ZED SDK for Windows 10/11 5.1`をダウンロードしてください。  
ダウンロードした`~~.exe`を実行してSDKをインストールし、PCを再起動してください。  
再起動後、`C:\Program Files (x86)\ZED SDK`にある`get_python_api.py`を適当なフォルダにコピーしてから実行し、PythonAPIをインストールしてください。  
```
python ~~\get_python_api.py
```

4. CUDAのインストール
[CUDA Toolkit 12.8](https://developer.nvidia.com/cuda-12-8-0-download-archive?target_os=Windows&target_arch=x86_64&target_version=11&target_type=exe_local)を開き、`cuda_12.8.x_xxx.exe`をダウンロードしてください。
ダウンロードした`cuda_12.8.x_xxx.exe`を管理者権限で実行し、指示に従ってインストールしてください。


## 実行
```
cd .\ArUco
python .\main.py
```
