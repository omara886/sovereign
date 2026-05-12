"""
Arabic QA — zero tolerance for script contamination.
Runs BEFORE brand QA. CRITICAL issues block asset from ever entering approval inbox.
"""
import re
import unicodedata


def detect_script_contamination(text: str) -> dict:
    issues = []

    # CJK: Chinese, Japanese Kana, Korean Hangul
    cjk_chars = [
        c for c in text
        if '一' <= c <= '鿿'
        or '぀' <= c <= 'ヿ'
        or '가' <= c <= '힯'
        or '㐀' <= c <= '䶿'   # CJK Extension A
        or '豈' <= c <= '﫿'   # CJK Compatibility
    ]
    if cjk_chars:
        issues.append({
            'type': 'CJK_CONTAMINATION',
            'severity': 'CRITICAL',
            'chars': cjk_chars[:5],
            'message': f'Arabic content contains {len(cjk_chars)} Chinese/Japanese/Korean characters: {cjk_chars[:3]}',
        })

    # Arabic ratio check (only for strings long enough to matter)
    alpha_chars = [c for c in text if c.isalpha()]
    arabic_chars = [c for c in text if '؀' <= c <= 'ۿ']
    if len(alpha_chars) >= 10:
        ratio = len(arabic_chars) / len(alpha_chars)
        if ratio < 0.25:
            issues.append({
                'type': 'INSUFFICIENT_ARABIC',
                'severity': 'HIGH',
                'ratio': round(ratio, 2),
                'message': f'Only {round(ratio * 100)}% Arabic characters — expected Gulf Arabic content',
            })

    # Broken Unicode (unassigned codepoints)
    for i, c in enumerate(text):
        if unicodedata.category(c) == 'Cn':
            issues.append({
                'type': 'BROKEN_UNICODE',
                'severity': 'HIGH',
                'position': i,
                'message': f'Unassigned Unicode codepoint U+{ord(c):04X} at position {i}',
            })
            break

    arabic_ratio = len(arabic_chars) / max(len(alpha_chars), 1)
    return {
        'passed': len(issues) == 0,
        'issues': issues,
        'arabic_ratio': round(arabic_ratio, 2),
    }


def validate_rtl_layout(html_content: str) -> dict:
    issues = []
    arabic_pattern = re.compile(r'[؀-ۿ]+')
    rtl_pattern = re.compile(r'dir=["\']rtl["\']')
    if arabic_pattern.search(html_content) and not rtl_pattern.search(html_content):
        issues.append({
            'type': 'MISSING_RTL_DIRECTION',
            'severity': 'HIGH',
            'message': 'Arabic text found without dir="rtl" attribute',
        })
    return {'passed': len(issues) == 0, 'issues': issues}


def run_arabic_qa(asset: dict) -> dict:
    all_issues: list[dict] = []

    copy_ar = asset.get('copy_ar') or ''
    if copy_ar.strip():
        result = detect_script_contamination(copy_ar)
        if not result['passed']:
            all_issues.extend(result['issues'])

    cta_ar = asset.get('cta_ar') or ''
    if cta_ar.strip():
        result = detect_script_contamination(cta_ar)
        if not result['passed']:
            # deduplicate — don't report same issue type twice
            existing_types = {i['type'] for i in all_issues}
            for issue in result['issues']:
                if issue['type'] not in existing_types:
                    all_issues.append(issue)

    passed = len(all_issues) == 0
    blocked = any(i['severity'] == 'CRITICAL' for i in all_issues)

    return {
        'passed': passed,
        'blocked': blocked,
        'score': 100 if passed else 0,
        'issues': all_issues,
    }
