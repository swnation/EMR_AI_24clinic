"""
의사랑 EMR 4개 영역 좌표 캘리브레이션
실행: python ocr/calibrate.py

사용법:
1. 의사랑 EMR을 열어둔 상태에서 실행
2. 각 영역(증상/특이증상/상병/오더)의 좌상단→우하단을 클릭
3. 좌표가 ocr/regions.json에 저장됨
"""
import json
import os
import sys
import time

# Windows 전용
try:
    import pyautogui
except ImportError:
    print("pyautogui 필요: pip install pyautogui")
    sys.exit(1)

REGIONS_PATH = os.path.join(os.path.dirname(__file__), "regions.json")

REGION_NAMES = [
    ("symptoms", "증상 탭 (차팅 텍스트)"),
    ("special", "특이증상 탭 (과거력/특이사항)"),
    ("dx", "상병 코드 목록"),
    ("orders", "오더 목록 (약품코드 + 용량/일수)"),
]


def get_click_position(prompt_text: str) -> tuple:
    """사용자 클릭 위치를 반환"""
    print(f"  → {prompt_text}")
    print("    (3초 후 클릭 위치를 감지합니다. 해당 위치로 마우스를 이동해주세요)")
    time.sleep(3)
    x, y = pyautogui.position()
    print(f"    좌표: ({x}, {y})")
    return (x, y)


def calibrate():
    regions = {}

    print("=" * 50)
    print("의사랑 EMR 영역 캘리브레이션")
    print("=" * 50)
    print()
    print("의사랑 EMR 화면을 열어두세요.")
    print("각 영역의 좌상단/우하단을 차례로 클릭합니다.")
    print()

    for key, name in REGION_NAMES:
        print(f"\n[{name}]")
        x1, y1 = get_click_position("좌상단 위치로 마우스를 이동하세요")
        x2, y2 = get_click_position("우하단 위치로 마우스를 이동하세요")
        regions[key] = {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
        print(f"  ✓ {name}: ({x1},{y1}) → ({x2},{y2})")

    # 저장
    with open(REGIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(regions, f, indent=2, ensure_ascii=False)

    print(f"\n저장 완료: {REGIONS_PATH}")
    print("레이아웃 변경 시 다시 실행하세요.")


if __name__ == "__main__":
    calibrate()
