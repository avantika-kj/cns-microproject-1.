"""
Priority-Based Emergency Message Scheduling Simulation Engine
Course: Communication and Network Systems (CNS)

Key Concept:
A single shared communication channel can only transmit one message at a time.
Messages arrive over time from two sources:
  1. Ambulance (Critical -> Priority 1, Non-critical -> Priority 2)
  2. Normal User (Standard -> Priority 3)

This module implements:
  - Message entity definition
  - Synthetic traffic generator
  - FIFO Scheduling simulation
  - Priority Scheduling simulation (Non-preemptive, arrival-time tie breaking)
  - Comparative performance metrics calculation
"""

from dataclasses import dataclass, field
import heapq
import random
import copy
from typing import List, Dict, Any, Tuple


# ============================================================================
# 1. MESSAGE DATA STRUCTURE
# ============================================================================

@dataclass(order=True)
class Message:
    """
    Represents an individual data packet/message traversing the network.
    
    The ordering tuple for heapq priority comparison is:
    (priority, arrival_time, message_id)
    - Lower priority number = Higher transmission precedence.
    - Tie-breaker = Earliest arrival time.
    """
    # Comparison fields used by Priority Queue (heapq)
    priority: int
    arrival_time: float
    message_id: int

    # Descriptive fields (excluded from heapq direct comparison)
    source_type: str = field(compare=False, default="Normal User")
    emergency_level: str = field(compare=False, default="None")
    transmission_time: float = field(compare=False, default=1.0)
    
    # Metrics fields computed during simulation
    start_time: float = field(compare=False, default=0.0)
    waiting_time: float = field(compare=False, default=0.0)
    completion_time: float = field(compare=False, default=0.0)

    @classmethod
    def create(
        cls,
        message_id: int,
        source_type: str,
        emergency_level: str,
        arrival_time: float,
        transmission_time: float = 1.0,
    ) -> "Message":
        """
        Factory helper enforcing project priority assignment rules:
          - Priority 1: Critical Ambulance
          - Priority 2: Non-critical Ambulance
          - Priority 3: Normal User
        """
        if source_type == "Ambulance":
            if emergency_level == "Critical":
                priority = 1
            else:
                emergency_level = "Non-critical"
                priority = 2
        else:
            source_type = "Normal User"
            emergency_level = "None"
            priority = 3

        return cls(
            priority=priority,
            arrival_time=round(arrival_time, 3),
            message_id=message_id,
            source_type=source_type,
            emergency_level=emergency_level,
            transmission_time=round(transmission_time, 3),
        )


# ============================================================================
# 2. MESSAGE TRAFFIC GENERATION
# ============================================================================

def generate_sample_scenario() -> List[Message]:
    """
    Generates the exact classic scenario described in the project brief:
      Message 1: Normal user (arrives at t=0.0)
      Message 2: Ambulance, Critical patient info (arrives at t=0.1)
      Message 3: Ambulance, Non-critical status info (arrives at t=0.2)
      Message 4: Normal user (arrives at t=0.3)
      Message 5: Ambulance, Critical patient alert (arrives at t=0.5)
    """
    messages = [
        Message.create(1, "Normal User", "None", arrival_time=0.0, transmission_time=1.0),
        Message.create(2, "Ambulance", "Critical", arrival_time=0.1, transmission_time=1.0),
        Message.create(3, "Ambulance", "Non-critical", arrival_time=0.2, transmission_time=1.0),
        Message.create(4, "Normal User", "None", arrival_time=0.3, transmission_time=1.0),
        Message.create(5, "Ambulance", "Critical", arrival_time=0.5, transmission_time=1.0),
    ]
    return messages


def generate_random_traffic(
    num_messages: int = 20,
    seed: int = 42,
    ambulance_ratio: float = 0.35,
    critical_ratio: float = 0.50,
    arrival_window: float = 15.0,
    min_tx_time: float = 0.8,
    max_tx_time: float = 1.5,
) -> List[Message]:
    """
    Generates synthetic network messages over time with controllable probabilities.
    
    Parameters:
      - num_messages: Total count of messages to simulate
      - seed: Random seed for repeatability
      - ambulance_ratio: Probability that a message is from an ambulance
      - critical_ratio: Probability that an ambulance message is critical
      - arrival_window: Maximum arrival timestamp (seconds)
      - min_tx_time, max_tx_time: Channel transmission duration range
    """
    random.seed(seed)
    messages = []
    
    # Generate random arrival times and sort them
    arrival_times = sorted([round(random.uniform(0.0, arrival_window), 2) for _ in range(num_messages)])

    for msg_id, arrival in enumerate(arrival_times, start=1):
        is_ambulance = random.random() < ambulance_ratio
        if is_ambulance:
            source = "Ambulance"
            is_crit = random.random() < critical_ratio
            level = "Critical" if is_crit else "Non-critical"
        else:
            source = "Normal User"
            level = "None"

        tx_time = round(random.uniform(min_tx_time, max_tx_time), 2)
        msg = Message.create(
            message_id=msg_id,
            source_type=source,
            emergency_level=level,
            arrival_time=arrival,
            transmission_time=tx_time,
        )
        messages.append(msg)

    return messages


