# Homework: Multithreaded Server with a Thread Pool

## Learning Goals

* Understand why “one thread per request” doesn’t scale
* Implement a thread pool that serves many requests concurrently
* Implement work queue with resilient designs (e.g., avoid unlimited memory growth)
* Measure throughput/latency under different workloads and pool sizes

## Development Environment

* Python 3

## The Task

You are building a multi-threaded server that handles a large volume of requests from clients.
The server communicates with clients through **TCP Sockets**.
The TCP server that handles many short requests from many clients. Each request is a single line:
```
OP ARG\n
```
Where:
OP is one of: SLEEP and ECHO
ARG is an integer for SLEEP or a string for ECHO

Server responds with one line:
```
OK RESULT\n
```
Or an error
```
ERR message\n
```

For example:
* `SLEEP 50`  ==> sleep 50 ms ==> `OK 50`
* `ECHO hello` ==> `OK hello`

## The Starter Code

* `server.py`: The server implementation for the student to complete.
* `client.py`: The client sending requests to the server. It is a complete implementation but the student may choose to modify it for better testing.

## Requirements

The homework assignment expects you to submit your **source code (server.py)**, and a **writeup** describing your implementation and testing, and how you satisfied the requirements below.

Requirements (graded)
* Use a **thread pool** (fixed number of worker threads). --- 50%
* Have a **bounded queue** for pending requests (max 1000 items). --10%
* Implement **backpressure**: when the queue is full, block until space is available or time out after 1 seconds and reject with `ERR server busy`. --10%
* Properly handle concurrency: handle multiple clients simultanously; close sockets cleanly on the leave of clients. -- 10%
* Testing your code thoroughly; describe you test cases in the writeup. -- 20%
* (Bonus) Additioanl robustness improvements and logging or debugging support. Describe all your bonus effort in the writeup.

## How to Run

Start the server
```bash
python server.py --host 127.0.0.1 --port 9000 --workers 8 --queue 500
```

Run the client
```bash
python3 client.py --host 127.0.0.1 --port 9000 --clients 5 --requests 200 --mix balanced
```

Enable concurrent requests by adding `--max-inflight 10` large than 1.


## API Hints

Absolutely — here is a **concise, minimal list** containing **only the APIs actually used in this assignment**, grouped by purpose, with one-line explanations.

### 1) Networking (`socket`)

* `socket.socket(AF_INET, SOCK_STREAM)`
  Create a TCP socket.

* `sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)`
  Allow fast server restart.

* `sock.bind((host, port))`
  Bind server to address.

* `sock.listen()`
  Start listening for connections.

* `sock.accept()`
  Accept a client connection.

* `sock.settimeout(seconds)`
  Set timeout for blocking socket calls.

* `conn.recv(bufsize)`
  Read bytes from client.

* `conn.sendall(data)`
  Send all bytes to client.

* `sock.close()` / `conn.close()`
  Close socket cleanly.

### 2) Threading (`threading`)

* `threading.Thread(target=..., daemon=True)`
  Create threads (accept loop, client readers, workers).

* `Thread.start()`
  Start thread execution.

* `Thread.join(timeout)`
  Wait for thread termination.

* `threading.Lock()`
  Protect shared data and serialize socket writes.

* `threading.Event()`
  Signal threads to stop.

### 3) Work Queue (`queue`)

* `queue.Queue(maxsize)`
  Bounded task queue.

* `Queue.put(item)`
  Enqueue task (blocking backpressure).

* `Queue.put_nowait(item)`
  Enqueue task (reject when full).

* `Queue.get()`
  Dequeue task (worker threads).

* `Queue.task_done()`
  Mark task completion.

* `queue.Full`
  Exception when queue is full.
