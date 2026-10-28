import json, pathlib
from src.core import MODELS
from src.main import HQ_MODELS
A = pathlib.Path(__file__).resolve().parents[1] / ".actor"

def test_every_input_field_has_description():
    for k, v in json.loads((A / "input_schema.json").read_text())["properties"].items():
        assert v.get("description"), k

def test_model_enum_matches_supported_models():
    enum = json.loads((A / "input_schema.json").read_text())["properties"]["model"]["enum"]
    assert set(enum) == set(MODELS) and HQ_MODELS <= set(MODELS)

def test_pricing_events_match_code():
    ev = json.loads((A / "pay_per_event.json").read_text())["events"]
    assert {"transcript-created", "audio-minute", "audio-minute-hq"} <= set(ev)


def test_billing_grace():
    from src.core import billable_minutes as b
    assert b(None) == 1 and b(60.4) == 1 and b(60.5) == 1 and b(60.6) == 2 and b(3600.3) == 60 and b(121) == 3
