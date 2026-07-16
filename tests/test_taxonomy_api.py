import json
from copy import deepcopy

from fastapi.testclient import TestClient

import app as api_app


def _valid_bridge_payload():
    return {
        "domain": "SheetMetal",
        "bucket": "DistanceRule",
        "taxonomy_rules": [
            {
                "Name": "Bridge Spacing",
                "RuleCategory": "SheetMetal",
                "Results": "Validation",
                "RuleType": "Feature",
                "Feature1": "Distance",
                "Feature2": "",
                "Object1": "Bridge",
                "Object2": "Bridge",
                "Constraints": {
                    "FilterParamList": [{"ExpName": "", "Operator": [""], "Value": [""]}],
                    "ConditionParamList": [{"ExpName": "", "Operator": [[""]], "Value": [[[""]]]}],
                    "ValidationParamList": [
                        {
                            "ExpName": "Distance.MinValue/SheetMetal.Thickness",
                            "Operator": [[">="]],
                            "Value": [[["4.5"]]],
                            "AllowedParams": [""],
                        }
                    ],
                    "AdditionalParamList": [{"ExpName": ""}],
                    "UserParamList": [{"ParamName": "", "DisplayName": "", "Value": [""], "MinValue": "", "MaxValue": ""}],
                },
            }
        ],
    }


def _bad_slot_bridge_payload():
    return {
        "domain": "SheetMetal",
        "bucket": "DistanceRule",
        "taxonomy_rules": [
            {
                "Name": "Minimum distance from bend to slot edge",
                "RuleCategory": "SheetMetal",
                "Results": "Validation",
                "RuleType": "Feature",
                "Feature1": "Distance",
                "Feature2": "",
                "Object1": "Bend",
                "Object2": "Bridge",
                "Constraints": {
                    "FilterParamList": [{"ExpName": "", "Operator": [""], "Value": [""]}],
                    "ConditionParamList": [{"ExpName": "", "Operator": [[""]], "Value": [[[""]]]}],
                    "ValidationParamList": [
                        {
                            "ExpName": "Distance.MinValue",
                            "Operator": [[">="]],
                            "Value": [[["Bridge.Length * SheetMetal.Thickness * Bend.MinRadius"]]],
                            "AllowedParams": ["Bridge.Length", "SheetMetal.Thickness", "Bend.MinRadius"],
                        }
                    ],
                    "AdditionalParamList": [{"ExpName": ""}],
                    "UserParamList": [{"ParamName": "", "DisplayName": "", "Value": [""], "MinValue": "", "MaxValue": ""}],
                },
            }
        ],
    }


def _valid_slot_payload():
    return {
        "domain": "SheetMetal",
        "bucket": "DistanceRule",
        "taxonomy_rules": [
            {
                "Name": "Minimum distance from bend to slot edge",
                "RuleCategory": "SheetMetal",
                "Results": "Validation",
                "RuleType": "Feature",
                "Feature1": "Distance",
                "Feature2": "",
                "Object1": "Bend",
                "Object2": "Slot",
                "Constraints": {
                    "FilterParamList": [{"ExpName": "", "Operator": [""], "Value": [""]}],
                    "ConditionParamList": [{"ExpName": "", "Operator": [[""]], "Value": [[[""]]]}],
                    "ValidationParamList": [
                        {
                            "ExpName": "Distance.MinValue",
                            "Operator": [[">="]],
                            "Value": [[["ProportionalityConstant*Slot.Length*SheetMetal.Thickness*Bend.MinRadius"]]],
                            "AllowedParams": ["Slot.Length", "SheetMetal.Thickness", "Bend.MinRadius"],
                        }
                    ],
                    "AdditionalParamList": [{"ExpName": ""}],
                    "UserParamList": [
                        {
                            "ParamName": "ProportionalityConstant",
                            "DisplayName": "Proportionality Constant",
                            "Value": [""],
                            "MinValue": "",
                            "MaxValue": "",
                        }
                    ],
                },
            }
        ],
    }