# ============================================================================
# 3. SCHEDULING METHOD 1: FIFO (First-In, First-Out)
# ============================================================================

def simulate_fifo(messages: List[Message]) -> List[Message]:
    """
    FIFO Scheduling Algorithm:
    --------------------------
    Transmits messages strictly in the order of their arrival time.
    Emergency level is IGNORED by the scheduler.
    
    Channel constraint:
      - Only one message transmits at a time.
      - Next transmission starts at: max(current_channel_free_time, arrival_time)
    """
    # Clone messages so original inputs are not mutated
    msgs = copy.deepcopy(messages)
    
    # Sort strictly by arrival time, breaking ties with message_id
    msgs.sort(key=lambda m: (m.arrival_time, m.message_id))

    channel_free_time = 0.0

    for msg in msgs:
        # Channel cannot start transmitting before the packet actually arrives
        start_time = max(channel_free_time, msg.arrival_time)
        waiting_time = start_time - msg.arrival_time
        completion_time = start_time + msg.transmission_time

        msg.start_time = round(start_time, 3)
        msg.waiting_time = round(waiting_time, 3)
        msg.completion_time = round(completion_time, 3)

        # Update channel availability
        channel_free_time = completion_time

    return msgs


# ============================================================================
# 4. SCHEDULING METHOD 2: PRIORITY-BASED SCHEDULING
# ============================================================================

def simulate_priority(messages: List[Message]) -> List[Message]:
    """
    Priority Scheduling Algorithm (Non-Preemptive):
    ------------------------------------------------
    When the channel becomes available, it always selects the highest priority
    message currently waiting in the ready queue.
    
    Priority Rules:
      - Priority 1: Critical Ambulance (highest)
      - Priority 2: Non-critical Ambulance
      - Priority 3: Normal User (lowest)
    
    Tie-breaker:
      - Earliest arrival_time among identical priority messages.
      
    Non-preemptive behavior:
      - If a lower priority message is ALREADY transmitting on the shared channel,
        it is NOT interrupted. The high-priority message will be selected as soon
        as the ongoing transmission finishes.
    """
    msgs = copy.deepcopy(messages)
    # Sort incoming arrivals chronologically to feed into the event simulator
    unprocessed = sorted(msgs, key=lambda m: (m.arrival_time, m.message_id))
    
    ready_queue: List[Message] = []  # Min-heap ordered by (priority, arrival_time, message_id)
    transmitted_order: List[Message] = []
    
    channel_free_time = 0.0
    idx = 0
    total_msgs = len(unprocessed)

    while idx < total_msgs or ready_queue:
        # If the channel is idle and no packets are waiting in the queue,
        # advance time to the arrival of the next incoming message
        if not ready_queue and channel_free_time <= unprocessed[idx].arrival_time:
            channel_free_time = unprocessed[idx].arrival_time

        # Enqueue all messages that have arrived up to channel_free_time
        while idx < total_msgs and unprocessed[idx].arrival_time <= channel_free_time:
            heapq.heappush(ready_queue, unprocessed[idx])
            idx += 1

        # If packets are ready, dequeue the highest priority one (lowest priority number)
        if ready_queue:
            msg = heapq.heappop(ready_queue)
            
            start_time = max(channel_free_time, msg.arrival_time)
            waiting_time = start_time - msg.arrival_time
            completion_time = start_time + msg.transmission_time

            msg.start_time = round(start_time, 3)
            msg.waiting_time = round(waiting_time, 3)
            msg.completion_time = round(completion_time, 3)

            channel_free_time = completion_time
            transmitted_order.append(msg)

    return transmitted_order


# ============================================================================
# 5. PERFORMANCE METRICS & ANALYSIS
# ============================================================================

