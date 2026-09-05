from fastapi.testclient import TestClient

import app as api

client = TestClient(api.app)


def test_root_endpoint():
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["status"] == "running"


def test_process_rules_taxonomy_simple(monkeypatch):
    class FakeTaxonomyService:
        def formalize_rule(self, rule_input):
            return {
                "rule_text": rule_input.rule_text,
                "status": "Success",
                "decision_code": "formalized",
                "domain": rule_input.rule_type,
                "bucket": "SimpleValidation",
                "taxonomy_rules": [
                    {
                        "Name": "Pocket Angle",
                        "RuleCategory": rule_input.rule_type,
                        "Results": "Validation",
                        "RuleType": "Feature",
                        "Feature1": "Pocket",
                        "Feature2": "",
                        "Object1": "",
                        "Object2": "",
                        "Constraints": {
                            "FilterParamList": [{"ExpName": "", "Operator": [""], "Value": [""]}],
                            "ConditionParamList": [{"ExpName": "", "Operator": [[""]], "Value": [[[""]]]}],
                            "ValidationParamList": [{"ExpName": "Pocket.SideFaceAngle", "Operator": [[">="]], "Value": [[["13.0"]]], "AllowedParams": [""]}],
                            "AdditionalParamList": [{"ExpName": ""}],
                            "UserParamList": [{"ParamName": "", "DisplayName": "", "Value": [""], "MinValue": "", "MaxValue": ""}],
                        },
                    }
                ],
                "validation_errors": [],
            }

    monkeypatch.setattr(api, "taxonomy_service", FakeTaxonomyService())

    payload = {
        "rules": [
            {
                "rule_text": "The side face angle of the pocket should be at least 13.0 degrees",
                "rule_type": "Milling",
            }
        ]
    }

    res = client.post("/process-rules-taxonomy", json=payload)
    assert res.status_code == 200
    results = res.json()
    assert len(results) == 1

    rule_res = results[0]
    assert rule_res["rule_text"] == "The side face angle of the pocket should be at least 13.0 degrees"
    assert rule_res["status"] == "Success"
    assert rule_res["decision_code"] == "formalized"
    assert rule_res["domain"] == "Milling"
    assert rule_res["bucket"] == "SimpleValidation"
    assert rule_res["taxonomy_rules"]
    assert not rule_res["decision_code"].startswith("endpoint_error")
