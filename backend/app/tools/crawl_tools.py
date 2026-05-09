import re

import httpx
from bs4 import BeautifulSoup


async def crawl_website(url: str) -> dict:
    pages = [url, f"{url.rstrip('/')}/about", f"{url.rstrip('/')}/brand"]
    out = {"url": url, "pages": []}
    colors, fonts, tones, ctas = set(), set(), set(), []
    async with httpx.AsyncClient(timeout=20) as client:
        for p in pages:
            try:
                r = await client.get(p, follow_redirects=True)
                if r.status_code >= 400:
                    continue
                soup = BeautifulSoup(r.text, "html.parser")
                text = " ".join(soup.stripped_strings)[:5000]
                found_colors = set(re.findall(r"#[0-9a-fA-F]{6}", r.text))
                found_fonts = set(re.findall(r"font-family\s*:\s*([^;]+);", r.text))
                cta_candidates = [t.get_text(strip=True) for t in soup.find_all(["a", "button"])][:20]
                colors.update(found_colors)
                fonts.update(found_fonts)
                ctas.extend([c for c in cta_candidates if c])
                for word in ["warm", "supportive", "professional", "friendly", "luxury", "minimal"]:
                    if word in text.lower():
                        tones.add(word)
                out["pages"].append({"url": p, "title": soup.title.string if soup.title else "", "text": text[:1200]})
            except Exception:
                continue
    out.update({"colors_detected": sorted(colors), "fonts_detected": sorted(fonts), "tone_words": sorted(tones), "cta_text": ctas[:10]})
    return out


def extract_brand_signals(crawl_result: dict) -> dict:
    colors = crawl_result.get("colors_detected") or []
    return {
        "color_palette": {
            "primary": colors[0] if len(colors) > 0 else "#0A0A0A",
            "secondary": colors[1] if len(colors) > 1 else "#1E293B",
            "accent": colors[2] if len(colors) > 2 else "#C9A84C",
            "background": "#0A0A0A",
            "text": "#F8F6F1",
        },
        "typography": {
            "headline_font": "Cormorant Garamond",
            "body_font": "IBM Plex Sans",
            "arabic_font": "Cairo",
            "data_font": "IBM Plex Mono",
        },
        "tone_words": crawl_result.get("tone_words", []),
        "ctas": crawl_result.get("cta_text", []),
    }
