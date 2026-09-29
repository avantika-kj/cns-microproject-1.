"""
Comparative Scheduling Experiment: FIFO vs. Priority Scheduling
Course: Communication and Network Systems (CNS)

Objective:
Demonstrate how Priority Scheduling changes message transmission order and
waiting time compared to standard FIFO, using the EXACT SAME input message set
and channel conditions.

No synthetic changes are made between the two runs. Both methods operate on
identical arrival timestamps and packet transmission durations.
"""

import copy
from typing import List, Dict, Any
from simulation_engine import Message, simulate_fifo, simulate_priority


def calculate_experiment_metrics(messages: List[Message]) -> Dict[str, Any]:
    """
    Computes all project-specified metrics for a given transmission schedule:
      - Average waiting time
      - Average transmission delay
      - Average completion time
      - Throughput (messages/sec)
      - Ambulance message average waiting time (P1 + P2)
      - Critical ambulance message average waiting time (P1)
      - Normal-user average waiting time (P3)
      - Number of critical ambulance messages transmitted before normal-user messages
    """
    if not messages:
        return {}

    n = len(messages)
    
    # Message subsets
    all_ambulance = [m for m in messages if m.source_type == "Ambulance"]
    critical_ambulance = [m for m in messages if m.priority == 1]
    non_critical_ambulance = [m for m in messages if m.priority == 2]
    normal_users = [m for m in messages if m.source_type == "Normal User"]

    # 1. Average waiting time
    avg_waiting_time = sum(m.waiting_time for m in messages) / n

    # 2. Average transmission delay
    avg_tx_delay = sum(m.transmission_time for m in messages) / n

    # 3. Average completion time (timestamp when transmission finishes)
    avg_completion_time = sum(m.completion_time for m in messages) / n

    # Average turnaround latency (completion_time - arrival_time)
    avg_turnaround_latency = sum(m.completion_time - m.arrival_time for m in messages) / n

    # 4. Throughput (total messages completed per unit simulation time)
    start_sim = min(m.arrival_time for m in messages)
    end_sim = max(m.completion_time for m in messages)
    total_time_span = max(end_sim - start_sim, 0.001)
    throughput = n / total_time_span

    # 5. Ambulance message average waiting time (Critical + Non-critical)
    avg_ambulance_wait = (
        sum(m.waiting_time for m in all_ambulance) / len(all_ambulance)
        if all_ambulance else 0.0
    )

    # 6. Critical ambulance message average waiting time (P1)
    avg_critical_ambulance_wait = (
        sum(m.waiting_time for m in critical_ambulance) / len(critical_ambulance)
        if critical_ambulance else 0.0
    )

    # 7. Normal-user average waiting time (P3)
    avg_normal_user_wait = (
        sum(m.waiting_time for m in normal_users) / len(normal_users)
        if normal_users else 0.0
    )

    # 8. Number of critical ambulance messages transmitted before normal-user messages
    # Metric A: Critical messages transmitted before the VERY FIRST normal user finished
    crit_before_first_normal = 0
    first_normal_seen = False
    for m in messages:
        if m.source_type == "Normal User":
            first_normal_seen = True
        elif m.priority == 1 and not first_normal_seen:
            crit_before_first_normal += 1

    # Metric B: Total number of (Critical, Normal) pairwise precedence inversions
    # (How many normal messages each critical message jumps ahead of)
    pairwise_precedences = 0
    normal_indices = [idx for idx, m in enumerate(messages) if m.source_type == "Normal User"]
    critical_indices = [idx for idx, m in enumerate(messages) if m.priority == 1]
    for c_idx in critical_indices:
        for n_idx in normal_indices:
            if c_idx < n_idx:
                pairwise_precedences += 1

    return {
        "total_messages": n,
        "avg_waiting_time": round(avg_waiting_time, 3),
        "avg_transmission_delay": round(avg_tx_delay, 3),
        "avg_completion_time": round(avg_completion_time, 3),
        "avg_turnaround_latency": round(avg_turnaround_latency, 3),
        "throughput_msgs_per_sec": round(throughput, 3),
        "ambulance_avg_waiting_time": round(avg_ambulance_wait, 3),
        "critical_ambulance_avg_waiting_time": round(avg_critical_ambulance_wait, 3),
        "normal_user_avg_waiting_time": round(avg_normal_user_wait, 3),
        "critical_transmitted_before_first_normal": crit_before_first_normal,
        "critical_ahead_of_normal_pairs": pairwise_precedences,
        "transmission_order": [f"M{m.message_id}" for m in messages],
    }


def run_comparative_experiment(messages: List[Message]) -> Dict[str, Any]:
    """
    Executes both FIFO and Priority Scheduling on the EXACT SAME input messages.
    Returns results in a structured Python dictionary.
    """
    # Create identical deep copies to guarantee independent, identical runs
    fifo_input = copy.deepcopy(messages)
    priority_input = copy.deepcopy(messages)

    # Run simulations
    fifo_scheduled = simulate_fifo(fifo_input)
    priority_scheduled = simulate_priority(priority_input)

    # Calculate metrics
    fifo_metrics = calculate_experiment_metrics(fifo_scheduled)
    priority_metrics = calculate_experiment_metrics(priority_scheduled)

    experiment_results = {
        "fifo": {
            "metrics": fifo_metrics,
            "scheduled_messages": [
                {
                    "message_id": m.message_id,
                    "source": m.source_type,
                    "emergency_level": m.emergency_level,
                    "priority": m.priority,
                    "arrival_time": m.arrival_time,
                    "start_time": m.start_time,
                    "transmission_time": m.transmission_time,
                    "waiting_time": m.waiting_time,
                    "completion_time": m.completion_time,
                }
                for m in fifo_scheduled
            ],
        },
        "priority": {
            "metrics": priority_metrics,
            "scheduled_messages": [
                {
                    "message_id": m.message_id,
                    "source": m.source_type,
                    "emergency_level": m.emergency_level,
                    "priority": m.priority,
                    "arrival_time": m.arrival_time,
                    "start_time": m.start_time,
                    "transmission_time": m.transmission_time,
                    "waiting_time": m.waiting_time,
                    "completion_time": m.completion_time,
                }
                for m in priority_scheduled
            ],
        },
    }

    return experiment_results


