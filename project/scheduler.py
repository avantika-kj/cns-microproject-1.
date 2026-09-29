"""
Scheduler Module
Course: Communication and Network Systems (CNS)
"""

from typing import List
from message import Message


def select_fifo_message(waiting_queue: List[Message]) -> Message:
    assert waiting_queue, "Cannot schedule from an empty waiting queue."
    waiting_queue.sort(key=lambda m: (m.arrival_time, m.message_id))
    return waiting_queue.pop(0)


def select_priority_message(waiting_queue: List[Message]) -> Message:
    assert waiting_queue, "Cannot schedule from an empty waiting queue."
    waiting_queue.sort(key=lambda m: (m.priority, m.arrival_time, m.message_id))
    return waiting_queue.pop(0)


def schedule_next_message(waiting_queue: List[Message], mode: str) -> Message:
    if mode.upper() == "FIFO":
        return select_fifo_message(waiting_queue)
    elif mode.upper() == "PRIORITY":
        return select_priority_message(waiting_queue)
    else:
        raise ValueError(f"Unknown scheduling mode: '{mode}'. Must be 'FIFO' or 'PRIORITY'.")
