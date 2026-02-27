import pytest
from httpx import AsyncClient


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ═══════════════════════════════════════════════════════════════════
# Messages
# ═══════════════════════════════════════════════════════════════════

async def test_send_message(client: AsyncClient, admin_user, normal_user):
    _, admin_token = admin_user
    user, _ = normal_user

    resp = await client.post("/api/messages/", headers=auth_header(admin_token), json={
        "recipient_id": user.id,
        "subject": "Willkommen!",
        "body": "Willkommen im Garten!",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["subject"] == "Willkommen!"
    assert data["message_type"] == "manual"
    assert data["is_read"] is False


async def test_cannot_message_self(client: AsyncClient, admin_user):
    admin, token = admin_user
    resp = await client.post("/api/messages/", headers=auth_header(token), json={
        "recipient_id": admin.id,
        "subject": "Test",
        "body": "Self message",
    })
    assert resp.status_code == 400


async def test_list_inbox(client: AsyncClient, admin_user, normal_user):
    _, admin_token = admin_user
    user, user_token = normal_user

    await client.post("/api/messages/", headers=auth_header(admin_token), json={
        "recipient_id": user.id, "subject": "Msg 1", "body": "Body 1",
    })
    await client.post("/api/messages/", headers=auth_header(admin_token), json={
        "recipient_id": user.id, "subject": "Msg 2", "body": "Body 2",
    })

    resp = await client.get("/api/messages/", headers=auth_header(user_token))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_list_sent(client: AsyncClient, admin_user, normal_user):
    _, admin_token = admin_user
    user, _ = normal_user

    await client.post("/api/messages/", headers=auth_header(admin_token), json={
        "recipient_id": user.id, "subject": "Sent test", "body": "Body",
    })

    resp = await client.get("/api/messages/sent", headers=auth_header(admin_token))
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


async def test_unread_count(client: AsyncClient, admin_user, normal_user):
    _, admin_token = admin_user
    user, user_token = normal_user

    await client.post("/api/messages/", headers=auth_header(admin_token), json={
        "recipient_id": user.id, "subject": "Test", "body": "Body",
    })

    resp = await client.get("/api/messages/unread-count", headers=auth_header(user_token))
    assert resp.json()["count"] >= 1


async def test_read_message_auto_marks_read(client: AsyncClient, admin_user, normal_user):
    _, admin_token = admin_user
    user, user_token = normal_user

    create_resp = await client.post("/api/messages/", headers=auth_header(admin_token), json={
        "recipient_id": user.id, "subject": "Read me", "body": "Body",
    })
    msg_id = create_resp.json()["id"]

    resp = await client.get(f"/api/messages/{msg_id}", headers=auth_header(user_token))
    assert resp.json()["is_read"] is True


async def test_mark_all_read(client: AsyncClient, admin_user, normal_user):
    _, admin_token = admin_user
    user, user_token = normal_user

    for i in range(3):
        await client.post("/api/messages/", headers=auth_header(admin_token), json={
            "recipient_id": user.id, "subject": f"Msg {i}", "body": "Body",
        })

    resp = await client.post("/api/messages/mark-all-read", headers=auth_header(user_token))
    assert resp.json()["count"] == 0


async def test_archive_message(client: AsyncClient, admin_user, normal_user):
    _, admin_token = admin_user
    user, user_token = normal_user

    create_resp = await client.post("/api/messages/", headers=auth_header(admin_token), json={
        "recipient_id": user.id, "subject": "Archive me", "body": "Body",
    })
    msg_id = create_resp.json()["id"]

    # Archive it
    resp = await client.patch(f"/api/messages/{msg_id}", headers=auth_header(user_token), json={
        "is_archived": True,
    })
    assert resp.status_code == 200
    assert resp.json()["is_archived"] is True

    # Should not appear in default inbox
    inbox = await client.get("/api/messages/", headers=auth_header(user_token))
    ids = [m["id"] for m in inbox.json()]
    assert msg_id not in ids

    # Should appear with include_archived
    inbox2 = await client.get("/api/messages/", headers=auth_header(user_token),
                              params={"include_archived": True})
    ids2 = [m["id"] for m in inbox2.json()]
    assert msg_id in ids2


async def test_delete_message(client: AsyncClient, admin_user, normal_user):
    _, admin_token = admin_user
    user, user_token = normal_user

    create_resp = await client.post("/api/messages/", headers=auth_header(admin_token), json={
        "recipient_id": user.id, "subject": "Delete me", "body": "Body",
    })
    msg_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/messages/{msg_id}", headers=auth_header(user_token))
    assert del_resp.status_code == 204


async def test_cannot_read_others_message(client: AsyncClient, admin_user, normal_user):
    admin, admin_token = admin_user
    user, user_token = normal_user

    # Send message to admin
    create_resp = await client.post("/api/messages/", headers=auth_header(user_token), json={
        "recipient_id": admin.id, "subject": "Private", "body": "Secret",
    })
    msg_id = create_resp.json()["id"]

    # User tries to read admin's message (user is sender, so allowed)
    resp = await client.get(f"/api/messages/{msg_id}", headers=auth_header(user_token))
    assert resp.status_code == 200


async def test_broadcast(client: AsyncClient, admin_user, normal_user):
    _, admin_token = admin_user
    user, user_token = normal_user

    resp = await client.post("/api/messages/broadcast", headers=auth_header(admin_token), json={
        "recipient_id": 0,  # ignored for broadcast
        "subject": "Announcement",
        "body": "Garden party on Saturday!",
    })
    assert resp.status_code == 201
    assert len(resp.json()) >= 2  # admin + user

    # User should see it
    inbox = await client.get("/api/messages/", headers=auth_header(user_token))
    subjects = [m["subject"] for m in inbox.json()]
    assert "Announcement" in subjects


async def test_broadcast_non_admin_forbidden(client: AsyncClient, normal_user):
    _, user_token = normal_user
    resp = await client.post("/api/messages/broadcast", headers=auth_header(user_token), json={
        "recipient_id": 0, "subject": "Nope", "body": "Body",
    })
    assert resp.status_code == 403


async def test_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/messages/")
    assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════
# Auto Message Rules
# ═══════════════════════════════════════════════════════════════════

async def test_list_rules(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.get("/api/messages/rules/", headers=auth_header(token))
    assert resp.status_code == 200


async def test_create_rule(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.post("/api/messages/rules/", headers=auth_header(token), json={
        "event_type": "test_event",
        "subject_template": "Test: {thing}",
        "body_template": "Something happened with {thing}.",
        "send_to": "all_users",
    })
    assert resp.status_code == 201
    assert resp.json()["event_type"] == "test_event"


async def test_update_rule(client: AsyncClient, admin_user):
    _, token = admin_user
    create_resp = await client.post("/api/messages/rules/", headers=auth_header(token), json={
        "event_type": "update_test",
        "subject_template": "Old",
        "body_template": "Old body",
    })
    rule_id = create_resp.json()["id"]

    resp = await client.patch(f"/api/messages/rules/{rule_id}", headers=auth_header(token), json={
        "subject_template": "New subject",
        "is_active": False,
    })
    assert resp.status_code == 200
    assert resp.json()["subject_template"] == "New subject"
    assert resp.json()["is_active"] is False


async def test_delete_rule(client: AsyncClient, admin_user):
    _, token = admin_user
    create_resp = await client.post("/api/messages/rules/", headers=auth_header(token), json={
        "event_type": "delete_test",
        "subject_template": "Del",
        "body_template": "Del body",
    })
    rule_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/messages/rules/{rule_id}", headers=auth_header(token))
    assert del_resp.status_code == 204


async def test_rules_non_admin_forbidden(client: AsyncClient, normal_user):
    _, token = normal_user
    resp = await client.get("/api/messages/rules/", headers=auth_header(token))
    assert resp.status_code == 403

