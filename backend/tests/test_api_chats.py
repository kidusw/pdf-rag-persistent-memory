async def test_create_list_get_delete(client):
    r = await client.post("/api/chats")
    assert r.status_code == 201
    created = r.json()
    assert created["messages"] == []
    assert created["title"] == ""
    assert [c["id"] for c in (await client.get("/api/chats")).json()] == [created["id"]]
    assert (await client.get(f"/api/chats/{created['id']}")).status_code == 200
    assert (await client.delete(f"/api/chats/{created['id']}")).status_code == 204
    assert (await client.get(f"/api/chats/{created['id']}")).status_code == 404


async def test_delete_missing_is_404(client):
    r = await client.delete("/api/chats/missing")
    assert r.status_code == 404
    assert r.json() == {"detail": "Chat not found"}


async def test_list_omits_messages(client):
    await client.post("/api/chats")
    assert set((await client.get("/api/chats")).json()[0]) == {"id", "title", "updated_at"}
