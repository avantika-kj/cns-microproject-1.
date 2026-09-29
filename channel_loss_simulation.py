"""
Communication Channel Packet Loss Simulation Module
Course: Communication and Network Systems (CNS)

NOTE:
This is a SIMULATED channel error model representing stochastic channel noise,
signal fading, or interference over an RF physical link. It is NOT a real-world
physical network measurement.

Channel Rules:
  - Physical channel transmission can suffer frame error with probability P_loss (e.g., 0%, 2%, 5%, 10%).
  - Packet loss is INDEPENDENT of message priority (the physical medium does not discriminate
    channel noise based on header priority).
  - Both FIFO and Priority scheduling are evaluated under the EXACT SAME channel conditions.
"""

from dataclasses import dataclass, field
import heapq
import random
import copy
from typing import List, Dict, Any, Tuple
from simulation_engine import Message


# ============================================================================
# 1. MESSAGE WITH TRANSMISSION STATUS
# ============================================================================

@dataclass
class ChannelMessage:
    """
    Message wrapper including delivery status from the physical channel.
    Status: "DELIVERED" or "LOST"
    """
    message_id: int
    source_type: str
    emergency_level: str
    priority: int
    arrival_time: float
    transmission_time: float
    start_time: float = 0.0
    waiting_time: float = 0.0
    completion_time: float = 0.0
    status: str = "DELIVERED"  # "DELIVERED" or "LOST"


# ============================================================================
# 2. DISCRETE-EVENT SIMULATION WITH CHANNEL LOSS
# ============================================================================

class LossyChannelDES:
    """
    Discrete-Event Simulator with an integrated stochastic packet loss model.
    """
    def __init__(self, mode: str = "PRIORITY", loss_probability: float = 0.05, seed: int = 42):
        assert mode in ("FIFO", "PRIORITY"), "Mode must be 'FIFO' or 'PRIORITY'"
        assert 0.0 <= loss_probability <= 1.0, "loss_probability must be between 0.0 and 1.0"
        
        self.mode = mode
        self.loss_probability = loss_probability
        self.seed = seed
        self.rng = random.Random(seed)

        self.current_time = 0.0
        self.channel_busy = False
        self.waiting_queue: List[ChannelMessage] = []
        self.processed_messages: List[ChannelMessage] = []

    def run(self, input_messages: List[Message], channel_loss_map: Dict[int, bool] = None) -> List[ChannelMessage]:
        """
        Runs the simulation.
        If channel_loss_map is provided (mapping message_id -> is_lost),
        it ensures identical channel outcomes across different scheduling methods.
        """
        self.current_time = 0.0
        self.channel_busy = False
        self.waiting_queue.clear()
        self.processed_messages.clear()

        # Convert to ChannelMessage objects
        msgs = [
            ChannelMessage(
                message_id=m.message_id,
                source_type=m.source_type,
                emergency_level=m.emergency_level,
                priority=m.priority,
                arrival_time=m.arrival_time,
                transmission_time=m.transmission_time,
            )
            for m in copy.deepcopy(input_messages)
        ]

        # Chronological arrival sequence
        unprocessed = sorted(msgs, key=lambda m: (m.arrival_time, m.message_id))
        idx = 0
        total_msgs = len(unprocessed)
        channel_free_time = 0.0

        while idx < total_msgs or self.waiting_queue:
            # Advance time if channel is idle and queue is empty
            if not self.waiting_queue and channel_free_time <= unprocessed[idx].arrival_time:
                channel_free_time = unprocessed[idx].arrival_time

            # Enqueue all messages that have arrived by channel_free_time
            while idx < total_msgs and unprocessed[idx].arrival_time <= channel_free_time:
                self.waiting_queue.append(unprocessed[idx])
                idx += 1

            if self.waiting_queue:
                # Scheduler selects next packet
                if self.mode == "FIFO":
                    # Earliest arrival time
                    self.waiting_queue.sort(key=lambda m: (m.arrival_time, m.message_id))
                else:
                    # Lowest priority number, tie-breaker: earliest arrival time
                    self.waiting_queue.sort(key=lambda m: (m.priority, m.arrival_time, m.message_id))

                msg = self.waiting_queue.pop(0)

                # Channel transmission calculations
                start_time = max(channel_free_time, msg.arrival_time)
                waiting_time = start_time - msg.arrival_time
                completion_time = start_time + msg.transmission_time

                msg.start_time = round(start_time, 3)
                msg.waiting_time = round(waiting_time, 3)
                msg.completion_time = round(completion_time, 3)

                # Channel Loss Decision:
                # If channel_loss_map is provided, use the predetermined outcome;
                # otherwise evaluate stochastic Bernoulli trial.
                if channel_loss_map is not None:
                    is_lost = channel_loss_map.get(msg.message_id, False)
                else:
                    is_lost = (self.rng.random() < self.loss_probability)

                msg.status = "LOST" if is_lost else "DELIVERED"

                channel_free_time = completion_time
                self.processed_messages.append(msg)

        return self.processed_messages


