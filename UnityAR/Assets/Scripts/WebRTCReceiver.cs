using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using Unity.WebRTC;
using System.Globalization;
using WebSocketSharp;


public class WebRTCReceiver : MonoBehaviour
{
    public string signalingIP;
    public GameObject targetQuad;
    public Camera targetCamera;
    public float z;

    private Renderer quadRenderer;
    private Transform quadTransform;
    private object lockObj = new object();

    // WebRTC用
    private RTCPeerConnection pc;
    private RTCDataChannel dataChannel;
    private RTCConfiguration config;

    // WebSocket(シグナリング)用
    private WebSocket ws;
    private Queue<string> sdpQueue = new Queue<string>();
    private Queue<string> candidateQueue = new Queue<string>();
    private List<RTCIceCandidateInit> pendingCandidates = new List<RTCIceCandidateInit>();
    private bool remoteDescSet = false;

    // ビデオトラック用
    private Queue<Texture> videoTextureQueue = new Queue<Texture>();

    void Start()
    {   
        // Quad情報
        quadRenderer = targetQuad.GetComponent<Renderer>();
        quadTransform = targetQuad.GetComponent<Transform>();

        // 重要
        StartCoroutine(WebRTC.Update());

        // STUN サーバ設定
        config = new RTCConfiguration
        {
            iceServers = new RTCIceServer[]
            {
                new RTCIceServer
                {
                    urls = new[] { "stun:stun.l.google.com:19302" }
                }
            }
        };

        // シグナリング用 WebSocket に接続
        ws = new WebSocket($"ws://{signalingIP}:8080");
        ws.OnOpen += (s, e) => { Debug.Log("[Unity] WS opened"); };
        ws.OnError += (s, e) => { Debug.LogWarning("[Unity] WS error: " + e.Message); };
        ws.OnClose += (s, e) => { Debug.Log("[Unity] WS closed: " + e.Reason); };
        // 受信メッセージはキューへ（SDP/Candidate）
        ws.OnMessage += (s, e) =>
        {
            string text = e.Data;
            if (text.Contains("\"type\":\"candidate\"") || text.Contains("\"type\": \"candidate\""))
            {
                lock (candidateQueue) candidateQueue.Enqueue(text);
            }
            else
            {
                lock (sdpQueue) sdpQueue.Enqueue(text);
            }
        };
        ws.ConnectAsync();

        // コルーチン
        StartCoroutine(SetupConnection());
    }

    void Update()
    {
        // ビデオテクスチャを適用
        lock (videoTextureQueue)
        {
            while (videoTextureQueue.Count > 0)
            {
                var tex = videoTextureQueue.Dequeue();
                if (quadRenderer != null && tex != null)
                {
                    quadRenderer.material.mainTexture = tex;
                }
            }
        }
    }

    IEnumerator SetupConnection()
    {
        pc = new RTCPeerConnection(ref config);

        // ビデオトラック
        pc.OnTrack = e =>
        {
            if (e.Track is VideoStreamTrack videoTrack)
            {
                videoTrack.OnVideoReceived += texture =>
                {
                    lock (videoTextureQueue)
                    {
                        videoTextureQueue.Enqueue(texture);
                    }
                };
            }
        };

        // Offerの受信（タイムアウトあり）
        string offerMsg = null;
        float timeout = 30f;    // sec
        float start = Time.time;
        while (Time.time - start < timeout)
        {
            lock (sdpQueue)
            {
                if (sdpQueue.Count > 0)
                {
                    offerMsg = sdpQueue.Dequeue();
                    break;
                }
            }
            yield return null;
        }
        if (string.IsNullOrEmpty(offerMsg))
        {
            Debug.LogWarning("[Unity] No offer received within timeout.");
            yield break;
        }

        // Offer をパースしてセット
        var sdpMsg = JsonUtility.FromJson<SDPMessage>(offerMsg);
        if (sdpMsg == null || sdpMsg.type != "offer")
        {
            Debug.LogWarning("[Unity] Received message is not a valid offer.");
            yield break;
        }

        var offerDesc = new RTCSessionDescription { type = RTCSdpType.Offer, sdp = sdpMsg.sdp };
        var opRemote = pc.SetRemoteDescription(ref offerDesc);
        yield return opRemote;
        if (opRemote.IsError)
        {
            Debug.LogError("[Unity] SetRemoteDescription failed: " + opRemote.Error.message);
            yield break;
        }

        // Answer（Local）
        var opAnswer = pc.CreateAnswer();
        yield return opAnswer;
        if (opAnswer.IsError)
        {
            Debug.LogError("[Unity] CreateAnswer failed: " + opAnswer.Error.message);
            yield break;
        }
        var answerDesc = opAnswer.Desc;
        var opLocal = pc.SetLocalDescription(ref answerDesc);
        yield return opLocal;
        if (opLocal.IsError)
        {
            Debug.LogError("[Unity] SetLocalDescription failed: " + opLocal.Error.message);
            yield break;
        }

        // Answer（Remote）
        if (ws != null && ws.IsAlive)
        {
            var reply = new SDPMessage { type = "answer", sdp = answerDesc.sdp };
            ws.Send(JsonUtility.ToJson(reply));
            Debug.Log("[Unity] Sent Answer.");
        }

        // remote description がセットされたので保留中の候補を追加
        remoteDescSet = true;
        if (pendingCandidates.Count > 0)
        {
            foreach (var c in pendingCandidates)
            {
                var cand = new RTCIceCandidate(c);
                pc.AddIceCandidate(cand);
            }
            pendingCandidates.Clear();
            Debug.Log("[Unity] Flushed pending candidates");
        }

        // 自分の ICE 候補が見つかったらシグナリングで送る
        pc.OnIceCandidate = candidate =>
        {
            if (candidate == null) return;
            var cm = new CandidateMessage
            {
                type = "candidate",
                candidate = candidate.Candidate,
                sdpMid = candidate.SdpMid,
                sdpMLineIndex = candidate.SdpMLineIndex
            };
            if (ws != null && ws.IsAlive) ws.Send(JsonUtility.ToJson(cm));
        };
        pc.OnIceConnectionChange = state => { Debug.Log("[Unity] ICE state: " + state.ToString()); };
         
        // DataChannel を受け取る
        pc.OnDataChannel = channel =>
        {
            dataChannel = channel;
            // 既にOpenかどうか
            if (channel.ReadyState == RTCDataChannelState.Open)
            {
                Debug.Log("[Unity] Remote DataChannel already Open. Setup immediately.");
                SetupDataChannelCallbacks(channel);
            }
            else
            {
                channel.OnOpen += () => 
                {
                    Debug.Log("[Unity] Remote DataChannel Opened: " + channel.Label);
                    SetupDataChannelCallbacks(channel);
                };
            }

            channel.OnClose += () =>
            {
                Debug.LogWarning("[Unity] DataChannel Closed.");
                dataChannel = null;
            };
            
            channel.OnError += (e) => Debug.LogError("[Unity] DataChannel Error: " + e);
        };

        StartCoroutine(ProcessCandidateQueue());
    }

