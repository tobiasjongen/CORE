"""Declare the stream, register a query and print its matches as they arrive.

Usage: python online_example/subscriber.py <declaration.core> <query.txt>
"""

import sys
import time
from pathlib import Path

import pycer

declaration_file, query_file = Path(sys.argv[1]), Path(sys.argv[2])

with pycer.PyClient("tcp://localhost", 5000) as client:
    if not client.list_all_streams():
        client.declare_stream(declaration_file.read_text())
    port = client.add_query(query_file.read_text())
    print(f"Query registered, results on port {port}. Waiting for matches...")

    def on_result(enumerator):
        for complex_event in enumerator:
            print(complex_event.to_string(), flush=True)

    client.subscribe_to_complex_event(on_result, port)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
