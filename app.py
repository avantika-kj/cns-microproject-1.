"""
Priority-Based Emergency Message Scheduling in a Communication Network
Course: Communication and Network Systems (CNS) - Minor Project
Streamlit Web Application

To execute:
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import random
from typing import List, Dict, Any

from message import Message
from scheduler import schedule_next_message
from simulation import generate_messages, simulate_channel
from metrics import calculate_metrics


# Set Matplotlib style
plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams.update({
    "font.size": 9,
    "figure.titlesize": 11,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "figure.autolayout": True,
})


# ============================================================================
# STREAMLIT USER INTERFACE
# ============================================================================

st.set_page_config(
    page_title="Emergency Message Scheduling Simulator",
    layout="wide",
)

st.title("Priority-Based Emergency Message Scheduling in a Communication Network")
st.markdown(
    """
    **CNS Minor Project - Shared Communication Channel Simulation**  
    A single shared communication channel serves both regular users and emergency ambulances.
    When network traffic contends for channel access, the scheduler enforces strict Quality of Service (QoS):
    - 🔴 **Priority 1 (Critical Ambulance):** Immediate transmission access for life-critical telemetry.
    - 🟡 **Priority 2 (Non-critical Ambulance):** Secondary transmission priority.
    - 🔵 **Priority 3 (Normal User):** Best-effort background web traffic.
    """
)

# Section 1: End-to-End System Block Diagram
with st.expander("📌 End-to-End System Architecture (8 Stages)", expanded=True):
    st.code(
        """
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
        """,
        language="text",
    )
st.divider()

# Navigation Tabs
tab_interactive, tab_experiments = st.tabs([
    "🕹️ Interactive Live Simulator",
    "📊 Predefined Load Experiments (Low, Medium, High Load)"
])


# ============================================================================
# TAB 1: INTERACTIVE SIMULATOR (SECTIONS 1 TO 5)
# ============================================================================
with tab_interactive:
    # Sidebar Controls
    st.sidebar.title("Simulation Parameters")
    st.sidebar.markdown("Configure shared physical channel and traffic generation:")

    num_messages = st.sidebar.slider("1. Number of Messages", min_value=5, max_value=35, value=12, step=1)
    sim_duration = st.sidebar.slider("2. Simulation Duration (s)", min_value=3.0, max_value=25.0, value=10.0, step=1.0)
    channel_tx_time = st.sidebar.slider("3. Channel Transmission Time (s)", min_value=0.5, max_value=2.0, value=1.0, step=0.1)

    loss_prob_pct = st.sidebar.selectbox("4. Packet Loss Probability", options=[0, 2, 5, 10], index=1)
    loss_prob = loss_prob_pct / 100.0

    seed = st.sidebar.number_input("5. Random Seed", min_value=1, max_value=9999, value=42, step=1)

    scheduling_mode = st.sidebar.radio(
        "6. Scheduling Mode",
        options=["FIFO", "Priority", "Compare Both"],
        index=2
    )

    # 1. Message Generation
    raw_messages = generate_messages(
        num_messages=num_messages,
        simulation_duration=sim_duration,
        channel_tx_time=channel_tx_time,
        seed=seed,
    )

    # Deterministic channel fading map
    loss_rng = random.Random(seed + 999)
    channel_loss_map = {m.message_id: (loss_rng.random() < loss_prob) for m in raw_messages}

    # 2. Run Simulations
    fifo_results = simulate_channel(raw_messages, mode="FIFO", loss_probability=loss_prob, channel_loss_map=channel_loss_map)
    priority_results = simulate_channel(raw_messages, mode="PRIORITY", loss_probability=loss_prob, channel_loss_map=channel_loss_map)

    # 3. Calculate Performance Metrics
    fifo_metrics = calculate_metrics(fifo_results)
    priority_metrics = calculate_metrics(priority_results)

    # SECTION 2: GENERATED MESSAGES TABLE
    st.subheader("Section 2: Generated Messages Table")
    st.caption("Messages generated across nodes with arrival timestamps and priority classes.")
    df_gen = pd.DataFrame([
        {
            "Message ID": f"M{m.message_id}",
            "Source": m.source_type,
            "Emergency Level": m.emergency_level,
            "Arrival Time": f"{m.arrival_time:.2f} s",
            "Priority": f"Priority {m.priority}",
        }
        for m in raw_messages
    ])
    st.dataframe(df_gen, use_container_width=True)

    # SECTION 3: VISUAL TRANSMISSION TIMELINE & TABLE
    st.subheader("Section 3: Transmission Queue & Visual Timeline")
    st.markdown(
        """
        **Time → ------------------------------------------------------------------------------------>**
        
        **Priority Hierarchy:** Critical Ambulance ($P_1$) $\\downarrow$ Non-critical Ambulance ($P_2$) $\\downarrow$ Normal User ($P_3$)
        """
    )

    active_results = priority_results if scheduling_mode in ("Priority", "Compare Both") else fifo_results
    active_mode_name = "Priority Scheduling" if scheduling_mode in ("Priority", "Compare Both") else "FIFO Scheduling"

    # Matplotlib Gantt Chart for Transmission Timeline
    fig_timeline, ax_timeline = plt.subplots(figsize=(10, 2.8))
    
    color_map = {1: "#dc2626", 2: "#d97706", 3: "#2563eb"}
    y_lane_map = {1: 2, 2: 1, 3: 0}

    for m in active_results:
        y_pos = y_lane_map[m.priority]
        start = m.start_time
        duration = m.transmission_time
        c = color_map[m.priority]

        ax_timeline.broken_barh(
            [(start, duration)],
            (y_pos - 0.35, 0.7),
            facecolors=c,
            edgecolor="#0f172a",
            linewidth=1.2,
        )
        # Label each message block inside the timeline
        ax_timeline.text(
            start + duration / 2.0,
            y_pos,
            f"M{m.message_id}",
            ha="center",
            va="center",
            color="white",
            fontweight="bold",
            fontsize=8,
        )

    ax_timeline.set_yticks([0, 1, 2])
    ax_timeline.set_yticklabels(["Normal (P3)", "Ambulance Non-Crit (P2)", "Ambulance Crit (P1)"])
    ax_timeline.set_xlabel("Shared Channel Timeline (Seconds) →")
    ax_timeline.set_title(f"Channel Allocation Timeline ({active_mode_name})", fontsize=10, fontweight="bold")
    ax_timeline.grid(True, linestyle="--", alpha=0.5, axis="x")
    st.pyplot(fig_timeline)
    plt.close(fig_timeline)

    # Required Transmission Order Table
    st.markdown("### Transmission Order & Waiting Time Table")
    df_tx = pd.DataFrame([
        {
            "Transmission Order": idx,
            "Message ID": f"M{m.message_id}",
            "Source": m.source_type,
            "Emergency Level": m.emergency_level,
            "Priority": f"Priority {m.priority}",
            "Waiting Time": f"{m.waiting_time:.2f} s",
        }
        for idx, m in enumerate(active_results, start=1)
    ])
    st.dataframe(df_tx, use_container_width=True)

    # SECTION 4: PERFORMANCE METRICS
    st.subheader(f"Section 4: Performance Metrics ({active_mode_name})")
    met = priority_metrics if scheduling_mode in ("Priority", "Compare Both") else fifo_metrics

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Average Waiting Time", f"{met['avg_waiting_time']} s")
    c2.metric("Average Total Delay", f"{met['avg_delay']} s")
    c3.metric("Throughput", f"{met['throughput']} msgs/s")
    c4.metric("Packet Loss Rate", f"{met['packet_loss_rate']} %")

    m1, m2, m3 = st.columns(3)
    m1.metric("Ambulance Avg Wait (All)", f"{met['ambulance_avg_waiting_time']} s")
    m2.metric("Critical Ambulance Avg Wait (P1)", f"{met['critical_ambulance_avg_waiting_time']} s")
    m3.metric("Normal-User Avg Wait (P3)", f"{met['normal_user_avg_waiting_time']} s")

    # SECTION 5: FIFO VS PRIORITY COMPARISON
    if scheduling_mode == "Compare Both":
        st.subheader("Section 5: FIFO vs. Priority Scheduling Comparison")
        st.caption("Side-by-side numerical comparison under identical message traffic and channel conditions.")

        comp_df = pd.DataFrame({
            "Performance Metric": [
                "Transmission Sequence",
                "Average Waiting Time (Overall)",
                "Average Total Delay",
                "Channel Throughput",
                "Packet Loss Rate",
                "Ambulance Avg Waiting Time (All)",
                "Critical Ambulance Avg Waiting Time (P1)",
                "Normal-User Avg Waiting Time (P3)",
            ],
            "FIFO Scheduling": [
                " -> ".join(fifo_metrics["transmission_order"]),
                f"{fifo_metrics['avg_waiting_time']:.3f} s",
                f"{fifo_metrics['avg_delay']:.3f} s",
                f"{fifo_metrics['throughput']:.3f} msgs/s",
                f"{fifo_metrics['packet_loss_rate']:.1f} %",
                f"{fifo_metrics['ambulance_avg_waiting_time']:.3f} s",
                f"{fifo_metrics['critical_ambulance_avg_waiting_time']:.3f} s",
                f"{fifo_metrics['normal_user_avg_waiting_time']:.3f} s",
            ],
            "Priority Scheduling": [
                " -> ".join(priority_metrics["transmission_order"]),
                f"{priority_metrics['avg_waiting_time']:.3f} s",
                f"{priority_metrics['avg_delay']:.3f} s",
                f"{priority_metrics['throughput']:.3f} msgs/s",
                f"{priority_metrics['packet_loss_rate']:.1f} %",
                f"{priority_metrics['ambulance_avg_waiting_time']:.3f} s",
                f"{priority_metrics['critical_ambulance_avg_waiting_time']:.3f} s",
                f"{priority_metrics['normal_user_avg_waiting_time']:.3f} s",
            ],
        })
        st.table(comp_df)

        # Matplotlib Comparison Charts
        st.markdown("### Comparative Performance Charts (Matplotlib)")
        col_fig1, col_fig2, col_fig3 = st.columns(3)

        with col_fig1:
            # 1. Waiting time by class
            fig_w, ax_w = plt.subplots(figsize=(4.5, 3.5))
            classes = ["Overall", "Crit (P1)", "Ambulance", "Norm (P3)"]
            fifo_w = [
                fifo_metrics["avg_waiting_time"],
                fifo_metrics["critical_ambulance_avg_waiting_time"],
                fifo_metrics["ambulance_avg_waiting_time"],
                fifo_metrics["normal_user_avg_waiting_time"],
            ]
            prio_w = [
                priority_metrics["avg_waiting_time"],
                priority_metrics["critical_ambulance_avg_waiting_time"],
                priority_metrics["ambulance_avg_waiting_time"],
                priority_metrics["normal_user_avg_waiting_time"],
            ]
            x = range(len(classes))
            width = 0.35
            ax_w.bar([i - width/2 for i in x], fifo_w, width=width, label="FIFO", color="#3b82f6")
            ax_w.bar([i + width/2 for i in x], prio_w, width=width, label="Priority", color="#10b981")
            ax_w.set_xticks(x)
            ax_w.set_xticklabels(classes, rotation=15)
            ax_w.set_ylabel("Waiting Time (s)")
            ax_w.set_title("Waiting Time by Traffic Class")
            ax_w.legend()
            st.pyplot(fig_w)
            plt.close(fig_w)

        with col_fig2:
            # 2. Average Delay
            fig_d, ax_d = plt.subplots(figsize=(4.5, 3.5))
            ax_d.bar(["FIFO", "Priority"], [fifo_metrics["avg_delay"], priority_metrics["avg_delay"]], color=["#3b82f6", "#10b981"], width=0.45)
            ax_d.set_ylabel("Turnaround Delay (s)")
            ax_d.set_title("Average Turnaround Delay")
            st.pyplot(fig_d)
            plt.close(fig_d)

        with col_fig3:
            # 3. Throughput
            fig_tp, ax_tp = plt.subplots(figsize=(4.5, 3.5))
            ax_tp.bar(["FIFO", "Priority"], [fifo_metrics["throughput"], priority_metrics["throughput"]], color=["#3b82f6", "#8b5cf6"], width=0.45)
            ax_tp.set_ylabel("Throughput (msgs/s)")
            ax_tp.set_title("Channel Throughput")
            st.pyplot(fig_tp)
            plt.close(fig_tp)

        # 4. Transmission sequence comparison
        st.markdown("**4. Message Transmission Order Comparison**")
        st.write("• **FIFO Sequence:**    ", " -> ".join(fifo_metrics["transmission_order"]))
        st.write("• **Priority Sequence:**", " -> ".join(priority_metrics["transmission_order"]))


# ============================================================================
# TAB 2: PREDEFINED NETWORK LOAD EXPERIMENTS
# ============================================================================
with tab_experiments:
    st.header("Predefined Network Load Experiments")
    st.markdown(
        """
        Three controlled experiments evaluate FIFO and Priority Scheduling across increasing traffic congestion.
        
        **Controlled Constants (Same across all 3 experiments):**
        - **Channel Transmission Time:** $T_{\\text{tx}} = 1.0\\text{ s}$ per message
        - **Simulated Packet Loss Probability:** $P_{\\text{loss}} = 2.0\\%$
        - **Random Seed:** $42$
        - **Message Classes & Arrival Timestamps:** Stochastically generated per load level and held identical between FIFO and Priority.
        """
    )
    st.divider()

    experiments_config = [
        {"name": "Experiment 1", "title": "Low Network Load", "num": 8, "duration": 20.0, "seed": 42},
        {"name": "Experiment 2", "title": "Medium Network Load", "num": 15, "duration": 15.0, "seed": 42},
        {"name": "Experiment 3", "title": "High Network Load", "num": 25, "duration": 12.0, "seed": 42},
    ]

    all_exp_rows = []
    exp_summary_data = []

    for cfg in experiments_config:
        msgs = generate_messages(
            num_messages=cfg["num"],
            simulation_duration=cfg["duration"],
            channel_tx_time=1.0,
            seed=cfg["seed"],
        )
        l_rng = random.Random(cfg["seed"] + 999)
        l_map = {m.message_id: (l_rng.random() < 0.02) for m in msgs}

        f_res = simulate_channel(msgs, mode="FIFO", loss_probability=0.02, channel_loss_map=l_map)
        p_res = simulate_channel(msgs, mode="PRIORITY", loss_probability=0.02, channel_loss_map=l_map)

        f_met = calculate_metrics(f_res)
        p_met = calculate_metrics(p_res)

        # FIFO Row
        all_exp_rows.append({
            "Experiment": cfg["name"],
            "Traffic Level": cfg["title"],
            "Scheduling Method": "FIFO",
            "Average Waiting Time": f"{f_met['avg_waiting_time']:.3f} s",
            "Average Delay": f"{f_met['avg_delay']:.3f} s",
            "Throughput": f"{f_met['throughput']:.3f} msgs/s",
            "Packet Loss Rate": f"{f_met['packet_loss_rate']:.1f}%",
            "Ambulance Average Waiting Time": f"{f_met['ambulance_avg_waiting_time']:.3f} s",
            "Critical Ambulance Average Waiting Time": f"{f_met['critical_ambulance_avg_waiting_time']:.3f} s",
            "Normal User Average Waiting Time": f"{f_met['normal_user_avg_waiting_time']:.3f} s",
        })

        # Priority Row
        all_exp_rows.append({
            "Experiment": cfg["name"],
            "Traffic Level": cfg["title"],
            "Scheduling Method": "Priority Scheduling",
            "Average Waiting Time": f"{p_met['avg_waiting_time']:.3f} s",
            "Average Delay": f"{p_met['avg_delay']:.3f} s",
            "Throughput": f"{p_met['throughput']:.3f} msgs/s",
            "Packet Loss Rate": f"{p_met['packet_loss_rate']:.1f}%",
            "Ambulance Average Waiting Time": f"{p_met['ambulance_avg_waiting_time']:.3f} s",
            "Critical Ambulance Average Waiting Time": f"{p_met['critical_ambulance_avg_waiting_time']:.3f} s",
            "Normal User Average Waiting Time": f"{p_met['normal_user_avg_waiting_time']:.3f} s",
        })

        exp_summary_data.append({
            "title": cfg["title"],
            "fifo": f_met,
            "priority": p_met,
        })

    # Results Table
    st.subheader("Comprehensive Simulation Results Table")
    st.dataframe(pd.DataFrame(all_exp_rows), use_container_width=True)

    # Matplotlib Plots Across Loads
    st.subheader("Comparative Performance Plots Across Network Loads (Matplotlib)")
    col_p1, col_p2 = st.columns(2)

    with col_p1:
        fig_load_p1, ax_load_p1 = plt.subplots(figsize=(5, 3.2))
        loads = [item["title"].replace(" Network Load", "") for item in exp_summary_data]
        fifo_crit = [item["fifo"]["critical_ambulance_avg_waiting_time"] for item in exp_summary_data]
        prio_crit = [item["priority"]["critical_ambulance_avg_waiting_time"] for item in exp_summary_data]
        x = range(len(loads))
        w = 0.35
        ax_load_p1.bar([i - w/2 for i in x], fifo_crit, width=w, label="FIFO", color="#ef4444")
        ax_load_p1.bar([i + w/2 for i in x], prio_crit, width=w, label="Priority", color="#10b981")
        ax_load_p1.set_xticks(x)
        ax_load_p1.set_xticklabels(loads)
        ax_load_p1.set_ylabel("Waiting Time (s)")
        ax_load_p1.set_title("Critical Ambulance (P1) Waiting Time Across Loads")
        ax_load_p1.legend()
        st.pyplot(fig_load_p1)
        plt.close(fig_load_p1)

    with col_p2:
        fig_load_p3, ax_load_p3 = plt.subplots(figsize=(5, 3.2))
        fifo_norm = [item["fifo"]["normal_user_avg_waiting_time"] for item in exp_summary_data]
        prio_norm = [item["priority"]["normal_user_avg_waiting_time"] for item in exp_summary_data]
        ax_load_p3.bar([i - w/2 for i in x], fifo_norm, width=w, label="FIFO", color="#3b82f6")
        ax_load_p3.bar([i + w/2 for i in x], prio_norm, width=w, label="Priority", color="#f59e0b")
        ax_load_p3.set_xticks(x)
        ax_load_p3.set_xticklabels(loads)
        ax_load_p3.set_ylabel("Waiting Time (s)")
        ax_load_p3.set_title("Normal User (P3) Waiting Time Across Loads")
        ax_load_p3.legend()
        st.pyplot(fig_load_p3)
        plt.close(fig_load_p3)
