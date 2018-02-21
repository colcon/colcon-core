# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import asyncio

from colcon_core.subprocess import new_event_loop


def run_until_complete(coroutine):
    loop = new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coroutine)
    finally:
        loop.close()
        assert loop.is_closed()
