"""
Discrete-Event Simulation (DES) for Communication Channel Scheduling
Course: Communication and Network Systems (CNS)

A formal Discrete-Event Simulator modeling:
  1. System Clock: Advances discretely to the next scheduled event time.
  2. Single Shared Communication Channel: States are IDLE or BUSY.
  3. Waiting Queue: Holds packets arriving while channel is busy.
     - In FIFO mode: Queue pops earliest arrival first.
     - In Priority mode: Queue pops highest priority (P1 > P2 > P3; tie-break: earliest arrival).
  4. Events:
     - ARRIVAL: A message reaches the network node.
     - COMPLETION: The currently transmitting message finishes and leaves the channel.
"""

from dataclasses import dataclass, field
import heapq
import copy
from typing import List, Dict, Any, Optional
from simulation_engine import Message


# ============================================================================
# 1. EVENT DEFINITION & PRIORITY QUEUE FOR DISCRETE EVENTS
# ============================================================================

@dataclass(order=True)
class Event:
    """
    Represents an event scheduled on the simulation timeline.
    Ordered by event timestamp so the simulation clock always jumps
    to the next chronologically occurring event.
    """
    time: float
    event_type: str = field(compare=False)  # "ARRIVAL" or "COMPLETION"
    message: Message = field(compare=False)


# ============================================================================
# 2. DISCRETE-EVENT SIMULATOR ENGINE
# ============================================================================

class CommunicationChannelDES:
    """
    Discrete-Event Simulator representing a single shared transmission channel
    and a buffer queue.
    """

    def __init__(self, mode: str = "PRIORITY"):
        """
        mode: "FIFO" or "PRIORITY"
        """
        assert mode in ("FIFO", "PRIORITY"), "Mode must be either 'FIFO' or 'PRIORITY'"
        self.mode = mode
        
        # State variables
        self.current_time: float = 0.0
        self.channel_busy: bool = False
        self.transmitting_message: Optional[Message] = None
        
        # Event calendar (min-heap of scheduled events)
        self.event_queue: List[Event] = []
        
        # Buffer queue for messages waiting while channel is busy
        self.waiting_queue: List[Message] = []
        
        # Records
        self.completed_messages: List[Message] = []
        self.event_log: List[str] = []

    def log(self, message_str: str):
        """Appends a timestamped entry to the event log."""
        entry = f"[{self.current_time:6.2f}s] {message_str}"
        self.event_log.append(entry)

    def select_next_message_from_queue(self) -> Message:
        """
        Scheduler selection logic:
          - FIFO: Selects message that arrived earliest.
          - PRIORITY: Selects lowest priority value (P1 > P2 > P3).
                      Tie-breaker: earliest arrival time.
        """
        if self.mode == "FIFO":
            # Earliest arrival time first
            self.waiting_queue.sort(key=lambda m: (m.arrival_time, m.message_id))
            return self.waiting_queue.pop(0)
        else:
            # Lowest priority number (P1=1, P2=2, P3=3), then earliest arrival
            self.waiting_queue.sort(key=lambda m: (m.priority, m.arrival_time, m.message_id))
            return self.waiting_queue.pop(0)

    def start_transmission(self, msg: Message):
        """
        Assigns the channel to a message and schedules its COMPLETION event.
        """
        self.channel_busy = True
        self.transmitting_message = msg
        msg.start_time = self.current_time
        msg.waiting_time = round(msg.start_time - msg.arrival_time, 3)
        msg.completion_time = round(self.current_time + msg.transmission_time, 3)

        self.log(
            f"CHANNEL OCCUPIED : M{msg.message_id} ({msg.source_type}, P{msg.priority}) "
            f"begins transmission. Duration: {msg.transmission_time:.2f}s, Finishes at t={msg.completion_time:.2f}s"
        )

        # Schedule COMPLETION event
        completion_event = Event(time=msg.completion_time, event_type="COMPLETION", message=msg)
        heapq.heappush(self.event_queue, completion_event)

    def handle_arrival(self, msg: Message):
        """
        Handles the ARRIVAL of a new message at the node.
        """
        self.log(f"MESSAGE ARRIVED : M{msg.message_id} ({msg.source_type} - {msg.emergency_level}, P{msg.priority})")

        if not self.channel_busy:
            # Channel is free -> transmit immediately without entering queue
            self.log(f"CHANNEL STATUS   : IDLE. M{msg.message_id} immediately accesses the channel.")
            self.start_transmission(msg)
        else:
            # Channel is occupied -> message must wait in the buffer queue
            self.waiting_queue.append(msg)
            queue_contents = [f"M{m.message_id}(P{m.priority})" for m in self.waiting_queue]
            self.log(
                f"CHANNEL STATUS   : BUSY transmitting M{self.transmitting_message.message_id}. "
                f"M{msg.message_id} ENTERS QUEUE. Queue={queue_contents}"
            )

    def handle_completion(self, msg: Message):
        """
        Handles the COMPLETION of message transmission over the channel.
        """
        self.log(
            f"TRANSMISSION END : M{msg.message_id} successfully sent! "
            f"Wait={msg.waiting_time:.2f}s, Total Delay={msg.completion_time - msg.arrival_time:.2f}s"
        )
        self.completed_messages.append(msg)
        self.channel_busy = False
        self.transmitting_message = None

        # Check if any messages are waiting in queue
        if self.waiting_queue:
            queue_contents = [f"M{m.message_id}(P{m.priority})" for m in self.waiting_queue]
            self.log(f"CHANNEL FREE     : Scheduler inspecting queue {queue_contents} under {self.mode} policy.")
            
            # Scheduler selects next message according to active policy
            next_msg = self.select_next_message_from_queue()
            self.log(f"SCHEDULER PICKED : M{next_msg.message_id} (Priority {next_msg.priority}) selected for channel.")
            
            self.start_transmission(next_msg)
        else:
            self.log("CHANNEL IDLE     : Waiting queue is empty. Channel is now listening for arrivals.")

    def run_simulation(self, messages: List[Message]) -> List[Message]:
        """
        Initializes the event queue with all message arrival events and executes
        the discrete-event simulation loop until all events and queues clear.
        """
        # Reset state
        self.current_time = 0.0
        self.channel_busy = False
        self.transmitting_message = None
        self.event_queue.clear()
        self.waiting_queue.clear()
        self.completed_messages.clear()
        self.event_log.clear()

        # Seed initial arrivals into event calendar
        for msg in messages:
            arrival_event = Event(time=msg.arrival_time, event_type="ARRIVAL", message=copy.deepcopy(msg))
            heapq.heappush(self.event_queue, arrival_event)

        self.log(f"--- SIMULATION STARTED (Policy: {self.mode}) ---")

        # Main discrete-event loop
        while self.event_queue:
            # Advance simulation clock directly to next scheduled event
            current_event = heapq.heappop(self.event_queue)
            self.current_time = current_event.time

            if current_event.event_type == "ARRIVAL":
                self.handle_arrival(current_event.message)
            elif current_event.event_type == "COMPLETION":
                self.handle_completion(current_event.message)

        self.log("--- SIMULATION COMPLETED ---")
        return self.completed_messages


