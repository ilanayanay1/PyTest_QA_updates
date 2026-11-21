from socket import socket, AF_INET, SOCK_STREAM, timeout as SocketTimeout


def fetch_current_measurement(port: int, command: bytes, timeout_seconds: float = 2.0) -> float:
    try:
        with socket(AF_INET, SOCK_STREAM) as s:
            s.settimeout(timeout_seconds)
            s.connect(("localhost", port))
            s.sendall(command)
            data = s.recv(1024)
    except (ConnectionRefusedError, OSError, SocketTimeout) as exc:
        raise RuntimeError(f"Failed to communicate with ammeter on port {port}: {exc}") from exc

    if not data:
        raise ValueError(f"Empty response received from ammeter on port {port}.")

    decoded = data.decode("utf-8").strip()
    try:
        return float(decoded)
    except ValueError as exc:
        raise ValueError(f"Invalid numeric measurement '{decoded}' from port {port}.") from exc


def request_current_from_ammeter(port: int, command: bytes):
    try:
        value = fetch_current_measurement(port, command)
        print(f"Received current measurement from port {port}: {value}")
    except Exception as exc:
       print(f"Error: {exc}")