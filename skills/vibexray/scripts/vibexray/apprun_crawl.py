"""Find routes in the code and visit them in a real browser. Playwright is an optional extra."""

from __future__ import annotations

import contextlib
import re
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse

from vibexray.apprun_boot import SKIP_DIRS, iter_source
from vibexray.model import Page
from vibexray.rules.base import redact

MAX_PAGES = 8
RUN_EXTRA_HINT = "Install the run extra: pip install 'vibexray[run]'"
ROUTE_JSX = re.compile(r"""<Route\b[^>]*?\bpath=\{?["'`]([^"'`]+)["'`]""", re.S)
ROUTE_ARRAY = re.compile(r"""\bpath\s*:\s*["'`](/[^"'`]*)["'`]""")
NEXT_PAGE = re.compile(r"^page\.(tsx|jsx|ts|js)$")
ASSET_EXT = re.compile(r"\.(png|jpe?g|gif|svg|webp|ico|pdf|zip|css|js|json|xml|txt|mp4|mp3)$", re.I)

COLLECT_JS = """() => {
  const vis = e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'; };
  const clean = t => (t || '').replace(/\\s+/g, ' ').trim().slice(0, 80);
  const buttons = [...document.querySelectorAll(
      'button, [role=button], input[type=submit], input[type=button]')]
    .filter(vis).map(e => clean(e.innerText || e.value || e.getAttribute('aria-label')))
    .filter(Boolean);
  const inputs = [...document.querySelectorAll(
      'input:not([type=hidden]):not([type=submit]):not([type=button]), textarea, select')]
    .filter(vis).map(e => {
      const lab = e.id ? document.querySelector('label[for="' + CSS.escape(e.id) + '"]') : null;
      return clean(e.getAttribute('aria-label') || (lab && lab.innerText) || e.placeholder || e.name);
    }).filter(Boolean);
  const links = [...document.querySelectorAll('a[href]')].map(a => a.href);
  return { buttons, inputs, links };
}"""


def _clean_route(path: str) -> str | None:
    # Dynamic segments and wildcards have no single URL to visit.
    if any(c in path for c in ":*[]()?") or path.startswith(("http", "#")):
        return None
    stripped = path.strip("/")
    return "/" + stripped if stripped else "/"


def _next_routes(root: Path) -> list[str]:
    found: set[str] = set()
    for base in ("app", "src/app"):
        d = root / base
        if not d.is_dir():
            continue
        for f in d.rglob("*"):
            if not NEXT_PAGE.match(f.name) or any(p in SKIP_DIRS for p in f.relative_to(d).parts):
                continue
            parts = [p for p in f.parent.relative_to(d).parts if not p.startswith("(")]
            if parts and parts[0] == "api":
                continue
            route = _clean_route("/".join(parts))
            if route:
                found.add(route)
    for base in ("pages", "src/pages"):
        d = root / base
        if not d.is_dir():
            continue
        for f in d.rglob("*"):
            if f.suffix not in (".tsx", ".jsx", ".ts", ".js") or f.name.startswith("_"):
                continue
            parts = [p for p in f.relative_to(d).with_suffix("").parts if p != "index"]
            if parts and parts[0] == "api":
                continue
            route = _clean_route("/".join(parts))
            if route:
                found.add(route)
    return sorted(found, key=lambda r: (r != "/", r))


def find_routes(root: Path) -> list[str]:
    out: list[str] = []
    for path in iter_source(root):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        matches = sorted(
            [*ROUTE_JSX.finditer(text), *ROUTE_ARRAY.finditer(text)], key=lambda m: m.start()
        )
        for m in matches:
            route = _clean_route(m.group(1))
            if route and route not in out:
                out.append(route)
    for route in _next_routes(root):
        if route not in out:
            out.append(route)
    return out


def _slug(path: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", path.lower()).strip("-") or "index"


def _same_origin_paths(base: str, links: list[str]) -> list[str]:
    origin = urlparse(base)
    out: list[str] = []
    for href in links:
        url, _ = urldefrag(urljoin(base, href))
        p = urlparse(url)
        if p.scheme not in ("http", "https") or p.netloc != origin.netloc:
            continue
        if ASSET_EXT.search(p.path) or p.path.startswith(("/_next", "/api/")):
            continue
        path = p.path or "/"
        if path not in out:
            out.append(path)
    return out


def crawl(url: str, root: Path, out_dir: Path) -> list[Page]:
    """Visit "/" first, then routes from code, then links found on pages.

    Raises ImportError when Playwright is missing so the caller can give the install hint.
    """
    from playwright.sync_api import sync_playwright

    screens = out_dir / "screens"
    screens.mkdir(parents=True, exist_ok=True)
    queue = ["/", *find_routes(root)]
    seen: set[str] = set()
    pages: list[Page] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, timeout=30000)
        try:
            ctx = browser.new_context(viewport={"width": 1280, "height": 800})
            while queue and len(pages) < MAX_PAGES:
                path = queue.pop(0)
                if path in seen:
                    continue
                seen.add(path)
                page = ctx.new_page()
                page.set_default_timeout(15000)
                errors: list[str] = []
                page.on("console", lambda m, e=errors: m.type == "error" and e.append(m.text))
                page.on("pageerror", lambda x, e=errors: e.append(str(x)))
                entry, links = _visit(page, url, path, len(pages) + 1, screens, out_dir, errors)
                pages.append(entry)
                for p in _same_origin_paths(url, links):
                    if p not in seen and p not in queue:
                        queue.append(p)
                page.close()
        finally:
            browser.close()
    return pages


def _visit(page, url, path, n, screens, out_dir, errors) -> tuple[Page, list[str]]:
    entry = Page(path=path)
    links: list[str] = []
    try:
        resp = page.goto(url.rstrip("/") + path, wait_until="load", timeout=45000)
        entry.status = resp.status if resp else None
        # Busy pages never go idle; the screenshot still works.
        with contextlib.suppress(Exception):
            page.wait_for_load_state("networkidle", timeout=3000)
        entry.title = (page.title() or "").strip()[:120]
        shot = screens / f"{n:02d}-{_slug(path)}.png"
        page.screenshot(path=str(shot), timeout=15000)
        entry.screenshot = str(shot.relative_to(out_dir))
        data = page.evaluate(COLLECT_JS)
        entry.buttons = list(dict.fromkeys(data["buttons"]))[:30]
        entry.inputs = list(dict.fromkeys(data["inputs"]))[:30]
        links = data["links"]
    except Exception as exc:  # noqa: BLE001 - one bad page must not stop the crawl
        errors.append(f"Could not load this page: {str(exc).splitlines()[0]}")
    entry.console_errors = [redact(e) for e in dict.fromkeys(errors)][:10]
    return entry, links
