"""
Simulation Engine Module
Course: Communication and Network Systems (CNS)

Responsibilities:
  - Generates stochastic message traffic over time.
  - Implements the discrete-event queueing model over a single shared channel.
  - Delegates packet scheduling decisions strictly to scheduler.py.
"""

import copy
import random
from typing import List, Dict, Optional
from message import Message
from scheduler import schedule_next_message


def generate_messages(
    num_messages: int,
    simulation_duration: float,
    channel_tx_time: float = 1.0,
    seed: int = 42,
    ambulance_ratio: float = 0.40,
    critical_ratio: float = 0.50,
) -> List[Message]:
    """
    Generates synthetic message traffic arriving over a shared simulation duration.
    Ensures sorted arrival timestamps across nodes.
    """
    rng = random.Random(seed)
    raw_arrivals = sorted([
        round(rng.uniform(0.0, simulation_duration), 2)
        for _ in range(num_messages)
    ])
    messages: List[Message] = []

    for idx, arrival in enumerate(raw_arrivals, start=1):
        is_ambulance = rng.random() < ambulance_ratio
        if is_ambulance:
            source = "Ambulance"
            is_critical = rng.random() < critical_ratio
            level = "Critical" if is_critical else "Non-critical"
        else:
            source = "Normal User"
            level = "None"

        messages.append(
            Message.create(
                message_id=idx,
                source_type=source,
                emergency_level=level,
                arrival_time=arrival,
                transmission_time=round(channel_tx_time, 2),
            )
        )

    return messages


def simulate_channel(
    input_messages: List[Message],
    mode: str = "PRIORITY",
    loss_probability: float = 0.0,
    channel_loss_map: Optional[Dict[int, bool]] = None,
) -> List[Message]:
    """
    Executes discrete-event queue simulation over a single shared communication channel.
    
    Channel Constraints:
      - Only ONE message is transmitted at any instant (Single Server Queue).
      - When channel is busy, arriving packets enter the waiting queue.
      - When channel becomes free, scheduler.schedule_next_message() selects the next packet.
      - Mode must be 'FIFO' or 'PRIORITY'.
    """
    msgs = copy.deepcopy(input_messages)
    unprocessed = sorted(msgs, key=lambda m: (m.arrival_time, m.message_id))

    waiting_queue: List[Message] = []
    processed: List[Message] = []
    channel_free_time = 0.0
    idx = 0
    total = len(unprocessed)

    # Initialize random number generator for channel packet loss if no map provided
    rng = random.Random(42)

    while idx < total or waiting_queue:
        # 1. Advance simulation clock if channel is idle and no packets are waiting
        if not waiting_queue and channel_free_time <= unprocessed[idx].arrival_time:
            channel_free_time = unprocessed[idx].arrival_time

        # 2. Arriving messages enter the waiting queue while channel is occupied
        while idx < total and unprocessed[idx].arrival_time <= channel_free_time:
            waiting_queue.append(unprocessed[idx])
            idx += 1

        # 3. Channel is free -> Scheduler selects next message from the queue
        if waiting_queue:
            msg = schedule_next_message(waiting_queue, mode=mode)

            # 4. Message transmission
            start = max(channel_free_time, msg.arrival_time)
            wait = start - msg.arrival_time
            completion = start + msg.transmission_time

            msg.start_time = round(start, 2)
            msg.waiting_time = round(wait, 2)
            msg.completion_time = round(completion, 2)

            # 5. Message completion & simulated channel packet loss
            if channel_loss_map is not None:
                is_lost = channel_loss_map.get(msg.message_id, False)
            else:
                is_lost = (rng.random() < loss_probability)

            msg.status = "LOST" if is_lost else "DELIVERED"

            channel_free_time = completion
            processed.append(msg)

    return processed
