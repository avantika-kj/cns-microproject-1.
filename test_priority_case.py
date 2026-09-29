"""
Dedicated Test Case for Priority-Based Emergency Message Scheduling
Course: Communication and Network Systems (CNS)

Test Scenario:
  M1 -> Normal User
  M2 -> Ambulance, Critical
  M3 -> Ambulance, Non-critical
  M4 -> Normal User
  M5 -> Ambulance, Critical

All messages arrive at approximately the same time (t = 0.0s).
Arrival order for tie-breaking: M1 -> M2 -> M3 -> M4 -> M5

Expected Priorities:
  M2, M5 -> Priority 1 (Critical Ambulance)
  M3     -> Priority 2 (Non-critical Ambulance)
  M1, M4 -> Priority 3 (Normal User)

Expected Transmission Order:
  M2 (P1, arrived first) -> M5 (P1, arrived second) -> M3 (P2) -> M1 (P3, arrived first) -> M4 (P3, arrived second)
"""

from simulation_engine import Message, simulate_priority


def run_priority_test():
    # All 5 messages arrive at the same time (t = 0.0s)
    # Their arrival order is M1, M2, M3, M4, M5 (captured by arrival_time=0.0 and message_id)
    messages = [
        Message.create(message_id=1, source_type="Normal User", emergency_level="None", arrival_time=0.0, transmission_time=1.0),
        Message.create(message_id=2, source_type="Ambulance", emergency_level="Critical", arrival_time=0.0, transmission_time=1.0),
        Message.create(message_id=3, source_type="Ambulance", emergency_level="Non-critical", arrival_time=0.0, transmission_time=1.0),
        Message.create(message_id=4, source_type="Normal User", emergency_level="None", arrival_time=0.0, transmission_time=1.0),
        Message.create(message_id=5, source_type="Ambulance", emergency_level="Critical", arrival_time=0.0, transmission_time=1.0),
    ]

    print("=" * 75)
    print(" INPUT MESSAGES (ARRIVING AT APPROXIMATELY THE SAME TIME)")
    print("=" * 75)
    print(f"{'Message ID':<15}{'Source':<18}{'Emergency Level':<18}{'Priority':<12}{'Arrival Time':<12}")
    print("-" * 75)
    for m in messages:
        print(f"M{m.message_id:<14}{m.source_type:<18}{m.emergency_level:<18}Priority {m.priority:<4}{m.arrival_time:<12.3f}s")
    print("=" * 75)

    # Run the Priority Scheduler
    scheduled_messages = simulate_priority(messages)

    print("\n" + "=" * 75)
    print(" OUTPUT: TRANSMISSION RESULTS FROM PRIORITY SCHEDULER")
    print("=" * 75)
    print(f"{'Tx Order':<12}{'Message ID':<15}{'Source':<18}{'Emergency Level':<18}{'Priority':<12}")
    print("-" * 75)

    for order_idx, m in enumerate(scheduled_messages, start=1):
        print(f"{order_idx:<12}M{m.message_id:<14}{m.source_type:<18}{m.emergency_level:<18}Priority {m.priority:<4}")
    print("=" * 75)

    # Programmatic Verification of Priority Order and Tie-Breaking
    actual_order = [m.message_id for m in scheduled_messages]
    expected_order = [2, 5, 3, 1, 4]
    
    print("\n>>> VERIFICATION CHECK:")
    print(f"  • Expected Transmission Order : {[f'M{i}' for i in expected_order]}")
    print(f"  • Actual Transmission Order   : {[f'M{i}' for i in actual_order]}")

    # Check 1: All P1 before P2, and all P2 before P3
    priority_sequence = [m.priority for m in scheduled_messages]
    is_non_decreasing_priority = priority_sequence == sorted(priority_sequence)
    
    # Check 2: Tie breaking for P1 (M2 before M5)
    p1_tie_break_ok = actual_order.index(2) < actual_order.index(5)
    
    # Check 3: Tie breaking for P3 (M1 before M4)
    p3_tie_break_ok = actual_order.index(1) < actual_order.index(4)

    # Check 4: Exact match with expected sequence
    exact_match = (actual_order == expected_order)

    print(f"\n  [✓] All Priority 1 messages transmitted before Priority 2 : {priority_sequence.index(2) > priority_sequence.index(1)}")
    print(f"  [✓] Priority 2 message transmitted before Priority 3      : {priority_sequence.index(3) > priority_sequence.index(2)}")
    print(f"  [✓] Tie-breaker for Priority 1 (M2 before M5)             : {p1_tie_break_ok}")
    print(f"  [✓] Tie-breaker for Priority 3 (M1 before M4)             : {p3_tie_break_ok}")
    print(f"  [✓] Overall Priority & Order Verification Status           : {'PASSED (SUCCESS)' if exact_match else 'FAILED'}")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    run_priority_test()
