#!/usr/bin/env python3
import argparse
import random
import socket
import logging
import threading
import time
import string
from dataclasses import dataclass

@dataclass
class Metrics:
    lock: threading.Lock
    sent: int = 0
    recv: int = 0
    ok: int = 0
    err: int = 0


def generate_random_number(low, high):
    return random.randint(low, high)


def generate_random_string(length):
    # Define the character pool: lowercase, uppercase, and digits
    characters = string.ascii_letters + string.digits
    # Use random.choices to select characters with replacement
    random_string = ''.join(random.choices(characters, k=length))
    return random_string


def make_request(mix: str) -> str:
    """
    mix:
      - sleep: mostly SLEEP
      - cpu: mostly FIB
      - balanced: mixed
    """
    if mix == "sleep":
        ms = generate_random_number(100, 1000)
        return f"SLEEP {ms}\n"
    elif mix == "echo":
        msg = generate_random_string(generate_random_number(1, 100))
        return f"ECHO {msg}\n"
    else:
        choice = random.random()
        if choice < 0.50:
            ms = generate_random_number(100, 1000)
            return f"SLEEP {ms}\n"
        else:
            msg = generate_random_string(generate_random_number(1, 100))
            return f"ECHO {msg}\n"


def recv_lines(sock: socket.socket, expected: int, timeout: float, logger: logging.Logger) -> list[str]:
    """
    Receive up to `expected` newline-terminated responses.
    """
    sock.settimeout(timeout)
    buf = b""
    lines: list[str] = []

    while len(lines) < expected:
        try:
            data = sock.recv(4096)
            if not data:
                logger.warning("server closed connection while receiving")
                break
            buf += data
            while b"\n" in buf and len(lines) < expected:
                raw, buf = buf.split(b"\n", 1)
                lines.append(raw.decode("utf-8", errors="replace"))
        except socket.timeout:
            logger.warning("recv timeout after %d/%d responses", len(lines), expected)
            break
        except OSError as e:
            logger.error("recv error: %s", e)
            break

    return lines


def client_thread(cid: int, host: str, port: int, requests: int, mix: str, max_inflight: int, recv_timeout: float, metrics: Metrics, log_level: int):
    """
    Pipelined client:
      - sends up to max_inflight requests without waiting
      - then reads responses
    """
    logger = logging.getLogger(f"client-{cid}")
    logger.setLevel(log_level)

    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        logger.info("connected to %s:%d", host, port)

        remaining = requests
        batch_id = 0

        while remaining > 0:
            batch = min(max_inflight, remaining)
            batch_id += 1

            payload = "".join(make_request(mix) for _ in range(batch))
            sock.sendall(payload.encode("utf-8"))
            logger.debug("sent batch %d (%d requests)", batch_id, batch)

            with metrics.lock:
                metrics.sent += batch

            lines = recv_lines(sock, expected=batch, timeout=recv_timeout, logger=logger)

            with metrics.lock:
                metrics.recv += len(lines)
                for s in lines:
                    if s.startswith("OK"):
                        metrics.ok += 1
                    else:
                        metrics.err += 1

            logger.info(
                "received batch %d: %d/%d responses",
                batch_id, len(lines), batch
            )

            if len(lines) < batch:
                logger.warning(
                    "batch %d incomplete (%d/%d), stopping client",
                    batch_id, len(lines), batch
                )
                break

            remaining -= batch

        logger.info("finished: sent=%d recv=%d", requests - remaining, requests - remaining)

    except OSError as e:
        logger.error("client error: %s", e)
    finally:
        if sock:
            try:
                sock.close()
                logger.info("connection closed")
            except OSError:
                pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=9000)
    ap.add_argument("--clients", type=int, default=50,
                    help="number of client threads")
    ap.add_argument("--requests", type=int, default=200,
                    help="number of requests to send for each client thread")
    ap.add_argument("--max-inflight", type=int, default=50,
                    help="max outstanding requests per connection")
    ap.add_argument("--recv-timeout", type=float, default=5.0,
                    help="socket recv timeout (seconds)")
    ap.add_argument("--mix", choices=["sleep", "cpu", "balanced"], default="balanced")
    ap.add_argument("--log-level", default="INFO",
                    choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = ap.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] [%(threadName)s] %(name)s: %(message)s",
    )

    metrics = Metrics(lock=threading.Lock())
    threads = []
    start = time.time()

    for i in range(args.clients):
        t = threading.Thread(target=client_thread, args=(i, args.host, args.port, args.requests, args.mix, args.max_inflight, args.recv_timeout, metrics, getattr(logging, args.log_level)))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    elapsed = time.time() - start
    with metrics.lock:
        sent = metrics.sent
        recv = metrics.recv
        ok = metrics.ok
        err = metrics.err

    rps = ok / elapsed if elapsed > 0 else 0.0
    logging.info(
        "SUMMARY sent=%d recv=%d ok=%d err=%d elapsed=%.2fs ok_rps=%.2f",
        sent, recv, ok, err, elapsed, rps
    )


if __name__ == "__main__":
    main()
