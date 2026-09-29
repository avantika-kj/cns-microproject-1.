"""
Metrics Module
Course: Communication and Network Systems (CNS)
"""

from typing import List, Dict, Any
from message import Message


def calculate_metrics(messages: List[Message]) -> Dict[str, Any]:
    if not messages:
        return {}

    n = len(messages)
    delivered = [m for m in messages if m.status == "DELIVERED"]
    lost = [m for m in messages if m.status == "LOST"]

    loss_rate = (len(lost) / n * 100.0) if n > 0 else 0.0

    avg_wait = sum(m.waiting_time for m in messages) / n
    avg_delay = sum(m.completion_time - m.arrival_time for m in messages) / n

    start_sim = min(m.arrival_time for m in messages)
    end_sim = max(m.completion_time for m in messages)
    duration = max(end_sim - start_sim, 0.001)
    throughput = len(delivered) / duration

    ambulance_msgs = [m for m in messages if m.source_type == "Ambulance"]
    critical_msgs = [m for m in messages if m.priority == 1]
    normal_msgs = [m for m in messages if m.source_type == "Normal User"]

    amb_avg_wait = (sum(m.waiting_time for m in ambulance_msgs) / len(ambulance_msgs)) if ambulance_msgs else 0.0
    crit_avg_wait = (sum(m.waiting_time for m in critical_msgs) / len(critical_msgs)) if critical_msgs else 0.0
    normal_avg_wait = (sum(m.waiting_time for m in normal_msgs) / len(normal_msgs)) if normal_msgs else 0.0

    crit_before_first_normal = 0
    first_normal_seen = False
    for m in messages:
        if m.source_type == "Normal User":
            first_normal_seen = True
        elif m.priority == 1 and not first_normal_seen:
            crit_before_first_normal += 1

    return {
        "total_messages": n,
        "total_delivered": len(delivered),
        "total_lost": len(lost),
        "packet_loss_rate": round(loss_rate, 2),
        "avg_waiting_time": round(avg_wait, 3),
        "avg_delay": round(avg_delay, 3),
        "throughput": round(throughput, 3),
        "ambulance_avg_waiting_time": round(amb_avg_wait, 3),
        "critical_ambulance_avg_waiting_time": round(crit_avg_wait, 3),
        "normal_user_avg_waiting_time": round(normal_avg_wait, 3),
        "critical_transmitted_before_first_normal": crit_before_first_normal,
        "transmission_order": [f"M{m.message_id}" for m in messages],
    }
