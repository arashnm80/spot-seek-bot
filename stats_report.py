#!/usr/bin/env python3
"""Print week or month stats from music.db. Usage: python3 stats_report.py --days 7"""

import argparse
from stats import format_stats_text, summarize_period


def main():
    parser = argparse.ArgumentParser(description="Spotseek period stats")
    parser.add_argument("--days", type=int, default=7, help="window length (7=week, 30=month)")
    parser.add_argument("--month", action="store_true", help="last 30 days")
    args = parser.parse_args()
    days = 30 if args.month else args.days
    title = "Monthly stats" if days >= 28 else "Weekly stats" if days == 7 else f"{days}-day stats"
    print(format_stats_text(summarize_period(days), title))


if __name__ == "__main__":
    main()
