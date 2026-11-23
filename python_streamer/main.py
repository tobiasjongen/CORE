import asyncio
import os

import pycer
from bluesky.create_post import CreatePostStreamer
from bluesky.create_post_offline import CreatePostStreamerOffline
from coinbase.ticker import TickerStreamer

CORE_HOST = os.environ.get("CORE_HOST", "tcp://localhost")
CORE_ROUTER_PORT = int(os.environ.get("CORE_ROUTER_PORT", "5000"))
CORE_STREAM_PORT = int(os.environ.get("CORE_STREAM_PORT", "5001"))


async def do():
    client = pycer.PyClient(CORE_HOST, CORE_ROUTER_PORT)

    streamer = pycer.PyStreamer(CORE_HOST, CORE_STREAM_PORT)

    ticker_streamer = TickerStreamer(client, streamer)
    # ticker_streamer = TickerStreamerOffline(client, streamer)

    bluesky_post_streamer = CreatePostStreamer(client, streamer)
    # bluesky_post_streamer = CreatePostStreamerOffline(client, streamer)

    tasks = []
    tasks.append(ticker_streamer.start())
    tasks.append(bluesky_post_streamer.start())
    await asyncio.gather(*tasks)


asyncio.run(do())
