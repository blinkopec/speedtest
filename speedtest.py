import argparse
import sys
import time
import urllib.error
import urllib.request

DEFAULT_REQUESTS = 10
CHUNK_SIZE = 64 * 1024


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Замер скорости скачивания по URL (последовательные запросы)"
    )
    p.add_argument("url", help="Адрес для скачивания (например, тяжелая картинка)")
    p.add_argument(
        "-n",
        "--requests",
        type=int,
        default=DEFAULT_REQUESTS,
        help=f"Количество запросов (по умолчанию {DEFAULT_REQUESTS})",
    )
    args = p.parse_args()
    if args.requests <= 0:
        p.error("--requests должен быть > 0")

    return args


def fetch_once(url: str) -> tuple[int, float]:
    req = urllib.request.Request(
        url,
        headers={
            "Accept-Encoding": "identity",
            "User-Agent": "speed-test-cli/1.0",
            "Cache-Control": "no-store",
        },
    )

    started = time.perf_counter()
    with urllib.request.urlopen(req, timeout=60) as resp:
        if resp.status < 200 or resp.status >= 300:
            raise RuntimeError(f"HTTP {resp.status} {resp.reason}")
    total = 0
    while True:
        chunk = resp.read(CHUNK_SIZE)
        if not chunk:
            break

        total += len(chunk)

    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return total, elapsed_ms


def format_bytes(b: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    v = float(b)
    i = 0
    while v >= 1024 and i < len(units) - 1:
        v /= 1024
        i += 1
    return f"{v:.2f} {units[i]}"


def main() -> int:
    args = parse_args()
    url = args.url
    n = args.requests

    print(f"URL:        {url}")
    print(f"Запросов:   {n}")
    print("─" * 60)

    total_bytes = 0
    total_ms = 0.0
    ok_count = 0

    for i in range(1, n + 1):
        try:
            nbytes, ms = fetch_once(url)
            total_bytes += nbytes
            total_ms += ms
            ok_count += 1
            mbps = (nbytes * 8) / (ms / 1000.0) / 1_000_000 if ms > 0 else 0.0
            print(
                f"#{i:02d}  "
                f"размер: {format_bytes(nbytes):>10}  "
                f"время: {ms:>8.0f} мс  "
                f"скорость: {mbps:>7.2f} Мбит/с"
            )
        except urllib.error.HTTPError as e:
            print(f"#{i:02d}  ошибка HTTP {e.code} {e.reason}", file=sys.stderr)
        except urllib.error.URLError as e:
            print(f"#{i:02d}  ошибка сети: {e.reason}", file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            print(f"#{i:02d}  ошибка: {e}", file=sys.stderr)

    print("─" * 60)

    if ok_count == 0 or total_ms == 0:
        print("Не удалось скачать данные.", file=sys.stderr)
        return 1

    avg_ms = total_ms / ok_count
    avg_mbps = (total_bytes * 8) / (total_ms / 1000.0) / 1_000_000

    print(f"Успешных запросов:      {ok_count}/{n}")
    print(f"Среднее время запроса:  {avg_ms:.1f} мс")
    print(f"Скачано всего:          {format_bytes(total_bytes)} ({total_bytes} B)")
    print(f"Средняя скорость:       {avg_mbps:.2f} Мбит/с")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
