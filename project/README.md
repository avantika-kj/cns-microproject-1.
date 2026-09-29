# Priority-Based Emergency Message Scheduling in a Communication Network

**Course:** Communication and Network Systems (CNS) — Minor Project  
**Author:** 3rd Year B.Tech Computer Science & Engineering

---

## 1. Project Overview

In a shared communication network, normal users and emergency ambulances contend for the exact same transmission medium. 

Under standard **FIFO (First-In, First-Out)** scheduling, critical ambulance telemetry can be stuck in a buffer queue behind long, non-critical user packets. This project implements a **3-tier Priority Queueing system**:
- 🔴 **Priority 1 (Critical Ambulance):** Patient vitals, cardiac alerts, stroke notifications.
- 🟡 **Priority 2 (Non-critical Ambulance):** Routine vehicular status, GPS updates, logistics.
- 🔵 **Priority 3 (Normal User):** Standard background web traffic.

---

## 2. Directory Structure

```text
project/
│
├── app.py              # Streamlit web application & visual dashboard
├── simulation.py       # Discrete-event simulation engine & traffic generator
├── scheduler.py        # FIFO and Priority queue dispatching algorithms
├── message.py          # Message dataclass & priority assignment factory
├── metrics.py          # Network QoS and queueing performance calculations
├── requirements.txt    # Required Python dependencies (streamlit, pandas)
└── README.md           # Installation, execution instructions, & documentation
```

### Module Responsibilities:
- **`message.py`**: Defines the `Message` data structure with fields (`message_id`, `source_type`, `emergency_level`, `priority`, `arrival_time`, `transmission_time`, `waiting_time`, `completion_time`, `status`).
- **`scheduler.py`**: Contains the scheduling selection functions (`select_fifo_message` and `select_priority_message`). No duplicate logic across files.
- **`simulation.py`**: Manages the single shared communication channel, timeline clock, buffer queues, and simulated physical channel packet loss.
- **`metrics.py`**: Computes average waiting time, turnaround delay, channel throughput, packet loss rate, and class-specific metrics.
- **`app.py`**: The Streamlit user interface featuring interactive controls, visual timelines, and comparative plots.

---

## 3. Installation and Setup

### Prerequisites
- Python 3.8 or higher
- `pip` package manager

### Step 1: Navigate to the project directory
```bash
cd project
```

### Step 2: Install required packages
```bash
pip install -r requirements.txt
```

---

## 4. How to Run the Project

Launch the Streamlit web dashboard with a single command:
```bash
streamlit run app.py
```

Once executed, open your browser at `http://localhost:8501`.

---

## 5. End-to-End System Block Diagram

```text
       ┌─────────────────┐
       │  Normal Users   │
       └────────┬────────┘
                │
                │
       ┌────────▼────────┐
       │    Ambulance    │
       │     Users       │
       └────────┬────────┘
                │
                ▼
      ┌─────────────────────┐
      │ Message Classifier  │
      └──────────┬──────────┘
                 │
                 ▼
      ┌─────────────────────┐
      │ Priority Assignment │
      │                     │
      │ P1 Critical         │
      │ P2 Non-critical     │
      │ P3 Normal           │
      └──────────┬──────────┘
                 │
                 ▼
      ┌─────────────────────┐
      │   Priority Queue    │
      └──────────┬──────────┘
                 │
                 ▼
      ┌─────────────────────┐
      │     Scheduler       │
      └──────────┬──────────┘
                 │
                 ▼
      ┌─────────────────────┐
      │ Shared Communication│
      │      Channel        │
      └──────────┬──────────┘
                 │
                 ▼
      ┌─────────────────────┐
      │   Hospital Server   │
      └─────────────────────┘
```

---

## 6. Predefined Network Load Experiments

The application provides three controlled experiments:
1. **Low Network Load:** 8 messages over 20 seconds (utilization $\rho \approx 0.40$).
2. **Medium Network Load:** 15 messages over 15 seconds (utilization $\rho \approx 1.00$).
3. **High Network Load:** 25 messages over 12 seconds (heavy congestion, arrival rate exceeds channel capacity).

Both FIFO and Priority modes evaluate the **exact same message arrivals and channel conditions** to ensure rigorous, objective comparison.
