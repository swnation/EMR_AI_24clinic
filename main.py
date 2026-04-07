"""
EMR_AI_24clinic - 의사랑 EMR 보조 도구
실행: python main.py

기능:
- F12: 의사랑 화면 스캔 → 상병/오더 체크
- 브라우저 UI: http://localhost:8080
"""
import subprocess
import sys
import webbrowser
import time
import threading
import json

# Windows 전용 모듈은 조건부 임포트
try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False
    print("[WARN] keyboard 모듈 없음. F12 단축키 비활성화.")
    print("       pip install keyboard")


def open_browser():
    time.sleep(1.5)
    webbrowser.open("http://localhost:8080")


def on_f12():
    """F12 눌렸을 때: 화면 캡처 → OCR → 체크 → 결과 전송"""
    try:
        from ocr.capture import capture_all
        from ocr.reader import ocr_all
        from ocr.parser import parse_all
        from app.checker import run_check

        print("\n[F12] 스캔 시작...")

        # 1. 캡처
        images = capture_all()
        print("  캡처 완료")

        # 2. OCR
        texts = ocr_all(images)
        print("  OCR 완료")

        # 3. 파싱
        parsed = parse_all(texts)
        print(f"  파싱: dx={len(parsed['dx'])}건, orders={len(parsed['orders'])}건")

        # 4. 체크
        results = run_check(
            dx=parsed["dx"],
            orders=parsed["orders"],
            symptoms=parsed["symptoms"],
            patient_type=parsed["patient_type"],
            order_details=parsed["order_details"],
        )

        # 5. 결과 표시
        err_count = sum(1 for r in results if r["level"] == "err")
        warn_count = sum(1 for r in results if r["level"] == "warn")
        print(f"  결과: {len(results)}건 (ERR: {err_count}, WARN: {warn_count})")
        for r in results:
            icon = {"err": "X", "warn": "!", "info": "i", "ok": "V"}.get(r["level"], "?")
            print(f"    [{icon}] {r['message']}")

        # 6. 브라우저로 결과 전송 (localhost API)
        try:
            import urllib.request
            data = json.dumps({
                "dx": parsed["dx"],
                "orders": parsed["orders"],
                "order_details": parsed["order_details"],
                "symptoms": parsed["symptoms"],
                "patient_type": parsed["patient_type"],
            }).encode("utf-8")
            req = urllib.request.Request(
                "http://localhost:8080/check",
                data=data,
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=3)
        except Exception:
            pass  # 서버 응답 실패해도 콘솔 출력은 이미 완료

        print("[F12] 스캔 완료\n")

    except FileNotFoundError as e:
        print(f"[F12] 오류: {e}")
        print("       먼저 python ocr/calibrate.py를 실행하세요.")
    except Exception as e:
        print(f"[F12] 오류: {e}")


def start_hotkey():
    """F12 단축키 등록"""
    if not HAS_KEYBOARD:
        return
    keyboard.add_hotkey("F12", on_f12)
    print("F12 단축키 등록 완료 (의사랑 옆에서 F12 누르세요)")


if __name__ == "__main__":
    print("=" * 50)
    print("  EMR_AI_24clinic 시작")
    print("  http://localhost:8080")
    print("  F12: 의사랑 화면 스캔")
    print("  종료: Ctrl+C")
    print("=" * 50)
    print()

    # F12 단축키 (별도 스레드)
    threading.Thread(target=start_hotkey, daemon=True).start()

    # 브라우저 자동 열기
    threading.Thread(target=open_browser, daemon=True).start()

    # FastAPI 서버 시작
    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "app.server:app",
        "--host", "127.0.0.1",
        "--port", "8080",
        "--reload"
    ])
