"""Record the demo GIF by driving the running app in a headless browser.

    pip install playwright pillow && playwright install chromium
    streamlit run app/streamlit_app.py            # in another terminal, models warmed up
    python scripts/record_demo.py [--shots 1 2 3] [--out docs/img/demo.gif]

Nobody types or edits anything by hand: each shot is a question from `SHOTS`, screenshots are
taken while the app retrieves, streams and finishes, and the frames become one GIF.

The recording is honest about time. The wait before the first words is played `WAIT_SPEEDUP`
times faster and says so on screen; the writing is played at real speed; every frame carries the
real seconds elapsed since "Ask".
"""

import argparse
import io
import os
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SHOTS = {
    1: (
        "A question",
        "How do attackers dump credentials from LSASS, and which Sigma rules detect it?",
        False,
    ),
    2: (
        "A raw command line",
        r"rundll32.exe C:\Windows\System32\comsvcs.dll, MiniDump 624 C:\temp\lsass.dmp full",
        False,
    ),
    3: ("A CVE", "Is CVE-2024-3400 exploited in the wild and what should I do?", False),
    4: ("Agent mode", "How do I detect and mitigate Kerberoasting?", True),
    5: (
        "A question in French",
        "Comment détecter le vol d'identifiants dans la mémoire de LSASS ?",
        False,
    ),
}
INTERVAL_S = 0.4  # one screenshot every 0.4 s
WAIT_SPEEDUP = 8  # the wait before the first token is shown this many times faster
HOLD_S = 4.0  # how long the finished answer stays on screen
BAR_H = 34


def capture(page, url: str, question: str, agent: bool, timeout_s: float) -> list[tuple]:
    """Ask one question; return [(png bytes, phase, seconds since Ask)], phase in wait/write/done."""
    page.goto(url)
    page.wait_for_selector("textarea", timeout=120_000)
    if agent:
        page.locator("label", has_text="Agent mode").first.click()
        page.wait_for_timeout(500)
    box = page.locator("textarea").first
    box.fill(question)
    box.press("Control+Enter")
    page.wait_for_timeout(300)
    frames = [(page.screenshot(), "wait", 0.0)]
    page.get_by_role("button", name="Ask").click()
    t0 = time.perf_counter()
    while True:
        page.wait_for_timeout(int(INTERVAL_S * 1000))
        now = time.perf_counter() - t0
        body = page.locator("body").inner_text()
        if "Full answer" in body:
            frames.append((page.screenshot(), "done", now))
            return frames
        if now > timeout_s:
            raise TimeoutError(f"no answer after {timeout_s:.0f} s for: {question}")
        frames.append((page.screenshot(), "write" if "▌" in body else "wait", now))


def caption(png: bytes, text: str, width: int) -> Image.Image:
    img = Image.open(io.BytesIO(png)).convert("RGB")
    if img.width != width:
        img = img.resize((width, round(img.height * width / img.width)), Image.LANCZOS)
    out = Image.new("RGB", (img.width, img.height + BAR_H), (24, 24, 27))
    out.paste(img, (0, 0))
    font = ImageFont.load_default(size=17)
    ImageDraw.Draw(out).text((12, img.height + 7), text, fill=(235, 235, 235), font=font)
    return out


def assemble(
    shots: list[tuple[str, list[tuple]]], width: int
) -> tuple[list[Image.Image], list[int]]:
    """Frames and their durations in ms: waits sped up, writing in real time, answers held."""
    images, durations = [], []
    for label, frames in shots:
        waits = [f for f in frames if f[1] == "wait"][::WAIT_SPEEDUP]
        for png, phase, t in waits + [f for f in frames if f[1] != "wait"]:
            if phase == "wait":
                text, ms = f"{label} · waiting {t:4.1f} s (shown {WAIT_SPEEDUP}× faster)", 400
            elif phase == "write":
                text, ms = f"{label} · writing {t:4.1f} s (real speed)", int(INTERVAL_S * 1000)
            else:
                text, ms = f"{label} · done in {t:.1f} s", int(HOLD_S * 1000)
            images.append(caption(png, text, width))
            durations.append(ms)
    return images, durations


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://localhost:8501")
    p.add_argument("--out", default="docs/img/demo.gif")
    p.add_argument("--shots", type=int, nargs="*", default=[3, 4, 5], choices=list(SHOTS))
    p.add_argument("--width", type=int, default=960, help="GIF width in pixels")
    p.add_argument("--timeout", type=float, default=240, help="seconds to wait for one answer")
    args = p.parse_args()

    from playwright.sync_api import sync_playwright

    recorded = []
    with sync_playwright() as pw:
        # DEMO_CHROMIUM: path of an already installed Chromium, if `playwright install` was not run
        browser = pw.chromium.launch(executable_path=os.getenv("DEMO_CHROMIUM") or None)
        page = browser.new_page(viewport={"width": 1280, "height": 1150})
        for n in args.shots:
            label, question, agent = SHOTS[n]
            frames = capture(page, args.url, question, agent, args.timeout)
            first = next((t for _, phase, t in frames if phase != "wait"), frames[-1][2])
            print(
                f"shot {n} ({label}): first words {first:.1f} s, done {frames[-1][2]:.1f} s, {len(frames)} screenshots",
                flush=True,
            )
            recorded.append((label, frames))
        browser.close()

    images, durations = assemble(recorded, args.width)
    palette = [im.quantize(colors=96, method=Image.MEDIANCUT, dither=Image.NONE) for im in images]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    palette[0].save(
        out, save_all=True, append_images=palette[1:], duration=durations, loop=0, optimize=True
    )
    print(
        f"{out}: {len(images)} frames, {sum(durations) / 1000:.0f} s, {out.stat().st_size / 1e6:.1f} MB"
    )


if __name__ == "__main__":
    main()