# ============================================================================
# 3. LOSS & RELIABILITY METRICS CALCULATION
# ============================================================================

def calculate_loss_metrics(messages: List[ChannelMessage]) -> Dict[str, Any]:
    """
    Computes packet loss and reliability metrics:
      - Total messages generated
      - Total successfully transmitted (DELIVERED)
      - Total lost
      - Packet loss rate (%)
      - Successfully delivered ambulance messages
      - Successfully delivered normal-user messages
    """
    total_generated = len(messages)
    delivered = [m for m in messages if m.status == "DELIVERED"]
    lost = [m for m in messages if m.status == "LOST"]

    loss_rate_pct = (len(lost) / total_generated * 100.0) if total_generated > 0 else 0.0

    # Ambulance deliveries (P1 and P2)
    ambulance_delivered = [m for m in delivered if m.source_type == "Ambulance"]
    critical_ambulance_delivered = [m for m in delivered if m.priority == 1]
    non_critical_ambulance_delivered = [m for m in delivered if m.priority == 2]

    # Normal user deliveries (P3)
    normal_delivered = [m for m in delivered if m.source_type == "Normal User"]

    # Latencies of successfully delivered messages
    delivered_waits = [m.waiting_time for m in delivered]
    avg_delivered_wait = (sum(delivered_waits) / len(delivered_waits)) if delivered_waits else 0.0

    p1_delivered = [m for m in delivered if m.priority == 1]
    p1_avg_wait = (sum(m.waiting_time for m in p1_delivered) / len(p1_delivered)) if p1_delivered else 0.0

    return {
        "total_generated": total_generated,
        "total_delivered": len(delivered),
        "total_lost": len(lost),
        "loss_rate_percent": round(loss_rate_pct, 2),
        "delivered_ambulance_total": len(ambulance_delivered),
        "delivered_critical_ambulance": len(critical_ambulance_delivered),
        "delivered_non_critical_ambulance": len(non_critical_ambulance_delivered),
        "delivered_normal_user": len(normal_delivered),
        "avg_delivered_waiting_time": round(avg_delivered_wait, 3),
        "p1_critical_avg_waiting_time": round(p1_avg_wait, 3),
        "transmission_order": [f"M{m.message_id}({m.status})" for m in messages],
    }


def run_comparative_loss_experiment(
    input_messages: List[Message],
    loss_probability: float,
    seed: int = 101,
) -> Dict[str, Any]:
    """
    Runs both FIFO and Priority scheduling under the EXACT SAME channel loss conditions.
    To ensure scientific fairness, channel loss trials are synchronized across both runs.
    """
    # Pre-generate channel loss map for all message IDs using a fixed seed
    # This guarantees that if Message #3 suffers channel fading in FIFO,
    # it experiences the exact same channel fading in Priority.
    rng = random.Random(seed)
    channel_loss_map = {
        m.message_id: (rng.random() < loss_probability)
        for m in input_messages
    }

    # Run FIFO Simulator
    fifo_sim = LossyChannelDES(mode="FIFO", loss_probability=loss_probability)
    fifo_results = fifo_sim.run(input_messages, channel_loss_map=channel_loss_map)
    fifo_metrics = calculate_loss_metrics(fifo_results)

    # Run Priority Simulator
    priority_sim = LossyChannelDES(mode="PRIORITY", loss_probability=loss_probability)
    priority_results = priority_sim.run(input_messages, channel_loss_map=channel_loss_map)
    priority_metrics = calculate_loss_metrics(priority_results)

    return {
        "loss_probability_setting": loss_probability,
        "fifo": {
            "metrics": fifo_metrics,
            "messages": fifo_results,
        },
        "priority": {
            "metrics": priority_metrics,
            "messages": priority_results,
        },
    }


