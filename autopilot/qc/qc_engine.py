"""
autopilot/qc/qc_engine.py
────────────────────────────────────────────────────────────────────────────────
Multi-layer Quality Control engine.

Layer 1: Technical checks (file exists, size, dimensions, format)
Layer 2: Gemini vision analysis (ask Gemini to review the output)
Layer 3: Task-specific rules

Returns a QCResult with pass/fail and detailed notes.
────────────────────────────────────────────────────────────────────────────────
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger('autopilot.qc')

# Minimum file sizes by type (bytes)
MIN_FILE_SIZES = {
    '.jpg': 30_000,    # 30 KB
    '.jpeg': 30_000,
    '.png': 20_000,    # 20 KB (can be smaller after compression)
    '.pdf': 50_000,    # 50 KB
    '.mp4': 1_000_000, # 1 MB for video
    '.txt': 500,       # 500 bytes minimum
}

# Minimum image dimensions (pixels)
MIN_DIMENSIONS = {
    'bg_cleanup':       (400, 400),
    'virtual_staging':  (512, 512),
    'product_listing':  None,        # Document, no dimension check
    'brand_starter_kit': None,       # Document
    'property_reel':    (512, 512),
}


@dataclass
class QCResult:
    passed: bool
    score: float          # 0.0 to 1.0
    issues: list[str] = field(default_factory=list)
    notes: str = ''
    gemini_review: str = ''

    def to_notes_string(self) -> str:
        status = '✅ PASS' if self.passed else '❌ FAIL'
        parts = [f"QC {status} (score: {self.score:.1%})"]
        if self.issues:
            parts.append("Issues found:")
            parts.extend(f"  • {issue}" for issue in self.issues)
        if self.gemini_review:
            parts.append(f"\nAI Review:\n{self.gemini_review}")
        return '\n'.join(parts)


# ── Layer 1: Technical checks ──────────────────────────────────────────────────

def check_technical(file_path: Path, task_type: str) -> tuple[bool, list[str]]:
    """
    Basic sanity checks: file exists, not empty, correct format, minimum size.
    Returns (passed, issues_list).
    """
    issues = []

    # File exists
    if not file_path.exists():
        return False, [f"File does not exist: {file_path.name}"]

    # File size
    size = file_path.stat().st_size
    min_size = MIN_FILE_SIZES.get(file_path.suffix.lower(), 1000)
    if size < min_size:
        issues.append(f"File too small: {size:,} bytes (min {min_size:,})")

    # Image dimension check
    min_dims = MIN_DIMENSIONS.get(task_type)
    if min_dims and file_path.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}:
        try:
            from PIL import Image
            with Image.open(file_path) as img:
                w, h = img.size
                if w < min_dims[0] or h < min_dims[1]:
                    issues.append(f"Image too small: {w}x{h} (min {min_dims[0]}x{min_dims[1]})")
        except ImportError:
            pass  # PIL not available
        except Exception as e:
            issues.append(f"Could not read image dimensions: {e}")

    return len(issues) == 0, issues


# ── Layer 2: Gemini vision QC ──────────────────────────────────────────────────

QC_PROMPTS = {
    'bg_cleanup': """Review this product photo with a removed background. Check:
1. Is the background cleanly removed? (clean edges, no background remnants)
2. Are there any edge artifacts or halos?
3. Is the product itself intact and not distorted?
4. Overall quality: Good/Acceptable/Poor?

Respond with: PASS or FAIL, then a brief explanation (2-3 sentences max).""",

    'virtual_staging': """Review this virtually staged room. Check:
1. Does the furniture look natural and photorealistic (not AI-generated looking)?
2. Are there any people or obvious AI artifacts?
3. Does the staging match the room's architecture?
4. Is the image high quality?

Respond with: PASS or FAIL, then a brief explanation (2-3 sentences max).""",

    'product_listing': """Review this product listing document. Check:
1. Does it have a proper title, bullet points, and description?
2. Is the content clear and professionally written?
3. Are there obvious errors or missing sections?

Respond with: PASS or FAIL, then a brief explanation (2-3 sentences max).""",

    'default': """Review this deliverable. Is it complete, professional quality, and free from obvious errors?