def print_comparison_table(results: Dict[str, Any], title: str = "COMPARATIVE PERFORMANCE REPORT"):
    """
    Prints a clear, side-by-side terminal comparison table showing the exact
    differences between FIFO and Priority Scheduling without bias.
    """
    f_met = results["fifo"]["metrics"]
    p_met = results["priority"]["metrics"]

    print("=" * 86)
    print(f" {title.upper()}")
    print("=" * 86)
    print(f"{'Performance Metric':<46} | {'FIFO Scheduling':<16} | {'Priority Scheduling':<18}")
    print("-" * 86)

    rows = [
        ("Transmission Order", str(f_met["transmission_order"]), str(p_met["transmission_order"])),
        ("Total Messages Processed", str(f_met["total_messages"]), str(p_met["total_messages"])),
        ("Average Waiting Time (Overall)", f"{f_met['avg_waiting_time']:.3f} s", f"{p_met['avg_waiting_time']:.3f} s"),
        ("Average Transmission Delay", f"{f_met['avg_transmission_delay']:.3f} s", f"{p_met['avg_transmission_delay']:.3f} s"),
        ("Average Completion Time", f"{f_met['avg_completion_time']:.3f} s", f"{p_met['avg_completion_time']:.3f} s"),
        ("Average Turnaround Latency", f"{f_met['avg_turnaround_latency']:.3f} s", f"{p_met['avg_turnaround_latency']:.3f} s"),
        ("Channel Throughput", f"{f_met['throughput_msgs_per_sec']:.3f} msgs/s", f"{p_met['throughput_msgs_per_sec']:.3f} msgs/s"),
        ("Ambulance Avg Waiting Time (All)", f"{f_met['ambulance_avg_waiting_time']:.3f} s", f"{p_met['ambulance_avg_waiting_time']:.3f} s"),
        ("Critical Ambulance Avg Waiting Time (P1)", f"{f_met['critical_ambulance_avg_waiting_time']:.3f} s", f"{p_met['critical_ambulance_avg_waiting_time']:.3f} s"),
        ("Normal-User Avg Waiting Time (P3)", f"{f_met['normal_user_avg_waiting_time']:.3f} s", f"{p_met['normal_user_avg_waiting_time']:.3f} s"),
        ("Critical Msgs Transmitted Before 1st Normal", str(f_met["critical_transmitted_before_first_normal"]), str(p_met["critical_transmitted_before_first_normal"])),
        ("Total (Critical < Normal) Precedence Pairs", str(f_met["critical_ahead_of_normal_pairs"]), str(p_met["critical_ahead_of_normal_pairs"])),
    ]

    for label, fifo_val, prio_val in rows:
        print(f"{label:<46} | {fifo_val:<16} | {prio_val:<18}")

    print("=" * 86 + "\n")


if __name__ == "__main__":
    # =========================================================================
    # EXPERIMENT 1: The Standard 5-Message Test Case (Arriving at t = 0.0s)
    # =========================================================================
    print(">>> EXPERIMENT 1: 5-MESSAGE SYSTEM (Simultaneous Arrival at t = 0.0s)")
    exp1_messages = [
        Message.create(message_id=1, source_type="Normal User", emergency_level="None", arrival_time=0.0, transmission_time=1.0),
        Message.create(message_id=2, source_type="Ambulance", emergency_level="Critical", arrival_time=0.0, transmission_time=1.0),
        Message.create(message_id=3, source_type="Ambulance", emergency_level="Non-critical", arrival_time=0.0, transmission_time=1.0),
        Message.create(message_id=4, source_type="Normal User", emergency_level="None", arrival_time=0.0, transmission_time=1.0),
        Message.create(message_id=5, source_type="Ambulance", emergency_level="Critical", arrival_time=0.0, transmission_time=1.0),
    ]

    results_exp1 = run_comparative_experiment(exp1_messages)
    print_comparison_table(results_exp1, title="Experiment 1: 5-Message Test Case (Simultaneous)")

    # =========================================================================
    # EXPERIMENT 2: Dynamic Multi-Message Scenario with Variable Traffic
    # =========================================================================
    print(">>> EXPERIMENT 2: 12-MESSAGE NETWORK TRAFFIC SCENARIO (Dynamic Arrivals)")
    from simulation_engine import generate_random_traffic
    exp2_messages = generate_random_traffic(
        num_messages=12,
        seed=2026,
        ambulance_ratio=0.45,
        critical_ratio=0.50,
        arrival_window=8.0,
        min_tx_time=0.8,
        max_tx_time=1.4
    )

    results_exp2 = run_comparative_experiment(exp2_messages)
    print_comparison_table(results_exp2, title="Experiment 2: 12-Message Dynamic Traffic")
