import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_get_stdlib_coverage_endpoint():
    response = client.get("/api/bridge/stdlib-coverage")
    assert response.status_code == 200
    data = response.json()

    assert "languages" in data
    assert "domain_distribution" in data
    assert "unmapped_candidates" in data
    assert "total_unmapped_candidates" in data

    languages = data["languages"]
    for lang in ("python", "csharp", "cpp", "go", "rust", "typescript"):
        assert lang in languages
        info = languages[lang]
        assert "total_containers" in info
        assert "mapped_count" in info
        assert "unmapped_count" in info
        assert "coverage_pct" in info
        assert info["total_containers"] > 0
        assert info["unmapped_count"] >= 0

    assert data["total_unmapped_candidates"] > 0
    top_candidate = data["unmapped_candidates"][0]
    assert "language" in top_candidate
    assert "qualified_name" in top_candidate
    assert "domain" in top_candidate
    assert "impedance_risk" in top_candidate
    assert top_candidate["impedance_risk"] in ("LOW", "MEDIUM", "HIGH")


def test_crawl_stdlib_endpoint():
    response = client.post("/api/bridge/crawl-stdlib")
    assert response.status_code == 200
    data = response.json()
    assert "languages" in data
    assert len(data["unmapped_candidates"]) > 0


def test_domain_distribution_categories():
    response = client.get("/api/bridge/stdlib-coverage")
    assert response.status_code == 200
    data = response.json()
    dist = data["domain_distribution"]
    assert "collection" in dist
    assert "concurrency" in dist
    assert "stream_io" in dist
