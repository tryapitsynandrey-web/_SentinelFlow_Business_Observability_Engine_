from datetime import datetime, timezone
from src.handlers.slack import SlackHandler
from src.models.entities import AlertEvent

def test_slack_payload_structure():
     handler = SlackHandler()
     
     event = AlertEvent(
         metric_id="test_db_cpu",
         evaluator_type="threshold",
         severity="critical",
         message="CPU hit 99%",
         timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
         context={"value": 99.0}
     )
     
     payload = handler._build_slack_payload(event)
     
     # Check deterministic structure
     assert payload["text"] == "*CRITICAL Alert:* test_db_cpu"
     assert len(payload["blocks"]) == 3
     
     header_block = payload["blocks"][0]
     assert header_block["type"] == "header"
     assert "CRITICAL Alert: test_db_cpu" in header_block["text"]["text"]
     
     section_block = payload["blocks"][1]
     assert section_block["type"] == "section"
     assert "CPU hit 99%" in section_block["text"]["text"]
     
     context_block = payload["blocks"][2]
     assert context_block["type"] == "context"
     assert "Evaluator: `threshold`" in context_block["elements"][0]["text"]

def test_slack_payload_no_secrets():
     handler = SlackHandler()
     
     event = AlertEvent(
         metric_id="test",
         evaluator_type="freshness",
         severity="high",
         message="test",
         timestamp=datetime.now(timezone.utc)
     )
     
     payload = handler._build_slack_payload(event)
     
     # Ensure the structure contains no config keys or env variables statically
     import json
     payload_str = json.dumps(payload)
     assert "SLACK_WEBHOOK_URL" not in payload_str