Respond with: PASS or FAIL, then a brief explanation.""",
}


def check_with_gemini(file_path: Path, task_type: str, browser) -> tuple[bool, str]:
    """
    Use Gemini to visually review the deliverable.
    Returns (passed, review_text).
    """
    if not browser:
        return True, "Gemini QC skipped (no browser)"

    prompt = QC_PROMPTS.get(task_type, QC_PROMPTS['default'])

    try:
        if file_path.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}:
            # Vision check
            review = browser.ask_gemini_with_image(
                prompt=prompt,
                image_path=file_path,
                timeout_sec=60,
            )
        else:
            # Text file: read content and ask Gemini to review
            content = file_path.read_text(encoding='utf-8', errors='replace')[:3000]
            text_prompt = f"{prompt}\n\nHere is the content to review:\n\n{content}"
            review = browser.ask_gemini(text_prompt, timeout_sec=60)

        if not review:
            return True, "Gemini did not respond — treating as pass"

        passed = 'PASS' in review.upper() and 'FAIL' not in review.upper()
        if 'FAIL' in review.upper():
            passed = False

        logger.info(f"   🤖 Gemini QC: {'✅ PASS' if passed else '❌ FAIL'}")
        return passed, review

    except Exception as e:
        logger.warning(f"⚠  Gemini QC error: {e} — treating as pass")
        return True, f"Gemini QC error: {e}"


# ── Layer 3: Task-specific rules ───────────────────────────────────────────────

def check_task_rules(file_path: Path, task_type: str, order_data: dict) -> tuple[bool, list[str]]:
    """
    Task-specific rule checks beyond technical and AI review.
    Returns (passed, issues).
    """
    issues = []

    if task_type == 'product_listing':
        if file_path.suffix == '.txt':
            content = file_path.read_text(encoding='utf-8', errors='replace')
            # Must have all sections
            required = ['TITLE', 'BULLETS', 'DESCRIPTION', 'KEYWORDS']
            for section in required:
                if section not in content.upper():
                    issues.append(f"Missing section: {section}")
            # Word count check
            words = len(content.split())
            if words < 150:
                issues.append(f"Content too short: {words} words (min 150)")

    elif task_type == 'bg_cleanup':
        if file_path.suffix.lower() in {'.jpg', '.jpeg', '.png'}:
            try:
                from PIL import Image
                with Image.open(file_path) as img:
                    # Check it's not completely white/black (common failure)
                    rgb = img.convert('RGB')
                    pixels = list(rgb.getdata())
                    unique = len(set(pixels))
                    if unique < 50:
                        issues.append("Image appears to be blank or monochrome")
            except Exception:
                pass

    return len(issues) == 0, issues


# ── Main QC entry point ────────────────────────────────────────────────────────

def run_qc(file_path: Path, task_type: str, order_data: dict,
           browser=None) -> QCResult:
    """
    Run full QC pipeline on a deliverable file.
    Returns QCResult with overall pass/fail and detailed notes.
    """
    logger.info(f"   🔬 Running QC: {file_path.name} ({task_type})")

    all_issues = []
    total_checks = 0
    passed_checks = 0

    # Layer 1: Technical
    total_checks += 1
    tech_pass, tech_issues = check_technical(file_path, task_type)
    all_issues.extend(tech_issues)
    if tech_pass:
        passed_checks += 1
    else:
        logger.warning(f"   ⚠  Technical QC failed: {tech_issues}")

    # Layer 3: Task rules (do before Gemini to save time if basic rules fail)
    total_checks += 1
    rule_pass, rule_issues = check_task_rules(file_path, task_type, order_data)
    all_issues.extend(rule_issues)
    if rule_pass:
        passed_checks += 1

    # Layer 2: Gemini vision (only if technical checks pass — no point reviewing broken files)
    gemini_review = ''
    if tech_pass:
        total_checks += 1
        gemini_pass, gemini_review = check_with_gemini(file_path, task_type, browser)
        if gemini_pass:
            passed_checks += 1
        else:
            all_issues.append(f"AI review: FAIL — {gemini_review[:200]}")

    score = passed_checks / total_checks if total_checks > 0 else 0.0
    overall_pass = score >= 0.67 and tech_pass  # Must pass tech + at least one other

    result = QCResult(
        passed=overall_pass,
        score=score,
        issues=all_issues,
        notes=f"{passed_checks}/{total_checks} QC checks passed",
        gemini_review=gemini_review,
    )

    if overall_pass:
        logger.info(f"   ✅ QC PASSED (score: {score:.1%})")
    else:
        logger.warning(f"   ❌ QC FAILED (score: {score:.1%}) — {all_issues}")

    return result
