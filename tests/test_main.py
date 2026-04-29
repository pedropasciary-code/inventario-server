import csv
import io
import json
import re
from datetime import UTC, datetime, timedelta

from app import models


AGENT_HEADERS = {"X-Agent-Token": "test-agent-token"}


def extract_csrf_token(response):
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
    assert match, response.text
    return match.group(1)


def login(client):
    response = client.get("/login")
    csrf_token = extract_csrf_token(response)

    return client.post(
        "/login",
        data={
            "username": "admin",
            "password": "strong-password",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )


def test_checkin_creates_and_updates_asset(client, db_session):
    payload = {
        "hostname": "PC-01",
        "serial": "SERIAL-01",
        "mac_address": "AA-BB-CC-00-00-01",
        "ip": "10.0.0.1",
    }

    create_response = client.post("/checkin", json=payload, headers=AGENT_HEADERS)
    assert create_response.status_code == 200
    assert create_response.json()["hostname"] == "PC-01"

    update_response = client.post(
        "/checkin",
        json={**payload, "hostname": "PC-01-RENAMED", "ip": "10.0.0.2"},
        headers=AGENT_HEADERS,
    )
    assert update_response.status_code == 200
    assert update_response.json()["id"] == create_response.json()["id"]
    assert update_response.json()["hostname"] == "PC-01-RENAMED"
    assert db_session.query(models.Asset).count() == 1


def test_checkin_normalizes_serial_and_mac_identity(client, db_session):
    create_response = client.post(
        "/checkin",
        json={
            "hostname": "PC-01",
            "serial": " serial-01 ",
            "mac_address": "aa:bb:cc:00:00:01",
        },
        headers=AGENT_HEADERS,
    )
    assert create_response.status_code == 200

    update_response = client.post(
        "/checkin",
        json={
            "hostname": "PC-01-UPDATED",
            "serial": "SERIAL-01",
            "mac_address": "AA-BB-CC-00-00-01",
        },
        headers=AGENT_HEADERS,
    )

    assert update_response.status_code == 200
    assert update_response.json()["id"] == create_response.json()["id"]
    asset = db_session.query(models.Asset).one()
    assert asset.serial == "SERIAL-01"
    assert asset.mac_address == "AA-BB-CC-00-00-01"


def test_checkin_rejects_invalid_agent_token(client):
    response = client.post(
        "/checkin",
        json={"hostname": "PC-01"},
        headers={"X-Agent-Token": "wrong-token"},
    )

    assert response.status_code == 401


def test_checkin_rejects_conflicting_identity(client):
    first = {
        "hostname": "PC-01",
        "serial": "SERIAL-01",
        "mac_address": "AA-BB-CC-00-00-01",
    }
    second = {
        "hostname": "PC-02",
        "serial": "SERIAL-02",
        "mac_address": "AA-BB-CC-00-00-02",
    }

    assert client.post("/checkin", json=first, headers=AGENT_HEADERS).status_code == 200
    assert client.post("/checkin", json=second, headers=AGENT_HEADERS).status_code == 200

    conflict_response = client.post(
        "/checkin",
        json={
            "hostname": "PC-CONFLICT",
            "serial": "SERIAL-01",
            "mac_address": "AA-BB-CC-00-00-02",
        },
        headers=AGENT_HEADERS,
    )

    assert conflict_response.status_code == 409


def test_login_requires_valid_csrf_token(client, admin_user):
    response = client.get("/login")
    assert response.status_code == 200

    invalid_response = client.post(
        "/login",
        data={
            "username": "admin",
            "password": "strong-password",
            "csrf_token": "invalid",
        },
    )

    assert invalid_response.status_code == 403


def test_login_rate_limit_blocks_repeated_failures(client, admin_user):
    csrf_token = extract_csrf_token(client.get("/login"))

    for _ in range(5):
        response = client.post(
            "/login",
            data={
                "username": "admin",
                "password": "wrong-password",
                "csrf_token": csrf_token,
            },
        )
        assert response.status_code == 401

    blocked_response = client.post(
        "/login",
        data={
            "username": "admin",
            "password": "wrong-password",
            "csrf_token": csrf_token,
        },
    )

    assert blocked_response.status_code == 429


def test_dashboard_paginates_and_shows_real_status(client, db_session, admin_user):
    now = datetime.now(UTC)

    for index in range(30):
        if index % 3 == 0:
            last_seen = now
        elif index % 3 == 1:
            last_seen = now - timedelta(days=2)
        else:
            last_seen = now - timedelta(days=10)

        db_session.add(
            models.Asset(
                hostname=f"PC-{index:02d}",
                serial=f"SERIAL-{index:02d}",
                mac_address=f"AA-BB-CC-00-00-{index:02d}",
                ultima_comunicacao=last_seen,
            )
        )

    db_session.commit()

    login_response = login(client)
    assert login_response.status_code == 303

    response = client.get("/dashboard?page=2&per_page=10")

    assert response.status_code == 200
    assert "Exibindo 11-20 de 30 ativos" in response.text
    assert "Página 2 de 3" in response.text
    assert "Comunicando" in response.text
    assert "Atrasado" in response.text
    assert "Inativo" in response.text


def test_asset_detail_shows_network_interfaces(client, db_session, admin_user):
    interfaces = [
        {
            "name": "Ethernet",
            "mac_address": "AA-BB-CC-00-00-01",
            "ip_addresses": ["192.168.0.10"],
            "is_virtual": False,
        },
        {
            "name": "VPN Adapter",
            "mac_address": "AA-BB-CC-00-00-02",
            "ip_addresses": ["10.8.0.2"],
            "is_virtual": True,
        },
    ]
    asset = models.Asset(
        hostname="PC-DETAIL",
        serial="SERIAL-DETAIL",
        mac_address="AA-BB-CC-00-00-01",
        network_interfaces=json.dumps(interfaces),
        ultima_comunicacao=datetime.now(UTC),
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)

    assert login(client).status_code == 303

    response = client.get(f"/assets/{asset.id}")

    assert response.status_code == 200
    assert "Interfaces de Rede" in response.text
    assert "Ethernet" in response.text
    assert "VPN Adapter" in response.text
    assert "Física" in response.text
    assert "Virtual" in response.text


def test_dashboard_filters_status_and_sorts(client, db_session, admin_user):
    now = datetime.now(UTC)
    db_session.add_all(
        [
            models.Asset(
                hostname="PC-ONLINE",
                usuario="ana",
                serial="SERIAL-ONLINE",
                mac_address="AA-BB-CC-00-10-01",
                ultima_comunicacao=now,
            ),
            models.Asset(
                hostname="PC-STALE",
                usuario="bruno",
                serial="SERIAL-STALE",
                mac_address="AA-BB-CC-00-10-02",
                ultima_comunicacao=now - timedelta(days=2),
            ),
            models.Asset(
                hostname="PC-INACTIVE",
                usuario="carla",
                serial="SERIAL-INACTIVE",
                mac_address="AA-BB-CC-00-10-03",
                ultima_comunicacao=now - timedelta(days=10),
            ),
        ]
    )
    db_session.commit()

    assert login(client).status_code == 303

    response = client.get("/dashboard?status=stale&sort=usuario&direction=desc&per_page=10")

    assert response.status_code == 200
    assert "PC-STALE" in response.text
    assert "PC-ONLINE" not in response.text
    assert "PC-INACTIVE" not in response.text
    assert "Atrasado" in response.text
    assert "10 por página" in response.text


def test_csv_export_includes_status_and_formatted_dates(client, db_session, admin_user):
    now = datetime.now(UTC)
    db_session.add_all(
        [
            models.Asset(
                hostname="PC-ONLINE",
                serial="SERIAL-ONLINE",
                mac_address="AA-BB-CC-00-20-01",
                ultima_comunicacao=now,
            ),
            models.Asset(
                hostname="PC-INACTIVE",
                serial="SERIAL-INACTIVE",
                mac_address="AA-BB-CC-00-20-02",
                ultima_comunicacao=now - timedelta(days=10),
            ),
        ]
    )
    db_session.commit()

    assert login(client).status_code == 303

    response = client.get("/export/csv?status=inactive")

    assert response.status_code == 200
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert len(rows) == 1
    assert rows[0]["Hostname"] == "PC-INACTIVE"
    assert rows[0]["Status"] == "Inativo"
    assert "/" in rows[0]["Ultima Comunicacao"]
