from __future__ import annotations

from src.tax_v15.schemas import ensure_v15_csv_files


def run() -> list[str]:
    return [str(path) for path in ensure_v15_csv_files()]


def main() -> None:
    created = run()
    print(f"v15 CSV 스키마 초기화 완료: 신규 {len(created)}개")


if __name__ == "__main__":
    main()
