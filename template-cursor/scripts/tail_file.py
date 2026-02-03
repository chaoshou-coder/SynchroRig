import argparse
import os
import time


def tail_last_lines(path: str, n: int) -> list[str]:
    if n <= 0:
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return lines[-n:]
    except FileNotFoundError:
        return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Tail a UTF-8 text file.")
    parser.add_argument("path", help="File path to tail")
    parser.add_argument(
        "--tail", type=int, default=50, help="How many last lines to print initially"
    )
    parser.add_argument("--poll", type=float, default=0.2, help="Polling interval in seconds")
    args = parser.parse_args()

    path = os.path.abspath(args.path)
    print(f"[tail] {path}", flush=True)

    for line in tail_last_lines(path, args.tail):
        print(line, end="", flush=True)

    # Follow
    last_size = os.path.getsize(path) if os.path.exists(path) else 0
    while True:
        if not os.path.exists(path):
            time.sleep(args.poll)
            continue

        size = os.path.getsize(path)
        if size < last_size:
            # file truncated/rewritten
            for line in tail_last_lines(path, args.tail):
                print(line, end="", flush=True)
            last_size = size
            time.sleep(args.poll)
            continue

        if size == last_size:
            time.sleep(args.poll)
            continue

        with open(path, "r", encoding="utf-8") as f:
            f.seek(last_size)
            chunk = f.read()
        if chunk:
            print(chunk, end="", flush=True)
        last_size = size
        time.sleep(args.poll)


if __name__ == "__main__":
    raise SystemExit(main())
