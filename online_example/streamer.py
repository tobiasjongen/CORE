"""Replay a CSV file into the running server, simulating a live source.

Usage: python online_example/streamer.py <data.csv> [events_per_second]
"""

import sys
import time
from pathlib import Path

import pycer

from tests.e2e.csv_parser import parse_csv

csv_file = Path(sys.argv[1])
rate = float(sys.argv[2]) if len(sys.argv) > 2 else 1000.0

with pycer.PyClient("tcp://localhost", 5000) as client:
    stream_info = client.list_all_streams()[0]  # declared by subscriber.py

events, _ = parse_csv(csv_file, stream_info)

with pycer.PyStreamer("tcp://localhost", 5001) as streamer:
    for i, event in enumerate(events, start=1):
        streamer.send_stream(stream_info.id, event)
        if i % 1000 == 0:
            print(f"Sent {i}/{len(events)} events", flush=True)
        time.sleep(1 / rate)
    print(f"Done, sent {len(events)} events")
    time.sleep(1)  # let the last events get processed before disconnecting
