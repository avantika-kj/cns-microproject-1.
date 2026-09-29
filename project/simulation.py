"""
Simulation Engine Module
Course: Communication and Network Systems (CNS)
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
    msgs = copy.deepcopy(input_messages)
    unprocessed = sorted(msgs, key=lambda m: (m.arrival_time, m.message_id))

    waiting_queue: List[Message] = []
    processed: List[Message] = []
    channel_free_time = 0.0
    idx = 0
    total = len(unprocessed)

    rng = random.Random(42)

    while idx < total or waiting_queue:
        if not waiting_queue and channel_free_time <= unprocessed[idx].arrival_time:
            channel_free_time = unprocessed[idx].arrival_time

        while idx < total and unprocessed[idx].arrival_time <= channel_free_time:
            waiting_queue.append(unprocessed[idx])
            idx += 1

        if waiting_queue:
            msg = schedule_next_message(waiting_queue, mode=mode)

            start = max(channel_free_time, msg.arrival_time)
            wait = start - msg.arrival_time
            completion = start + msg.transmission_time

            msg.start_time = round(start, 2)
            msg.waiting_time = round(wait, 2)
            msg.completion_time = round(completion, 2)

            if channel_loss_map is not None:
                is_lost = channel_loss_map.get(msg.message_id, False)
            else:
                is_lost = (rng.random() < loss_probability)

            msg.status = "LOST" if is_lost else "DELIVERED"

            channel_free_time = completion
            processed.append(msg)

    return processed
