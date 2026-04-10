"""
Windows OCR 텍스트 추출 모듈
winocr 패키지 사용 (Python 3.12+ 호환)
PIL Image → 한국어 OCR → 텍스트
"""
import asyncio
import sys
import io

try:
    from PIL import Image
except ImportError:
    print("필요: pip install Pillow")
    sys.exit(1)


def _is_windows():
    return sys.platform == "win32"


def ocr_image(image: Image.Image) -> str:
    """이미지에서 텍스트 추출"""
    if _is_windows():
        try:
            from winocr import recognize_pil_sync
            result = recognize_pil_sync(image, 'ko')
            return result['text']
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


if __name__ == "__main__":
    import os
    captures_dir = "ocr/captures"
    if os.path.isdir(captures_dir):
        for f in sorted(os.listdir(captures_dir)):
            if f.endswith(".png"):
                img = Image.open(os.path.join(captures_dir, f))
                text = ocr_image(img)
                print(f"=== {f} ===")
                print(text[:200])
                print()
    else:
        print("캡처 파일 없음. 먼저 python ocr/capture.py 실행하세요.")
