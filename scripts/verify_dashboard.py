"""Optional read-only browser acceptance check; requires explicit rendered-content selectors."""
import argparse
import json
from pathlib import Path
from urllib.parse import quote, urlsplit

from superset_cli.config import get_instance, load_config


# ponytail: DOM/SVG/2D-canvas checks only; add renderer-specific checks when needed.
_RENDERED = r"""selector => {
    const element = document.querySelector(selector);
    if (!element) return false;
    if (!element.checkVisibility) return null;
    const options = {opacityProperty: true, visibilityProperty: true, contentVisibilityAuto: true};
    if (!element.checkVisibility(options)) return false;
    if (element instanceof HTMLCanvasElement) {
        const context = element.getContext('2d');
        if (!context) return null;
        if (!element.width || !element.height) return false;
        try {
            return context.getImageData(0, 0, element.width, element.height).data.some((value, index) => index % 4 === 3 && value > 0);
        } catch { return null; }
    }
    if (element instanceof SVGElement) {
        const shapes = element.tagName === 'svg' ? element.querySelectorAll('path,rect,circle,ellipse,line,polyline,polygon,text,use,image') : [element];
        return Array.from(shapes).some(shape => {
            const box = shape.getBBox();
            return shape.checkVisibility(options) && (box.width > 0 || box.height > 0);
        });
    }
    return Boolean((element.innerText || '').trim());
}"""


def verify_page(page, expected, *, timeout=30000, error_selector='[role="alert"]'):
    if not expected:
        raise ValueError("At least one expected rendered-content selector is required.")
    if urlsplit(page.url).path.startswith("/login") or page.locator('input[type="password"]').is_visible():
        raise RuntimeError("login: browser authentication is required")
    try:
        for selector in expected:
            page.locator(selector).first.scroll_into_view_if_needed(timeout=timeout)
            page.wait_for_function(_RENDERED, arg=selector, timeout=timeout)
    except Exception as exc:
        if page.locator(error_selector).count() and page.locator(error_selector).first.is_visible():
            raise RuntimeError("chart_error: visible error indicator") from exc
        present = any(page.locator(selector).count() for selector in expected)
        body_empty = not page.locator("body").inner_text().strip()
        rendered = page.evaluate(_RENDERED, selector)
        kind = "blocked" if rendered is None else ("blank" if present or body_empty else "loading_timeout")
        raise RuntimeError(f"{kind}: expected rendered content is not visible") from exc
    if page.locator(error_selector).count() and page.locator(error_selector).first.is_visible():
        raise RuntimeError("chart_error: visible error indicator")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--instance", required=True)
    parser.add_argument("--dashboard", required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--expect", action="append", required=True, help="CSS selector for actual rendered chart content, not its holder.")
    parser.add_argument("--tab", action="append", default=[])
    parser.add_argument("--tab-expect", action="append", default=[], help="One rendered selector per --tab, in the same order.")
    parser.add_argument("--min-tabs", type=int, default=0)
    parser.add_argument("--timeout", type=int, default=30000)
    parser.add_argument("--width", type=int, default=1440)
    parser.add_argument("--height", type=int, default=1000)
    parser.add_argument("--browser-executable", type=Path)
    parser.add_argument("--screenshot-dir", type=Path)
    parser.add_argument("--screenshot-selector", help="Capture an inner container instead of the viewport.")
    parser.add_argument("--error-selector", default='[role="alert"]')
    args = parser.parse_args()
    if len(args.tab) != len(args.tab_expect) or min(args.timeout, args.width, args.height) < 1 or args.min_tabs < 0:
        parser.error("Pair every --tab with --tab-expect and use positive timeout/viewport dimensions.")
    instance = get_instance(load_config(args.config), args.instance)
    if instance is None:
        parser.error("Unknown configured instance.")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        parser.error("Optional dependency missing: run with 'uv run --with playwright'.")
    counts = {"console_errors": 0, "page_errors": 0}
    try:
        with sync_playwright() as pw:
            launch = {"headless": True}
            if args.browser_executable:
                launch["executable_path"] = str(args.browser_executable)
            with pw.chromium.launch(**launch) as browser:
                context = browser.new_context(storage_state=str(args.state), viewport={"width": args.width, "height": args.height})
                page = context.new_page()
                # Counts provide bounded evidence without echoing secret-bearing browser logs.
                page.on("console", lambda event: counts.__setitem__("console_errors", counts["console_errors"] + (event.type == "error")))
                page.on("pageerror", lambda event: counts.__setitem__("page_errors", counts["page_errors"] + 1))
                page.goto(f"{instance.base_url}/superset/dashboard/{quote(args.dashboard, safe='')}/", wait_until="domcontentloaded", timeout=args.timeout)
                if page.get_by_role("tab").count() < args.min_tabs:
                    raise RuntimeError("tabs: fewer than the expected number")
                checks = [(None, args.expect)] + [(tab, [selector]) for tab, selector in zip(args.tab, args.tab_expect)]
                for index, (tab, selectors) in enumerate(checks):
                    if tab:
                        page.get_by_role("tab", name=tab, exact=True).click(timeout=args.timeout)
                    verify_page(page, selectors, timeout=args.timeout, error_selector=args.error_selector)
                    if args.screenshot_dir:
                        args.screenshot_dir.mkdir(parents=True, exist_ok=True)
                        destination = str(args.screenshot_dir / f"view-{index}.png")
                        if args.screenshot_selector:
                            page.locator(args.screenshot_selector).screenshot(path=destination)
                        else:
                            page.screenshot(path=destination, full_page=False)
                context.close()
        if counts["page_errors"]:
            raise RuntimeError("page_error: executed page reported an exception")
    except Exception as exc:
        known = str(exc).split(":", 1)[0]
        kind = known if known in {"login", "blank", "loading_timeout", "chart_error", "tabs", "page_error"} else "blocked"
        print(json.dumps({"passed": False, "reason": kind, **counts}))
        return 1
    print(json.dumps({"passed": True, "verified_views": len(checks), **counts}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