def calculate_metrics(transmitted_messages: List[Message]) -> Dict[str, Any]:
    """
    Computes key Communication and Network Systems (CNS) performance metrics:
      1. Average waiting time (overall and per priority tier)
      2. Average total delay (completion_time - arrival_time)
      3. Total transmission span and throughput (packets/second)
      4. Transmission sequence and ambulance-before-normal precedence count
    """
    if not transmitted_messages:
        return {}

    total_msgs = len(transmitted_messages)
    p1_msgs = [m for m in transmitted_messages if m.priority == 1]
    p2_msgs = [m for m in transmitted_messages if m.priority == 2]
    p3_msgs = [m for m in transmitted_messages if m.priority == 3]

    # Delays = waiting_time + transmission_time = completion_time - arrival_time
    all_delays = [m.completion_time - m.arrival_time for m in transmitted_messages]
    all_waits = [m.waiting_time for m in transmitted_messages]

    avg_wait = sum(all_waits) / total_msgs
    avg_delay = sum(all_delays) / total_msgs

    # Priority-specific averages
    p1_avg_wait = (sum(m.waiting_time for m in p1_msgs) / len(p1_msgs)) if p1_msgs else 0.0
    p2_avg_wait = (sum(m.waiting_time for m in p2_msgs) / len(p2_msgs)) if p2_msgs else 0.0
    p3_avg_wait = (sum(m.waiting_time for m in p3_msgs) / len(p3_msgs)) if p3_msgs else 0.0

    p1_avg_delay = (sum(m.completion_time - m.arrival_time for m in p1_msgs) / len(p1_msgs)) if p1_msgs else 0.0
    p2_avg_delay = (sum(m.completion_time - m.arrival_time for m in p2_msgs) / len(p2_msgs)) if p2_msgs else 0.0
    p3_avg_delay = (sum(m.completion_time - m.arrival_time for m in p3_msgs) / len(p3_msgs)) if p3_msgs else 0.0

    # Total channel active duration and throughput
    first_arrival = min(m.arrival_time for m in transmitted_messages)
    last_completion = max(m.completion_time for m in transmitted_messages)
    total_time_span = max(last_completion - first_arrival, 0.001)
    throughput = total_msgs / total_time_span  # messages per second

    # Precedence metric: count how many ambulance messages (P1 or P2)
    # completed transmission before normal-user messages (P3)
    ambulance_before_normal_count = 0
    normal_completed_so_far = 0
    for m in transmitted_messages:
        if m.source_type == "Normal User":
            normal_completed_so_far += 1
        elif m.source_type == "Ambulance":
            # If transmitted when 0 normal users had finished, it was ahead of all normal users
            if normal_completed_so_far == 0:
                ambulance_before_normal_count += 1

    return {
        "total_messages": total_msgs,
        "count_p1_critical": len(p1_msgs),
        "count_p2_non_critical": len(p2_msgs),
        "count_p3_normal": len(p3_msgs),
        "avg_waiting_time_overall": round(avg_wait, 3),
        "avg_delay_overall": round(avg_delay, 3),
        "avg_waiting_time_p1_critical": round(p1_avg_wait, 3),
        "avg_waiting_time_p2_non_critical": round(p2_avg_wait, 3),
        "avg_waiting_time_p3_normal": round(p3_avg_wait, 3),
        "avg_delay_p1_critical": round(p1_avg_delay, 3),
        "avg_delay_p2_non_critical": round(p2_avg_delay, 3),
        "avg_delay_p3_normal": round(p3_avg_delay, 3),
        "total_simulation_time": round(total_time_span, 3),
        "throughput_msgs_per_sec": round(throughput, 3),
        "ambulance_completed_before_any_normal": ambulance_before_normal_count,
        "transmission_order": [m.message_id for m in transmitted_messages],
    }


def compare_scheduling_methods(messages: List[Message]) -> Tuple[List[Message], List[Message], Dict[str, Any], Dict[str, Any]]:
    """
    Runs both FIFO and Priority Scheduling on the exact same message dataset,
    and returns scheduled results and comparative metrics.
    """
    fifo_results = simulate_fifo(messages)
    priority_results = simulate_priority(messages)

    fifo_metrics = calculate_metrics(fifo_results)
    priority_metrics = calculate_metrics(priority_results)

    return fifo_results, priority_results, fifo_metrics, priority_metrics


# ============================================================================
# 6. DEMONSTRATION & TEST RUNNER
# ============================================================================

