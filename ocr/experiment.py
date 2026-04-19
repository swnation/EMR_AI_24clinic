"""
OCR 전처리 × 언어 조합 실험 스크립트
================================================
실행: python ocr/experiment.py

사전 준비:
1. ocr/captures/{symptoms,special,dx,orders}.png
   → python ocr/capture.py 로 생성
2. ocr/ground_truth/{symptoms,special,dx,orders}.txt
   → Snipping Tool로 수동 캡처 → 텍스트 추출 → 각 txt로 저장
================================================
"""
import os
import sys

try:
    from PIL import Image, ImageEnhance, ImageFilter
except ImportError:
    print("필요: pip install Pillow")
    sys.exit(1)

try:
    from winocr import recognize_pil_sync
except ImportError:
    print("필요: pip install winocr")
    sys.exit(1)

try:
    from rapidfuzz import fuzz
except ImportError:
    print("필요: pip install rapidfuzz")
    sys.exit(1)


CAPTURES_DIR = "ocr/captures"
GROUND_TRUTH_DIR = "ocr/ground_truth"
RESULT_FILE = "ocr/experiment_results.txt"
REGIONS = ["symptoms", "special", "dx", "orders"]
LANGUAGES = ["ko", "en"]


# =========================================================
# 전처리 버전들
# =========================================================

def v0_none(img):
    """전처리 없음"""
    return img.convert("RGB")


def v1_upscale_2x(img):
    """2배 업스케일만"""
    w, h = img.size
    img = img.resize((w * 2, h * 2), Image.LANCZOS)
    return img.convert("RGB")


def v2_upscale_3x(img):
    """3배 업스케일만"""
    w, h = img.size
    img = img.resize((w * 3, h * 3), Image.LANCZOS)
    return img.convert("RGB")


def v3_upscale_2x_gray(img):
    """2배 + 그레이스케일"""
    w, h = img.size
    img = img.resize((w * 2, h * 2), Image.LANCZOS)
    img = img.convert("L")
    return img.convert("RGB")


def v4_upscale_2x_gray_unsharp(img):
    """2배 + 그레이스케일 + UnsharpMask"""
    w, h = img.size
    img = img.resize((w * 2, h * 2), Image.LANCZOS)
    img = img.convert("L")
    img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3))
    return img.convert("RGB")


def _otsu_threshold(gray_img):
    """Otsu 알고리즘으로 최적 threshold 자동 계산"""
    hist = gray_img.histogram()[:256]
    total = sum(hist)
    sum_all = sum(i * hist[i] for i in range(256))
    sum_b = 0
    w_b = 0
    max_var = 0.0
    threshold = 0
    for t in range(256):
        w_b += hist[t]
        if w_b == 0:
            continue
        w_f = total - w_b
        if w_f == 0:
            break
        sum_b += t * hist[t]
        m_b = sum_b / w_b
        m_f = (sum_all - sum_b) / w_f
        var = w_b * w_f * (m_b - m_f) ** 2
        if var > max_var:
            max_var = var
            threshold = t
    return threshold


def v5_upscale_3x_otsu(img):
    """3배 + 그레이스케일 + Otsu adaptive 이진화"""
    w, h = img.size
    img = img.resize((w * 3, h * 3), Image.LANCZOS)
    img = img.convert("L")
    t = _otsu_threshold(img)
    img = img.point(lambda p: 255 if p > t else 0)
    return img.convert("RGB")


def v6_current(img):
    """현재 reader.py와 동일 (baseline)"""
    w, h = img.size
    img = img.resize((w * 4, h * 4), Image.LANCZOS)
    img = img.convert("L")
    img = ImageEnhance.Contrast(img).enhance(2.0)
    img = ImageEnhance.Sharpness(img).enhance(2.0)
    img = img.point(lambda p: 255 if p > 140 else 0)
    return img.convert("RGB")


PREPROCESSORS = {
    "v0_none          ": v0_none,
    "v1_upscale2x     ": v1_upscale_2x,
    "v2_upscale3x     ": v2_upscale_3x,
    "v3_2x_gray       ": v3_upscale_2x_gray,
    "v4_2x_gray_sharp ": v4_upscale_2x_gray_unsharp,
    "v5_3x_otsu       ": v5_upscale_3x_otsu,
    "v6_current       ": v6_current,
}


# =========================================================
# OCR 및 점수 계산
# =========================================================

