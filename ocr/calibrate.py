"""
의사랑 EMR 4개 영역 좌표 캘리브레이션
실행: python ocr/calibrate.py

사용법:
1. 의사랑 EMR을 열어둔 상태에서 실행
2. 각 영역(증상/특이증상/상병/오더)의 좌상단 위치로 마우스 이동 → Enter
3. 같은 영역의 우하단 위치로 마우스 이동 → Enter
4. 4개 영역을 차례로 반복하면 ocr/regions.json에 저장됨

중간에 그만두려면: Ctrl+C
"""
import json
import os
import sys
import time

try:
    import pyautogui
except ImportError:
    print("pyautogui 필요: pip install pyautogui")
    sys.exit(1)

try:
    import keyboard
except ImportError:
    print("keyboard 필요: pip install keyboard")
    sys.exit(1)

REGIONS_PATH = os.path.join(os.path.dirname(__file__), "regions.json")

REGION_NAMES = [
    ("symptoms", "증상 탭 (차팅 텍스트)"),
    ("special", "특이증상 탭 (과거력/특이사항)"),
    ("dx", "상병 코드 목록"),
    ("orders", "오더 목록 (약품코드 + 용량/일수)"),
]


def wait_for_enter_and_get_position(prompt_text: str) -> tuple:
    """마우스를 원하는 위치로 이동한 뒤 Enter 키를 누르면 현재 좌표 반환"""
    print(f"  → {prompt_text}")
    print(f"    (마우스 이동 후 Enter 키를 누르세요)")

    # 이전 Enter 입력의 잔여 감지를 피하기 위해 잠깐 대기
    time.sleep(0.3)

    keyboard.wait('enter')

    x, y = pyautogui.position()
    print(f"    좌표 기록: ({x}, {y})")
    return (x, y)


def calibrate():
    regions = {}

    print("=" * 60)
    print("  의사랑 EMR 영역 캘리브레이션 (Enter 방식)")
    print("=" * 60)
    print()
    print("  의사랑 EMR 화면을 열어두세요.")
    print("  각 영역마다 좌상단 → 우하단 순서로 마우스를 옮긴 뒤")
    print("  Enter 키를 누르면 그 시점의 마우스 좌표가 기록됩니다.")
    print()
    print("  총 4개 영역 × 2점 = 8번 Enter 입력이 필요합니다.")
    print("  중간에 그만두려면 Ctrl+C.")
    print()

    for key, name in REGION_NAMES:
        print(f"\n[{name}]")
        x1, y1 = wait_for_enter_and_get_position("좌상단 위치로 마우스를 이동한 뒤 Enter")
        x2, y2 = wait_for_enter_and_get_position("우하단 위치로 마우스를 이동한 뒤 Enter")
        regions[key] = {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
        print(f"  ✓ {name}: ({x1},{y1}) → ({x2},{y2})")

    # 저장
    with open(REGIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(regions, f, indent=2, ensure_ascii=False)

    print()
    print("=" * 60)
    print(f"  저장 완료: {REGIONS_PATH}")
    print("  레이아웃 변경 시 다시 실행하세요.")
    print("=" * 60)


if __name__ == "__main__":
    calibrate()
