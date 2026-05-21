import asyncio
from pathlib import Path

from app.tools.image_tools import composite_premium_arabic
from app.tools.qa_tools import run_final_qa_gate, run_image_qa_gate


async def test_therapia_instagram_post():
    Path("backend/test_output").mkdir(parents=True, exist_ok=True)
    bg_bytes = open("backend/test_assets/therapia_bg_test.jpg", "rb").read()

    bg_qa = await run_image_qa_gate(bg_bytes, min_aesthetic=5.0)
    assert bg_qa["passed"], f"BG QA failed: {bg_qa['reason']}"

    final = await asyncio.to_thread(
        composite_premium_arabic,
        bg_bytes,
        copy_ar="راحة بالك أقرب مما تتوقع",
        copy_en="Online therapy, your schedule.",
        cta_ar="ابدأ الآن",
        brand_colors={"primary": "#0F3D3E", "accent": "#D7B98E"},
        width=1080,
        height=1350,
        layout_pattern="glass_card",
    )

    final_qa = await run_final_qa_gate(final, "راحة بالك")
    assert final_qa["passed"], f"Final QA failed: {final_qa['reason']}"

    open("backend/test_output/therapia_instagram_v2.jpg", "wb").write(final)
    print(f"PASS aesthetic={bg_qa['scores'].get('aesthetic')}")
    print(f"PASS contrast={final_qa['scores'].get('contrast')}")
    print(f"PASS arabic_ocr={final_qa['scores'].get('ocr_arabic_legible')}")


if __name__ == "__main__":
    asyncio.run(test_therapia_instagram_post())