# ============================================================================
# 4. DEMO RUNNER: MULTIPLE LOSS PROBABILITIES (0%, 2%, 5%, 10%)
# ============================================================================

def print_loss_comparison_table(experiment_output: Dict[str, Any]):
    """Prints a clear side-by-side terminal report comparing FIFO and Priority under loss."""
    p_loss = experiment_output["loss_probability_setting"]
    f_met = experiment_output["fifo"]["metrics"]
    p_met = experiment_output["priority"]["metrics"]

    print("=" * 86)
    print(f" SIMULATED CHANNEL LOSS EXPERIMENT: P(Loss) = {p_loss * 100:.1f}%")
    print(" (Note: Simulated RF channel fading model. Does not reflect physical lab instruments.)")
    print("=" * 86)
    print(f"{'Metric':<46} | {'FIFO Mode':<16} | {'Priority Mode':<18}")
    print("-" * 86)

    rows = [
        ("Total Messages Generated", str(f_met["total_generated"]), str(p_met["total_generated"])),
        ("Total Successfully Delivered", str(f_met["total_delivered"]), str(p_met["total_delivered"])),
        ("Total Lost / Corrupted", str(f_met["total_lost"]), str(p_met["total_lost"])),
        ("Observed Packet Loss Rate", f"{f_met['loss_rate_percent']:.1f}%", f"{p_met['loss_rate_percent']:.1f}%"),
        ("Delivered Ambulance Messages (All)", str(f_met["delivered_ambulance_total"]), str(p_met["delivered_ambulance_total"])),
        ("  ↳ Critical Ambulance (P1) Delivered", str(f_met["delivered_critical_ambulance"]), str(p_met["delivered_critical_ambulance"])),
        ("  ↳ Non-Critical Ambulance (P2) Delivered", str(f_met["delivered_non_critical_ambulance"]), str(p_met["delivered_non_critical_ambulance"])),
        ("Delivered Normal-User Messages (P3)", str(f_met["delivered_normal_user"]), str(p_met["delivered_normal_user"])),
        ("P1 Critical Avg Waiting Time (Delivered)", f"{f_met['p1_critical_avg_waiting_time']:.3f} s", f"{p_met['p1_critical_avg_waiting_time']:.3f} s"),
        ("Overall Avg Waiting Time (Delivered)", f"{f_met['avg_delivered_waiting_time']:.3f} s", f"{p_met['avg_delivered_waiting_time']:.3f} s"),
    ]

    for label, fifo_val, prio_val in rows:
        print(f"{label:<46} | {fifo_val:<16} | {prio_val:<18}")

    print("=" * 86 + "\n")


if __name__ == "__main__":
    print("\n--- CNS PROJECT: SIMULATED CHANNEL PACKET LOSS ANALYSIS ---")
    
    # Generate a realistic 50-message workload for clear statistical representation
    from simulation_engine import generate_random_traffic
    workload = generate_random_traffic(
        num_messages=50,
        seed=101,
        ambulance_ratio=0.40,
        critical_ratio=0.50,
        arrival_window=25.0,
        min_tx_time=0.8,
        max_tx_time=1.2,
    )

    # Test across multiple loss probabilities: 0%, 2%, 5%, 10%
    loss_scenarios = [0.00, 0.02, 0.05, 0.10]

    for p in loss_scenarios:
        res = run_comparative_loss_experiment(workload, loss_probability=p, seed=2026)
        print_loss_comparison_table(res)
