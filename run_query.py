"""Run a single CEQL query over a CSV stream with pycer.

Usage:
    python run_query.py <query.txt> <declaration.core> <data.csv> [options.core]
                        [--output matches.csv] [--id-attribute id]

Without --output, all matches are printed in CORE's text format. With --output, one
line per match is written to the CSV file instead: the value of the --id-attribute
(default: id) of every event in the match, in match order, comma-separated.
"""

import argparse
import os
import re
import sys
import time
from pathlib import Path

import pycer

from tests.e2e.csv_parser import parse_csv

# One match in get_output(): "[start,end], ((id: <type> attributes: [v1 v2 ...]) (id: ...) )"
EVENT_RE = re.compile(r"id: (\d+) attributes: \[([^\]]*)\]")


def write_csv(output: str, stream_info: pycer.PyStreamInfo, id_attribute: str, path: Path) -> int:
    """Write the id attribute of every matched event as CSV; return the number of matches."""
    id_index = {}  # event type id -> position of id_attribute in its attribute list
    for event_info in stream_info.events_info:
        names = [a.name for a in event_info.attributes_info]
        if id_attribute in names:
            id_index[event_info.id] = names.index(id_attribute)

    matches = 0
    path.parent.mkdir(parents=True, exist_ok=True)  # e.g. output/
    with open(path, "w") as out:
        for line in output.splitlines():
            if not line.startswith("["):
                continue
            ids = []
            for type_id, attributes in EVENT_RE.findall(line):
                type_id = int(type_id)
                if type_id not in id_index:
                    sys.exit(f"event type {type_id} has no attribute '{id_attribute}' (see --id-attribute)")
                ids.append(attributes.split()[id_index[type_id]])
            out.write(",".join(ids) + "\n")
            matches += 1
    return matches


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0], usage=__doc__.split("Usage:\n")[1].split("\n\n")[0]
    )
    parser.add_argument("query", type=Path)
    parser.add_argument("declaration", type=Path)
    parser.add_argument("data", type=Path)
    parser.add_argument("options", type=Path, nargs="?")
    parser.add_argument("--output", type=Path, help="write matches as CSV of event ids to this file")
    parser.add_argument("--id-attribute", default="id", help="attribute written per event (default: id)")
    args = parser.parse_args()

    server = pycer.PyOfflineServer()
    stream_info = server.declare_stream(args.declaration.read_text())
    if args.options:
        server.declare_option(args.options.read_text())
    server.add_query(args.query.read_text())

    events, delays_ns = parse_csv(args.data, stream_info)
    if any(d > 0 for d in delays_ns):
        # .corecsv files contain inter-event delays; replay them faithfully
        for event, delay_ns in zip(events, delays_ns):
            if delay_ns > 0:
                time.sleep(delay_ns / 1e9)
            server.send_event(event)
    else:
        server.send_events(events)

    print(f"Read events {len(events)}")
    if args.output:
        matches = write_csv(server.get_output(), stream_info, args.id_attribute, args.output)
        print(f"{matches} matches written to {args.output}")
    else:
        print(server.get_output())


if __name__ == "__main__":
    try:
        main()
        sys.stdout.flush()
    except BrokenPipeError:
        # Output was piped into e.g. `head`, which closed early; exit quietly
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(0)
