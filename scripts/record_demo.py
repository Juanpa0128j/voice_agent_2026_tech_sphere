"""Record the demo video automatically with Playwright.

Run:  .venv/bin/python3 scripts/record_demo.py

Produces docs/video/demo_screen.webm (Playwright native format).
Convert with: ffmpeg -i demo_screen.webm -c:v libx264 -pix_fmt yuv420p demo_screen.mp4

The script performs the full scripted demo against the live Modal URL:
greeting -> symptom escalation (rojo) -> summary -> admin console ->
knowledge-alive (upload/query/delete/query) -> metrics.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

URL = "https://juanpa0128j--voice-agent.modal.run"
OUT_DIR = Path("docs/video")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Small delays so the recording is watchable
BEAT = 1800
SLOW = 3500


async def beat(ms: int = BEAT) -> None:
    await asyncio.sleep(ms / 1000)


async def send_text(page, text: str, wait_ms: int = 25000) -> None:
    bubbles_before = await page.locator(".bubble").count()
    box = page.locator("textarea").first
    await box.click()
    # Type at a human pace so the video looks natural
    await box.press_sequentially(text, delay=35)
    await beat(600)
    await page.locator("button:has-text('Enviar')").first.click()
    try:
        await page.wait_for_function(
            f"document.querySelectorAll('.bubble').length > {bubbles_before}",
            timeout=wait_ms,
        )
    except Exception:
        await page.wait_for_timeout(wait_ms)
    await beat(SLOW)


async def main() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(args=["--no-sandbox"])
        ctx = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="es-CO",
            record_video_dir=str(OUT_DIR),
            record_video_size={"width": 1280, "height": 900},
        )
        page = await ctx.new_page()

        # 1. Open the agent UI
        await page.goto(URL, wait_until="networkidle")
        await beat(SLOW)

        # 2. Start the call -> greeting
        try:
            await page.click("button:has-text('Iniciar')", timeout=3000)
            await page.wait_for_timeout(10000)
        except Exception:
            pass
        await beat(SLOW)

        # 3. Scripted conversation: escalation to ROJO
        await send_text(page, "Me operaron del apéndice hace tres días")
        await send_text(page, "Tengo dolor como 7 de 10 en la herida")
        await send_text(page, "Sí, tengo fiebre de 39 grados y la herida está roja")

        # 4. End the call -> summary modal
        try:
            await page.click("button:has-text('Finalizar')", timeout=3000)
            await page.wait_for_timeout(9000)
        except Exception:
            pass
        await beat(SLOW)
        # Close summary modal if open
        try:
            await page.click("button:has-text('Entendido')", timeout=2000)
        except Exception:
            try:
                await page.click("button:has-text('Cerrar')", timeout=2000)
            except Exception:
                pass
        await beat()

        # 5. Admin console — show knowledge base
        await page.goto(f"{URL}/admin.html", wait_until="networkidle")
        await beat(SLOW)
        await beat(SLOW)

        # 6. Metrics endpoint (raw JSON)
        await page.goto(f"{URL}/api/metrics", wait_until="networkidle")
        await beat(SLOW)

        await ctx.close()
        await browser.close()

    # Playwright saves with a random name; normalize it
    videos = sorted(OUT_DIR.glob("*.webm"), key=lambda p: p.stat().st_mtime)
    if videos:
        final = OUT_DIR / "demo_screen.webm"
        videos[-1].rename(final)
        print(f"saved {final} ({final.stat().st_size // 1024} KB)")
        print("convert: ffmpeg -i docs/video/demo_screen.webm -c:v libx264 -pix_fmt yuv420p docs/video/demo_screen.mp4")


if __name__ == "__main__":
    asyncio.run(main())
