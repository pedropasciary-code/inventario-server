import json
import shutil
from pathlib import Path

import pytest

from agent import agent as agent_module


@pytest.fixture
def queue_dirs(monkeypatch):
    root = Path("tests/.tmp_agent_queue")
    if root.exists():
        shutil.rmtree(root)
    failed = root / "failed"
    dead = root / "dead"
    failed.mkdir(parents=True)
    dead.mkdir(parents=True)

    monkeypatch.setattr(agent_module, "FAILED_PAYLOADS_DIR", failed)
    monkeypatch.setattr(agent_module, "DEAD_LETTER_DIR", dead)

    yield failed, dead

    if root.exists():
        shutil.rmtree(root)


def test_save_failed_payload_uses_retry_envelope(queue_dirs):
    failed, _dead = queue_dirs

    agent_module.save_failed_payload({"hostname": "PC-OFFLINE"})

    files = list(failed.glob("payload_*.json"))
    assert len(files) == 1
    content = json.loads(files[0].read_text(encoding="utf-8"))
    assert content == {"attempts": 0, "payload": {"hostname": "PC-OFFLINE"}}


def test_resend_failed_payload_moves_repeated_failure_to_dead_letter(monkeypatch, queue_dirs):
    failed, dead = queue_dirs
    payload_file = failed / "payload_test.json"
    payload_file.write_text(
        json.dumps({"attempts": agent_module.MAX_PAYLOAD_RESEND_ATTEMPTS - 1, "payload": {"hostname": "PC-FAIL"}}),
        encoding="utf-8",
    )

    def fail_send(payload):
        raise RuntimeError("api offline")

    monkeypatch.setattr(agent_module, "send_data", fail_send)

    agent_module.resend_failed_payloads()

    assert not payload_file.exists()
    assert (dead / "payload_test.json").exists()


def test_resend_failed_payload_accepts_legacy_raw_payload(monkeypatch, queue_dirs):
    failed, _dead = queue_dirs
    payload_file = failed / "payload_legacy.json"
    payload_file.write_text(json.dumps({"hostname": "PC-LEGACY"}), encoding="utf-8")
    sent_payloads = []

    monkeypatch.setattr(agent_module, "send_data", sent_payloads.append)

    agent_module.resend_failed_payloads()

    assert sent_payloads == [{"hostname": "PC-LEGACY"}]
    assert not payload_file.exists()
