"""
autopilot/browser_driver.py
────────────────────────────────────────────────────────────────────────────────
Playwright-based Chrome driver for the AutoPilot.

The agent uses a DEDICATED Chrome profile signed into the AutoPilot Google
account (pilot.deleqate@gmail.com with Google One AI Premium).

This means:
  - gemini.google.com → Gemini Advanced (2M context, better reasoning)
  - labs.google/flow   → Google Flow (image + video generation)
  - drive.google.com  → Google Drive (file storage)

Key design: we reuse ONE browser context across the session (persistent profile)
so the agent stays signed in without re-authenticating on every task.
────────────────────────────────────────────────────────────────────────────────
"""

import logging
import time
import random
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger('autopilot.browser')

try:
    from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, TimeoutError as PWTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("⚠  playwright not installed — run: pip install playwright && playwright install chromium")

from autopilot import config


def _human_pause(min_sec: float = 0.8, max_sec: float = 2.2):
    """Random pause between actions — makes automation look human to Google."""
    time.sleep(random.uniform(min_sec, max_sec))


def _human_type(page, selector: str, text: str):
    """
    Type text character-by-character with small random delays.
    Looks identical to a human typing at ~80 WPM.
    Falls back to clipboard paste for very long text (>300 chars).
    """
    if len(text) > 300:
        # For long prompts: insert_text sends one real input event — fast and
        # React-safe (execCommand crashes React-based apps like Google Flow)
        el = page.query_selector(selector)
        if el:
            el.click()
            _human_pause(0.2, 0.5)
            page.keyboard.insert_text(text)
    else:
        el = page.query_selector(selector)
        if el:
            el.click()
            _human_pause(0.2, 0.5)
            for char in text:
                el.type(char, delay=random.randint(40, 130))


