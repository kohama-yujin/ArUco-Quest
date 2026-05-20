import cv2
from cv2 import aruco
import numpy as np
import pyzed.sl as sl
import asyncio
from aiortc.mediastreams import VideoStreamTrack
from av import VideoFrame
from scipy.spatial.transform import Rotation as R_scipy


class ZEDVideoTrack(VideoStreamTrack):
    def __init__(self, marker_size, fov_queue, pose_queue):
        super().__init__()
        self.fov_queue = fov_queue
        self.pose_queue = pose_queue

        # ZEDカメラの初期化
        self.zed = sl.Camera()
        init_params = sl.InitParameters()
        init_params.camera_resolution = sl.RESOLUTION.HD720
        init_params.camera_fps = 60
        isDepth = False  # 深度画像を取得するかどうか
        init_params.depth_mode = sl.DEPTH_MODE.PERFORMANCE if isDepth else sl.DEPTH_MODE.NONE

        # カメラ起動
        status = self.zed.open(init_params)
        if status != sl.ERROR_CODE.SUCCESS:
            print("The camera did not open:", status)
            exit()

        # 画像取得のためのオブジェクト
        self.image_zed = sl.Mat()

        # カメラの視野角を取得
        cam_info = self.zed.get_camera_information()
        cam_config = cam_info.camera_configuration
        left_cam_params = cam_config.calibration_parameters.left_cam
        self.vfov = left_cam_params.v_fov
        self.hfov = left_cam_params.h_fov

        # キューへ格納
        if self.fov_queue.qsize() == self.fov_queue.maxsize:
            self.fov_queue.get_nowait() # 古いデータを捨てる
        self.fov_queue.put_nowait(self.vfov)

        # カメラの内部パラメータ
        width = 1280
        height = 720
        f = left_cam_params.fx
        u0 = width / 2.0
        v0 = height / 2.0
        
        # 投影行列
        self.A = np.array([[f, 0.0, u0], [0.0, f, v0], [0.0, 0.0, 1.0]], dtype="double")
        # 歪み係数
        self.dist_coeff = np.zeros((4, 1))

        # Arucoマーカーの設定
        self.aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
        self.aruco_parameters = aruco.DetectorParameters()
        
        # マーカーの四隅（3次元点）
        self.point_3D = np.array(
            [
                (-marker_size / 2, marker_size / 2, 0.0),
                (marker_size / 2, marker_size / 2, 0.0),
                (marker_size / 2, -marker_size / 2, 0.0),
                (-marker_size / 2, -marker_size / 2, 0.0),
            ]
        )


    async def recv(self):
        pts, time_base = await self.next_timestamp()
        if self.zed.grab() == sl.ERROR_CODE.SUCCESS:

            self.zed.retrieve_image(self.image_zed, sl.VIEW.LEFT)
            frame_np = self.image_zed.get_data()
            frame_rgb = cv2.cvtColor(frame_np, cv2.COLOR_BGR2RGB)

            # PnP 計算
            frame_marker = self.compute_camera_pose(frame_rgb)

            video_frame = VideoFrame.from_ndarray(frame_marker, format="rgb24")
            video_frame.pts = pts
            video_frame.time_base = time_base
            
            return video_frame

        # フレームが取得できない場合は待機
        await asyncio.sleep(0.001)
        return await self.recv()
    
    
    def compute_camera_pose(self, frame):

        # マーカ検出
        self.corners, self.ids, _ = aruco.detectMarkers(
            frame, self.aruco_dict, parameters=self.aruco_parameters
        )
        # マーカの描画
        frame = aruco.drawDetectedMarkers(frame, self.corners, self.ids)

        # カメラ姿勢を計算（ビューイング変換行列の取得）
        if self.ids is not None:
            c = self.corners[0][0]
            x1, x2, x3, x4 = c[:, 0]
            y1, y2, y3, y4 = c[:, 1]

            self.point_2D = np.array([(x1, y1), (x2, y2), (x3, y3), (x4, y4)], dtype="double")
            _, vec_R, t_w2c_cv = cv2.solvePnP(
                self.point_3D, self.point_2D, self.A, self.dist_coeff, flags=0
            )
            R_w2c_cv = cv2.Rodrigues(vec_R)[0]

            # cv2 → Unityの座標系に変換する回転行列
            R_cv2unity = np.array([[1.0, 0.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, 1.0]])
            R_w2c_unity = np.dot(R_cv2unity, R_w2c_cv)
            t_w2c_unity = np.dot(R_cv2unity, t_w2c_cv)

            # モデリング変換（ArUco)
            R_c2w_rpy = R_w2c_unity.T
            t_c2w_rpy = -R_c2w_rpy @ t_w2c_unity

            # 世界座標系同士の変換（ArUco -> Unity)
            R_rpy2unity = np.array([[0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [-1.0, 0.0, 0.0]])
            R_c2w_unity = R_rpy2unity @ R_c2w_rpy
            t_c2w_unity = R_rpy2unity @ t_c2w_rpy

            # クォータニオンに変換
            q_c2w_unity = R_scipy.from_matrix(R_c2w_unity).as_quat()

            # キューへ格納
            pose_dict = {
                "trans": t_c2w_unity.flatten().tolist(),
                "quat": q_c2w_unity.tolist(),
            }
            if self.pose_queue.qsize() == self.pose_queue.maxsize:
                self.pose_queue.get_nowait() # 古いデータを捨てる
            self.pose_queue.put_nowait(pose_dict)

        return frame