"""
flow_xray.py — Standalone UI X-ray for Google Flow's asset picker.

PURPOSE
-------
The AutoPilot agent can click everything in Flow EXCEPT "Add to Prompt" in the
asset picker. The picker's contents (Add to Prompt, Upload media, Search assets,
asset rows) are visibly on screen but invisible to document.querySelectorAll.
Hypothesis: closed shadow root or out-of-process iframe (OOPIF).

This script does NOT patch anything. It opens the SAME Chrome profile the agent
uses, walks you into a Flow project, helps you open the picker, then dumps every
way of "seeing" the page so we can locate "Add to Prompt" definitively:

  1. page.accessibility.snapshot()   -> pierces CLOSED shadow DOM
  2. recursive open-shadow-root walk -> every element incl. open shadow trees
  3. all frames (incl. OOPIFs)       -> context.pages + page.frames
  4. full-page screenshot + JSON of every interactive element w/ bounding boxes
  5. targeted search for the 5 buttons we care about, in EVERY layer

OUTPUT
------
Everything is written to:  autopilot/outputs/xray/<timestamp>/
  - ax_tree.json              (accessibility snapshot)
  - interactive_elements.json (DOM walk incl. open shadow roots, with bboxes)
  - frames.json               (every frame/OOPIF and what it contains)
  - targets_found.json        (where each of the 5 key buttons was located)
  - page.png                  (full-page screenshot)
  - SUMMARY.txt               (human-readable verdict)

HOW TO RUN
----------
  Double-click RUN_XRAY.bat in the Deleqate-main folder.
  Fully automatic: opens Flow, enters a project, opens the picker, uploads a
  test image so 'Add to Prompt' should be on screen, dumps everything, closes.
  All console output is also written to outputs/xray/<timestamp>/run.log
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Make sibling imports work whether run as module or script
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

try:
    import config  # reuses CHROME_PROFILE_DIR, GOOGLE_FLOW_URL, OUTPUT_DIR
except Exception:
    config = None

try:
    from playwright.sync_api import sync_playwright
except Exception:
    print("ERROR: Playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)


# The five things we MUST be able to see/click. We search every layer for these.
TARGET_TEXTS = [
    "Add to Prompt",     # the blocker
    "Upload media",      # picker upload entry
    "Search assets",     # picker search field (placeholder)
    "Add Media",         # prompt-bar "+"  (icon ligature: addAdd Media)
    "Create",            # submit/generate arrow (icon ligature: arrow_forwardCreate)
    "Nano Banana",       # model chip -> output settings (tools)
    "16:9",              # ratio button
]


def ts():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def out_root():
    if config and getattr(config, "OUTPUT_DIR", None):
        base = Path(config.OUTPUT_DIR) / "xray"
    else:
        base = HERE / "outputs" / "xray"
    d = base / ts()
    d.mkdir(parents=True, exist_ok=True)
    return d


def profile_dir():
    if config and getattr(config, "CHROME_PROFILE_DIR", None):
        return str(config.CHROME_PROFILE_DIR)
    return str(Path.home() / "AppData" / "Local" / "ChromeProfiles" / "AutoPilot")


def flow_url():
    if config and getattr(config, "GOOGLE_FLOW_URL", None):
        return config.GOOGLE_FLOW_URL
    return "https://labs.google/flow"


# ---------------------------------------------------------------------------
# JS payloads
# ---------------------------------------------------------------------------

# Deep walk that DESCENDS INTO OPEN SHADOW ROOTS. Closed roots are invisible to
# this on purpose — that's the diagnostic: anything we can SEE on screen but
# that does NOT appear here is in a closed root or another frame.
JS_DEEP_INTERACTIVE = r"""
() => {
  const out = [];
  const seen = new Set();
  function visible(el) {
    const r = el.getBoundingClientRect();
    if (r.width < 3 || r.height < 3) return null;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' || cs.opacity === '0') return null;
    return r;
  }
  function isInteractive(el) {
    const tag = el.tagName.toLowerCase();
    if (['button','a','input','textarea','select'].includes(tag)) return true;
    const role = (el.getAttribute && el.getAttribute('role')) || '';
    if (['button','link','textbox','option','tab','menuitem'].includes(role)) return true;
    if (el.getAttribute && el.getAttribute('contenteditable') === 'true') return true;
    return false;
  }
  function walk(node, shadowDepth) {
    if (!node) return;
    let kids;
    try { kids = node.querySelectorAll('*'); } catch (e) { return; }
    for (const el of kids) {
      if (seen.has(el)) continue;
      seen.add(el);
      if (isInteractive(el)) {
        const r = visible(el);
        if (r) {
          out.push({
            tag: el.tagName.toLowerCase(),
            role: (el.getAttribute && el.getAttribute('role')) || null,
            text: (el.textContent || '').trim().slice(0, 60),
            ariaLabel: (el.getAttribute && el.getAttribute('aria-label')) || null,
            placeholder: el.placeholder || null,
            x: Math.round(r.x + r.width / 2),
            y: Math.round(r.y + r.height / 2),
            w: Math.round(r.width),
            h: Math.round(r.height),
            shadowDepth: shadowDepth,
          });
        }
      }
      // descend into OPEN shadow roots
      if (el.shadowRoot) walk(el.shadowRoot, shadowDepth + 1);
    }
  }
  walk(document, 0);
  // also report whether any element ADVERTISES a closed root we can't enter
  // (we can't read closed roots, but we can count elements whose shadowRoot is null
  //  yet are custom elements — a weak hint)
  let customEls = 0;
  for (const el of document.querySelectorAll('*')) {
    if (el.tagName.includes('-')) customEls++;
  }
  return { elements: out, customElementCount: customEls,
           viewport: {w: window.innerWidth, h: window.innerHeight} };
}
"""

JS_FIND_TEXT_DEEP = r"""
(want) => {
  const hits = [];
  const seen = new Set();
  const wl = want.toLowerCase();
  function check(el, shadowDepth) {
    const tag = el.tagName.toLowerCase();
    // skip containers/scripts — they match everything via textContent and
    // produce false positives from the page's embedded JSON data
    if (['html', 'body', 'script', 'style', 'head'].includes(tag)) return;
    const t = (el.textContent || '').trim();
    if (t.length > want.length + 60) return;   // innermost elements only
    const al = (el.getAttribute && el.getAttribute('aria-label')) || '';
    const ph = el.placeholder || '';
    if (t.toLowerCase().includes(wl) || al.toLowerCase().includes(wl) || ph.toLowerCase().includes(wl)) {
      const r = el.getBoundingClientRect();
      hits.push({
        tag: el.tagName.toLowerCase(),
        text: t.slice(0, 60), ariaLabel: al || null, placeholder: ph || null,
        x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2),
        w: Math.round(r.width), h: Math.round(r.height),
        shadowDepth, onScreen: (r.width>2 && r.height>2)
      });
    }
  }
  function walk(node, d) {
    let kids; try { kids = node.querySelectorAll('*'); } catch(e){ return; }
    for (const el of kids) {
      if (seen.has(el)) continue; seen.add(el);
      check(el, d);
      if (el.shadowRoot) walk(el.shadowRoot, d+1);
    }
  }
  walk(document, 0);
  return hits;
}
"""


def dump_ax(page, d):
    try:
        snap = page.accessibility.snapshot(interesting_only=False)
        (d / "ax_tree.json").write_text(json.dumps(snap, indent=2), encoding="utf-8")
        # flatten and search for targets in the AX tree
        found = {t: [] for t in TARGET_TEXTS}
        def walk(node):
            if not node:
                return
            name = (node.get("name") or "")
            for t in TARGET_TEXTS:
                if t.lower() in name.lower():
                    found[t].append({"role": node.get("role"), "name": name})
            for c in node.get("children", []) or []:
                walk(c)
        walk(snap)
        return found
    except Exception as e:
        (d / "ax_tree.json").write_text(json.dumps({"error": str(e)}), encoding="utf-8")
        return {}


def dump_frames(page, d):
    info = []
    for fr in page.frames:
        rec = {"url": fr.url, "name": fr.name, "is_main": fr == page.main_frame}
        try:
            rec["interactive"] = fr.evaluate(JS_DEEP_INTERACTIVE)["elements"][:80]
        except Exception as e:
            rec["interactive_error"] = str(e)
        info.append(rec)
    (d / "frames.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    return info


def search_targets(page, d):
    """Search every frame (deep, incl. open shadow) for the 5 key buttons."""
    results = {}
    for t in TARGET_TEXTS:
        results[t] = {"frames": []}
        for fr in page.frames:
            try:
                hits = fr.evaluate(JS_FIND_TEXT_DEEP, t)
            except Exception as e:
                hits = [{"error": str(e)}]
            if hits:
                results[t]["frames"].append({
                    "frame_url": fr.url,
                    "is_main": fr == page.main_frame,
                    "hits": hits,
                })
    (d / "targets_found.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results


def find_test_image():
    """Any small image we can upload to make 'Add to Prompt' appear."""
    candidates = []
    if config and getattr(config, "OUTPUT_DIR", None):
        candidates += sorted(Path(config.OUTPUT_DIR).glob("*.png"))
    candidates += sorted((HERE / "outputs").glob("*.png"))
    for p in candidates:
        try:
            if p.stat().st_size < 2_000_000:
                return p
        except Exception:
            continue
    return candidates[0] if candidates else None


class Tee:
    """Mirror prints to a log file so the run is debuggable without a terminal."""
    def __init__(self, logfile):
        self.f = open(logfile, "w", encoding="utf-8")
        self.stdout = sys.stdout

    def write(self, s):
        self.stdout.write(s)
        self.f.write(s)
        self.f.flush()

    def flush(self):
        self.stdout.flush()
        self.f.flush()


def main():
    d = out_root()
    sys.stdout = Tee(d / "run.log")
    print("=" * 70)
    print("Flow X-RAY — writing to:")
    print(" ", d)
    print("=" * 70)

    pw = sync_playwright().start()
    ctx = pw.chromium.launch_persistent_context(
        user_data_dir=profile_dir(),
        headless=False,
        channel="chrome",
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-first-run",
            "--no-default-browser-check",
            "--start-maximized",
        ],
        ignore_default_args=["--enable-automation"],
        viewport=None,
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    try:
        print("\n[1/6] Opening Google Flow…")
        page.goto(flow_url(), timeout=40000)
        time.sleep(5)

        # Enter a project so the prompt bar + picker exist
        print("[2/6] Entering a project (New project / first project)…")
        for sel in ['button:has-text("New project")',
                    '[aria-label*="New project" i]',
                    'button:has-text("Create project")']:
            try:
                b = page.query_selector(sel)
                if b and b.is_visible():
                    b.click()
                    break
            except Exception:
                continue
        time.sleep(6)

        # Recover from Flow client-side crash
        try:
            if "Application error" in (page.inner_text("body", timeout=4000) or ""):
                page.reload(timeout=40000)
                time.sleep(6)
        except Exception:
            pass

        # KEY INSIGHT from run 20260612_193801: the page has TWO "+" buttons.
        # Top-right "+" = media library menu (Upload media / Create Collection/
        # Character/Scene) — the agent has been clicking THIS one. WRONG.
        # The REAL asset picker (with 'Add to Prompt') opens from the small "+"
        # on the PROMPT BAR at the bottom, next to "What do you want to create?".
        print("[3/6] Opening the asset picker via the PROMPT-BAR '+' (bottom)…")
        clicked_plus = page.evaluate(r"""() => {
            // find the prompt input to anchor the search
            const inputs = Array.from(document.querySelectorAll('textarea, div[contenteditable="true"]'));
            let anchor = null;
            for (const el of inputs) {
                const r = el.getBoundingClientRect();
                if (r.width > 100 && r.y > window.innerHeight * 0.5) { anchor = r; break; }
            }
            if (!anchor) return {ok: false, reason: 'no prompt input found'};
            // find clickable elements near the prompt bar (below/around input),
            // pick the LEFT-most one — that's the "+"
            const cands = [];
            for (const el of document.querySelectorAll('button, [role="button"], i, span, div')) {
                const r = el.getBoundingClientRect();
                if (r.width < 8 || r.width > 60 || r.height < 8 || r.height > 60) continue;
                if (Math.abs((r.y + r.height/2) - (anchor.y + anchor.height + 20)) > 55) continue;
                if (r.x < anchor.x - 30 || r.x > anchor.x + 120) continue;
                const t = (el.textContent || '').trim();
                cands.push({x: r.x + r.width/2, y: r.y + r.height/2, text: t.slice(0,20)});
            }
            cands.sort((a,b) => a.x - b.x);
            return cands.length ? {ok: true, btn: cands[0], all: cands.slice(0,6)}
                                : {ok: false, reason: 'no small clickable near prompt bar'};
        }""")
        print(f"    prompt-bar '+' search: {clicked_plus}")
        if clicked_plus.get('ok'):
            page.mouse.click(clicked_plus['btn']['x'], clicked_plus['btn']['y'])
            time.sleep(3)
        page.screenshot(path=str(d / "after_plus_click.png"))

        # Upload a test image INSIDE the picker so 'Add to Prompt' appears
        img = find_test_image()
        if img:
            print(f"    uploading test image: {img.name}")
            try:
                inp = page.query_selector('input[type="file"]')
                if inp:
                    inp.set_input_files(str(img))
                    print("    upload sent via input[type=file]")
                else:
                    print("    no input[type=file] found — skipping upload")
            except Exception as e:
                print(f"    upload failed: {e}")
            time.sleep(7)   # let Flow process; preview + Add to Prompt should render
        else:
            print("    no test image found — dumping with whatever is on screen")
        page.screenshot(path=str(d / "after_upload.png"))
        time.sleep(2)

        # ---- DUMP EVERYTHING ----
        print("\n[4/6] Capturing screenshot…")
        page.screenshot(path=str(d / "page.png"), full_page=False)

        print("[5/6] Dumping AX tree, frames, and deep DOM walk…")
        ax_found = dump_ax(page, d)
        frames_info = dump_frames(page, d)

        try:
            deep = page.evaluate(JS_DEEP_INTERACTIVE)
        except Exception as e:
            deep = {"error": str(e)}
        (d / "interactive_elements.json").write_text(json.dumps(deep, indent=2), encoding="utf-8")

        print("[6/6] Searching every layer for the key buttons…")
        targets = search_targets(page, d)

        # ---- SUMMARY ----
        lines = []
        lines.append("FLOW X-RAY SUMMARY")
        lines.append("=" * 50)
        lines.append(f"timestamp: {d.name}")
        lines.append(f"page url : {page.url}")
        lines.append(f"frames   : {len(page.frames)} (incl. main)")
        if isinstance(deep, dict) and "elements" in deep:
            maxdepth = max([e.get("shadowDepth", 0) for e in deep["elements"]] or [0])
            lines.append(f"deep DOM interactive elements (open shadow incl.): {len(deep['elements'])}")
            lines.append(f"max OPEN shadow depth reached: {maxdepth}")
            lines.append(f"custom elements on page: {deep.get('customElementCount')}")
        lines.append("")
        lines.append("WHERE EACH KEY BUTTON WAS FOUND")
        lines.append("-" * 50)
        for t in TARGET_TEXTS:
            in_dom = sum(len(f["hits"]) for f in targets[t]["frames"])
            in_ax = len(ax_found.get(t, []))
            verdict = []
            if in_dom:
                fr_main = any(f["is_main"] for f in targets[t]["frames"])
                verdict.append(f"DOM/shadow x{in_dom} ({'main' if fr_main else 'sub'}-frame)")
            if in_ax:
                verdict.append(f"AX-tree x{in_ax}")
            if not verdict:
                verdict.append("*** NOT FOUND in DOM/shadow OR AX — vision-only ***")
            lines.append(f"  {t:<16}: {', '.join(verdict)}")
        lines.append("")
        lines.append("INTERPRETATION")
        lines.append("-" * 50)
        atp = targets["Add to Prompt"]
        atp_dom = sum(len(f["hits"]) for f in atp["frames"])
        atp_ax = len(ax_found.get("Add to Prompt", []))
        if atp_dom:
            lines.append("Add to Prompt IS in the DOM/open-shadow walk -> the old")
            lines.append("querySelectorAll missed it because it didn't descend shadow")
            lines.append("roots. FIX: deep-shadow click (this script's walk) -> mouse click xy.")
        elif atp_ax:
            lines.append("Add to Prompt is in the AX tree but NOT the DOM walk -> it lives")
            lines.append("in a CLOSED shadow root. FIX: page.get_by_role('button',")
            lines.append("name='Add to Prompt') which resolves via the AX layer.")
        else:
            lines.append("Add to Prompt is invisible to DOM AND AX -> OOPIF or fully")
            lines.append("opaque. FIX: VISION fallback — screenshot -> locate button ->")
            lines.append("page.mouse.click(x,y). See page.png; coords come from vision.")
        lines.append("")
        lines.append("Send me: SUMMARY.txt + targets_found.json + page.png (+ ax_tree.json)")
        (d / "SUMMARY.txt").write_text("\n".join(lines), encoding="utf-8")

        print("\n" + "=" * 70)
        print("\n".join(lines))
        print("=" * 70)
        print(f"\nAll files written to:\n  {d}\n")
        print("Closing browser in 5 seconds…")
        time.sleep(5)

    except Exception as e:
        import traceback
        print("FATAL ERROR:")
        traceback.print_exc()
        try:
            page.screenshot(path=str(d / "error_state.png"))
        except Exception:
            pass
        (d / "SUMMARY.txt").write_text(f"FATAL ERROR: {e}\nSee run.log", encoding="utf-8")
        time.sleep(3)

    finally:
        try:
            ctx.close()
        except Exception:
            pass
        try:
            pw.stop()
        except Exception:
            pass


if __name__ == "__main__":
    main()
