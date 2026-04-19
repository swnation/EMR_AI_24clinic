"""
Windows OCR 텍스트 추출 모듈
winocr 패키지 사용 (Python 3.12+ 호환)

두 가지 전처리 버전 비교 가능:
- _preprocess_minimal: RGB 변환만 (winocr 호환용 최소 처리)
- _preprocess_heavy: 기존 버전 (4배 업스케일 + 그레이 + 대비 + 선명 + 이진화)

기본값은 minimal. 아래 `_preprocess = ...` 줄에서 교체 가능.
직접 실행하면 (python ocr/reader.py) 두 버전 결과를 나란히 출력하여 비교.
"""
import sys

try:
    from PIL import Image, ImageEnhance
except ImportError:
    print("필요: pip install Pillow")
    sys.exit(1)


def _is_windows():
    return sys.platform == "win32"


# =========================================================
# 전처리 버전들
# =========================================================

def _preprocess_minimal(image: Image.Image) -> Image.Image:
    """최소 전처리: RGB 변환만 (Snipping Tool과 가장 가까운 출발점)"""
    return image.convert("RGB")


def _preprocess_heavy(image: Image.Image) -> Image.Image:
    """기존 전처리: 4배 업스케일 + 그레이 + 대비 2.0 + 선명 2.0 + 이진화 140"""
    w, h = image.size
    image = image.resize((w * 4, h * 4), Image.LANCZOS)
    image = image.convert("L")
    image = ImageEnhance.Contrast(image).enhance(2.0)
    image = ImageEnhance.Sharpness(image).enhance(2.0)
    threshold = 140
    image = image.point(lambda p: 255 if p > threshold else 0)
    return image.convert("RGB")


# ── 현재 파이프라인에서 사용할 전처리 ──
# 비교 실험 결과 좋은 쪽으로 이 한 줄만 바꾸면 됨.
_preprocess = _preprocess_minimal
# _preprocess = _preprocess_heavy


# =========================================================
# OCR 인터페이스
# =========================================================

def ocr_image(image: Image.Image) -> str:
    """이미지에서 텍스트 추출 (전처리 + OCR)"""
    if _is_windows():
        try:
            from winocr import recognize_pil_sync
            processed = _preprocess(image)
            result = recognize_pil_sync(processed, 'ko')
            return result.get('text', '') if isinstance(result, dict) else ''
        except Exception as e:
            return f"[Windows OCR 실패: {e}]"
    else:
        return "[OCR는 Windows에서만 동작합니다]"


def ocr_all(images: dict) -> dict:
    """4개 영역 이미지 dict → 텍스트 dict 반환"""
    result = {}
    for name, img in images.items():
        result[name] = ocr_image(img)
    return result


# =========================================================
# 비교 테스트 모드 (python ocr/reader.py 로 직접 실행)
# =========================================================

def _run_ocr_with(preproc, image):
    """주어진 전처리 함수로 OCR 실행"""
    try:
        from winocr import recognize_pil_sync
        processed = preproc(image)
        result = recognize_pil_sync(processed, 'ko')
        return result.get('text', '') if isinstance(result, dict) else ''
    except Exception as e:
        return f"[실패: {e}]"


def _compare_mode():
    """captures/ 폴더의 이미지 각각에 대해 minimal vs heavy 결과 나란히 출력"""
    import os

    captures_dir = "ocr/captures"
    if not os.path.isdir(captures_dir):
        print("캡처 폴더 없음.")
        print("  해결: python ocr/capture.py 먼저 실행")
        return

    if not _is_windows():
        print("Windows에서만 동작합니다.")
        return

    files = [f for f in sorted(os.listdir(captures_dir)) if f.endswith(".png")]
    if not files:
        print("캡처 파일 없음. python ocr/capture.py 먼저 실행")
        return

    print()
    print("=" * 72)
    print(" OCR 전처리 비교: [A] 최소 전처리  vs  [B] 기존 전처리")
    print("=" * 72)

    for f in files:
        img = Image.open(os.path.join(captures_dir, f))
        print()
        print("█" * 72)
        print(f"  파일: {f}    원본 크기: {img.size[0]}x{img.size[1]}")
        print("█" * 72)

        text_min = _run_ocr_with(_preprocess_minimal, img)
        text_heavy = _run_ocr_with(_preprocess_heavy, img)

        print()
        print("┌─ [A] 최소 전처리 (RGB 변환만) " + "─" * 40)
        print(text_min.strip() if text_min.strip() else "(빈 결과)")
        print("└" + "─" * 71)
        print()
        print("┌─ [B] 기존 전처리 (4배+그레이+대비+선명+이진화) " + "─" * 22)
        print(text_heavy.strip() if text_heavy.strip() else "(빈 결과)")
        print("└" + "─" * 71)

    print()
    print("=" * 72)
    print(" 판단: Snipping Tool 결과와 더 비슷한 쪽이 선택.")
    print("       보통 [A]가 나을 가능성이 높음 (Snipping Tool도 가벼운 전처리).")
    print("=" * 72)


if __name__ == "__main__":
    _compare_mode()
