import pytest
from fastapi.testclient import TestClient

# Mock out startup event or ensure imports are clean
from app import app

client = TestClient(app)

def test_root_endpoint():
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["status"] == "running"

def test_process_rules_taxonomy_simple():
    payload = {
        "rules": [
            {
                "rule_text": "The side face angle of the pocket should be at least 13.0 degrees",
                "rule_type": "Milling"
            }
        ]
    }
    # Test taxonomy endpoint
    res = client.post("/process-rules-taxonomy", json=payload)
    assert res.status_code == 200
    results = res.json()
    assert len(results) == 1
    
    rule_res = results[0]
    assert rule_res["rule_text"] == "The side face angle of the pocket should be at least 13.0 degrees"
    assert rule_res["status"] in ("Success", "Review Needed")
    assert rule_res["domain"] == "Milling"
    assert rule_res["bucket"] == "SimpleValidation"
