"""
Message Data Structure Module
Course: Communication and Network Systems (CNS)
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Message:
    """
    Represents a discrete communication packet in the network.
    
    Attributes:
        message_id: Unique integer identifier.
        source_type: "Normal User" or "Ambulance".
        emergency_level: "Critical", "Non-critical", or "None".
        priority: 1 (Critical Ambulance), 2 (Non-critical Ambulance), 3 (Normal User).
        arrival_time: Timestamp (seconds) when packet arrives at the node.
        transmission_time: Physical transmission duration over the channel.
        start_time: Timestamp when transmission begins on the channel.
        waiting_time: Queuing delay (start_time - arrival_time).
        completion_time: Timestamp when transmission finishes (start_time + transmission_time).
        status: Delivery status from the physical channel ("DELIVERED" or "LOST").
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
    status: str = "DELIVERED"

    @classmethod
    def create(
        cls,
        message_id: int,
        source_type: str,
        emergency_level: str = "None",
        arrival_time: float = 0.0,
        transmission_time: float = 1.0,
        priority: Optional[int] = None,
    ) -> "Message":
        """
        Factory method that maps source and emergency level to priority:
          - Ambulance + Critical     -> Priority 1
          - Ambulance + Non-critical -> Priority 2
          - Normal User              -> Priority 3
        """
        if priority is None:
            if source_type == "Ambulance" and emergency_level == "Critical":
                priority = 1
            elif source_type == "Ambulance" and emergency_level == "Non-critical":
                priority = 2
            else:
                priority = 3

        return cls(
            message_id=message_id,
            source_type=source_type,
            emergency_level=emergency_level,
            priority=priority,
            arrival_time=round(arrival_time, 2),
            transmission_time=round(transmission_time, 2),
        )
