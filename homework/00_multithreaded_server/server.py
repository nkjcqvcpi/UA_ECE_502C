#!/usr/bin/env python3
import argparse
import queue
import socket
import threading
import time
from dataclasses import dataclass
from typing import Optional, Tuple

# ----------------------------
# Request/Response protocol
# ----------------------------

@dataclass
class Task:
    conn: socket.socket
    addr: Tuple[str, int]
    line: str
    enqueued_at: float  # perf timing


def parse_and_execute(line: str) -> str:
    """
    Parse a single request line and return a response line (without trailing newline).
    Supported:
      SLEEP ms
      FACT n
      FIB n
      ECHO text...
    """
    line = line.strip()
    if not line:
        return "ERR empty request"

    parts = line.split(" ", 1)
    op = parts[0].upper()
    arg = parts[1] if len(parts) > 1 else ""

    try:
        if op == "SLEEP":
            ms = int(arg)
            if ms < 0 or ms > 10_000:
                return "ERR SLEEP ms must be 0..10000"
            time.sleep(ms / 1000.0)
            return f"OK {ms}"

        elif op == "ECHO":
            return f"OK {arg}"

        else:
            return f"ERR unknown op {op}"
    except ValueError:
        return "ERR invalid argument"


# ----------------------------
# Thread pool + server
# ----------------------------

class ThreadPoolServer:
    def __init__(self, host: str, port: int, workers: int, queue_size: int, reject_when_full: bool):
        self.host = host
        self.port = port
        self.workers = workers
        self.queue_size = queue_size
        self.reject_when_full = reject_when_full

        self.task_q: "queue.Queue[Task]" = queue.Queue(maxsize=queue_size)

        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []
        self._accept_thread: Optional[threading.Thread] = None

        # Per-connection locks for safe concurrent writes
        self._conn_locks: dict[socket.socket, threading.Lock] = {}
        self._conn_locks_lock = threading.Lock()

        # Stats
        self._lock = threading.Lock()
        self._processed = 0
        self._total_latency = 0.0  # seconds
        self._start_time = time.time()

    def start(self) -> None:
        """
        Start worker threads + accept loop + stats reporter.
        """
        # TODO(1): start worker threads (self.workers), each runs self._worker_loop
        for i in range(self.workers):
            t = threading.Thread(target=self._worker_loop, args=(i,), daemon=True)
            self._threads.append(t)
            t.start()

        # TODO(2): start accept loop in a thread (self._accept_loop)
        self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._accept_thread.start()

        # TODO(3): start stats reporter thread (self._stats_loop)
        t = threading.Thread(target=self._stats_loop, daemon=True)
        self._threads.append(t)
        t.start()
        
        # Block until stopped
        try:
            while not self._stop.is_set():
                time.sleep(1.0)
        except KeyboardInterrupt:
            # Propagate interrupt to main
            raise

    def stop(self) -> None:
        """
        Signal stop and close server.
        """
        self._stop.set()

        # Wake workers blocked on queue.get()
        for _ in range(self.workers):
            try:
                self.task_q.put_nowait(Task(conn=None, addr=("0.0.0.0", 0), line="", enqueued_at=time.time()))  # type: ignore
            except queue.Full:
                pass

        for t in self._threads:
            t.join(timeout=2.0)
        if self._accept_thread:
            self._accept_thread.join(timeout=2.0)

    def _stats_loop(self) -> None:
        while not self._stop.is_set():
            time.sleep(2.0)
            with self._lock:
                processed = self._processed
                avg_ms = (self._total_latency / processed * 1000.0) if processed else 0.0
            qlen = self.task_q.qsize()
            elapsed = time.time() - self._start_time
            rps = processed / elapsed if elapsed > 0 else 0.0
            print(f"[stats] processed={processed} avg_latency_ms={avg_ms:.2f} qlen={qlen} rps={rps:.2f}")

    def _accept_loop(self) -> None:
        """
        Accept clients and read lines, enqueue tasks.
        Each client may send many requests; handle line-by-line.
        """
        # TODO(4): create listening socket, accept connections in a loop until stop
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((self.host, self.port))
        server_sock.listen()
        server_sock.settimeout(1.0)

        def handle_client(conn: socket.socket, addr: Tuple[str, int]) -> None:
            """Handle a single client connection."""
            try:
                # Set TCP_NODELAY for lower latency
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                
                buf = b""
                while not self._stop.is_set():
                    try:
                        data = conn.recv(4096)
                        if not data:
                            # Client closed connection
                            break
                        
                        buf += data
                        
                        # Process complete lines
                        while b"\n" in buf:
                            line_bytes, buf = buf.split(b"\n", 1)
                            line = line_bytes.decode("utf-8", errors="replace")
                            
                            # Create task
                            task = Task(conn=conn, addr=addr, line=line, enqueued_at=time.time())
                            
                            # Enqueue task with backpressure handling
                            try:
                                if self.reject_when_full:
                                    self.task_q.put_nowait(task)
                                else:
                                    self.task_q.put(task, block=True, timeout=1.0)
                            except queue.Full:
                                # Use connection lock to avoid race with worker threads
                                with self._conn_locks_lock:
                                    if conn not in self._conn_locks:
                                        self._conn_locks[conn] = threading.Lock()
                                    conn_lock = self._conn_locks[conn]
                                try:
                                    with conn_lock:
                                        conn.sendall(b"ERR server busy\n")
                                except (BrokenPipeError, ConnectionResetError, OSError):
                                    return
                    except (ConnectionResetError, BrokenPipeError, OSError):
                        break
            finally:
                try:
                    conn.close()
                except OSError:
                    pass
                # Clean up connection lock to prevent memory leak
                with self._conn_locks_lock:
                    self._conn_locks.pop(conn, None)
        
        try:
            while not self._stop.is_set():
                try:
                    conn, addr = server_sock.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                
                t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
                t.start()
        finally:
            server_sock.close()

    def _worker_loop(self, worker_id: int) -> None:
        """
        Worker threads: take tasks from queue and process them.
        """
        while not self._stop.is_set():
            task = self.task_q.get()
            # Sentinel check: we used conn=None to wake workers during shutdown
            if task.conn is None:
                self.task_q.task_done()
                break

            started = time.time()
            resp = parse_and_execute(task.line)
            resp_line = resp + "\n"

            try:
                # TODO(5): send response back to client safely
                # Get or create per-connection lock
                with self._conn_locks_lock:
                    if task.conn not in self._conn_locks:
                        self._conn_locks[task.conn] = threading.Lock()
                    conn_lock = self._conn_locks[task.conn]
                
                # Use per-connection lock to serialize writes to the same connection
                with conn_lock:
                    task.conn.sendall(resp_line.encode("utf-8"))
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass

            finished = time.time()
            with self._lock:
                self._processed += 1
                self._total_latency += (finished - task.enqueued_at)

            self.task_q.task_done()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=9000)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--queue", type=int, default=500)
    ap.add_argument("--reject-when-full", action="store_true", help="reject with ERR server busy instead of blocking")
    args = ap.parse_args()

    srv = ThreadPoolServer(
        host=args.host,
        port=args.port,
        workers=args.workers,
        queue_size=args.queue,
        reject_when_full=args.reject_when_full,
    )

    try:
        srv.start()
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        srv.stop()


if __name__ == "__main__":
    main()
