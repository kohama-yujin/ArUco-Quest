"""
ArUco マーカーシート生成ツール
A4 PDFの中央に1つのマーカーを配置
"""

import os
import cv2
from pathlib import Path
from PIL import Image


class MarkerSheetGenerator:
    """ArUcoマーカーシート生成クラス"""
    
    def __init__(self, marker_id: int = 0, marker_size_cm: float = 9.3):
        """
        初期化
        
        Args:
            marker_id: マーカーID
            marker_size_cm: マーカーサイズ（cm）
        """
        self.marker_id = marker_id
        self.marker_size_cm = marker_size_cm
        self.dpi = 300
        
        # A4サイズ (cm) -> ピクセル変換
        self.marker_size_px = int(marker_size_cm * self.dpi / 2.54)
        self.a4_width_px = int(21.0 * self.dpi / 2.54)   # A4幅
        self.a4_height_px = int(29.7 * self.dpi / 2.54)  # A4高さ
        
        # 出力ディレクトリ作成
        Path("output").mkdir(exist_ok=True)
        
        # ArUcoディクショナリー取得
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    
    def generate_marker(self) -> Image.Image:
        """ArUcoマーカーを生成して返す"""
        marker_img = cv2.aruco.generateImageMarker(
            self.aruco_dict,
            self.marker_id,
            self.marker_size_px,
            borderBits=1
        )
        return Image.fromarray(marker_img, mode='L').convert('RGB')
    
    def generate_and_save(self, filename: str = "aruco_marker.pdf") -> str:
        """A4 PDFの中央にマーカーを配置して保存"""
        # 白いA4シート作成
        sheet = Image.new('RGB', (self.a4_width_px, self.a4_height_px), color='white')
        
        # マーカーを生成
        marker = self.generate_marker()
        
        # 中央に配置
        x = (self.a4_width_px - self.marker_size_px) // 2
        y = (self.a4_height_px - self.marker_size_px) // 2
        sheet.paste(marker, (x, y))
        
        # PDF保存
        output_path = os.path.join("output", filename)
        sheet.convert('1').save(output_path, dpi=(self.dpi, self.dpi))
        
        print(f"マーカーシート作成完了: {output_path}")
        return output_path


def main():
    """メイン関数"""
    generator = MarkerSheetGenerator(marker_id=0)
    generator.generate_and_save()


if __name__ == "__main__":
    main()
