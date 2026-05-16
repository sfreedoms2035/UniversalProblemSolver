#!/usr/bin/env python3
"""
Gemini Web Chat Automation Pipeline - Core
"""

import asyncio
import json
import sys
import io
from pathlib import Path
from playwright.async_api import async_playwright
import time
from datetime import datetime

# Fix Windows console for Unicode output
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    else:
        # Keep reference to prevent garbage collection closing the buffer
        _old_stdout = sys.stdout
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


class GeminiPipeline:
    # Tool identifiers and their UI labels
    TOOL_LABELS = {
        'general': None,
        'image': 'Bild erstellen',
        'video': 'Video erstellen',
        'canvas': 'Canvas',
        'deep_research': 'Deep Research',
        'music': 'Musik erstellen',
        'learning': 'Lernhilfe',
        'deep_think': 'Deep Think',
    }
    TOOL_DESCRIPTIONS = {
        'general': 'No tool selected (general task)',
        'image': 'Create images with Imagen AI',
        'video': 'Create videos with Veo 2 AI',
        'canvas': 'Interactive workspace for docs, code, and visualizations',
        'deep_research': 'Multi-step research with web search and source synthesis',
        'music': 'Create music with AI',
        'learning': 'Guided learning and tutoring assistance',
        'deep_think': 'Extended reasoning mode (requires Ultra subscription)',
    }

    def __init__(self, headless=False, output_dir="./output", persistent=False,
                 model=None, tool=None, tools=None):
        self.headless = headless
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.persistent = persistent
        self.model = model or 'pro'  # fast, thinking, pro
        self.tool = tool or 'general'  # requested tool
        self.active_tool = self.tool   # actually selected tool (may fall back to general)
        self.tools = tools or []     # reserved for future use
        self.browser = None
        self.page = None
        self.playwright = None
        self.context = None
        self._research_report = None

    async def setup_browser(self):
        self.playwright = await async_playwright().start()
        launch_args = [
            '--no-sandbox', '--disable-setuid-sandbox', '--start-maximized',
            '--disable-blink-features=AutomationControlled',
            '--disable-features=ChromeWhatsNewUI,ChromeLabs',
            '--no-first-run', '--no-default-browser-check',
        ]
        ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'

        self.browser = await self.playwright.chromium.launch(
            headless=self.headless, channel='chrome', args=launch_args)

        # Always try to load saved session if it exists
        storage_file = Path(self.output_dir) / 'gemini_session.json'
        storage_state = str(storage_file) if storage_file.exists() else None
        if storage_state:
            print(f"Loaded saved session from {storage_file}")

        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080}, user_agent=ua,
            locale='de-DE', timezone_id='Europe/Berlin',
            storage_state=storage_state,
            permissions=['clipboard-read', 'clipboard-write'])
        self.page = await self.context.new_page()

    async def navigate_to_gemini(self):
        print("Navigating to Gemini web chat...")
        for attempt in range(3):
            try:
                await self.page.goto('https://gemini.google.com/', wait_until='domcontentloaded', timeout=30000)
                break
            except Exception as e:
                if attempt < 2:
                    print(f"Navigation attempt {attempt+1} failed, retrying...")
                    await asyncio.sleep(2)
                else:
                    raise
        await asyncio.sleep(3)
        await self.dismiss_overlays()
        await self.handle_login_state()
        await self.dismiss_overlays()
        await self.switch_to_text_mode()

    async def dismiss_overlays(self):
        try:
            overlay_container = await self.page.query_selector('.cdk-overlay-container')
            if overlay_container:
                kids = await overlay_container.query_selector_all('*')
                if kids:
                    print("Dismissing overlay...")
                    await self.page.keyboard.press('Escape')
                    await asyncio.sleep(1)
                    labels = ['Ablehnen', 'Decline', 'Reject', 'Accept', 'Zustimmen',
                              'Schließen', 'Close', 'OK', 'Got it', 'Verstanden',
                              'button[aria-label="Close"]']
                    for label in labels:
                        try:
                            btn = await self.page.query_selector(f'button:text-is("{label}")')
                            if not btn:
                                btn = await self.page.query_selector(f'button:has-text("{label}")')
                            if btn and await btn.is_visible():
                                await btn.click(force=True, timeout=3000)
                                await asyncio.sleep(0.5)
                        except:
                            continue
                    btns = await overlay_container.query_selector_all('button')
                    for b in btns:
                        try:
                            if await b.is_visible():
                                await b.click(force=True, timeout=2000)
                                await asyncio.sleep(0.5)
                                break
                        except:
                            continue
                await asyncio.sleep(1)
        except:
            pass

    async def handle_login_state(self):
        print("Checking login state...")
        url = self.page.url
        if 'accounts.google.com' in url or 'signin' in url:
            if self.headless:
                raise RuntimeError(
                    "No valid session found. Run with visible browser first:\n"
                    "  python main.py --prompt \"test\"\n"
                    "Log in to Gemini, then the session will be saved automatically.")
            print("\n" + "="*60)
            print("LOGIN REQUIRED")
            print("="*60)
            print("The browser shows the Google login page.")
            print("Please log in, then press ENTER here.")
            print("="*60)
            input("\nPress ENTER after logging in...")
            try:
                await self.page.wait_for_url('**gemini.google.com**', timeout=30000)
            except:
                print("Note: timeout waiting for Gemini after login")
            await asyncio.sleep(3)
        elif 'gemini.google.com' in url:
            found = False
            for sel in ['div.ql-editor', 'div[contenteditable="true"]', '[role="textbox"]']:
                try:
                    el = await self.page.query_selector(sel)
                    if el and await el.is_visible():
                        found = True
                        break
                except:
                    continue
            if found:
                await self._save_session()
            else:
                for sel in ['button:has-text("Sign in")', 'button:has-text("Log in")',
                            'a:has-text("Sign in")']:
                    try:
                        el = await self.page.query_selector(sel)
                        if el and await el.is_visible():
                            if self.headless:
                                raise RuntimeError(
                                    "No valid session found. Run with visible browser first:\n"
                                    "  python main.py --prompt \"test\"\n"
                                    "Log in to Gemini, then the session will be saved automatically.")
                            print("\nLogin button detected - please sign in")
                            input("Press ENTER after signing in...")
                            await asyncio.sleep(3)
                            break
                    except:
                        continue
        else:
            if self.headless:
                raise RuntimeError(
                    f"Unexpected URL: {url}. No valid session found.\n"
                    "Run with visible browser first:\n"
                    "  python main.py --prompt \"test\"")
            print(f"Unexpected URL: {url}")
            input("Press ENTER once on Gemini page...")
            await asyncio.sleep(3)

    async def switch_to_text_mode(self):
        print("Checking input mode...")
        for sel in ['button[aria-label="Text"]', 'button[aria-label="Switch to text input"]',
                    'button:has-text("Text")', 'button:text-is("Aa")', 'button:text-is("abc")',
                    'button[data-value="text"]']:
            try:
                el = await self.page.query_selector(sel)
                if el and await el.is_visible():
                    await el.click()
                    await asyncio.sleep(1)
                    print("Switched to text mode")
                    return
            except:
                continue
        for sel in ['button[aria-label="Ink"]', 'button[aria-label="Draw"]',
                    'button:has-text("Ink")']:
            try:
                el = await self.page.query_selector(sel)
                if el and await el.is_visible():
                    sel_state = await el.get_attribute('aria-pressed')
                    checked = await el.get_attribute('aria-checked')
                    cls = (await el.get_attribute('class')) or ''
                    if sel_state == 'true' or checked == 'true' or 'selected' in cls or 'active' in cls:
                        await el.click()
                        await asyncio.sleep(1)
                        print("Disabled ink mode")
                        return
            except:
                continue
        print("Text mode assumed")

    async def select_model(self, mode='pro'):
        """Select Gemini mode: fast, thinking, or pro"""
        mode_map = {
            'fast': 'Fast',
            'thinking': 'Thinking-Modus',
            'pro': 'Pro',
        }
        target = mode_map.get(mode.lower(), 'Pro')
        target_lower = target.lower()
        print(f"Selecting mode: {target}")

        for attempt in range(3):
            btn = await self.page.query_selector('button[data-test-id="bard-mode-menu-button"]')
            if not btn or not await btn.is_visible():
                await asyncio.sleep(2)
                continue

            current_text = (await btn.text_content() or '').strip()
            if target_lower in current_text.lower():
                print(f"Already on {target}")
                return

            await btn.click(force=True)
            await asyncio.sleep(1.5)

            # Find the exact menu item by checking the first word of each item's text
            items = await self.page.query_selector_all(
                '.cdk-overlay-container [role="menuitem"], '
                '.cdk-overlay-container button, '
                '.cdk-overlay-container [role="option"]'
            )

            item = None
            for i in items:
                try:
                    t = (await i.text_content() or '').strip()
                    # Check if the text starts with the target or the first word matches
                    first_word = t.split()[0] if t else ''
                    if target_lower == first_word.lower() or t.lower().startswith(target_lower):
                        item = i
                        break
                except:
                    continue

            if item and await item.is_visible():
                await item.click(force=True, timeout=5000)
                await asyncio.sleep(1)
                print(f"Mode switched to {target}")
                return

            await asyncio.sleep(1)

        print(f"Could not select mode {target}")

    async def select_tool(self, tool='general'):
        """Select a Gemini tool: general, image, video, canvas, deep_research,
        music, learning, or deep_think. Opens the toolbox drawer and clicks the tool.
        Falls back to model menu for deep_think if not found in toolbox."""
        if tool == 'general':
            return

        label = self.TOOL_LABELS.get(tool)
        if not label:
            print(f"Unknown tool: {tool}")
            return

        print(f"Selecting tool: {label}")

        # Try toolbox drawer first
        result = await self._select_toolbox_drawer_tool(label)
        if result == 'selected':
            return
        if result == 'disabled':
            print(f"Tool '{label}' is disabled, falling back to general mode")
            self.active_tool = 'general'
            return

        # Fallback: try model menu (e.g. Deep Think)
        result = await self._select_model_menu_tool(label)
        if result == 'selected':
            return
        if result == 'disabled':
            print(f"Tool '{label}' in model menu is disabled, falling back to general mode")
            self.active_tool = 'general'
            return

        print(f"Could not find tool '{label}', falling back to general mode")
        self.active_tool = 'general'

    async def _select_toolbox_drawer_tool(self, label):
        """Try to select a tool from the toolbox drawer.
        Returns 'selected', 'disabled', or False."""
        for attempt in range(3):
            btn = await self.page.query_selector('button.toolbox-drawer-button')
            if not btn or not await btn.is_visible():
                await asyncio.sleep(2)
                continue

            await btn.click(force=True)
            await asyncio.sleep(1.5)

            items = await self.page.query_selector_all(
                'toolbox-drawer-item button[role="menuitemcheckbox"]'
            )
            for item in items:
                try:
                    item_label_el = await item.query_selector('.label, .gds-label-l')
                    if not item_label_el:
                        continue
                    item_label = (await item_label_el.inner_text() or '').strip()
                    if item_label == label:
                        disabled = await item.get_attribute('disabled') or ''
                        if disabled:
                            await self.page.keyboard.press('Escape')
                            await asyncio.sleep(0.5)
                            return 'disabled'
                        await item.click(force=True, timeout=5000)
                        await asyncio.sleep(1)
                        await self.page.keyboard.press('Escape')
                        await asyncio.sleep(0.5)
                        print(f"Tool selected: {label}")
                        self.active_tool = self.tool
                        return 'selected'
                except:
                    continue

            await asyncio.sleep(1)
        return False

    async def _select_model_menu_tool(self, label):
        """Try to select a tool from the model menu (e.g. Deep Think).
        Returns 'selected', 'disabled', or False."""
        for attempt in range(3):
            btn = await self.page.query_selector('button[data-test-id="bard-mode-menu-button"]')
            if not btn or not await btn.is_visible():
                await asyncio.sleep(2)
                continue

            await btn.click(force=True)
            await asyncio.sleep(1.5)

            items = await self.page.query_selector_all(
                '.cdk-overlay-container [role="menuitem"], '
                '.cdk-overlay-container button, '
                '.cdk-overlay-container [role="option"]'
            )
            for item in items:
                try:
                    t = (await item.text_content() or '').strip()
                    if label in t:
                        disabled = await item.get_attribute('disabled') or ''
                        if disabled:
                            await self.page.keyboard.press('Escape')
                            await asyncio.sleep(0.5)
                            return 'disabled'
                        await item.click(force=True, timeout=5000)
                        await asyncio.sleep(1)
                        print(f"Tool selected from model menu: {label}")
                        self.active_tool = self.tool
                        return 'selected'
                except:
                    continue

            await asyncio.sleep(1)
        return False

    async def detect_available_tools(self):
        """Detect which tools are available in the current session.
        Returns dict mapping tool IDs to availability status."""
        available = {}
        for tid in self.TOOL_LABELS:
            available[tid] = {'label': self.TOOL_LABELS[tid], 'available': False}

        try:
            # Open the toolbox drawer
            btn = await self.page.query_selector('button.toolbox-drawer-button')
            if btn and await btn.is_visible():
                await btn.click(force=True)
                await asyncio.sleep(1.5)

                items = await self.page.query_selector_all(
                    'toolbox-drawer-item button[role="menuitemcheckbox"]'
                )
                for item in items:
                    try:
                        label_el = await item.query_selector('.label, .gds-label-l')
                        if not label_el:
                            continue
                        label_text = (await label_el.inner_text() or '').strip()
                        disabled = await item.get_attribute('disabled') or ''
                        for tid, tlabel in self.TOOL_LABELS.items():
                            if tlabel and tlabel == label_text:
                                available[tid]['available'] = not disabled
                                break
                    except:
                        continue

                await self.page.keyboard.press('Escape')
                await asyncio.sleep(0.5)
        except:
            pass

        # Check model menu for Deep Think
        try:
            model_btn = await self.page.query_selector('button[data-test-id="bard-mode-menu-button"]')
            if model_btn and await model_btn.is_visible():
                await model_btn.click(force=True)
                await asyncio.sleep(1)
                items = await self.page.query_selector_all(
                    '.cdk-overlay-container [role="menuitem"], '
                    '.cdk-overlay-container [role="option"]'
                )
                for item in items:
                    try:
                        t = (await item.text_content() or '').strip()
                        if 'Deep Think' in t:
                            disabled = await item.get_attribute('disabled') or ''
                            available['deep_think']['available'] = not disabled
                            break
                    except:
                        continue
                await self.page.keyboard.press('Escape')
                await asyncio.sleep(0.5)
        except:
            pass

        return available

    def get_input_selectors(self):
        return [
            'div.ql-editor', 'div[contenteditable="true"]', 'textarea',
            'input[type="text"]', 'rich-textarea', '[role="textbox"]', '.new-input-ui'
        ]

    async def send_prompt(self, prompt):
        print(f"Sending prompt: {prompt[:50]}...")
        text_input = None
        for sel in self.get_input_selectors():
            try:
                text_input = await self.page.wait_for_selector(sel, timeout=10000)
                if text_input and await text_input.is_visible():
                    break
            except:
                continue
        if not text_input:
            raise Exception("Could not find text input element")
        await self.dismiss_overlays()
        try:
            await text_input.click(force=True, timeout=5000)
        except:
            await self.page.evaluate('el => el.click()', text_input)
        await asyncio.sleep(0.5)
        await self.force_text_mode()
        await text_input.click(click_count=3)
        await asyncio.sleep(0.2)
        await self.page.keyboard.press('Control+A')
        await self.page.keyboard.press('Backspace')
        await asyncio.sleep(0.3)
        for i in range(0, len(prompt), 50):
            chunk = prompt[i:i+50]
            await self.page.keyboard.type(chunk, delay=20)
            await asyncio.sleep(0.1)
        await asyncio.sleep(1)
        print("Prompt typed into the input field.")

    async def force_text_mode(self):
        for sel in ['button[aria-label="Text input"]', 'button[aria-label="Text"]',
                    '[data-tooltip*="text" i]', 'button:text-is("Text")',
                    'button:text-is("Aa")', 'button:text-is("abc")']:
            try:
                el = await self.page.query_selector(sel)
                if el and await el.is_visible():
                    await el.click()
                    await asyncio.sleep(0.3)
            except:
                continue
        await self.page.keyboard.press('Escape')
        await asyncio.sleep(0.3)

    async def wait_for_login(self):
        print("\n" + "="*60)
        print("LOGIN SETUP")
        print("="*60)
        print("The browser is open. Log in to Gemini, then press ENTER.")
        print("="*60)
        input("\nPress ENTER after logging in...")

    async def wait_for_confirm(self):
        print("\n" + "="*60)
        print("CONFIRM PROMPT")
        print("="*60)
        print("Prompt typed. Check browser:")
        print("1. Verify text looks correct")
        print("2. Ensure TEXT mode (not ink mode)")
        print("3. Press ENTER to send, or type 'cancel'")
        print("="*60)
        r = input("\nPress ENTER to send / 'cancel': ")
        if r.strip().lower() == 'cancel':
            raise Exception("Cancelled")
        print("Sending...\n")

    async def submit_prompt(self):
        print("Sending prompt...")
        # Try clicking the send button first (more reliable across modes)
        try:
            btn = await self.page.query_selector('button[aria-label="Nachricht senden"], button.send-button, button[aria-label*="send" i], button.submit')
            if btn and await btn.is_visible():
                await btn.click(force=True, timeout=5000)
                await asyncio.sleep(0.5)
                print("Prompt sent.")
                return
        except:
            pass
        # If a tool is active, try tool-specific button
        if self.active_tool != 'general':
            try:
                btn = await self.page.query_selector(
                    'button[aria-label="Recherche starten"], '
                    'button:has-text("Recherche starten"), '
                    'button:has-text("Recherchieren"), '
                    'button[aria-label="Start research"], '
                    'button:has-text("Start research"), '
                    'button[aria-label*="research" i]'
                )
                if btn and await btn.is_visible():
                    await btn.click(force=True, timeout=5000)
                    await asyncio.sleep(0.5)
                    print("Prompt sent via tool button.")
                    return
            except:
                pass
        # Fallback: press Enter
        await self.page.keyboard.press('Enter')
        await asyncio.sleep(0.5)
        print("Prompt sent via Enter.")

    async def _confirm_deep_research(self):
        """Wait for the Deep Research plan to appear, then click confirm to start"""
        print("Waiting for research plan...")
        await asyncio.sleep(3)  # Let the first click settle
        start = time.time()
        plan_keywords = ['Forschungsplan', 'Research Plan', 'Plan', 'Rechercheplan',
                         'Suchplan', 'Deep Research']
        confirm_keywords = ['recherche starten', 'start research', 'starten',
                            'recherche beginnen', 'begin research', 'research starten']

        conv_sel = 'div.conversation-container'
        found_plan = False

        while time.time() - start < 60:
            try:
                conv = await self.page.query_selector(conv_sel)
                content = await conv.inner_text() if conv else ''
            except:
                content = ''

            if not found_plan:
                if any(k in content for k in plan_keywords):
                    found_plan = True
                    print("Research plan detected.")
                    await asyncio.sleep(2)

            if found_plan:
                # Use JS to find any confirm button in shadow DOMs
                clicked = await self.page.evaluate(f'''() => {{
                    const patterns = {str(confirm_keywords)};
                    function clickIn(root) {{
                        for (const sel of ['button', '[role="button"]', 'a[role="button"]', '[mat-button]']) {{
                            for (const el of root.querySelectorAll(sel)) {{
                                try {{
                                    if (el.offsetParent === null) continue;
                                    const t = (el.textContent || el.getAttribute('aria-label') || '').toLowerCase().trim();
                                    if (patterns.some(p => t.includes(p))) {{
                                        el.click();
                                        return true;
                                    }}
                                }} catch(e) {{}}
                            }}
                        }}
                        for (const el of root.querySelectorAll('*')) {{
                            try {{ if (el.shadowRoot) {{ if (clickIn(el.shadowRoot)) return true; }} }} catch(e) {{}}
                        }}
                        return false;
                    }}
                    return clickIn(document);
                }}''')
                if clicked:
                    await asyncio.sleep(1)
                    print("Research confirmed.")
                    return

            await asyncio.sleep(1)

        print("Research plan confirmation timed out, proceeding anyway.")

    async def _copy_research_report(self):
        """After Deep Research finishes, copy the full report via Teilen → Kopieren"""
        print("Extracting research report...")
        
        # Click "Teilen und exportieren" button
        share_btn = await self.page.evaluate('''() => {
            const patterns = ['teilen', 'exportieren', 'share', 'export', 'mehr'];
            function search(root) {
                for (const el of root.querySelectorAll('button, [role="button"], a')) {
                    try {
                        if (el.offsetParent === null) continue;
                        const t = (el.textContent || el.getAttribute('aria-label') || '').toLowerCase().trim();
                        if (patterns.some(p => t.includes(p))) {
                            el.click();
                            return true;
                        }
                    } catch(e) {}
                }
                for (const el of root.querySelectorAll('*')) {
                    try { if (el.shadowRoot && search(el.shadowRoot)) return true; } catch(e) {}
                }
                return false;
            }
            return search(document);
        }''')
        if not share_btn:
            print("  Share button not found")
            return
        print("  Share menu opened")
        await asyncio.sleep(1.5)

        # Click "Inhalte kopieren" / "Copy content" in the menu
        copy_btn = await self.page.evaluate('''() => {
            const patterns = ['inhalte kopieren', 'copy content', 'kopieren', 'copy',
                              'inhalte', 'content kopieren'];
            function search(root) {
                for (const el of root.querySelectorAll('button, [role="button"], [role="menuitem"], a')) {
                    try {
                        if (el.offsetParent === null) continue;
                        const t = (el.textContent || el.getAttribute('aria-label') || '').toLowerCase().trim();
                        if (patterns.some(p => t.includes(p))) {
                            el.click();
                            return true;
                        }
                    } catch(e) {}
                }
                for (const el of root.querySelectorAll('*')) {
                    try { if (el.shadowRoot && search(el.shadowRoot)) return true; } catch(e) {}
                }
                return false;
            }
            return search(document);
        }''')
        if not copy_btn:
            print("  Copy button not found")
            return
        print("  Content copied to clipboard")
        await asyncio.sleep(1)

        # Read clipboard
        try:
            await self.page.bring_to_front()
            await asyncio.sleep(0.5)
            self._research_report = await self.page.evaluate(
                'navigator.clipboard.readText()'
            )
            if self._research_report:
                print(f"  Report extracted ({len(self._research_report)} chars)")
        except:
            print("  Could not read clipboard")

    async def wait_for_response(self, timeout=120):
        """Wait for Gemini response to finish streaming."""
        start = time.time()
        last_len = 0
        last_content = ''
        stable = 0
        no_grow = 0
        grew_past_initial = False
        initial_len = None
        # Answer prefixes for regular chat
        answer_prefixes = ['Gemini hat gesagt', 'Gemini said', 'Antwort']
        # Deep Research completion indicators
        research_done = ['Fertig', 'Abgeschlossen', 'Complete', 'Completed',
                         'Zusammenfassung', 'Summary', 'Ergebnis', 'Result',
                         'Fazit', 'Conclusion']

        is_deep_research = self.active_tool == 'deep_research'
        # Adjust timeout for Deep Research (min 300s)
        if is_deep_research and timeout < 300:
            timeout = 300

        conv_sel = 'div.conversation-container'

        while time.time() - start < timeout:
            try:
                conv = await self.page.query_selector(conv_sel)
                if conv:
                    content = await conv.inner_text() or ''
                else:
                    content = await self.page.evaluate('document.body.innerText') or ''
            except:
                content = ''

            if content and len(content) > 20:
                has_answer = any(p in content for p in answer_prefixes)
                has_research = any(p in content for p in research_done)
                cur_len = len(content)

                if initial_len is None:
                    initial_len = cur_len

                if is_deep_research:
                    # Detect that research output has begun (content grew past plan)
                    if cur_len > initial_len + 50:
                        grew_past_initial = True

                    # Only consider completion signals AFTER new research output appeared
                    if grew_past_initial and (has_answer or has_research):
                        if content == last_content:
                            stable += 1
                        else:
                            stable = 0
                            last_content = content
                        if stable >= 5:
                            return
                elif has_answer:
                    # Regular chat: standard stability check
                    if cur_len == last_len:
                        stable += 1
                    else:
                        stable = 0
                        last_len = cur_len
                    if stable >= 5:
                        return

            await asyncio.sleep(1)
        # Fallback
        for sel in ['div[data-message-author-role="model"]', '.response-container']:
            try:
                els = await self.page.query_selector_all(sel)
                if els:
                    content = await els[-1].text_content()
                    if content and len(content) > 10:
                        return
            except:
                pass

    async def click_thinking_toggle(self):
        """Click the 'Gedankengang anzeigen' button to reveal thinking"""
        for sel in [
            'button:has-text("Gedankengang")',
            'button:has-text("Show thinking")',
            'button:has-text("Thought process")',
            '[aria-label*="thinking" i]',
            '[aria-label*="thought" i]',
            'button:has-text("View thinking")',
            'button:has-text("Show thought")',
            'summary:has-text("Gedankengang")',
            'summary:has-text("Show thinking")',
            'summary:has-text("Thought process")',
            'details summary',
        ]:
            try:
                btn = await self.page.query_selector(sel)
                if btn and await btn.is_visible():
                    await btn.click(force=True, timeout=5000)
                    await asyncio.sleep(1)
                    print("Thinking section expanded")
                    return True
            except:
                continue
        return False

    async def extract_model(self):
        """Identify the Gemini model name from the selected mode"""
        model_map = {
            'pro': 'Gemini 3.1 Pro',
            'thinking': 'Gemini Thinking',
            'fast': 'Gemini Fast',
        }
        return model_map.get(self.model)

    async def extract_response(self):
        """Extract thinking and answer from Gemini response.
        Uses conversation container innerText to pierce Angular shadow DOM."""
        print("Extracting response...")

        # If research report was copied from Deep Research, use it directly
        if self._research_report:
            answer = self._research_report
            model = await self.extract_model()
            return {'thinking': '', 'answer': answer, 'model': model,
                    'tool': self.active_tool, 'tool_label': self.TOOL_LABELS.get(self.active_tool)}

        # Try to expand any collapsed thinking section
        await self.click_thinking_toggle()

        thinking = ""
        answer = ""

        # Get text from the conversation container (cleanest source)
        conv_sel = 'div.conversation-container'
        try:
            conv = await self.page.query_selector(conv_sel)
            if conv:
                full_text = await conv.inner_text() or ''
            else:
                full_text = await self.page.evaluate('document.body.innerText') or ''
        except:
            full_text = ''

        full_text = full_text.strip()
        if not full_text:
            return {'thinking': thinking, 'answer': answer, 'model': await self.extract_model()}

        # Remove prompt prefix if present
        for sep in ['Du hast gesagt', 'You said']:
            if sep in full_text:
                parts = full_text.split(sep, 1)
                full_text = parts[1].strip()

        # Check for answer separator
        for sep in ['Gemini hat gesagt', 'Gemini said', 'Antwort']:
            if sep in full_text:
                parts = full_text.split(sep, 1)
                pre_answer = parts[0].strip()
                answer = parts[1].strip()
                # Extract thinking from pre-answer text if thinking keywords present
                thinking_keywords = ['Gedankengang anzeigen', 'Gedankengang ausgeblendet',
                                     'Gedankengang', 'Show thinking', 'Hide thinking',
                                     'Thought process']
                if any(k in pre_answer for k in thinking_keywords):
                    # Find first thinking keyword and take everything after it
                    for k in thinking_keywords:
                        if k in pre_answer:
                            thinking = pre_answer.split(k, 1)[1].strip()
                            # Clean residual keywords
                            for k2 in thinking_keywords:
                                thinking = thinking.replace(k2, '').strip()
                            break
                break

        if not answer:
            answer = full_text
            for n in ['Gedankengang anzeigen', 'Gedankengang ausgeblendet',
                      'Gedankengang', 'Show thinking', 'Hide thinking']:
                answer = answer.replace(n, '').strip()

        model = await self.extract_model()
        return {'thinking': thinking, 'answer': answer, 'model': model,
                'tool': self.active_tool, 'tool_label': self.TOOL_LABELS.get(self.active_tool)}

    async def save_result(self, prompt, response_data, duration, filename=None, error=None):
        """Save structured JSON result and markdown report"""
        if not filename:
            filename = f"gemini_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'prompt': prompt,
            'thinking': response_data.get('thinking', ''),
            'answer': response_data.get('answer', ''),
            'model': response_data.get('model'),
            'model_selected': self.model,
            'tool': response_data.get('tool', self.active_tool),
            'tool_label': response_data.get('tool_label', self.TOOL_LABELS.get(self.active_tool)),
            'duration_seconds': round(duration, 2),
            'duration_formatted': f"{int(duration // 60)}m {int(duration % 60)}s",
            'error': error,
            'response_length': len(response_data.get('answer', '')),
            'thinking_length': len(response_data.get('thinking', '')),
        }
        
        json_file = self.output_dir / f"{filename}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"Result saved to: {json_file}")

        # Generate markdown report
        md_file = self.output_dir / f"{filename}.md"
        self._save_markdown(result, md_file)
        
        return str(json_file)

    def _save_markdown(self, result, path):
        """Save result as a formatted markdown report, preserving code blocks"""
        answer = result.get('answer', '')
        answer_md = self._detect_code_blocks(answer)

        lines = []
        lines.append(f"# Gemini Response")
        lines.append(f"")
        lines.append(f"**Prompt:** {result['prompt']}")
        lines.append(f"**Model:** {result.get('model', 'N/A')}")
        tool_label = result.get('tool_label')
        if tool_label:
            lines[-1] += f" [{tool_label}]"
        lines.append(f"**Duration:** {result.get('duration_formatted', 'N/A')}")
        lines.append(f"**Timestamp:** {result.get('timestamp', 'N/A')}")
        lines.append(f"")

        thinking = result.get('thinking', '')
        if thinking:
            lines.append(f"---")
            lines.append(f"")
            lines.append(f"## Thinking")
            lines.append(f"")
            lines.append(f"{thinking}")
            lines.append(f"")

        if answer_md:
            lines.append(f"---")
            lines.append(f"")
            lines.append(f"## Answer")
            lines.append(f"")
            lines.append(answer_md)
            lines.append(f"")

        if result.get('error'):
            lines.append(f"---")
            lines.append(f"")
            lines.append(f"## Error")
            lines.append(f"")
            lines.append(f"```")
            lines.append(result['error'])
            lines.append(f"```")

        lines.append(f"---")
        lines.append(f"")
        lines.append(f"*Generated by Gemini Web Chat Pipeline*")

        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print(f"Markdown report saved to: {path}")

    def _detect_code_blocks(self, text):
        """Detect code blocks in plain text and add markdown fences"""
        if not text:
            return text

        # Known programming languages that Gemini often uses as code block labels
        lang_keywords = [
            'python', 'javascript', 'typescript', 'java', 'c++', 'c#', 'ruby',
            'go', 'rust', 'swift', 'kotlin', 'php', 'html', 'css', 'bash',
            'shell', 'sql', 'json', 'xml', 'yaml', 'toml', 'dockerfile',
            'makefile', 'r', 'matlab', 'perl', 'scala', 'dart', 'lua',
            'haskell', 'elixir', 'clojure', 'erlang', 'fortran', 'cobol',
            'solidity', 'terraform', 'graphql', 'markdown', 'text', 'plaintext',
        ]

        lines = text.split('\n')
        result = []
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip().lower()
            # Check if this line looks like a code block header (language name)
            if stripped in lang_keywords:
                # Look ahead: are there 1+ non-empty lines of code after?
                code_lines = []
                j = i + 1
                while j < len(lines) and lines[j].strip():
                    code_lines.append(lines[j])
                    j += 1
                # Check if next line is also a language (false positive guard)
                next_is_lang = (j < len(lines) and lines[j].strip().lower() in lang_keywords)
                if code_lines and not next_is_lang:
                    lang = line.strip()
                    result.append(f'```{lang}')
                    result.extend(code_lines)
                    result.append('```')
                    i = j
                    continue
            result.append(line)
            i += 1

        return '\n'.join(result)

    async def visualize_result(self, response_data):
        print("\n" + "="*80)
        print("GEMINI RESPONSE")
        print("="*80)
        if response_data.get('model'):
            model_str = response_data['model']
            if response_data.get('tool_label'):
                model_str += f" [{response_data['tool_label']}]"
            print(f"Model: {model_str}")
        if response_data.get('thinking'):
            print("\n" + "-"*40)
            print("THINKING:")
            print("-"*40)
            print(response_data['thinking'])
        print("\n" + "-"*40)
        print("ANSWER:")
        print("-"*40)
        print(response_data.get('answer', ''))
        print("\n" + "="*80)
        print(f"Thinking: {len(response_data.get('thinking', ''))} chars")
        print(f"Answer: {len(response_data.get('answer', ''))} chars")

    async def _save_session(self):
        """Save browser session to disk"""
        try:
            storage = await self.context.storage_state()
            with open(self.output_dir / 'gemini_session.json', 'w', encoding='utf-8') as f:
                json.dump(storage, f, indent=2)
            print("Session saved for next run")
        except:
            pass

    async def cleanup(self):
        try:
            if self.context:
                await self._save_session()
                await self.context.close()
        except:
            pass
        try:
            if self.browser:
                await self.browser.close()
        except:
            pass
        try:
            if self.playwright:
                await self.playwright.stop()
        except:
            pass

    async def run(self, prompt=None, prompt_file=None, output_filename=None,
                  pause_for_login=False, confirm_before_send=True, timeout=120):
        start_time = time.time()
        try:
            if prompt_file:
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    prompt = f.read().strip()
            elif not prompt:
                raise ValueError("prompt or prompt_file required")
            await self.setup_browser()
            await self.navigate_to_gemini()
            if pause_for_login:
                await self.wait_for_login()
            # Apply model configuration
            await self.select_model(self.model)
            # Apply tool configuration
            await self.select_tool(self.tool)
            await self.send_prompt(prompt)
            if confirm_before_send:
                await self.wait_for_confirm()
            await self.submit_prompt()
            if self.active_tool == 'deep_research':
                await self._confirm_deep_research()
            await self.wait_for_response(timeout=timeout)
            if self.active_tool == 'deep_research':
                await self._copy_research_report()
            response_data = await self.extract_response()
            duration = time.time() - start_time
            
            if response_data.get('answer'):
                saved = await self.save_result(prompt, response_data, duration, output_filename)
                await self.visualize_result(response_data)
                return {
                    'success': True,
                    'prompt': prompt,
                    'response': response_data.get('answer'),
                    'thinking': response_data.get('thinking'),
                    'model': response_data.get('model'),
                    'tool': response_data.get('tool', self.active_tool),
                    'tool_label': response_data.get('tool_label'),
                    'duration': duration,
                    'response_file': saved,
                    'response_length': len(response_data.get('answer', '')),
                }
            else:
                print("No response received")
                duration = time.time() - start_time
                saved = await self.save_result(prompt, {'thinking': '', 'answer': '', 'model': None},
                                                duration, output_filename, error='No response')
                return {'success': False, 'error': 'No response', 'response_file': saved}
        except Exception as e:
            duration = time.time() - start_time
            print(f"Error: {e}")
            try:
                ss = self.output_dir / "error_screenshot.png"
                await self.page.screenshot(path=str(ss))
                print(f"Screenshot saved: {ss}")
            except:
                pass
            error_prompt = prompt if prompt else (prompt_file or 'unknown')
            saved = await self.save_result(
                error_prompt,
                {'thinking': '', 'answer': '', 'model': None},
                duration, output_filename, error=str(e))
            return {'success': False, 'error': str(e), 'response_file': saved}
        finally:
            await self.cleanup()
