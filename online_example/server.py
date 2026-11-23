"""Start the CORE online server and keep it running until Ctrl+C."""

import time

import pycer

with pycer.PyOnlineServer(router_port=5000, stream_listener_port=5001, starting_query_port=5002):
    print("CORE server running (router :5000, streams :5001, queries :5002+). Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down")
