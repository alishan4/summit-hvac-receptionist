import json

from app.security import sign, verify_signature
from tests.conftest import TEST_KEY, signed_post, tool_body

BODY = b'{"event":"call_ended"}'
NOW = 1_800_000_000_000


def test_valid_signature():
    assert verify_signature(BODY, sign(BODY, TEST_KEY, NOW), TEST_KEY, now_ms=NOW + 1000)


def test_wrong_key():
    assert not verify_signature(BODY, sign(BODY, "other", NOW), TEST_KEY, now_ms=NOW)


def test_tampered_body():
    assert not verify_signature(b'{"event":"x"}', sign(BODY, TEST_KEY, NOW), TEST_KEY, now_ms=NOW)


def test_replay_outside_window():
    assert not verify_signature(BODY, sign(BODY, TEST_KEY, NOW), TEST_KEY, now_ms=NOW + 6 * 60 * 1000)


def test_malformed_or_missing():
    assert not verify_signature(BODY, None, TEST_KEY)
    assert not verify_signature(BODY, "garbage", TEST_KEY)
    assert not verify_signature(BODY, "v=1,d=zz", TEST_KEY)
    assert not verify_signature(BODY, sign(BODY, TEST_KEY, NOW), "", now_ms=NOW)


def test_endpoints_reject_unsigned_and_badly_signed(client):
    body = tool_body("c1", "check_service_area", {"zip": "80202"})
    assert client.post("/tools/check_service_area", json=body).status_code == 401
    assert signed_post(client, "/tools/check_service_area", body, key="wrong").status_code == 401
    assert client.post("/webhooks/retell", json={"event": "call_started"}).status_code == 401


def test_endpoint_accepts_valid_signature(client):
    r = signed_post(client, "/tools/check_service_area", tool_body("c1", "x", {"zip": "80202"}))
    assert r.status_code == 200 and r.json()["in_service_area"] is True


def test_health_is_open(client):
    assert client.get("/health").json()["status"] == "ok"
