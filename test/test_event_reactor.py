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
        if event[0] in ('first', 'third'):
            raise RuntimeError('custom exception')


def test_create_event_reactor():
    context = Mock()
    context.args = Mock()
    context.args.event_handlers = []
    with EntryPointContext(
        extension1=Extension1, extension2=Extension2, extension3=Extension3
    ):
        event_reactor = create_event_reactor(context)
    queue = event_reactor.get_queue()
    assert isinstance(queue, Queue)

    # use larger interval to prevent different timing to effect the results
    event_reactor.TIMER_INTERVAL = 0.25

    # add a few dummy events
    with patch('colcon_core.event_reactor.logger.error') as error:
        queue.put(('first', None))

        event_reactor.start()
        queue.put(('second', None))
        queue.put(('third', None))

        # check the collected events so far
        event_reactor.flush()
    assert len(event_reactor._observers[0].events) == 4
    assert len(event_reactor._observers[1].events) == 4
    assert isinstance(event_reactor._observers[0].events[0][0], TimerEvent)
    assert isinstance(event_reactor._observers[1].events[0][0], TimerEvent)
    assert event_reactor._observers[0].events[1:] == \
        [('first', None), ('second', None), ('third', None)]
    assert event_reactor._observers[1].events[1:] == \
        [('first', None), ('second', None), ('third', None)]

    # the raised exception is catched and results in an error message
    assert error.call_count == 2
    assert len(error.call_args_list[0][0]) == 1
    assert error.call_args_list[0][0][0].startswith(
        "Exception in event handler extension 'extension3': "
        'custom exception\n')
    assert len(error.call_args_list[1][0]) == 1
    assert error.call_args_list[1][0][0].startswith(
        "Exception in event handler extension 'extension3': "
        'custom exception\n')

    # wait for another timer event to be generated
    time.sleep(event_reactor.TIMER_INTERVAL)
    assert len(event_reactor._observers[0].events) == 5
    assert len(event_reactor._observers[1].events) == 5
    assert isinstance(event_reactor._observers[0].events[-1][0], TimerEvent)
    assert isinstance(event_reactor._observers[1].events[-1][0], TimerEvent)

    # signal to stop the thread and wait for it to join
    event_reactor.join()
    assert len(event_reactor._observers[0].events) == 6
    assert len(event_reactor._observers[1].events) == 6
    assert isinstance(
        event_reactor._observers[0].events[-1][0], EventReactorShutdown)
    assert isinstance(
        event_reactor._observers[1].events[-1][0], EventReactorShutdown)

    # no harm in flushing after the thread has been joined
    event_reactor.flush()
