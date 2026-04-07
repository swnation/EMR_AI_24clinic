"""
의사랑 EMR 화면 캡처 모듈
calibrate.py에서 저장한 regions.json 좌표 사용
"""
import json
import os
import sys

try:
    import pyautogui
    from PIL import Image
except ImportError:
    print("필요 패키지: pip install pyautogui Pillow")
    sys.exit(1)

REGIONS_PATH = os.path.join(os.path.dirname(__file__), "regions.json")


def load_regions() -> dict:
    """저장된 영역 좌표 로드"""
    if not os.path.exists(REGIONS_PATH):
        raise FileNotFoundError(
            f"regions.json 없음. 먼저 python ocr/calibrate.py 실행하세요."
        )
    with open(REGIONS_PATH, encoding="utf-8") as f:
        return json.load(f)


def capture_region(region: dict) -> Image.Image:
    """특정 영역 캡처 → PIL Image 반환"""
    x1, y1 = region["x1"], region["y1"]
    x2, y2 = region["x2"], region["y2"]
    width = x2 - x1
    height = y2 - y1
    return pyautogui.screenshot(region=(x1, y1, width, height))


def capture_all() -> dict:
    """4개 영역 전부 캡처 → {name: PIL Image} dict 반환"""
    regions = load_regions()
    result = {}
    for name, coords in regions.items():
        result[name] = capture_region(coords)
    return result


if __name__ == "__main__":
    # 테스트: 4개 영역 캡처 후 파일로 저장
    images = capture_all()
    os.makedirs("ocr/captures", exist_ok=True)
    for name, img in images.items():
        path = f"ocr/captures/{name}.png"
        img.save(path)
        print(f"저장: {path} ({img.size[0]}x{img.size[1]})")
