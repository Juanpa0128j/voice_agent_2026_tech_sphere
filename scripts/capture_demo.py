"""Capture demo screenshots from the live Modal deployment.

Run:  .venv/bin/python3 scripts/capture_demo.py

Produces PNGs in docs/screenshots/ for embedding in the final report.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

URL = "https://juanpa0128j--voice-agent.modal.run"
OUT_DIR = Path("docs/screenshots")
OUT_DIR.mkdir(parents=True, exist_ok=True)


async def shot(page, name: str) -> None:
    target = OUT_DIR / f"{name}.png"
    await page.screenshot(path=str(target), full_page=True)
    print(f"  saved {target} ({target.stat().st_size // 1024} KB)")


async def send_text(page, text: str, wait_ms: int = 15000) -> None:
    """Type into the fallback textarea and click Enviar, then wait for the agent bubble."""
    bubbles_before = await page.locator(".bubble").count()
    await page.locator("textarea").first.fill(text)
    await page.locator("button:has-text('Enviar')").first.click()
    # Wait until a new agent bubble appears
    try:
        await page.wait_for_function(
            f"document.querySelectorAll('.bubble').length > {bubbles_before}",
            timeout=wait_ms,
        )
    except Exception:
        await page.wait_for_timeout(wait_ms)


async def main() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(args=["--no-sandbox"])
        ctx = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="es-CO",
        )
        page = await ctx.new_page()

        print("1. UI (initial state)")
        await page.goto(URL, wait_until="networkidle")
        await page.wait_for_timeout(2000)
        await shot(page, "01_ui_initial")

        print("2. Start call (greeting)")
        try:
            await page.click("button:has-text('Iniciar')", timeout=3000)
            await page.wait_for_timeout(8000)  # greeting response
        except Exception as exc:
            print(f"  (start click failed: {exc})")
        await shot(page, "02_ui_greeting")

        print("3. UI after ROJO call (fiebre 39 + dolor 9)")
        await send_text(page, "doctor tengo fiebre de 39 grados y dolor 9 de 10 en la herida", 25000)
        await page.wait_for_timeout(1500)
        await shot(page, "03_ui_after_rojo")

        print("4. UI after VERDE call (me siento bien)")
        await send_text(page, "me siento bien hoy solo un poco de cansancio", 25000)
        await page.wait_for_timeout(1500)
        await shot(page, "04_ui_after_verde")

        print("5. Admin console")
        await page.goto(f"{URL}/admin.html", wait_until="networkidle")
        await page.wait_for_timeout(3000)
        await shot(page, "05_admin_console")

        print("6. /api/metrics")
        metrics_page = await ctx.new_page()
        await metrics_page.goto(f"{URL}/api/metrics", wait_until="networkidle")
        await metrics_page.wait_for_timeout(1500)
        await shot(metrics_page, "06_api_metrics")

        print("7. /docs (OpenAPI Swagger UI)")
        docs_page = await ctx.new_page()
        try:
            await docs_page.goto(f"{URL}/docs", wait_until="networkidle", timeout=10000)
            await docs_page.wait_for_timeout(2000)
            await shot(docs_page, "07_openapi_docs")
        except Exception as exc:
            print(f"  (/docs not available: {exc})")

        await browser.close()
    print("\nAll screenshots saved to docs/screenshots/")


if __name__ == "__main__":
    asyncio.run(main())
