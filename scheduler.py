"""
Scheduler Module
Course: Communication and Network Systems (CNS)

Responsibilities:
  - Selects the next message from the buffer queue under:
    1. FIFO (First-In, First-Out)
    2. Priority Scheduling (P1 > P2 > P3, with arrival time tie-breaker)
"""

from typing import List
from message import Message


def select_fifo_message(waiting_queue: List[Message]) -> Message:
    """
    FIFO Policy:
      Selects the message with the earliest arrival time.
      Tie-breaker: lower message_id.
    """
    assert waiting_queue, "Cannot schedule from an empty waiting queue."
    waiting_queue.sort(key=lambda m: (m.arrival_time, m.message_id))
    return waiting_queue.pop(0)


def select_priority_message(waiting_queue: List[Message]) -> Message:
    """
    Priority Scheduling Policy:
      Selects the message with the highest priority (P1=1 > P2=2 > P3=3).
      Tie-breaker: earliest arrival_time, then message_id.
    """
    assert waiting_queue, "Cannot schedule from an empty waiting queue."
    waiting_queue.sort(key=lambda m: (m.priority, m.arrival_time, m.message_id))
    return waiting_queue.pop(0)


def schedule_next_message(waiting_queue: List[Message], mode: str) -> Message:
    """
    Dispatches to the selected scheduling policy.
    Mode must be 'FIFO' or 'PRIORITY'.
    """
    if mode.upper() == "FIFO":
        return select_fifo_message(waiting_queue)
    elif mode.upper() == "PRIORITY":
        return select_priority_message(waiting_queue)
    else:
        raise ValueError(f"Unknown scheduling mode: '{mode}'. Must be 'FIFO' or 'PRIORITY'.")
