"""
Message Data Structure Module
Course: Communication and Network Systems (CNS)
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Message:
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