    // コールバック登録処理を共通化
    private void SetupDataChannelCallbacks(RTCDataChannel channel)
    {
        channel.OnMessage += bytes =>
        {
            string jsonString = System.Text.Encoding.UTF8.GetString(bytes);
            ProcessDataChannelJson(jsonString);
        };
    }
    
    // 受け取った JSON の処理
    private void ProcessDataChannelJson(string json)
    {        
        if (string.IsNullOrWhiteSpace(json))
        {
            Debug.LogWarning("[Unity] Empty JSON message");
            return;
        }

        // ヘッダー解析
        MessageHeader header = JsonUtility.FromJson<MessageHeader>(json);
        Debug.Log("[Unity] DataChannel JSON type = '" + header.type + "'");

        // Type ごとに処理
        switch (header.type)
        {
            case "FOV_UPDATE":
                FovData fovData = JsonUtility.FromJson<FovData>(json);
                float vFov = fovData.vFov;
                lock (lockObj)
                {
                    targetCamera.fieldOfView = vFov;

                    // 水平FOVも計算可能
                    float hFov = 2f * Mathf.Atan(Mathf.Tan(vFov * Mathf.Deg2Rad / 2f) * targetCamera.aspect) * Mathf.Rad2Deg;

                    // Quadの幅と高さを計算
                    float height = 2f * z * Mathf.Tan(vFov * Mathf.Deg2Rad / 2f);
                    float width = 2f * z * Mathf.Tan(hFov * Mathf.Deg2Rad / 2f);

                    // Quadのサイズを設定
                    quadTransform.localPosition = new Vector3(0f, 0f, z);
                    quadTransform.localScale = new Vector3(width, height, 1f);
                }
                break;

            case "CAMERA_POSE":
                CameraPose cameraPose = JsonUtility.FromJson<CameraPose>(json);
                float px = cameraPose.px / 100; // cm → m
                float py = cameraPose.py / 100; // cm → m
                float pz = cameraPose.pz / 100; // cm → m
                float qx = cameraPose.qx;
                float qy = cameraPose.qy;
                float qz = cameraPose.qz;
                float qw = cameraPose.qw;
                lock (lockObj)
                {
                    targetCamera.transform.localPosition = new Vector3(px, py, pz);
                    targetCamera.transform.localRotation = new Quaternion(qx, qy, qz, qw);
                }
                break;

            default:
                Debug.Log("[Unity] Unknown DataChannel JSON type: " + header.type);
                break;
        }
    }

    IEnumerator ProcessCandidateQueue()
    {
        while (true)
        {
            string msg = null;
            lock (candidateQueue)
            {
                if (candidateQueue.Count > 0) msg = candidateQueue.Dequeue();
            }

            if (!string.IsNullOrEmpty(msg))
            {
                var cm = JsonUtility.FromJson<CandidateMessage>(msg);
                if (cm != null && cm.type == "candidate")
                {
                    var init = new RTCIceCandidateInit { candidate = cm.candidate, sdpMid = cm.sdpMid, sdpMLineIndex = cm.sdpMLineIndex };
                    if (remoteDescSet && pc != null)
                    {
                        var candObj = new RTCIceCandidate(init);
                        pc.AddIceCandidate(candObj);
                    }
                    else
                    {
                        pendingCandidates.Add(init);
                    }
                }
            }

            yield return null;
        }
    }

    private void OnDestroy()
    {
        dataChannel?.Dispose();
        pc?.Close();
        pc?.Dispose();
        if (ws != null)
        {
            ws.Close();
            ws = null;
        }
    }

    [System.Serializable]
    public class SDPMessage
    {
        public string type;
        public string sdp;
    }

    [System.Serializable]
    public class CandidateMessage
    {
        public string type;
        public string candidate;
        public string sdpMid;
        public int? sdpMLineIndex;
    }

    [System.Serializable]
    public class MessageHeader
    {
        public string type;
    }

    [System.Serializable]
    public class FovData
    {
        public string type;
        public float vFov;
    }

    [System.Serializable]
    public class CameraPose
    {
        public string type;
        public float px;
        public float py;
        public float pz;
        public float qx;
        public float qy;
        public float qz;
        public float qw;
    }
}