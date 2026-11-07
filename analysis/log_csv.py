#!/usr/bin/env python3
"""Split a HAL-1 SD card log (e.g. HAL4_LOG.TXT) into sens1.csv, sens2.csv and gps.csv.

Usage:
    python3 log_csv.py --log-path HAL4_LOG.TXT

The log is read from the repo's logs/ folder and the CSVs are written there too. Each row
gets a "run" column, which goes up by one at every "=== HAL-1 LOG START ===",
because tick_ms restarts at 0 each time the board reboots and keeps writing
to the same file.
"""
import argparse
import csv
import re
from pathlib import Path

COLUMNS = {
    "SENS1": ["tick_ms", "lat", "lon", "baro_alt_m", "gps_alt_m", "vvel_ms", "temp_c"],
    "SENS2": ["tick_ms", "accX_g", "accY_g", "accZ_g",
              "gyrX_dps", "gyrY_dps", "gyrZ_dps",
              "roll_deg", "pitch_deg", "yaw_deg",
              "s1cmd_deg", "s2cmd_deg", "rssi",
              "pyro_main_drogue", "pyro_backup_drogue", "pyro_main_chute"],
    "GPS":   ["tick_ms", "lat", "lon", "alt_m", "utc_time", "sats", "hdop"],
}

LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"

# Fields in the log are separated by both tabs and commas.
SPLIT = re.compile(r"[\t,]")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--log-path", required=True, help="SD card log file name in logs/, e.g. HAL4_LOG.TXT")
    args = parser.parse_args()

    log_path = LOGS_DIR / Path(args.log_path).name
    if not log_path.is_file():
        parser.error(f"{log_path} not found")
    out_dir = LOGS_DIR

    files, writers = {}, {}
    for tag, cols in COLUMNS.items():
        f = open(out_dir / f"{tag.lower()}.csv", "w", newline="")
        files[tag] = f
        writers[tag] = csv.writer(f)
        writers[tag].writerow(["run"] + cols)

    counts = {tag: 0 for tag in COLUMNS}
    skipped = 0
    run = 0

    with open(log_path, "r", errors="replace") as log:
        for line in log:
            line = line.strip()
            if not line:
                continue
            if line.startswith("=== HAL-1 LOG START"):
                run += 1
                continue

            fields = SPLIT.split(line)
            tag = fields[0]
            if tag not in COLUMNS:
                continue  # DYN / EVENT lines aren't exported

            values = fields[1:]
            if values and values[-1] == "":
                values = values[:-1]  # trailing comma (SENS1 header)
            if not values or not values[0].isdigit():
                continue  # header line ("tick_ms ...")
            if len(values) != len(COLUMNS[tag]):
                skipped += 1  # truncated/corrupt line, e.g. power cut mid-write
                continue

            writers[tag].writerow([run] + values)
            counts[tag] += 1

    for f in files.values():
        f.close()

    print(f"Runs found: {run}")
    for tag, n in counts.items():
        print(f"  {tag.lower()}.csv: {n} rows")
    if skipped:
        print(f"  skipped {skipped} malformed line(s)")
    print(f"Written to: {out_dir.resolve()}")


if __name__ == "__main__":
    main()