# ============================================================================
# 3. DEMONSTRATION & COMPARATIVE EVENT TRACE
# ============================================================================

def run_discrete_event_comparison():
    """
    Runs a realistic dynamic scenario where messages arrive while the channel
    is busy, illustrating step-by-step queue entry and scheduler decisions.
    """
    # Realistic CNS Scenario:
    # M1 arrives at 0.0s (Normal User, Tx = 1.0s) -> Channel busy until 1.0s.
    # While channel is busy:
    #   - M2 arrives at 0.2s (Ambulance Critical, P1, Tx = 1.0s) -> Enters queue
    #   - M3 arrives at 0.4s (Ambulance Non-critical, P2, Tx = 1.0s) -> Enters queue
    #   - M4 arrives at 0.6s (Normal User, P3, Tx = 1.0s) -> Enters queue
    #   - M5 arrives at 0.8s (Ambulance Critical, P1, Tx = 1.0s) -> Enters queue
    scenario_messages = [
        Message.create(message_id=1, source_type="Normal User", emergency_level="None", arrival_time=0.0, transmission_time=1.0),
        Message.create(message_id=2, source_type="Ambulance", emergency_level="Critical", arrival_time=0.2, transmission_time=1.0),
        Message.create(message_id=3, source_type="Ambulance", emergency_level="Non-critical", arrival_time=0.4, transmission_time=1.0),
        Message.create(message_id=4, source_type="Normal User", emergency_level="None", arrival_time=0.6, transmission_time=1.0),
        Message.create(message_id=5, source_type="Ambulance", emergency_level="Critical", arrival_time=0.8, transmission_time=1.0),
    ]

    print("=" * 80)
    print(" DISCRETE-EVENT SIMULATION: STEP-BY-STEP REALISTIC QUEUE TRACE")
    print("=" * 80)

    # 1. Run FIFO Mode
    fifo_sim = CommunicationChannelDES(mode="FIFO")
    fifo_results = fifo_sim.run_simulation(scenario_messages)

    print("\n" + "#" * 80)
    print(" 1. FIFO MODE EVENT-BY-EVENT TIMELINE")
    print("#" * 80)
    for entry in fifo_sim.event_log:
        print(entry)

    # 2. Run Priority Mode
    prio_sim = CommunicationChannelDES(mode="PRIORITY")
    prio_results = prio_sim.run_simulation(scenario_messages)

    print("\n" + "#" * 80)
    print(" 2. PRIORITY MODE EVENT-BY-EVENT TIMELINE")
    print("#" * 80)
    for entry in prio_sim.event_log:
        print(entry)

    # Summary
    print("\n" + "=" * 80)
    print(" SUMMARY COMPARISON OF TRANSMISSION SEQUENCE")
    print("=" * 80)
    print(f"FIFO Transmission Order     : {[f'M{m.message_id}' for m in fifo_results]}")
    print(f"Priority Transmission Order : {[f'M{m.message_id}' for m in prio_results]}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_discrete_event_comparison()
