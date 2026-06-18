from __future__ import annotations

from .node_runtime import NodeRuntime
from .queue_store import QueueFullError


class ConsoleUI:
    def __init__(self, runtime: NodeRuntime) -> None:
        self.runtime = runtime

    def run(self) -> None:
        self._show_help()
        while not self.runtime.stop_event.is_set():
            try:
                cmd_text = input("> ").strip()
            except EOFError:
                break
            except KeyboardInterrupt:
                print()
                break

            if not cmd_text:
                continue

            if cmd_text == "help":
                self._show_help()
                continue

            if cmd_text == "queue":
                for line in self.runtime.get_queue_lines():
                    print(line)
                continue

            if cmd_text == "ring":
                print(self.runtime.get_ring_text())
                continue

            if cmd_text == "state":
                view = self.runtime.get_state_view()
                print(f"local={view.local_name} ip={view.local_ip} porta={view.local_port}")
                print(f"anel={' -> '.join(view.members) if view.members else '(vazio)'}")
                print(f"sucessor={view.next_name or '(nenhum)'}")
                print(f"fila={view.queue_size} voo={view.data_in_flight}")
                print(f"ultimo_token={view.last_token_at:.3f}")
                continue

            if cmd_text == "drop-token":
                self.runtime.drop_next_token()
                continue

            if cmd_text == "insert-token":
                self.runtime.insert_token()
                continue

            if cmd_text == "exit":
                break

            if cmd_text.startswith("send "):
                parts = cmd_text.split(" ", 2)
                if len(parts) < 3:
                    print("uso: send <destino> <mensagem>")
                    continue
                try:
                    self.runtime.queue_unicast(parts[1], parts[2])
                except QueueFullError as exc:
                    print(str(exc))
                continue

            if cmd_text.startswith("broadcast "):
                parts = cmd_text.split(" ", 1)
                if len(parts) < 2 or not parts[1]:
                    print("uso: broadcast <mensagem>")
                    continue
                try:
                    self.runtime.queue_bcast(parts[1])
                except QueueFullError as exc:
                    print(str(exc))
                continue

            print("comando invalido, use help")

    def _show_help(self) -> None:
        print("send <destino> <mensagem>")
        print("broadcast <mensagem>")
        print("queue")
        print("ring")
        print("state")
        print("drop-token")
        print("insert-token")
        print("help")
        print("exit")
