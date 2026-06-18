from __future__ import annotations

import time
from threading import Lock

from .models import NodeInfo


class RingState:
    def __init__(self, local_name: str) -> None:
        self.local_name = local_name
        self.nodes_by_name: dict[str, NodeInfo] = {}
        self.name_order: list[str] = []
        self.next_name = ""
        self.leader_name = ""
        self.topology_dirty = True
        self._lock = Lock()

    def upsert_node(self, node: NodeInfo) -> bool:
        with self._lock:
            old_node = self.nodes_by_name.get(node.nickname)
            if old_node is None:
                node.last_seen = time.monotonic()
                self.nodes_by_name[node.nickname] = node
                self.topology_dirty = True
                return True

            changed = (
                old_node.ip_addr != node.ip_addr
                or old_node.port_num != node.port_num
            )
            old_node.ip_addr = node.ip_addr
            old_node.port_num = node.port_num
            old_node.last_seen = time.monotonic()
            if changed:
                self.topology_dirty = True
            return changed

    def apply_order(self) -> None:
        with self._lock:
            self.name_order = sorted(self.nodes_by_name)
            if not self.name_order:
                self.next_name = ""
                self.leader_name = ""
                self.topology_dirty = False
                return

            self.leader_name = self.name_order[0]
            if self.local_name not in self.name_order:
                self.next_name = ""
            else:
                idx = self.name_order.index(self.local_name)
                next_idx = (idx + 1) % len(self.name_order)
                self.next_name = self.name_order[next_idx]
            self.topology_dirty = False

    def apply_if_dirty(self) -> bool:
        with self._lock:
            if not self.topology_dirty:
                return False
        self.apply_order()
        return True

    def has_node(self, nick_name: str) -> bool:
        with self._lock:
            return nick_name in self.nodes_by_name

    def get_next_node(self) -> NodeInfo | None:
        with self._lock:
            if not self.next_name:
                return None
            return self.nodes_by_name.get(self.next_name)

    def get_members(self) -> list[str]:
        with self._lock:
            return list(self.name_order)

    def is_leader(self) -> bool:
        with self._lock:
            return self.leader_name == self.local_name

    def mark_dirty(self) -> None:
        with self._lock:
            self.topology_dirty = True

    def snapshot_text(self) -> str:
        with self._lock:
            members = " -> ".join(self.name_order)
            return members or "(vazio)"
