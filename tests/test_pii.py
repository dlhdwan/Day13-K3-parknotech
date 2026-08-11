import json

from app.logging_config import scrub_event
from app.pii import scrub_text


def test_scrub_email() -> None:
    out = scrub_text("Email me at student@vinuni.edu.vn")
    assert "student@" not in out
    assert "REDACTED_EMAIL" in out


def test_scrub_common_vietnamese_phone_formats() -> None:
    phone_numbers = (
        "0901234567",
        "090 123 4567",
        "090.123.4567",
        "090-123-4567",
        "+84 90 123 4567",
    )

    for phone_number in phone_numbers:
        out = scrub_text(f"Contact: {phone_number}")
        assert phone_number not in out
        assert "REDACTED_PHONE_VN" in out


def test_scrub_additional_sensitive_identifiers() -> None:
    sensitive_values = {
        "cccd": ("001201234567", "REDACTED_CCCD"),
        "credit_card": ("4111 1111 1111 1111", "REDACTED_CREDIT_CARD"),
        "passport": ("A1234567", "REDACTED_PASSPORT"),
        "address_vn": ("Số nhà 12, phường Bến Nghé", "REDACTED_ADDRESS_VN"),
    }

    for raw_value, redaction_marker in sensitive_values.values():
        out = scrub_text(f"Sensitive value: {raw_value}")
        assert redaction_marker in out


def test_scrub_event_recursively_covers_all_string_fields() -> None:
    event = {
        "session_id": "student@vinuni.edu.vn",
        "payload": {
            "items": [
                "A1234567",
                {"phone": "090 123 4567"},
            ]
        },
    }

    scrubbed = scrub_event(None, "info", event)
    rendered = json.dumps(scrubbed, ensure_ascii=False)

    assert "student@" not in rendered
    assert "A1234567" not in rendered
    assert "090 123 4567" not in rendered
    assert "REDACTED_EMAIL" in rendered
    assert "REDACTED_PASSPORT" in rendered
    assert "REDACTED_PHONE_VN" in rendered