def run_ocr(img, lang):
    """OCR 실행. 실패 시 에러 메시지 반환."""
    try:
        result = recognize_pil_sync(img, lang)
        if isinstance(result, dict):
            return result.get("text", "")
        return ""
    except Exception as e:
        return f"[ERROR: {e}]"


def score(ocr_text, ground_truth):
    """글자 일치율 (0~100, Levenshtein 기반)"""
    if not ground_truth:
        return 0.0
    return fuzz.ratio(ocr_text.strip(), ground_truth.strip())


def load_ground_truth(region):
    path = os.path.join(GROUND_TRUTH_DIR, f"{region}.txt")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return f.read()


# =========================================================
# 메인
# =========================================================

def main():
    # 준비 상태 확인
    missing_captures = [
        r for r in REGIONS
        if not os.path.exists(os.path.join(CAPTURES_DIR, f"{r}.png"))
    ]
    if missing_captures:
        print(f"[ERROR] 캡처 파일 누락: {missing_captures}")
        print("  해결: python ocr/capture.py 실행")
        return

    missing_gt = [
        r for r in REGIONS
        if not os.path.exists(os.path.join(GROUND_TRUTH_DIR, f"{r}.txt"))
    ]
    if missing_gt:
        print(f"[ERROR] 정답 파일 누락: {missing_gt}")
        print(f"  해결: Snipping Tool로 캡처 → 텍스트 추출 → {GROUND_TRUTH_DIR}/*.txt 저장")
        return

    print()
    print("=" * 75)
    print(" OCR 전처리 × 언어 조합 실험")
    print("=" * 75)

    all_results = {}

    for region in REGIONS:
        img_path = os.path.join(CAPTURES_DIR, f"{region}.png")
        img = Image.open(img_path)
        gt = load_ground_truth(region)

        print(f"\n■ 영역: {region}")
        print(f"  원본 크기: {img.size[0]}x{img.size[1]}  /  정답 길이: {len(gt)}자")
        print("-" * 75)
        print(f"  {'전처리':<20} {'언어':<5} {'점수':>6}   샘플 (처음 40자)")
        print("-" * 75)

        results = []
        for pname, pfunc in PREPROCESSORS.items():
            try:
                processed = pfunc(img)
            except Exception as e:
                print(f"  {pname:<20} 전처리 실패: {e}")
                continue

            for lang in LANGUAGES:
                text = run_ocr(processed, lang)
                sc = score(text, gt)
                sample = text.replace("\n", " ")[:40]
                is_baseline = "v6_current" in pname and lang == "ko"
                marker = "  ← 현재" if is_baseline else ""
                print(f"  {pname:<20} {lang:<5} {sc:>5.1f}   {sample}{marker}")
                results.append((pname.strip(), lang, sc, text))

        results.sort(key=lambda r: r[2], reverse=True)
        all_results[region] = results

    # 요약
    print()
    print("=" * 75)
    print(" 영역별 최적 조합 요약")
    print("=" * 75)

    for region in REGIONS:
        best = all_results[region][0]
        current = next(
            (r for r in all_results[region]
             if r[0] == "v6_current" and r[1] == "ko"),
            None
        )
        current_score = current[2] if current else 0
        improvement = best[2] - current_score
        print(f"\n■ {region}")
        print(f"    최적:  {best[0]:<20} + {best[1]:<4} →  {best[2]:>5.1f}점")
        print(f"    현재:  v6_current           + ko   →  {current_score:>5.1f}점")
        print(f"    개선:  {'+' if improvement >= 0 else ''}{improvement:.1f}점")

    # 상세 결과 저장
    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        f.write("OCR 전처리×언어 조합 실험 상세 결과\n")
        f.write("=" * 75 + "\n")
        for region in REGIONS:
            f.write(f"\n\n{'#' * 20}  영역: {region}  {'#' * 20}\n")
            gt = load_ground_truth(region)
            f.write(f"\n[GROUND TRUTH]\n{gt}\n")
            f.write("\n[OCR 결과 (점수 내림차순)]\n")
            for pname, lang, sc, text in all_results[region]:
                f.write(f"\n--- {pname} + {lang}  (score: {sc:.1f}) ---\n{text}\n")

    print()
    print("=" * 75)
    print(f" 상세 결과는 {RESULT_FILE} 에 저장됨")
    print("=" * 75)


if __name__ == "__main__":
    main()