class BrowserDriver:
    """
    Manages a persistent Chrome browser instance for the AutoPilot.
    Uses the AutoPilot's dedicated Chrome profile so Google sessions persist.
    """

    def __init__(self):
        self._playwright = None
        self._browser: Optional['Browser'] = None
        self._context: Optional['BrowserContext'] = None
        self.page: Optional['Page'] = None
        self._signed_into_google = False

    def start(self, headless: bool = False) -> bool:
        """
        Launch Chrome with the AutoPilot's dedicated profile.
        headless=False: Chrome window visible (recommended — Google is happier with visible Chrome).
        headless=True: background mode (can be minimised manually after launch).
        """
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("❌ Playwright not installed. Run: pip install playwright && playwright install chromium")
            return False

        try:
            self._playwright = sync_playwright().start()

            profile_dir = Path(config.CHROME_PROFILE_DIR)
            profile_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"🌐 Using Chrome profile: {profile_dir}")

            # Launch persistent context (keeps cookies, Google session, etc.)
            # channel='chrome' = use REAL installed Chrome, not Playwright's
            # bundled Chromium — Google web apps are far more stable in it.
            launch_kwargs = dict(
                user_data_dir=str(profile_dir),
                headless=headless,
                channel='chrome',
                args=[
                    '--disable-blink-features=AutomationControlled',   # hides webdriver flag
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-extensions-except=',
                    '--start-maximized',
                ],
                ignore_default_args=['--enable-automation'],  # removes automation banner
                viewport=None,          # None = use --start-maximized window size
                accept_downloads=True,
                downloads_path=str(config.OUTPUT_DIR),
            )
            try:
                self._context = self._playwright.chromium.launch_persistent_context(**launch_kwargs)
            except Exception:
                # Real Chrome not found — fall back to bundled Chromium
                logger.warning("⚠  Installed Chrome not found, falling back to bundled Chromium")
                launch_kwargs.pop('channel', None)
                self._context = self._playwright.chromium.launch_persistent_context(**launch_kwargs)

            self.page = self._context.new_page()

            # Set a real user-agent (Playwright's default includes "HeadlessChrome" — bad)
            self.page.set_extra_http_headers({
                'Accept-Language': 'en-IN,en;q=0.9',
            })

            logger.info("🌐 Chrome browser started (AutoPilot profile)")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to start browser: {e}")
            logger.error("   If you see 'Opening in existing browser session' — close Chrome and retry.")
            return False

    def stop(self):
        """Close browser gracefully."""
        try:
            if self._context:
                self._context.close()
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass
        self._browser = None
        self._context = None
        self.page = None
        logger.info("🌐 Browser closed")

    def ensure_google_signed_in(self) -> bool:
        """
        Verify the AutoPilot Google account is signed in.
        If not, open accounts.google.com for manual sign-in.
        """
        if self._signed_into_google:
            return True

        self.page.goto('https://accounts.google.com/', timeout=20000)
        time.sleep(2)

        # Check if signed in
        url = self.page.url
        if 'myaccount.google.com' in url or 'accounts.google.com/v3/signin' not in url:
            # Try checking the email shown
            try:
                email_text = self.page.inner_text('body', timeout=3000)
                if config.AUTOPILOT_EMAIL.split('@')[0].lower() in email_text.lower():
                    self._signed_into_google = True
                    logger.info(f"✅ Google account confirmed: {config.AUTOPILOT_EMAIL}")
                    return True
            except Exception:
                pass

        logger.warning("⚠  Google account not signed in. Please sign in manually:")
        logger.warning(f"   1. The browser will open accounts.google.com")
        logger.warning(f"   2. Sign in as: {config.AUTOPILOT_EMAIL}")
        logger.warning(f"   3. The agent will continue automatically")

        self.page.goto('https://accounts.google.com/signin', timeout=20000)
        # Wait up to 2 minutes for manual sign-in
        for _ in range(24):
            time.sleep(5)
            current_url = self.page.url
            if 'myaccount' in current_url or 'google.com/u/' in current_url:
                self._signed_into_google = True
                logger.info(f"✅ Signed into Google: {config.AUTOPILOT_EMAIL}")
                return True

        logger.error("❌ Google sign-in timed out after 2 minutes")
        return False

    # ── Gemini Advanced ────────────────────────────────────────────────────────

    def ask_gemini(self, prompt: str, timeout_sec: int = 60) -> str:
        """
        Send a prompt to Gemini Advanced (gemini.google.com) and return the response.
        Uses the AutoPilot's Google One AI Premium account.
        Behaves like a human: navigates, waits, pastes, submits.
        """
        try:
            self.page.goto('https://gemini.google.com/', timeout=30000)
            _human_pause(2.5, 4.0)   # wait for page to settle like a human would

            # Extended selector list — Gemini updates their DOM regularly
            input_selectors = [
                'rich-textarea div[contenteditable="true"]',
                'div[contenteditable="true"][role="textbox"]',
                'div[contenteditable="true"]',
                'textarea[placeholder]',
                '.ql-editor',
                'ms-autosize-textarea textarea',
            ]
            input_sel = None
            for sel in input_selectors:
                try:
                    self.page.wait_for_selector(sel, timeout=6000)
                    el = self.page.query_selector(sel)
                    if el and el.is_visible():
                        input_sel = sel
                        break
                except PWTimeout:
                    continue

            if not input_sel:
                logger.error("❌ Could not find Gemini input field — taking debug screenshot")
                self.take_screenshot('gemini_no_input')
                return ''

            # Click to focus, clear any previous text
            self.page.click(input_sel)
            _human_pause(0.3, 0.7)
            self.page.keyboard.press('Control+a')
            self.page.keyboard.press('Delete')
            _human_pause(0.2, 0.5)

            # Insert the prompt with real input events (React/Angular-safe)
            for sel in ('rich-textarea div[contenteditable="true"]',
                        'div[contenteditable="true"][role="textbox"]',
                        'div[contenteditable="true"]'):
                el = self.page.query_selector(sel)
                if el and el.is_visible():
                    el.click()
                    _human_pause(0.3, 0.6)
                    self.page.keyboard.insert_text(prompt)
                    break
            _human_pause(0.8, 1.5)

            # Submit with Enter (same as pressing the send button)
            self.page.keyboard.press('Enter')
            logger.debug(f"   💬 Prompt sent to Gemini ({len(prompt)} chars)")

            return self._wait_for_gemini_response(timeout_sec)

        except Exception as e:
            logger.error(f"❌ Gemini error: {e}")
            return ''

    def ask_gemini_with_image(self, prompt: str, image_path: Path, timeout_sec: int = 90) -> str:
        """
        Send a prompt + image to Gemini for vision analysis (QC, staging review, etc.)
        """
        try:
            self.page.goto('https://gemini.google.com/', timeout=20000)
            time.sleep(3)

            # Upload the image. Prefer setting a hidden <input type=file>
            # directly — modern Gemini's paperclip opens a MENU first, so
            # waiting for a filechooser on the paperclip click times out.
            uploaded = False
            inp = self.page.query_selector('input[type="file"]')
            if inp:
                try:
                    inp.set_input_files(str(image_path))
                    uploaded = True
                except Exception:
                    pass

            if not uploaded:
                # Click paperclip to open the menu, then the upload entry
                attach_selectors = [
                    'button[aria-label*="attach" i]',
                    'button[aria-label*="upload" i]',
                    'button[aria-label*="Add files" i]',
                    'mat-icon[fonticon="attach_file"]',
                    'button[aria-label*="plus" i]',
                ]
                for sel in attach_selectors:
                    btn = self.page.query_selector(sel)
                    if btn and btn.is_visible():
                        btn.click()
                        time.sleep(1.2)
                        break
                # After the menu opens, a real file input usually appears
                inp = self.page.query_selector('input[type="file"]')
                if inp:
                    inp.set_input_files(str(image_path))
                    uploaded = True
                else:
                    # Last resort: menu item that opens an OS file chooser
                    menu_selectors = [
                        'text=/upload.*file/i',
                        '[role="menuitem"]:has-text("Upload")',
                        'button:has-text("Upload files")',
                    ]
                    for sel in menu_selectors:
                        item = self.page.query_selector(sel)
                        if item and item.is_visible():
                            try:
                                with self.page.expect_file_chooser(timeout=8000) as fc_info:
                                    item.click()
                                fc_info.value.set_files(str(image_path))
                                uploaded = True
                            except Exception:
                                pass
                            break

            if not uploaded:
                logger.error("❌ Gemini: could not upload image — taking screenshot")
                self.take_screenshot('gemini_no_upload')
                return ''
            time.sleep(2.5)

            # Now type the prompt with real input events (React-safe)
            input_el = self.page.query_selector('div[contenteditable="true"]')
            if input_el:
                input_el.click()
                time.sleep(0.5)
                self.page.keyboard.insert_text(prompt)
            time.sleep(1)
            self.page.keyboard.press('Enter')

            return self._wait_for_gemini_response(timeout_sec)

        except Exception as e:
            logger.error(f"❌ Gemini image analysis error: {e}")
            return ''

    def _wait_for_gemini_response(self, timeout_sec: int = 60) -> str:
        """Wait for Gemini to finish generating and return the response text."""
        # Gemini shows a stop/pause button while generating
        stop_selectors = [
            'button[aria-label*="Stop generating"]',
            'button[aria-label*="stop"]',
            'button[aria-label*="Stop"]',
            'button[aria-label*="Pause"]',
            '.stop-button',
            'mat-icon[fonticon="stop"]',
        ]
        # Response content selectors — ordered most-specific first
        response_selectors = [
            'model-response .response-container-content',
            'model-response',
            '.model-response-text',
            'message-content',
            '[data-message-author-role="model"]',
            '.response-container-content',
            '.conversation-container model-response',
        ]

        start_time = time.time()

        # Wait up to 8 s for the stop button to appear (generation started)
        for _ in range(16):
            time.sleep(0.5)
            if any(self.page.query_selector(sel) for sel in stop_selectors):
                break

        # Wait for stop button to disappear (generation complete)
        while time.time() - start_time < timeout_sec:
            time.sleep(1.5)
            still_generating = any(self.page.query_selector(sel) for sel in stop_selectors)
            if not still_generating:
                break

        _human_pause(1.0, 2.0)   # settle before reading

        # Extract the last response
        for sel in response_selectors:
            elements = self.page.query_selector_all(sel)
            if elements:
                text = elements[-1].inner_text()
                if text.strip():
                    logger.debug(f"   💬 Gemini responded ({len(text)} chars)")
                    return text.strip()

        # Fallback: scrape visible text from the main content area
        try:
            text = self.page.inner_text('main', timeout=4000)
            return text.strip()
        except Exception:
            return ''

    # ── Google Flow (image & video generation) ─────────────────────────────────

    def generate_with_flow(self, prompt: str,
                            reference_images: list[Path] = None,
                            generation_type: str = 'image',
                            timeout_sec: int = 180,
                            download_dir: Optional[Path] = None) -> list[Path]:
        """
        Use Google Flow (labs.google/flow) to generate images.
        Behaves like a human: loads page, uploads reference image,
        pastes prompt, clicks Generate, waits, downloads result.
        """
        if download_dir is None:
            download_dir = config.OUTPUT_DIR

        downloaded_files = []

        try:
            self.page.goto(config.GOOGLE_FLOW_URL, timeout=30000)
            _human_pause(3.5, 5.0)   # page load + JS render settle time

            logger.info(f"   🎨 Google Flow opened — generating {generation_type}")

            # Flow lands on its home page — we must enter a project before the
            # prompt input exists. Click "New project" (or open the first
            # existing project) like a human would.
            if not self._flow_quick_has_prompt_input():
                project_entry_selectors = [
                    'button:has-text("New project")',
                    'text=/^\\+?\\s*New project$/i',
                    '[aria-label*="New project" i]',
                    'button:has-text("Create project")',
                ]
                entered = False
                for sel in project_entry_selectors:
                    try:
                        btn = self.page.query_selector(sel)
                        if btn and btn.is_visible():
                            _human_pause(0.4, 0.9)
                            btn.click()
                            logger.info("   📂 Clicked 'New project' in Google Flow")
                            entered = True
                            break
                    except Exception:
                        continue
                if not entered:
                    logger.warning("⚠  Could not find 'New project' button on Flow home page")
                    self.take_screenshot('flow_no_new_project')
                # Wait for the project editor to render
                _human_pause(4.0, 6.0)
                try:
                    self.page.wait_for_load_state('networkidle', timeout=15000)
                except Exception:
                    pass
                _human_pause(1.5, 2.5)

            # Flow sometimes crashes with "Application error: a client-side
            # exception" right after entering a project — reload to recover
            for _attempt in range(2):
                try:
                    body_text = (self.page.inner_text('body', timeout=5000) or '')[:300]
                except Exception:
                    body_text = ''
                if 'Application error' in body_text:
                    logger.warning("⚠  Flow client-side crash detected — reloading page")
                    self.page.reload(timeout=30000)
                    _human_pause(4.0, 6.0)
                else:
                    break

            # Upload reference images first (they anchor the composition).
            # An upload only counts when 'Add to Prompt' succeeded — otherwise
            # the image sits in the library and is NOT an input to generation.
            attached_count = 0
            if reference_images:
                for img_path in reference_images:
                    if img_path.exists():
                        if self._flow_upload_image(img_path):
                            attached_count += 1
                        _human_pause(1.5, 3.0)
                if attached_count == 0:
                    logger.error("❌ No reference image could be attached to the "
                                 "prompt — aborting this room (won't generate "
                                 "from text alone)")
                    self._debug_dump_ui_texts('(after failed attaches)')
                    self.take_screenshot('flow_attach_failed')
                    return []
                logger.info(f"   📎 {attached_count}/{len(reference_images)} reference image(s) attached to prompt")

            # Make sure the asset picker is CLOSED before touching the prompt
            # box — otherwise the prompt lands in the picker's search bar and
            # the Generate click hits a random picker button.
            # (click outside — NEVER Escape, it can close the project)
            self._flow_dismiss_picker()
            self._flow_dismiss_picker()

            # Find prompt input — Flow uses various implementations depending on version
            prompt_selectors = [
                'textarea[placeholder*="prompt" i]',
                'textarea[placeholder*="Describe" i]',
                'textarea[aria-label*="prompt" i]',
                'div[contenteditable="true"][aria-label*="prompt" i]',
                'div[contenteditable="true"]',
                '.prompt-input textarea',
                'rich-textarea textarea',
                'textarea',
            ]
            prompt_sel = None
            for sel in prompt_selectors:
                try:
                    self.page.wait_for_selector(sel, timeout=6000)
                    el = self.page.query_selector(sel)
                    if el and el.is_visible():
                        prompt_sel = sel
                        break
                except PWTimeout:
                    continue

            if not prompt_sel:
                logger.error("❌ Google Flow: could not find prompt input — taking screenshot")
                self.take_screenshot('flow_no_input')
                return []

            # Click, clear, then paste prompt
            self.page.click(prompt_sel)
            _human_pause(0.3, 0.7)
            self.page.keyboard.press('Control+a')
            self.page.keyboard.press('Delete')
            _human_pause(0.2, 0.5)

            # Insert the prompt with real input events (keyboard.insert_text).
            # NEVER use document.execCommand here — it corrupts the React state
            # behind Flow's prompt box and crashes the page ("Application error").
            el = self.page.query_selector(prompt_sel)
            tag = el.evaluate('el => el.tagName.toLowerCase()') if el else ''
            if tag == 'textarea':
                el.fill(prompt)
            else:
                el.click()
                _human_pause(0.3, 0.6)
                self.page.keyboard.insert_text(prompt)
            _human_pause(0.8, 1.5)

            # Configure output settings like a human: Image tab, 16:9 ratio
            # (property photos), x4 outputs (pick best of four), Nano Banana 2
            self._flow_configure_output(generation_type=generation_type)

            # Snapshot every image on the page BEFORE generating, so uploads
            # and thumbnails are never mistaken for generated results
            baseline_srcs = self._snapshot_image_srcs()

            # Click the Generate button
            generate_selectors = [
                'button:has-text("Generate")',
                'button[aria-label*="Generate" i]',
                'button:has-text("Create")',
                'button[aria-label*="Create" i]',
                'button[aria-label*="Send" i]',
                'button[aria-label*="Submit" i]',
                'button[aria-label*="Run" i]',
                'button[type="submit"]',
                '.generate-button',
                # Flow's submit is often an icon-only arrow button next to the prompt box
                'textarea ~ button',
                'div[contenteditable="true"] ~ button',
            ]
            generated = False
            # Flow's submit is the 'Create' arrow — its full text content
            # including the icon ligature is 'arrow_forwardCreate'
            if self._click_by_text('arrow_forwardCreate'):
                generated = True
                logger.info("   ▶  Generation started (Create arrow)")
            for sel in generate_selectors if not generated else []:
                try:
                    btn = self.page.query_selector(sel)
                    if btn and btn.is_enabled() and btn.is_visible():
                        _human_pause(0.4, 0.9)   # pause before clicking like a human
                        btn.click()
                        generated = True
                        logger.info("   ▶  Generation started in Google Flow")
                        break
                except Exception:
                    continue

            if not generated:
                # The submit is an arrow icon at the right end of the prompt
                # bar — click the last enabled button inside the prompt area,
                # then fall back to Enter / Ctrl+Enter
                try:
                    arrow = self.page.query_selector(
                        'form button:last-of-type, '
                        '[class*="prompt"] button:last-of-type')
                    if arrow and arrow.is_enabled() and arrow.is_visible():
                        arrow.click()
                        generated = True
                        logger.info("   ▶  Generation started (arrow submit)")
                except Exception:
                    pass
            if not generated:
                logger.warning("⚠  Generate button not found — trying Enter")
                self.page.keyboard.press('Enter')
                _human_pause(0.8, 1.2)
                self.page.keyboard.press('Control+Enter')

            # Wait and download
            downloaded_files = self._wait_and_download_flow_results(
                timeout_sec=timeout_sec,
                download_dir=download_dir,
                generation_type=generation_type,
                baseline_srcs=baseline_srcs,
            )

        except Exception as e:
            logger.error(f"❌ Google Flow error: {e}")
            self.take_screenshot('flow_error')

        return downloaded_files

    def _flow_quick_has_prompt_input(self) -> bool:
        """Quick non-blocking check: are we already inside a Flow project
        (i.e. a prompt input is present)?"""
        try:
            for sel in ('textarea', 'div[contenteditable="true"]'):
                el = self.page.query_selector(sel)
                if el and el.is_visible():
                    return True
        except Exception:
            pass
        return False

    def _flow_picker_open(self) -> bool:
        """Is the asset picker popover open? (detected by its search field)"""
        try:
            return bool(self.page.evaluate(
                """() => !!Array.from(document.querySelectorAll('input'))
                    .find(i => (i.placeholder || '').toLowerCase().includes('search assets'))"""))
        except Exception:
            return False

    def _flow_dismiss_picker(self):
        """Close the asset picker by clicking a neutral spot on the canvas.
        NEVER press Escape in the Flow editor — it can navigate back and
        close the whole project."""
        try:
            if self._flow_picker_open():
                size = self.page.evaluate(
                    '() => ({w: window.innerWidth, h: window.innerHeight})')
                self.page.mouse.click(size['w'] * 0.85, size['h'] * 0.18)
                _human_pause(0.6, 1.0)
        except Exception:
            pass

    def _flow_open_prompt_picker(self) -> bool:
        """Open the REAL asset picker via the PROMPT-BAR '+' (bottom of page).

        X-RAY FINDING (outputs/xray/20260612_194458): Flow has TWO '+' buttons:
          - top-right header: 'addAdd Media' → media-library menu (Upload media/
            Create Collection/Character/Scene). NO 'Add to Prompt' here. WRONG.
          - prompt bar (bottom): 'add_2Create' → the actual asset picker with
            Search assets / asset rows / preview + white 'Add to Prompt'. RIGHT.
        We find the prompt input geometrically and click the left-most small
        clickable on the prompt bar — robust against text/ligature changes."""
        if self._flow_picker_open():
            return True
        try:
            res = self.page.evaluate(r"""() => {
                const inputs = Array.from(document.querySelectorAll('textarea, div[contenteditable="true"]'));
                let anchor = null;
                for (const el of inputs) {
                    const r = el.getBoundingClientRect();
                    if (r.width > 100 && r.y > window.innerHeight * 0.5) { anchor = r; break; }
                }
                if (!anchor) return null;
                const cands = [];
                for (const el of document.querySelectorAll('button, [role="button"], i, span, div')) {
                    const r = el.getBoundingClientRect();
                    if (r.width < 8 || r.width > 60 || r.height < 8 || r.height > 60) continue;
                    if (Math.abs((r.y + r.height/2) - (anchor.y + anchor.height + 20)) > 55) continue;
                    if (r.x < anchor.x - 30 || r.x > anchor.x + 120) continue;
                    cands.push({x: r.x + r.width/2, y: r.y + r.height/2});
                }
                cands.sort((a,b) => a.x - b.x);
                return cands.length ? cands[0] : null;
            }""")
            if res:
                self.page.mouse.click(res['x'], res['y'])
                _human_pause(1.5, 2.5)
                if self._flow_picker_open():
                    logger.info("   ➕ Asset picker opened (prompt-bar '+')")
                    return True
            # Text fallback: the prompt-bar '+' reads 'add_2Create' (icon
            # ligature add_2 + label Create) — NOT 'addAdd Media' (top-right)
            if self._click_by_text('add_2Create'):
                _human_pause(1.5, 2.5)
                if self._flow_picker_open():
                    logger.info("   ➕ Asset picker opened (add_2Create fallback)")
                    return True
        except Exception as e:
            logger.warning(f"⚠  Could not open prompt-bar picker: {e}")
        logger.warning("⚠  Prompt-bar '+' not found — asset picker NOT open")
        self._debug_dump_ui_texts('(looking for prompt-bar +)')
        self.take_screenshot('flow_no_prompt_picker')
        return False

    def _flow_prompt_chip_count(self) -> int:
        """How many image chips are attached to the prompt bar right now?
        (Small thumbnails rendered just above the prompt input. Counting them
        is the ground truth for 'is this image a generation input?' — the
        June 2026 Flow UI attaches an asset the moment its row is clicked in
        the picker, WITHOUT showing an 'Add to Prompt' button.)"""
        try:
            n = self.page.evaluate(r"""() => {
                const inputs = Array.from(document.querySelectorAll('textarea, div[contenteditable="true"]'));
                let anchor = null;
                for (const el of inputs) {
                    const r = el.getBoundingClientRect();
                    if (r.width > 100 && r.y > window.innerHeight * 0.5) { anchor = r; break; }
                }
                if (!anchor) return -1;
                let count = 0;
                for (const img of document.querySelectorAll('img')) {
                    const r = img.getBoundingClientRect();
                    if (r.width < 16 || r.width > 120 || r.height < 16 || r.height > 120) continue;
                    const cy = r.y + r.height / 2;
                    if (cy < anchor.y - 160 || cy > anchor.y + 5) continue;
                    if (r.x < anchor.x - 40 || r.x > anchor.x + anchor.width) continue;
                    count++;
                }
                return count;
            }""")
            return int(n)
        except Exception:
            return -1

    def _flow_upload_image(self, image_path: Path):
        """Upload a reference image to Google Flow THE HUMAN WAY:
        1. open the asset picker via the PROMPT-BAR '+' (NOT the top-right
           'Add Media' — that one opens the media-library menu, see X-ray note
           in _flow_open_prompt_picker)
        2. upload the file inside the picker
        3. attach to prompt: clicking the asset row attaches directly in the
           current UI (verified by chip count); 'Add to Prompt' is a fallback"""
        try:
            # 1. Open the asset picker if it isn't open
            if not self._flow_open_prompt_picker():
                return False

            # 2. Upload inside the picker: direct file input first,
            #    else the 'Upload media' entry with an OS chooser
            uploaded = False
            inp = self.page.query_selector('input[type="file"]')
            if inp:
                inp.set_input_files(str(image_path))
                uploaded = True
            else:
                try:
                    with self.page.expect_file_chooser(timeout=8000) as fc_info:
                        if not self._click_by_text('Upload media', exact=False):
                            raise RuntimeError("'Upload media' not found")
                    fc_info.value.set_files(str(image_path))
                    uploaded = True
                except Exception as e:
                    logger.warning(f"⚠  Picker upload failed: {e}")

            if not uploaded:
                logger.warning(f"⚠  Could not upload {image_path.name} to Flow")
                self.take_screenshot('flow_no_upload')
                return False

            logger.info(f"   ⬆  Uploaded to Flow: {image_path.name}")
            time.sleep(3.0)   # let Flow process the upload

            # 3. Attach to prompt
            return self._flow_attach_uploaded_asset(image_path)
        except Exception as e:
            logger.warning(f"⚠  Could not upload image to Flow: {e}")
            return False

    def _flow_attach_uploaded_asset(self, image_path: Path = None):
        """After uploading to Flow's asset library, the asset must become a
        GENERATION INPUT (a chip on the prompt bar).

        June 2026 UI (verified live, agent run 19:53–20:00): clicking the
        asset's row in the picker attaches it to the prompt DIRECTLY — there
        is no 'Add to Prompt' button anymore. Ground truth for success is the
        prompt-bar CHIP COUNT increasing, not any button click.
        Older UI had a preview + white 'Add to Prompt' button — kept as a
        fallback in case Google A/B tests it back."""
        try:
            _human_pause(1.2, 2.0)   # let the upload finish processing
            chips_before = self._flow_prompt_chip_count()

            def attached() -> bool:
                n = self._flow_prompt_chip_count()
                return n >= 0 and chips_before >= 0 and n > chips_before

            # 1. Select the uploaded asset in the picker (by filename) —
            #    in the current UI this click IS the attach action.
            if image_path is not None:
                partial = image_path.stem[:18]
                try:
                    row = self.page.locator(f'text={partial}').first
                    if row.is_visible():
                        row.click()
                        logger.info(f"   🖱  Selected asset in picker: {image_path.name}")
                        _human_pause(0.8, 1.4)
                except Exception:
                    pass

            if attached():
                logger.info("   ➕ Asset attached to prompt (chip visible on prompt bar)")
                return True

            # 2. Fallback: old UI's 'Add to Prompt' button (retry loop)
            deadline = time.time() + 12
            reopened = False
            while time.time() < deadline:
                if self._click_by_text('Add to Prompt'):
                    _human_pause(0.8, 1.4)
                    if attached():
                        logger.info("   ➕ Asset attached to prompt (Add to Prompt)")
                        return True
                if attached():
                    logger.info("   ➕ Asset attached to prompt (chip visible on prompt bar)")
                    return True
                if not reopened and time.time() - (deadline - 12) > 5:
                    reopened = True
                    # Picker may have closed — re-open via the PROMPT-BAR '+'
                    if self._flow_open_prompt_picker():
                        logger.info("   ➕ Re-opened asset picker (prompt-bar +)")
                        _human_pause(1.0, 1.6)
                    if image_path is not None:
                        try:
                            row = self.page.locator(f'text={image_path.stem[:18]}').first
                            if row.is_visible():
                                row.click()
                                _human_pause(0.8, 1.4)
                        except Exception:
                            pass
                time.sleep(0.7)

            logger.warning(f"⚠  Asset did not attach to prompt "
                           f"(chips before={chips_before}, now={self._flow_prompt_chip_count()})")
            self._debug_dump_ui_texts('(asset picker)')
            self.take_screenshot('flow_no_add_to_prompt')
            return False
        except Exception as e:
            logger.warning(f"⚠  Could not attach asset to prompt: {e}")
            return False

    def _click_by_text(self, text: str, exact: bool = True) -> bool:
        """Click an element by its visible text. Searches the raw DOM with JS
        (any tag, any frame), finds the innermost visible match, and clicks its
        screen coordinates with a real mouse click. Returns True if clicked."""
        js = """(args) => {
            const want = args.text.toLowerCase();
            const els = Array.from(document.querySelectorAll('button, [role="button"], a, div, span'));
            let best = null;
            for (const el of els) {
                const t = (el.textContent || '').trim();
                if (!t || t.length > args.text.length + 30) continue;
                const ok = args.exact ? (t === args.text)
                                      : t.toLowerCase().includes(want);
                if (!ok) continue;
                const r = el.getBoundingClientRect();
                if (r.width < 5 || r.height < 5) continue;
                const cs = getComputedStyle(el);
                if (cs.visibility === 'hidden' || cs.display === 'none' || cs.opacity === '0') continue;
                best = el;   // keep the LAST (innermost/most recent) match
            }
            if (!best) return null;
            best.scrollIntoView({block: 'center'});
            const r = best.getBoundingClientRect();
            return {x: r.x + r.width / 2, y: r.y + r.height / 2};
        }"""
        for frame in self.page.frames:
            try:
                box = frame.evaluate(js, {'text': text, 'exact': exact})
                if not box:
                    continue
                ox, oy = 0, 0
                if frame != self.page.main_frame:
                    fe = frame.frame_element()
                    fb = fe.bounding_box() if fe else None
                    if fb:
                        ox, oy = fb['x'], fb['y']
                self.page.mouse.click(box['x'] + ox, box['y'] + oy)
                return True
            except Exception:
                continue
        if exact:
            return self._click_by_text(text, exact=False)
        return False

    def _debug_dump_ui_texts(self, label: str = ''):
        """Log the visible clickable texts on the page — ground truth for
        debugging 'button not found' instead of guessing selectors."""
        try:
            texts = self.page.evaluate(
                """() => Array.from(document.querySelectorAll('button, [role="button"], a'))
                    .map(e => (e.textContent || '').trim())
                    .filter(t => t && t.length < 40)
                    .slice(0, 60)""")
            logger.info(f"   🧭 Visible clickables {label}: {texts}")
        except Exception:
            pass

    # ════════════════════════════════════════════════════════════════════════
    # GOOGLE FLOW PLATFORM KNOWLEDGE (UI map as of June 2026)
    #
    # Home (labs.google/fx/tools/flow):
    #   grid of projects + "New project" button → opens project editor
    # Project editor:
    #   - TWO different "+" buttons (X-ray verified 12 Jun 2026):
    #       TOP-RIGHT header "+" = 'addAdd Media' → media-library menu only
    #         (Upload media / Create Collection / Character / Scene) — NO
    #         'Add to Prompt' here. DO NOT use for attaching to prompt.
    #       PROMPT-BAR "+" (bottom-left of prompt box) = 'add_2Create' →
    #         the REAL asset picker. Use _flow_open_prompt_picker().
    #   - Prompt bar at bottom: "What do you want to create?"
    #       [+] button  → opens asset picker (upload/select reference images)
    #       [Agent] chip → agent mode toggle
    #       [model chip e.g. "Nano Banana 2 ▢ x4"] → opens OUTPUT SETTINGS panel
    #       [→] arrow   → submit/generate
    #   - Output settings panel (opened from model chip):
    #       Image | Video tabs
    #       aspect ratios: 16:9, 4:3, 1:1, 3:4, 9:16
    #       output count: 1x, x2, x3, x4
    #       model dropdown: Nano Banana Pro / Nano Banana 2 / Imagen 4 (images)
    #                       Veo (video)
    #   - Asset picker (from [+]):
    #       list of uploaded assets, "Upload media" button,
    #       selecting an asset shows preview + white "Add to Prompt" button —
    #       an upload is NOT part of the prompt until "Add to Prompt" is clicked
    #   - Results render as large tiles in the project canvas
    # ════════════════════════════════════════════════════════════════════════

    def _flow_configure_output(self, generation_type: str = 'image',
                               aspect_ratio: str = '16:9',
                               count: str = 'x4',
                               model: str = 'Nano Banana 2'):
        """Open Flow's output-settings panel (via the model chip on the prompt
        bar) and configure: Image/Video tab, aspect ratio, output count, model.
        Every step is best-effort — Flow's defaults are used if a control
        isn't found."""
        try:
            # Open the settings panel by clicking the model chip
            opened = False
            for chip_text in ('Nano Banana', 'Imagen', 'Veo'):
                try:
                    chip = self.page.get_by_text(re.compile(chip_text, re.I)).last
                    if chip.count() > 0 and chip.is_visible():
                        chip.click()
                        opened = True
                        _human_pause(0.8, 1.4)
                        break
                except Exception:
                    continue
            if not opened:
                logger.debug("   🎛  Output settings chip not found — using Flow defaults")
                return

            # 1. Image vs Video tab
            tab = 'Image' if generation_type == 'image' else 'Video'
            if self._click_by_text(tab):
                logger.info(f"   🎛  Output type: {tab}")
                _human_pause(0.4, 0.8)

            # 2. Aspect ratio (16:9 suits property/interior photos)
            if self._click_by_text(aspect_ratio):
                logger.info(f"   🎛  Aspect ratio: {aspect_ratio}")
                _human_pause(0.4, 0.8)

            # 3. Output count (x4 = four options to pick the best from)
            if self._click_by_text(count):
                logger.info(f"   🎛  Output count: {count}")
                _human_pause(0.4, 0.8)

            # 4. Model
            if self._click_by_text(model):
                logger.info(f"   🎛  Model: {model}")
                _human_pause(0.4, 0.8)

            # Close the panel by clicking a neutral canvas spot (no Escape!)
            try:
                size = self.page.evaluate(
                    '() => ({w: window.innerWidth, h: window.innerHeight})')
                self.page.mouse.click(size['w'] * 0.85, size['h'] * 0.18)
            except Exception:
                pass
            _human_pause(0.5, 0.9)
        except Exception as e:
            logger.debug(f"   🎛  Output configuration skipped: {e}")

    def _snapshot_image_srcs(self) -> set:
        """All img srcs currently on the page — taken BEFORE generation so
        uploads/thumbnails are never mistaken for generated results."""
        try:
            return set(self.page.eval_on_selector_all(
                'img', 'els => els.map(e => e.src).filter(Boolean)'))
        except Exception:
            return set()

    def _download_img_src(self, src: str, dest: Path) -> bool:
        """Download an image src (works for blob: and authenticated URLs by
        fetching inside the page context with the page's own cookies)."""
        try:
            b64 = self.page.evaluate(
                """async (src) => {
                    const r = await fetch(src);
                    const b = await r.blob();
                    return await new Promise(res => {
                        const fr = new FileReader();
                        fr.onloadend = () => res(fr.result);
                        fr.readAsDataURL(b);
                    });
                }""", src)
            if not b64 or ',' not in b64:
                return False
            import base64
            dest.write_bytes(base64.b64decode(b64.split(',', 1)[1]))
            return dest.stat().st_size > 30_000   # reject tiny icons/placeholders
        except Exception as e:
            logger.warning(f"⚠  Could not download result image: {e}")
            return False

    def _wait_and_download_flow_results(self, timeout_sec: int,
                                         download_dir: Path,
                                         generation_type: str,
                                         baseline_srcs: set = None) -> list[Path]:
        """Wait for Flow to finish generating and download NEW images only —
        anything whose src existed before Generate (uploads, thumbnails, UI)
        is excluded."""
        downloaded = []
        start_time = time.time()
        baseline = baseline_srcs or set()
        announced = False

        logger.info(f"   ⏳ Waiting for Flow to generate ({timeout_sec}s max)...")
        while time.time() - start_time < timeout_sec:
            time.sleep(5)

            try:
                candidates = self.page.eval_on_selector_all(
                    'img',
                    """els => els
                        .filter(e => e.src && e.naturalWidth >= 400 && e.naturalHeight >= 300)
                        .map(e => e.src)""")
            except Exception:
                candidates = []

            new_srcs = [s for s in candidates if s not in baseline]
            if new_srcs:
                if not announced:
                    logger.info(f"   ✅ {len(new_srcs)} new result image(s) detected")
                    announced = True
                # Give Flow a few seconds to finish rendering all variants
                time.sleep(6)
                try:
                    candidates = self.page.eval_on_selector_all(
                        'img',
                        """els => els
                            .filter(e => e.src && e.naturalWidth >= 400 && e.naturalHeight >= 300)
                            .map(e => e.src)""")
                    new_srcs = [s for s in candidates if s not in baseline]
                except Exception:
                    pass

                ext = 'jpg' if generation_type == 'image' else 'mp4'
                seen = set()
                for i, src in enumerate(new_srcs):
                    if src in seen:
                        continue
                    seen.add(src)
                    fname = download_dir / f'flow_result_{int(time.time())}_{i+1}.{ext}'
                    if self._download_img_src(src, fname):
                        downloaded.append(fname)
                        logger.info(f"   ⬇  Downloaded Flow result: {fname.name}")
                if downloaded:
                    return downloaded
                # Detected new images but couldn't save any — keep waiting

            # Check for error messages
            error_el = self.page.query_selector('.error-message, [aria-label*="error"]')
            if error_el:
                logger.error(f"❌ Flow generation error: {error_el.inner_text()}")
                break

        if not downloaded:
            # INTEGRITY: never pass a screenshot off as a deliverable.
            # Save one for debugging only and return empty so the task fails
            # honestly and escalates to a human instead of shipping garbage.
            logger.error("❌ No results produced by Flow — saving DEBUG screenshot "
                         "(NOT a deliverable) and failing this room")
            try:
                self.take_screenshot('flow_no_result_debug')
            except Exception:
                pass

        return downloaded

    # ── Utility ────────────────────────────────────────────────────────────────

    def take_screenshot(self, name: str = 'debug') -> Path:
        """Take a screenshot for debugging."""
        path = config.OUTPUT_DIR / f'{name}_{int(time.time())}.png'
        self.page.screenshot(path=str(path))
        return path

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
