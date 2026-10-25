from a2a_claude_agent.session_store import InMemorySessionStore


async def test_set_get_delete():
    store = InMemorySessionStore()

    assert await store.get("ctx") is None
    await store.set("ctx", "s1")
    assert await store.get("ctx") == "s1"
    await store.set("ctx", "s2")
    assert await store.get("ctx") == "s2"
    await store.delete("ctx")
    assert await store.get("ctx") is None


async def test_delete_unknown_is_ignored():
    await InMemorySessionStore().delete("missing")


async def test_contexts_are_independent():
    store = InMemorySessionStore()
    await store.set("a", "s-a")
    await store.set("b", "s-b")

    assert await store.get("a") == "s-a"
    assert await store.get("b") == "s-b"
