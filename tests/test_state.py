from __future__ import annotations

import unittest

from src.fault_service import FaultService
from src.models import NodeInfo, QueueItem
from src.queue_store import QueueFullError, QueueStore
from src.ring_state import RingState
from src.token_state import TokenState


class StateTest(unittest.TestCase):
    def test_queue_limit(self) -> None:
        queue_store = QueueStore(max_size=2)
        queue_store.put(QueueItem("A", "m1", 1))
        queue_store.put(QueueItem("B", "m2", 2))
        with self.assertRaises(QueueFullError):
            queue_store.put(QueueItem("C", "m3", 3))

    def test_queue_retry(self) -> None:
        queue_store = QueueStore()
        queue_store.put(QueueItem("A", "msg", 1))
        item = queue_store.mark_retry()
        self.assertIsNotNone(item)
        self.assertEqual(item.retry_total, 1)

    def test_ring_order_and_next(self) -> None:
        ring_state = RingState(local_name="B")
        ring_state.upsert_node(NodeInfo("C", "127.0.0.1", 6003))
        ring_state.upsert_node(NodeInfo("B", "127.0.0.1", 6002))
        ring_state.upsert_node(NodeInfo("A", "127.0.0.1", 6001))
        ring_state.apply_order()
        self.assertEqual(ring_state.get_members(), ["A", "B", "C"])
        self.assertEqual(ring_state.get_next_node().nickname, "C")
        self.assertFalse(ring_state.is_leader())

    def test_token_dup_and_timeout(self) -> None:
        token_state = TokenState()
        token_state.note_token(10.0)
        self.assertTrue(token_state.check_dup(10.2, 0.5))
        self.assertFalse(token_state.check_dup(10.6, 0.5))
        token_state.note_ring(11.0)
        self.assertTrue(token_state.should_rebuild(12.1, 1.0))

    def test_fault_broadcast_not_corrupted(self) -> None:
        fault_service = FaultService(100.0)
        self.assertEqual(fault_service.maybe_corrupt("abc", True), "abc")


if __name__ == "__main__":
    unittest.main()
