import importlib.util
import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from superset_cli.auth import export_playwright_state
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_dashboard.py"


def test_browser_recipe_cli_tabs_and_inner_screenshots(tmp_path):
    pytest.importorskip("playwright.sync_api")
    chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    if not chrome.exists():
        pytest.skip("Optional installed Chrome is unavailable")
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):
            pass
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type","text/html")
            self.end_headers()
            self.wfile.write(b'''<div id="dashboard"><button role="tab">Overview</button><button role="tab" onclick="document.querySelector('#details').style.display='block'">Details</button><table id="first"><tr><td>42</td></tr></table><table id="details" style="display:none"><tr><td>7</td></tr></table></div>''')
    server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    config,state=tmp_path/"config.yaml",tmp_path/"state.json"
    config.write_text(f"instances:\n  - name: example\n    base_url: http://127.0.0.1:{server.server_port}\n")
    state.write_text('{"cookies":[],"origins":[]}')
    try:
        result=subprocess.run([sys.executable,str(SCRIPT),"--config",str(config),"--instance","example","--dashboard","7","--state",str(state),"--expect","#first","--tab","Details","--tab-expect","#details","--min-tabs","2","--browser-executable",str(chrome),"--screenshot-dir",str(tmp_path/"screenshots"),"--screenshot-selector","#dashboard"],capture_output=True,text=True,timeout=30)
        assert result.returncode==0,result.stdout+result.stderr
        assert json.loads(result.stdout)["verified_views"]==2
        assert len(list((tmp_path/"screenshots").glob("*.png")))==2
    finally:
        server.shutdown()
        server.server_close()


def recipe():
    spec = importlib.util.spec_from_file_location("dashboard_recipe", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_playwright_export_context_loading(tmp_path):
    playwright = pytest.importorskip("playwright.sync_api")
    chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    if not chrome.exists():
        pytest.skip("Optional installed Chrome is unavailable")
    source, output = tmp_path / "source.json", tmp_path / "export.json"
    source.write_text(json.dumps({"cookies": [{"name":"session", "value":"synthetic", "domain":"example.com", "path":"/", "expires":None}]}))
    export_playwright_state(source, output)
    with playwright.sync_playwright() as pw:
        with pw.chromium.launch(executable_path=str(chrome), headless=True) as browser:
            with browser.new_context(storage_state=str(output)) as context:
                cookies = context.cookies()
                assert len(cookies) == 1
                assert cookies[0]["expires"] == -1


def test_recipe_requires_expected_content():
    with pytest.raises(ValueError, match="expected"):
        recipe().verify_page(None, [], timeout=100)


@pytest.mark.parametrize("markup,selector,valid", [
    ('<div id="chart"><table><tr><td>42</td></tr></table></div>', '#chart table', True),
    ('<div id="chart" style="display:none"><table><tr><td>42</td></tr></table></div>', '#chart table', False),
    ('<div id="chart" style="opacity:0"><table><tr><td>42</td></tr></table></div>', '#chart table', False),
    ('<div id="chart" style="width:20px;height:20px"></div>', '#chart', False),
    ('<canvas id="chart" width="20" height="20"></canvas>', '#chart', False),
    ('<canvas id="chart" width="20" height="20"></canvas><script>document.querySelector("canvas").getContext("2d").fillRect(0,0,10,10)</script>', '#chart', True),
    ('<svg id="chart" width="20" height="20"><rect width="10" height="10"/></svg>', '#chart', True),
    ('<svg id="chart" width="20" height="20"></svg>', '#chart', False),
    ('<div id="chart">0</div>', '#chart', True),
    ('<div style="margin-top:10000px;content-visibility:auto;contain-intrinsic-size:100px"><table id="chart"><tr><td>42</td></tr></table></div>', '#chart', True),
])
def test_browser_recipe_working_and_css_hidden(markup,selector,valid):
    playwright = pytest.importorskip("playwright.sync_api")
    chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    if not chrome.exists():
        pytest.skip("Optional installed Chrome is unavailable")
    module = recipe()
    with playwright.sync_playwright() as pw:
        with pw.chromium.launch(executable_path=str(chrome), headless=True) as browser:
            page = browser.new_page()
            page.set_content(markup)
            if not valid:
                with pytest.raises(RuntimeError, match="blank"):
                    module.verify_page(page, [selector], timeout=100)
            else:
                module.verify_page(page, [selector], timeout=100)
            page.close()


def test_browser_recipe_login():
    playwright = pytest.importorskip("playwright.sync_api")
    chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    if not chrome.exists():
        pytest.skip("Optional installed Chrome is unavailable")
    with playwright.sync_playwright() as pw:
        with pw.chromium.launch(executable_path=str(chrome), headless=True) as browser:
            page = browser.new_page()
            page.set_content('<input type="password">')
            with pytest.raises(RuntimeError, match="login"):
                recipe().verify_page(page, ["#chart"], timeout=100)
