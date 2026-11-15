import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_static_index_serves_html():
    res = client.get("/")
    assert res.status_code == 200
    assert "<!DOCTYPE html>" in res.text
    assert "UTSS Universal Language Analysis" in res.text
    assert "id=\"db-select\"" in res.text
    assert "id=\"sql-editor\"" in res.text
    assert "id=\"results-table\"" in res.text

def test_static_assets_serve():
    css = client.get("/static/style.css")
    assert css.status_code == 200
    assert "font-family" in css.text

    js = client.get("/static/app.js")
    assert js.status_code == 200
    assert "fetch" in js.text

def test_app_js_preserves_editor_on_db_switch():
    js = client.get("/static/app.js").text
    assert "preserveEditor" in js
    assert "preservedSql" in js
