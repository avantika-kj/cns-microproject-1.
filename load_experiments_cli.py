"""
Predefined Network Load Experiments (Low, Medium, High Load)
Course: Communication and Network Systems (CNS)
"""

import random
import copy
from typing import List, Dict, Any
from simulation_engine import Message, simulate_fifo, simulate_priority


def generate_load_messages(
    num_messages: int,
    simulation_duration: float,
    channel_tx_time: float = 1.0,
    seed: int = 42,
    ambulance_ratio: float = 0.40,
    critical_ratio: float = 0.50,
) -> List[Message]:
    rng = random.Random(seed)
    raw_arrivals = sorted([round(rng.uniform(0.0, simulation_duration), 2) for _ in range(num_messages)])
    messages = []
    
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
                transmission_time=channel_tx_time,
            )
        )
    return messages


def compute_metrics(messages: List[Message], loss_map: Dict[int, bool]) -> Dict[str, Any]:
    n = len(messages)
    lost_count = sum(1 for m in messages if loss_map.get(m.message_id, False))
    loss_rate = (lost_count / n * 100.0) if n > 0 else 0.0

    avg_wait = sum(m.waiting_time for m in messages) / n
    avg_delay = sum(m.completion_time - m.arrival_time for m in messages) / n

    start_t = min(m.arrival_time for m in messages)
    end_t = max(m.completion_time for m in messages)
    throughput = (n - lost_count) / max(end_t - start_t, 0.001)

    amb_msgs = [m for m in messages if m.source_type == "Ambulance"]
    crit_msgs = [m for m in messages if m.priority == 1]
    norm_msgs = [m for m in messages if m.source_type == "Normal User"]

    amb_wait = (sum(m.waiting_time for m in amb_msgs) / len(amb_msgs)) if amb_msgs else 0.0
    crit_wait = (sum(m.waiting_time for m in crit_msgs) / len(crit_msgs)) if crit_msgs else 0.0
    norm_wait = (sum(m.waiting_time for m in norm_msgs) / len(norm_msgs)) if norm_msgs else 0.0

    return {
        "avg_waiting_time": round(avg_wait, 3),
        "avg_delay": round(avg_delay, 3),
        "throughput": round(throughput, 3),
        "packet_loss_rate": round(loss_rate, 2),
        "ambulance_avg_wait": round(amb_wait, 3),
        "critical_ambulance_avg_wait": round(crit_wait, 3),
        "normal_user_avg_wait": round(norm_wait, 3),
    }


def run_all_load_experiments():
    configs = [
        ("Experiment 1", "Low Load (8 msgs / 20s)", 8, 20.0),
        ("Experiment 2", "Medium Load (15 msgs / 15s)", 15, 15.0),
        ("Experiment 3", "High Load (25 msgs / 12s)", 25, 12.0),
    ]

    print("=" * 115)
    print(" PREDEFINED NETWORK LOAD EXPERIMENTS (CONTROLLED CHANNELS: Tx=1.0s, Loss=2.0%, Seed=42)")
    print("=" * 115)
    header = (
        f"{'Experiment':<15} | {'Scheduling Method':<18} | {'Avg Wait':<10} | {'Avg Delay':<10} | "
        f"{'Throughput':<12} | {'Loss Rate':<10} | {'Amb Wait':<10} | {'Crit Wait (P1)':<15} | {'Normal Wait':<12}"
    )
    print(header)
    print("-" * 115)

    for exp_id, title, num, dur in configs:
        msgs = generate_load_messages(num_messages=num, simulation_duration=dur, channel_tx_time=1.0, seed=42)
        loss_rng = random.Random(42 + 999)
        loss_map = {m.message_id: (loss_rng.random() < 0.02) for m in msgs}

        fifo_res = simulate_fifo(copy.deepcopy(msgs))
        prio_res = simulate_priority(copy.deepcopy(msgs))

        f = compute_metrics(fifo_res, loss_map)
        p = compute_metrics(prio_res, loss_map)

        print(
            f"{exp_id:<15} | {'FIFO':<18} | {f['avg_waiting_time']:<8.3f} s | {f['avg_delay']:<8.3f} s | "
            f"{f['throughput']:<8.3f} m/s | {f['packet_loss_rate']:<8.1f}% | {f['ambulance_avg_wait']:<8.3f} s | "
            f"{f['critical_ambulance_avg_wait']:<13.3f} s | {f['normal_user_avg_wait']:<10.3f} s"
        )
        print(
            f"{'':<15} | {'Priority':<18} | {p['avg_waiting_time']:<8.3f} s | {p['avg_delay']:<8.3f} s | "
            f"{p['throughput']:<8.3f} m/s | {p['packet_loss_rate']:<8.1f}% | {p['ambulance_avg_wait']:<8.3f} s | "
            f"{p['critical_ambulance_avg_wait']:<13.3f} s | {p['normal_user_avg_wait']:<10.3f} s"
        )
        print("-" * 115)


if __name__ == "__main__":
    run_all_load_experiments()
