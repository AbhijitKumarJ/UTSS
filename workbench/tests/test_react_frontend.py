import re
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_react_index_serves_bundle_tags():
    res = client.get("/")
    assert res.status_code == 200
    assert '<div id="root">' in res.text
    # Check that script module and css links are present
    assert 'script type="module"' in res.text
    assert 'link rel="stylesheet"' in res.text
    
    # Extract script src
    js_match = re.search(r'src="([^"]+index-[^"]+\.js)"', res.text)
    assert js_match is not None, "Vite JS bundle script tag not found in index.html"
    js_path = js_match.group(1)
    
    # Fetch the bundle
    js_res = client.get(js_path)
    assert js_res.status_code == 200
    assert len(js_res.content) > 1000

    # Extract css href
    css_match = re.search(r'href="([^"]+index-[^"]+\.css)"', res.text)
    assert css_match is not None, "Vite CSS bundle link tag not found in index.html"
    css_path = css_match.group(1)
    
    # Fetch the CSS bundle
    css_res = client.get(css_path)
    assert css_res.status_code == 200
    assert "data-theme" in css_res.text
    assert "vscode-dark" in css_res.text
    assert "monokai" in css_res.text
    assert "utss-dark" in css_res.text

def test_assets_endpoint_accessible():
    # Test mounting of both /static/assets and /assets
    res = client.get("/")
    css_match = re.search(r'href="/static/(assets/[^"]+\.css)"', res.text)
    if css_match:
        asset_rel = css_match.group(1)
        res_direct = client.get(f"/{asset_rel}")
        assert res_direct.status_code == 200
