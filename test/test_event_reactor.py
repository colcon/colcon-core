# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from queue import Queue
import time

from colcon_core.event.timer import TimerEvent
from colcon_core.event_handler import EventHandlerExtensionPoint
from colcon_core.event_reactor import create_event_reactor
from colcon_core.event_reactor import EventReactorShutdown
from mock import Mock
from mock import patch

from .entry_point_context import EntryPointContext


class CustomExtension(EventHandlerExtensionPoint):

    def __init__(self):
        super().__init__()
        self.events = []

    def __call__(self, event):
        self.events.append(event)


class Extension1(CustomExtension):
    pass


class Extension2(CustomExtension):

    def __init__(self):
        super().__init__()
        self.enabled = False


class Extension3(CustomExtension):

    def __call__(self, event):
        super().__call__(event)
        if event[0] == 'first':
            raise ValueError("ValueError for '%s'" % event[0])
        if event[0] == 'third':
            raise RuntimeError("RuntimeError for '%s'" % event[0])


def test_create_event_reactor():
    context = Mock()
    context.args = Mock()
    context.args.event_handlers = []
    with EntryPointContext(
        extension1=Extension1, extension2=Extension2, extension3=Extension3
    ):
        event_reactor = create_event_reactor(context)

    with event_reactor:
        queue = event_reactor.get_queue()
        assert isinstance(queue, Queue)

        # use larger interval to prevent different timing to effect the results
        event_reactor.TIMER_INTERVAL = 1.0

        # add a few dummy events
        with patch('colcon_core.event_reactor.logger.error') as error:
            assert error.call_count == 0

            queue.put(('first', None))
            event_reactor.flush()
            assert error.call_count == 1

            queue.put(('second', None))
            event_reactor.flush()
            assert error.call_count == 1

            queue.put(('third', None))
            event_reactor.flush()
            assert error.call_count == 2

        # 1 timer event, 3 mock string events
        assert len(event_reactor._observers[0].events) == 4
        assert len(event_reactor._observers[1].events) == 4
        # both observers got the timer event
        assert isinstance(event_reactor._observers[0].events[0][0], TimerEvent)
        assert isinstance(event_reactor._observers[1].events[0][0], TimerEvent)
        # both observers got the 3 mock string events
        assert event_reactor._observers[0].events[1:] == \
            [('first', None), ('second', None), ('third', None)]
        assert event_reactor._observers[1].events[1:] == \
            [('first', None), ('second', None), ('third', None)]

        # the raised exception is catched and results in an error message
        assert error.call_count == 2
        assert len(error.call_args_list[0][0]) == 1
        assert error.call_args_list[0][0][0].startswith(
            "Exception in event handler extension 'extension3': "
            "ValueError for 'first'\n")
        assert len(error.call_args_list[1][0]) == 1
        assert error.call_args_list[1][0][0].startswith(
            "Exception in event handler extension 'extension3': "
            "RuntimeError for 'third'")

        # wait for another timer event to be generated
        time.sleep(1.5 * event_reactor.TIMER_INTERVAL)
        assert len(event_reactor._observers[0].events) == 5
        assert len(event_reactor._observers[1].events) == 5
        assert isinstance(
            event_reactor._observers[0].events[-1][0], TimerEvent)
        assert isinstance(
            event_reactor._observers[1].events[-1][0], TimerEvent)

    assert len(event_reactor._observers[0].events) == 6
    assert len(event_reactor._observers[1].events) == 6
    assert isinstance(
        event_reactor._observers[0].events[-1][0], EventReactorShutdown)
    assert isinstance(
        event_reactor._observers[1].events[-1][0], EventReactorShutdown)

    # no harm in flushing after the thread has been joined
    event_reactor.flush()