def print_simulation_report(title: str, results: List[Message], metrics: Dict[str, Any]):
    """Pretty prints scheduling results and metrics table."""
    print("=" * 80)
    print(f" {title.upper()}")
    print("=" * 80)
    print(f"{'Msg ID':<7}{'Source':<13}{'Emergency':<15}{'Priority':<10}{'Arrival':<10}{'Start':<9}{'Tx Time':<9}{'Wait':<9}{'Finish':<9}")
    print("-" * 80)
    for m in results:
        print(
            f"#{m.message_id:<6}{m.source_type:<13}{m.emergency_level:<15}P{m.priority:<9}"
            f"{m.arrival_time:<10.2f}{m.start_time:<9.2f}{m.transmission_time:<9.2f}{m.waiting_time:<9.2f}{m.completion_time:<9.2f}"
        )
    print("-" * 80)
    print("Key Performance Metrics:")
    print(f"  • Overall Avg Waiting Time      : {metrics['avg_waiting_time_overall']:.3f} s")
    print(f"  • Overall Avg Total Delay       : {metrics['avg_delay_overall']:.3f} s")
    print(f"  • P1 (Critical) Avg Wait Time   : {metrics['avg_waiting_time_p1_critical']:.3f} s  (Delay: {metrics['avg_delay_p1_critical']:.3f} s)")
    print(f"  • P2 (Non-Crit) Avg Wait Time   : {metrics['avg_waiting_time_p2_non_critical']:.3f} s  (Delay: {metrics['avg_delay_p2_non_critical']:.3f} s)")
    print(f"  • P3 (Normal) Avg Wait Time     : {metrics['avg_waiting_time_p3_normal']:.3f} s  (Delay: {metrics['avg_delay_p3_normal']:.3f} s)")
    print(f"  • Network Throughput            : {metrics['throughput_msgs_per_sec']:.3f} msgs/s")
    print(f"  • Transmission Order (Msg IDs)  : {metrics['transmission_order']}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    print("\n--- CNS MINOR PROJECT: EMERGENCY MESSAGE SCHEDULING SIMULATION ---")
    
    # 1. Exact User Example: Simultaneous Arrival at t = 0.0
    print("\n>>> TEST 1: SIMULTANEOUS ARRIVAL (Exact Prompt Example)")
    print("    All 3 messages arrive at time t = 0.0s simultaneously:")
    print("      • Message 1: Normal User (Priority 3)")
    print("      • Message 2: Ambulance Critical (Priority 1)")
    print("      • Message 3: Ambulance Non-Critical (Priority 2)")
    print("    Expected Priority Transmission Order: Message 2 -> Message 3 -> Message 1\n")
    simultaneous_msgs = [
        Message.create(message_id=1, source_type="Normal User", emergency_level="None", arrival_time=0.0, transmission_time=1.0),
        Message.create(message_id=2, source_type="Ambulance", emergency_level="Critical", arrival_time=0.0, transmission_time=1.0),
        Message.create(message_id=3, source_type="Ambulance", emergency_level="Non-critical", arrival_time=0.0, transmission_time=1.0),
    ]

    fifo_sim, prio_sim, fifo_sim_met, prio_sim_met = compare_scheduling_methods(simultaneous_msgs)
    print_simulation_report("Method 1: FIFO Scheduling (Simultaneous Arrival)", fifo_sim, fifo_sim_met)
    print_simulation_report("Method 2: Priority-Based Scheduling (Simultaneous Arrival)", prio_sim, prio_sim_met)

    # 2. Dynamic/Staggered Arrival Scenario
    print("\n>>> TEST 2: STAGGERED ARRIVAL (Non-preemptive channel test)")
    print("    Normal user starts transmitting at t=0.0, Emergency messages arrive mid-transmission.")
    staggered_msgs = [
        Message.create(message_id=1, source_type="Normal User", emergency_level="None", arrival_time=0.0, transmission_time=1.0),
        Message.create(message_id=2, source_type="Ambulance", emergency_level="Critical", arrival_time=0.1, transmission_time=1.0),
        Message.create(message_id=3, source_type="Ambulance", emergency_level="Non-critical", arrival_time=0.2, transmission_time=1.0),
    ]
    fifo_stg, prio_stg, fifo_stg_met, prio_stg_met = compare_scheduling_methods(staggered_msgs)
    print_simulation_report("Method 1: FIFO Scheduling (Staggered Arrival)", fifo_stg, fifo_stg_met)
    print_simulation_report("Method 2: Priority-Based Scheduling (Staggered Arrival)", prio_stg, prio_stg_met)

    # 3. Multi-Message Traffic Simulation
    print("\n>>> TEST 3: REALISTIC MULTI-MESSAGE NETWORK SIMULATION (10 Packets)")
    random_dataset = generate_random_traffic(num_messages=10, seed=101, arrival_window=8.0)
    fifo_rnd, prio_rnd, fifo_rnd_met, prio_rnd_met = compare_scheduling_methods(random_dataset)
    print_simulation_report("Method 1: FIFO Scheduling (10 Packets)", fifo_rnd, fifo_rnd_met)
    print_simulation_report("Method 2: Priority Scheduling (10 Packets)", prio_rnd, prio_rnd_met)
