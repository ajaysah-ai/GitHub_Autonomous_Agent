"""
Feedback storage
=================
Har feedback entry me `goal`, `username`, aur `goal_achieved` HAMESHA server
khud bharta hai (thread ke saved state se) — user in cheezo ko edit nahi
kar sakta. `rating`/`comment` optional hain, na diye jaye to "good" default
hoga.

Implementation note: AsyncSqliteStore ka exact `search`/`list` surface
version-dependent hai, isliye yaha sirf `aget`/`aput` use kiya hai (jo
already baaki code me bhi use ho raha hai) + ek chhota manual index
(`feedback_index`) jo saare feedback thread_ids track karta hai.
"""

from __future__ import annotations

import time
from typing import Optional, List, Dict, Any


async def save_feedback(
    store,
    thread_id: str,
    username: str,
    goal: str,
    goal_achieved: bool,
    rating: Optional[str] = None,
    comment: Optional[str] = None,
) -> Dict[str, Any]:
    entry = {
        "thread_id": thread_id,
        "username": username,
        "goal": goal,
        "goal_achieved": goal_achieved,
        "rating": rating if rating else "good",
        "comment": comment if comment else "good",
        "created_at": time.time(),
    }
    await store.aput(namespace=("feedback",), key=thread_id, value=entry)

    idx_item = await store.aget(namespace=("feedback_index",), key="all")
    idx = idx_item.value if idx_item else {"thread_ids": []}
    if thread_id not in idx["thread_ids"]:
        idx["thread_ids"].append(thread_id)
        await store.aput(namespace=("feedback_index",), key="all", value=idx)
    return entry


async def list_all_feedback(store) -> List[Dict[str, Any]]:
    idx_item = await store.aget(namespace=("feedback_index",), key="all")
    if not idx_item:
        return []
    out = []
    for tid in idx_item.value.get("thread_ids", []):
        item = await store.aget(namespace=("feedback",), key=tid)
        if item:
            out.append(item.value)
    # Most recent first
    out.sort(key=lambda e: e.get("created_at", 0), reverse=True)
    return out