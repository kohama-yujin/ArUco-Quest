import asyncio
import json
import websockets
import cv2
from aiortc import RTCPeerConnection, RTCConfiguration, RTCIceServer, RTCSessionDescription

from config import MARKER_SIZE
from ZEDVideoTrack import ZEDVideoTrack


# STUN のみの設定
config = RTCConfiguration(
    iceServers=[
        RTCIceServer(urls=["stun:stun.l.google.com:19302"])
    ]
)

async def send_pose_data(channel, pose_queue):
    print("Compute camera pose task started.")

    while True:
        pose_dict = None

        try:
            # キュー変更まで待機
            pose_dict = await pose_queue.get()

            # チャンネル状態チェック
            if channel.readyState != 'open':
                print(f"Error: DataChannel state changed to '{channel.readyState}'. Aborting send.")
                break

            pose_json = json.dumps({
                "type": "CAMERA_POSE",
                "px": pose_dict["trans"][0],
                "py": pose_dict["trans"][1],
                "pz": pose_dict["trans"][2],
                "qx": pose_dict["quat"][0],
                "qy": pose_dict["quat"][1],
                "qz": pose_dict["quat"][2],
                "qw": pose_dict["quat"][3],
            })
            
            # DataChannelで送信
            channel.send(pose_json)
            await asyncio.sleep(0.02)

        except Exception as e:
            # 送信エラー
            print(f"Error sending pose data: {type(e).__name__} - {e}")
            break

        finally:
            if pose_dict is not None:
                # キューから取り出したことを通知
                pose_queue.task_done()
        
        
async def handler(ws):
    # 共有キューの作成
    fov_queue = asyncio.Queue(1)
    pose_queue = asyncio.Queue(1)
    # RTCオブジェクト
    pc = RTCPeerConnection(configuration=config)
    # ビデオトラック
    pc.addTrack(ZEDVideoTrack(MARKER_SIZE, fov_queue, pose_queue))

    # Trickle ICE で Candidate を送信
    @pc.on("icecandidate")
    def on_icecandidate(candidate):
        if candidate is None:
            return
        cstr = getattr(candidate, 'candidate', None)
        msg = {
            "type": "candidate",
            "candidate": cstr if cstr is not None else str(candidate),
            "sdpMid": getattr(candidate, 'sdpMid', None),
            "sdpMLineIndex": getattr(candidate, 'sdpMLineIndex', None)
        }
        asyncio.create_task(ws.send(json.dumps(msg)))

    # DataChannel 作成
    channel = pc.createDataChannel("camera_info", ordered=True, maxRetransmits=0)
    
    @channel.on("open")
    async def on_open():
        print("DataChannel opened.")
        await asyncio.sleep(0.1)

        # 垂直視野角
        v_fov = fov_queue.get_nowait()
        channel.send(json.dumps({
            "type": "FOV_UPDATE",
            "vFov": v_fov
        }))
        print(f"Sent vfov= {v_fov}.")

        asyncio.create_task(send_pose_data(channel, pose_queue))

    @channel.on("close")
    def on_close():
        print("DataChannel closed.")
    
    @channel.on("message")
    def on_message(msg):
        print("Unity:", msg)

    # Offer 作成
    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)
    await ws.send(json.dumps({
        "type": pc.localDescription.type,
        "sdp": pc.localDescription.sdp
    }))
    print("Sent Offer.")

    # Unity からのメッセージを処理 (Answer / Candidate)
    while True:
        # 受信
        message = await ws.recv()
        try:
            msg = json.loads(message)
        except Exception:
            print("Received non-json message from WS")
            continue

        typ = msg.get("type")
        if typ == "answer":
            answer = RTCSessionDescription(msg["sdp"], msg["type"])
            await pc.setRemoteDescription(answer)
            print("Set remote description with answer")
            break
        elif typ == "candidate":
            cand = {
                "candidate": msg.get("candidate"),
                "sdpMid": msg.get("sdpMid"),
                "sdpMLineIndex": msg.get("sdpMLineIndex")
            }
            await pc.addIceCandidate(cand)
            print("Added remote candidate from Unity")
        else:
            print("Unknown signaling message type:", typ)

    await asyncio.Future()

async def main():
    async with websockets.serve(handler, "0.0.0.0", 8080):
        print("Launch the signaling server...")
        await asyncio.Future()

asyncio.run(main())