class FakeLLM:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def call(self, prompt, json_mode=False):
        self.calls.append({"prompt": prompt, "json_mode": json_mode})
        if not self.responses:
            raise AssertionError("Unexpected LLM call")
        response = self.responses.pop(0)
        if isinstance(response, RawLLMResponse):
            return str(response)
        return json.dumps(response)


class RawLLMResponse(str):
    pass


def test_taxonomy_endpoint_returns_grouped_success(monkeypatch):
    fake_llm = FakeLLM([_valid_bridge_payload()])
    monkeypatch.setattr(api_app, "llm_client", fake_llm)

    client = TestClient(api_app.app)
    response = client.post(
        "/process-rules-taxonomy",
        json={"rules": [{"rule_text": "Distance between bridges should be at least 4.5 times sheet thickness"}]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body[0]["status"] == "Success"
    assert body[0]["decision_code"] == "formalized"
    assert body[0]["bucket"] == "DistanceRule"
    assert len(body[0]["taxonomy_rules"]) == 1
    assert fake_llm.calls[0]["json_mode"] is True


def test_taxonomy_endpoint_repairs_invalid_llm_payload(monkeypatch):
    invalid = _valid_bridge_payload()
    invalid["taxonomy_rules"][0]["Recom"] = "legacy field should be rejected"

    fake_llm = FakeLLM([invalid, _valid_bridge_payload()])
    monkeypatch.setattr(api_app, "llm_client", fake_llm)

    client = TestClient(api_app.app)
    response = client.post(
        "/process-rules-taxonomy",
        json={"rules": [{"rule_text": "Distance between bridges should be at least 4.5 times sheet thickness"}]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body[0]["status"] == "Success"
    assert len(fake_llm.calls) == 2


def test_taxonomy_endpoint_repairs_unbalanced_json_response(monkeypatch):
    fake_llm = FakeLLM([
        RawLLMResponse('{"domain": "SheetMetal", "bucket": "DistanceRule", "taxonomy_rules": ['),
        _valid_bridge_payload(),
    ])
    monkeypatch.setattr(api_app, "llm_client", fake_llm)

    client = TestClient(api_app.app)
    response = client.post(
        "/process-rules-taxonomy",
        json={"rules": [{"rule_text": "Distance between bridges should be at least 4.5 times sheet thickness"}]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body[0]["status"] == "Success"
    assert body[0]["decision_code"] == "formalized"
    assert len(fake_llm.calls) == 2


def test_taxonomy_endpoint_respects_explicit_domain_override(monkeypatch):
    llm_payload = deepcopy(_valid_bridge_payload())
    llm_payload["domain"] = "Drilling"
    llm_payload["taxonomy_rules"][0]["RuleCategory"] = "Drilling"

    fake_llm = FakeLLM([llm_payload])
    monkeypatch.setattr(api_app, "llm_client", fake_llm)

    client = TestClient(api_app.app)
    response = client.post(
        "/process-rules-taxonomy",
        json={
            "rules": [
                {
                    "rule_text": "Distance between bridges should be at least 4.5 times sheet thickness",
                    "rule_type": "Sheetmetal",
                }
            ]
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body[0]["status"] == "Success"
    assert body[0]["domain"] == "SheetMetal"
    assert body[0]["taxonomy_rules"][0]["RuleCategory"] == "SheetMetal"


def test_taxonomy_endpoint_repairs_ungrounded_example_object(monkeypatch):
    rule_text = (
        "The minimum distance from the inside surface of a bend to the edge of a slot is directly proportional "
        "to the length of the slot, material thickness, and radius of the bend."
    )
    fake_llm = FakeLLM([_bad_slot_bridge_payload(), _valid_slot_payload()])
    monkeypatch.setattr(api_app, "llm_client", fake_llm)

    client = TestClient(api_app.app)
    response = client.post("/process-rules-taxonomy", json={"rules": [{"rule_text": rule_text}]})

    assert response.status_code == 200
    body = response.json()
    assert body[0]["status"] == "Success"
    assert body[0]["taxonomy_rules"][0]["Object2"] == "Slot"
    assert "Slot.Length" in body[0]["taxonomy_rules"][0]["Constraints"]["ValidationParamList"][0]["AllowedParams"]
    assert len(fake_llm.calls) == 2
