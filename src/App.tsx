import React, { useState, useMemo } from 'react';
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  Clock,
  Radio,
  Sliders,
  Sparkles,
  Zap,
  ShieldAlert,
  Users,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Info,
  Layers,
  TrendingDown,
  TrendingUp,
} from 'lucide-react';

// ============================================================================
// TYPES & DATA STRUCTURES
// ============================================================================

interface MessageItem {
  message_id: number;
  source_type: 'Ambulance' | 'Normal User';
  emergency_level: 'Critical' | 'Non-critical' | 'None';
  priority: 1 | 2 | 3;
  arrival_time: number;
  transmission_time: number;
  start_time?: number;
  waiting_time?: number;
  completion_time?: number;
  status?: 'DELIVERED' | 'LOST';
}

interface SimMetrics {
  total_messages: number;
  delivered_messages: number;
  lost_messages: number;
  loss_rate_percent: number;
  avg_waiting_time: number;
  avg_delay: number;
  throughput: number;
  ambulance_avg_wait: number;
  critical_ambulance_avg_wait: number;
  normal_user_avg_wait: number;
  critical_transmitted_before_first_normal: number;
  transmission_order: number[];
}

// Simple deterministic PRNG
function createPRNG(seed: number) {
  let s = seed % 2147483647;
  if (s <= 0) s += 2147483646;
  return function () {
    s = (s * 16807) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

// Generate traffic
function generateMessages(
  num: number,
  duration: number,
  txTime: number,
  seed: number,
  ambRatio: number = 0.4,
  critRatio: number = 0.5
): MessageItem[] {
  const rng = createPRNG(seed);
  const rawArrivals = Array.from({ length: num }, () =>
    Math.round(rng() * duration * 100) / 100
  ).sort((a, b) => a - b);

  return rawArrivals.map((arrival, idx) => {
    const isAmbulance = rng() < ambRatio;
    let source: 'Ambulance' | 'Normal User' = 'Normal User';
    let level: 'Critical' | 'Non-critical' | 'None' = 'None';
    let priority: 1 | 2 | 3 = 3;

    if (isAmbulance) {
      source = 'Ambulance';
      const isCrit = rng() < critRatio;
      if (isCrit) {
        level = 'Critical';
        priority = 1;
      } else {
        level = 'Non-critical';
        priority = 2;
      }
    }

    return {
      message_id: idx + 1,
      source_type: source,
      emergency_level: level,
      priority,
      arrival_time: arrival,
      transmission_time: txTime,
    };
  });
}

// Discrete-event simulator
function runSimulation(
  rawMessages: MessageItem[],
  mode: 'FIFO' | 'PRIORITY',
  lossProb: number,
  lossMap: Record<number, boolean>
): { processed: MessageItem[]; metrics: SimMetrics } {
  const msgs: MessageItem[] = JSON.parse(JSON.stringify(rawMessages));
  msgs.sort((a, b) => a.arrival_time - b.arrival_time || a.message_id - b.message_id);

  const waitingQueue: MessageItem[] = [];
  const processed: MessageItem[] = [];
  let channelFreeTime = 0.0;
  let idx = 0;
  const total = msgs.length;

  while (idx < total || waitingQueue.length > 0) {
    if (waitingQueue.length === 0 && channelFreeTime <= msgs[idx].arrival_time) {
      channelFreeTime = msgs[idx].arrival_time;
    }

    while (idx < total && msgs[idx].arrival_time <= channelFreeTime) {
      waitingQueue.push(msgs[idx]);
      idx++;
    }

    if (waitingQueue.length > 0) {
      if (mode === 'FIFO') {
        waitingQueue.sort((a, b) => a.arrival_time - b.arrival_time || a.message_id - b.message_id);
      } else {
        waitingQueue.sort((a, b) => a.priority - b.priority || a.arrival_time - b.arrival_time || a.message_id - b.message_id);
      }

      const msg = waitingQueue.shift()!;
      const start = Math.max(channelFreeTime, msg.arrival_time);
      const wait = start - msg.arrival_time;
      const completion = start + msg.transmission_time;

      msg.start_time = Math.round(start * 100) / 100;
      msg.waiting_time = Math.round(wait * 100) / 100;
      msg.completion_time = Math.round(completion * 100) / 100;

      const isLost = lossMap[msg.message_id] ?? false;
      msg.status = isLost ? 'LOST' : 'DELIVERED';

      channelFreeTime = completion;
      processed.push(msg);
    }
  }

  // Calculate metrics
  const n = processed.length;
  const delivered = processed.filter((m) => m.status === 'DELIVERED');
  const lost = processed.filter((m) => m.status === 'LOST');
  const lossRate = n > 0 ? (lost.length / n) * 100 : 0;

  const avgWait = n > 0 ? processed.reduce((sum, m) => sum + (m.waiting_time || 0), 0) / n : 0;
  const avgDelay = n > 0 ? processed.reduce((sum, m) => sum + ((m.completion_time || 0) - m.arrival_time), 0) / n : 0;

  const minArrival = Math.min(...processed.map((m) => m.arrival_time));
  const maxCompletion = Math.max(...processed.map((m) => m.completion_time || 0));
  const span = Math.max(maxCompletion - minArrival, 0.001);
  const throughput = delivered.length / span;

  const amb = processed.filter((m) => m.source_type === 'Ambulance');
  const crit = processed.filter((m) => m.priority === 1);
  const norm = processed.filter((m) => m.source_type === 'Normal User');

  const ambWait = amb.length > 0 ? amb.reduce((s, m) => s + (m.waiting_time || 0), 0) / amb.length : 0;
  const critWait = crit.length > 0 ? crit.reduce((s, m) => s + (m.waiting_time || 0), 0) / crit.length : 0;
  const normWait = norm.length > 0 ? norm.reduce((s, m) => s + (m.waiting_time || 0), 0) / norm.length : 0;

  let critBeforeFirstNormal = 0;
  let seenNormal = false;
  for (const m of processed) {
    if (m.source_type === 'Normal User') {
      seenNormal = true;
    } else if (m.priority === 1 && !seenNormal) {
      critBeforeFirstNormal++;
    }
  }

  return {
    processed,
    metrics: {
      total_messages: n,
      delivered_messages: delivered.length,
      lost_messages: lost.length,
      loss_rate_percent: Math.round(lossRate * 10) / 10,
      avg_waiting_time: Math.round(avgWait * 1000) / 1000,
      avg_delay: Math.round(avgDelay * 1000) / 1000,
      throughput: Math.round(throughput * 1000) / 1000,
      ambulance_avg_wait: Math.round(ambWait * 1000) / 1000,
      critical_ambulance_avg_wait: Math.round(critWait * 1000) / 1000,
      normal_user_avg_wait: Math.round(normWait * 1000) / 1000,
      critical_transmitted_before_first_normal: critBeforeFirstNormal,
      transmission_order: processed.map((m) => m.message_id),
    },
  };
}

export default function App() {
  // Sidebar states
  const [numMessages, setNumMessages] = useState<number>(15);
  const [simDuration, setSimDuration] = useState<number>(12);
  const [channelTxTime, setChannelTxTime] = useState<number>(1.0);
  const [packetLossPct, setPacketLossPct] = useState<number>(2);
  const [seed, setSeed] = useState<number>(42);
  const [schedulingMode, setSchedulingMode] = useState<'FIFO' | 'Priority' | 'Compare Both'>('Compare Both');

  // Generate messages & simulations
  const { rawMessages, fifoData, prioData } = useMemo(() => {
    const msgs = generateMessages(numMessages, simDuration, channelTxTime, seed);

    const lossRng = createPRNG(seed + 999);
    const lossProb = packetLossPct / 100.0;
    const lossMap: Record<number, boolean> = {};
    for (const m of msgs) {
      lossMap[m.message_id] = lossRng() < lossProb;
    }

    const fifo = runSimulation(msgs, 'FIFO', lossProb, lossMap);
    const prio = runSimulation(msgs, 'PRIORITY', lossProb, lossMap);

    return { rawMessages: msgs, fifoData: fifo, prioData: prio };
  }, [numMessages, simDuration, channelTxTime, packetLossPct, seed]);

  // Quick Preset Scenarios
  const loadPreset = (preset: 'five_simultaneous' | 'heavy_emergency' | 'balanced') => {
    if (preset === 'five_simultaneous') {
      setNumMessages(5);
      setSimDuration(0.1);
      setChannelTxTime(1.0);
      setPacketLossPct(0);
      setSeed(42);
      setSchedulingMode('Compare Both');
    } else if (preset === 'heavy_emergency') {
      setNumMessages(20);
      setSimDuration(10);
      setChannelTxTime(1.2);
      setPacketLossPct(5);
      setSeed(101);
      setSchedulingMode('Compare Both');
    } else {
      setNumMessages(15);
      setSimDuration(12);
      setChannelTxTime(1.0);
      setPacketLossPct(2);
      setSeed(42);
      setSchedulingMode('Compare Both');
    }
  };

  // Active display metrics
  const activeMetrics = schedulingMode === 'Priority' ? prioData.metrics : fifoData.metrics;

  // Navigation Tab: 'interactive' | 'experiments'
  const [activeTab, setActiveTab] = useState<'interactive' | 'experiments'>('interactive');

  // Predefined Experiments computation (Low, Medium, High Load)
  const predefinedExperiments = useMemo(() => {
    const configs = [
      { name: 'Experiment 1', title: 'Low Network Load', num: 8, duration: 20.0, seed: 42 },
      { name: 'Experiment 2', title: 'Medium Network Load', num: 15, duration: 15.0, seed: 42 },
      { name: 'Experiment 3', title: 'High Network Load', num: 25, duration: 12.0, seed: 42 },
    ];

    return configs.map((cfg) => {
      const msgs = generateMessages(cfg.num, cfg.duration, 1.0, cfg.seed);
      const lossProb = 0.02; // Fixed 2%
      const lossRng = createPRNG(cfg.seed + 999);
      const lossMap: Record<number, boolean> = {};
      for (const m of msgs) {
        lossMap[m.message_id] = lossRng() < lossProb;
      }

      const fifo = runSimulation(msgs, 'FIFO', lossProb, lossMap);
      const prio = runSimulation(msgs, 'PRIORITY', lossProb, lossMap);

      return {
        ...cfg,
        fifo,
        prio,
      };
    });
  }, []);

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col md:flex-row">
      {/* ========================================================================= */}
      {/* SIDEBAR */}
      {/* ========================================================================= */}
      <aside className="w-full md:w-80 bg-slate-950 border-r border-slate-800 p-5 shrink-0 flex flex-col gap-6 overflow-y-auto">
        <div>
          <div className="flex items-center gap-2 text-rose-500 font-semibold tracking-wider text-xs uppercase">
            <Radio className="w-4 h-4" />
            <span>CNS Minor Project</span>
          </div>
          <h2 className="text-xl font-bold text-white mt-1">Simulation Control</h2>
          <p className="text-xs text-slate-400 mt-1">
            Configure shared physical channel and traffic generation parameters.
          </p>
        </div>

        {/* Preset buttons */}
        <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800">
          <label className="text-xs font-semibold text-slate-300 block mb-2">Quick Presets:</label>
          <div className="grid grid-cols-1 gap-1.5 text-xs">
            <button
              onClick={() => loadPreset('five_simultaneous')}
              className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-left rounded text-slate-200 transition font-medium flex items-center justify-between"
            >
              <span>5-Msg Simultaneous</span>
              <span className="text-[10px] bg-rose-500/20 text-rose-300 px-1.5 py-0.5 rounded">Core Demo</span>
            </button>
            <button
              onClick={() => loadPreset('balanced')}
              className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-left rounded text-slate-200 transition font-medium"
            >
              15-Msg Standard Traffic
            </button>
            <button
              onClick={() => loadPreset('heavy_emergency')}
              className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-left rounded text-slate-200 transition font-medium"
            >
              Heavy Emergency Load (5% Loss)
            </button>
          </div>
        </div>

        {/* Input 1: Number of messages */}
        <div>
          <div className="flex justify-between items-center text-xs font-medium text-slate-300 mb-1.5">
            <span>1. Number of Messages</span>
            <span className="font-mono text-cyan-400 bg-cyan-950/50 px-2 py-0.5 rounded border border-cyan-800/40">{numMessages}</span>
          </div>
          <input
            type="range"
            min={3}
            max={40}
            value={numMessages}
            onChange={(e) => setNumMessages(Number(e.target.value))}
            className="w-full accent-cyan-500 cursor-pointer"
          />
        </div>

        {/* Input 2: Simulation Duration */}
        <div>
          <div className="flex justify-between items-center text-xs font-medium text-slate-300 mb-1.5">
            <span>2. Simulation Duration (s)</span>
            <span className="font-mono text-cyan-400 bg-cyan-950/50 px-2 py-0.5 rounded border border-cyan-800/40">{simDuration} s</span>
          </div>
          <input
            type="range"
            min={1}
            max={30}
            step={1}
            value={simDuration}
            onChange={(e) => setSimDuration(Number(e.target.value))}
            className="w-full accent-cyan-500 cursor-pointer"
          />
        </div>

        {/* Input 3: Channel Transmission Time */}
        <div>
          <div className="flex justify-between items-center text-xs font-medium text-slate-300 mb-1.5">
            <span>3. Channel Tx Time (s)</span>
            <span className="font-mono text-cyan-400 bg-cyan-950/50 px-2 py-0.5 rounded border border-cyan-800/40">{channelTxTime.toFixed(1)} s</span>
          </div>
          <input
            type="range"
            min={0.2}
            max={2.5}
            step={0.1}
            value={channelTxTime}
            onChange={(e) => setChannelTxTime(Number(e.target.value))}
            className="w-full accent-cyan-500 cursor-pointer"
          />
        </div>

        {/* Input 4: Packet Loss Probability */}
        <div>
          <label className="text-xs font-medium text-slate-300 block mb-1.5">
            4. Packet Loss Probability
          </label>
          <div className="grid grid-cols-4 gap-1.5">
            {[0, 2, 5, 10].map((val) => (
              <button
                key={val}
                onClick={() => setPacketLossPct(val)}
                className={`py-1.5 text-xs font-medium rounded border transition ${
                  packetLossPct === val
                    ? 'bg-rose-600 border-rose-500 text-white'
                    : 'bg-slate-900 border-slate-800 text-slate-300 hover:bg-slate-800'
                }`}
              >
                {val}%
              </button>
            ))}
          </div>
          <p className="text-[11px] text-slate-500 mt-1 italic">
            *Simulated channel fading independent of priority.
          </p>
        </div>

        {/* Input 5: Random Seed */}
        <div>
          <div className="flex justify-between items-center text-xs font-medium text-slate-300 mb-1.5">
            <span>5. Random Seed</span>
            <button
              onClick={() => setSeed(Math.floor(Math.random() * 9000) + 100)}
              className="text-[11px] text-cyan-400 flex items-center gap-1 hover:underline"
            >
              <RefreshCw className="w-3 h-3" /> New
            </button>
          </div>
          <input
            type="number"
            value={seed}
            onChange={(e) => setSeed(Number(e.target.value) || 1)}
            className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-1.5 text-xs text-white font-mono focus:outline-none focus:border-cyan-500"
          />
        </div>

        {/* Input 6: Scheduling Mode */}
        <div>
          <label className="text-xs font-medium text-slate-300 block mb-2">
            6. Scheduling Mode
          </label>
          <div className="space-y-1.5">
            {(['Compare Both', 'Priority', 'FIFO'] as const).map((m) => (
              <label
                key={m}
                className={`flex items-center gap-2 p-2 rounded border cursor-pointer text-xs transition ${
                  schedulingMode === m
                    ? 'bg-cyan-950/60 border-cyan-500 text-cyan-200'
                    : 'bg-slate-900/60 border-slate-800 text-slate-400 hover:bg-slate-800'
                }`}
              >
                <input
                  type="radio"
                  name="schedulingMode"
                  checked={schedulingMode === m}
                  onChange={() => setSchedulingMode(m)}
                  className="accent-cyan-500"
                />
                <span className="font-medium">{m}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="mt-auto pt-4 border-t border-slate-800/80 text-[11px] text-slate-500">
          <p>Streamlit App: <code className="text-slate-300 font-mono">app.py</code></p>
          <p>Local run: <code className="text-slate-300 font-mono">streamlit run app.py</code></p>
        </div>
      </aside>

      {/* ========================================================================= */}
      {/* MAIN CONTENT AREA */}
      {/* ========================================================================= */}
      <main className="flex-1 p-6 md:p-8 overflow-y-auto space-y-8 max-w-7xl mx-auto w-full">
        {/* Navigation Tabs */}
        <div className="flex items-center gap-3 border-b border-slate-800 pb-3">
          <button
            onClick={() => setActiveTab('interactive')}
            className={`px-4 py-2 rounded-lg font-semibold text-xs transition flex items-center gap-2 ${
              activeTab === 'interactive'
                ? 'bg-cyan-600 text-white shadow-lg shadow-cyan-900/40'
                : 'bg-slate-900 text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            <Activity className="w-4 h-4" />
            <span>Interactive Simulator</span>
          </button>

          <button
            onClick={() => setActiveTab('experiments')}
            className={`px-4 py-2 rounded-lg font-semibold text-xs transition flex items-center gap-2 ${
              activeTab === 'experiments'
                ? 'bg-rose-600 text-white shadow-lg shadow-rose-900/40'
                : 'bg-slate-900 text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            <BarChart3 className="w-4 h-4" />
            <span>Predefined Load Experiments (Low, Medium, High)</span>
            <span className="text-[10px] bg-rose-950 text-rose-200 border border-rose-800/60 px-1.5 py-0.5 rounded font-mono">
              3 Experiments
            </span>
          </button>
        </div>

        {activeTab === 'interactive' && (
          <div className="space-y-8">
            {/* SECTION 1: TITLE & EXPLANATION */}
            <section className="bg-slate-950 border border-slate-800/80 rounded-xl p-6 shadow-xl relative overflow-hidden">
              <div className="absolute top-0 right-0 w-80 h-80 bg-rose-500/5 rounded-full blur-3xl pointer-events-none" />
              <div className="flex items-center gap-3 mb-2">
                <span className="bg-rose-500/10 text-rose-400 border border-rose-500/30 text-xs px-2.5 py-0.5 rounded-full font-mono font-medium">
                  CNS Minor Project
                </span>
                <span className="text-xs text-slate-400 flex items-center gap-1 font-mono">
                  <Zap className="w-3.5 h-3.5 text-amber-400" /> Single Shared Channel Simulation
                </span>
              </div>
              <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">
                Priority-Based Emergency Message Scheduling
              </h1>
          <p className="text-slate-300 text-sm mt-3 leading-relaxed max-w-4xl">
            In a shared communication network, normal users and emergency ambulances contend for the exact same transmission medium.
            Under standard <strong>FIFO</strong> scheduling, critical medical telemetry suffers unacceptable delay if queued behind normal browsing.
            This project models a <strong>3-tier Priority Queueing system</strong> where:
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4">
            <div className="bg-slate-900 border border-rose-900/40 p-3 rounded-lg flex items-start gap-3">
              <span className="text-xs font-bold px-2 py-1 rounded bg-rose-500/20 text-rose-400 border border-rose-500/40">
                P1
              </span>
              <div>
                <div className="text-xs font-semibold text-rose-300">Critical Ambulance</div>
                <div className="text-[11px] text-slate-400">Vital signs, cardiac alerts. Highest priority.</div>
              </div>
            </div>

            <div className="bg-slate-900 border border-amber-900/40 p-3 rounded-lg flex items-start gap-3">
              <span className="text-xs font-bold px-2 py-1 rounded bg-amber-500/20 text-amber-400 border border-amber-500/40">
                P2
              </span>
              <div>
                <div className="text-xs font-semibold text-amber-300">Non-Critical Ambulance</div>
                <div className="text-[11px] text-slate-400">Routine ETA, status telemetry, vehicle logs.</div>
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-3 rounded-lg flex items-start gap-3">
              <span className="text-xs font-bold px-2 py-1 rounded bg-slate-800 text-slate-400 border border-slate-700">
                P3
              </span>
              <div>
                <div className="text-xs font-semibold text-slate-300">Normal User</div>
                <div className="text-[11px] text-slate-400">Standard web traffic. Served after emergency queues.</div>
              </div>
            </div>
          </div>

          {/* End-to-End System Block Diagram Display */}
          <div className="mt-5 pt-4 border-t border-slate-800/80">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5 font-mono">
                <Info className="w-3.5 h-3.5 text-cyan-400" />
                End-to-End System Block Diagram
              </span>
              <span className="text-[11px] text-slate-500 font-mono">8-Stage Communication Model</span>
            </div>
            <pre className="bg-slate-900/90 text-cyan-300 p-4 rounded-lg border border-slate-800 font-mono text-[11px] sm:text-xs overflow-x-auto leading-tight shadow-inner">
{`       ┌─────────────────┐
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
      └─────────────────────┘`}
            </pre>
          </div>
        </section>

        {/* SECTION 2: GENERATED MESSAGES TABLE */}
        <section className="bg-slate-950 border border-slate-800 rounded-xl p-6 shadow-lg">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Layers className="w-5 h-5 text-cyan-400" />
                Section 2: Generated Messages
              </h2>
              <p className="text-xs text-slate-400">
                Message pool generated across nodes. Both FIFO and Priority operate on this identical set.
              </p>
            </div>
            <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
              <span className="px-2 py-1 rounded bg-slate-900 border border-slate-800">
                Total: {rawMessages.length} msgs
              </span>
              <span className="px-2 py-1 rounded bg-rose-950/40 border border-rose-900/50 text-rose-300">
                P1: {rawMessages.filter((m) => m.priority === 1).length}
              </span>
              <span className="px-2 py-1 rounded bg-amber-950/40 border border-amber-900/50 text-amber-300">
                P2: {rawMessages.filter((m) => m.priority === 2).length}
              </span>
              <span className="px-2 py-1 rounded bg-slate-800 text-slate-300">
                P3: {rawMessages.filter((m) => m.priority === 3).length}
              </span>
            </div>
          </div>

          <div className="overflow-x-auto border border-slate-800/80 rounded-lg max-h-64 overflow-y-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-900/90 text-slate-400 sticky top-0 uppercase tracking-wider font-semibold border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-4">Message ID</th>
                  <th className="py-2.5 px-4">Source</th>
                  <th className="py-2.5 px-4">Emergency Level</th>
                  <th className="py-2.5 px-4">Arrival Time (s)</th>
                  <th className="py-2.5 px-4">Priority</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {rawMessages.map((m) => (
                  <tr key={m.message_id} className="hover:bg-slate-900/40 transition">
                    <td className="py-2 px-4 font-bold text-slate-200">M{m.message_id}</td>
                    <td className="py-2 px-4 font-sans">
                      <span className="flex items-center gap-1.5">
                        {m.source_type === 'Ambulance' ? (
                          <Activity className="w-3.5 h-3.5 text-rose-400" />
                        ) : (
                          <Users className="w-3.5 h-3.5 text-slate-400" />
                        )}
                        <span>{m.source_type}</span>
                      </span>
                    </td>
                    <td className="py-2 px-4 font-sans">
                      {m.emergency_level === 'Critical' && (
                        <span className="px-2 py-0.5 rounded text-[11px] bg-rose-500/20 text-rose-300 border border-rose-500/40 font-medium">
                          Critical
                        </span>
                      )}
                      {m.emergency_level === 'Non-critical' && (
                        <span className="px-2 py-0.5 rounded text-[11px] bg-amber-500/20 text-amber-300 border border-amber-500/40 font-medium">
                          Non-critical
                        </span>
                      )}
                      {m.emergency_level === 'None' && (
                        <span className="px-2 py-0.5 rounded text-[11px] bg-slate-800 text-slate-400 font-medium">
                          None
                        </span>
                      )}
                    </td>
                    <td className="py-2 px-4 text-cyan-300">{m.arrival_time.toFixed(2)} s</td>
                    <td className="py-2 px-4">
                      {m.priority === 1 && (
                        <span className="px-2 py-0.5 rounded text-[11px] bg-rose-600 text-white font-bold">
                          Priority 1
                        </span>
                      )}
                      {m.priority === 2 && (
                        <span className="px-2 py-0.5 rounded text-[11px] bg-amber-600 text-white font-bold">
                          Priority 2
                        </span>
                      )}
                      {m.priority === 3 && (
                        <span className="px-2 py-0.5 rounded text-[11px] bg-slate-700 text-slate-300 font-bold">
                          Priority 3
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* SECTION 3: TRANSMISSION QUEUE & VISUAL TIMELINE */}
        <section className="bg-slate-950 border border-slate-800 rounded-xl p-6 shadow-lg space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Clock className="w-5 h-5 text-amber-400" />
                Section 3: Visual Transmission Timeline & Priority Queue
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Visual representation of how the single shared channel is allocated over time.
              </p>
            </div>
            <div className="text-xs font-mono text-slate-400 bg-slate-900 border border-slate-800 px-3 py-1.5 rounded flex items-center gap-2">
              <span className="text-slate-300 font-bold">Time →</span>
              <span className="text-slate-600">----------------------------&gt;</span>
            </div>
          </div>

          {/* Priority Hierarchy Indicator */}
          <div className="bg-slate-900/60 border border-slate-800 p-3 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
            <span className="font-semibold text-slate-300 uppercase tracking-wider text-[11px]">
              Transmission Sequence Hierarchy:
            </span>
            <div className="flex items-center gap-3 font-medium">
              <span className="text-rose-400 flex items-center gap-1">
                🔴 Critical Ambulance (P1)
              </span>
              <span className="text-slate-500">↓</span>
              <span className="text-amber-400 flex items-center gap-1">
                🟡 Non-critical Ambulance (P2)
              </span>
              <span className="text-slate-500">↓</span>
              <span className="text-blue-400 flex items-center gap-1">
                🔵 Normal User (P3)
              </span>
            </div>
          </div>

          {/* Visual Channel Timeline Component */}
          {(() => {
            const activeResults = schedulingMode === 'Priority' || schedulingMode === 'Compare Both' ? prioData.processed : fifoData.processed;
            const maxTime = Math.max(...activeResults.map((m) => m.completion_time || 0), 1.0);

            return (
              <div className="space-y-4">
                <div className="bg-slate-900 border border-slate-800/90 rounded-lg p-4 font-mono">
                  <div className="flex justify-between items-center text-[11px] text-slate-400 mb-2 border-b border-slate-800 pb-2">
                    <span className="text-emerald-400 font-bold">
                      {schedulingMode === 'Priority' || schedulingMode === 'Compare Both'
                        ? 'Priority Scheduling Channel Allocation (Lanes by Class)'
                        : 'FIFO Scheduling Channel Allocation (Lanes by Class)'}
                    </span>
                    <span className="text-slate-400">Total Span: {maxTime.toFixed(2)}s</span>
                  </div>

                  {/* Lane 1: Critical Ambulance (P1) */}
                  <div className="mb-3">
                    <div className="flex justify-between items-center text-[11px] text-rose-400 font-bold mb-1">
                      <span>🔴 Lane 1: Critical Ambulance (P1)</span>
                      <span className="text-[10px] text-slate-500 font-normal">Immediate Preemptive Access</span>
                    </div>
                    <div className="relative h-8 bg-slate-950 border border-slate-800/70 rounded overflow-hidden">
                      {activeResults.filter((m) => m.priority === 1).map((m) => {
                        const leftPct = ((m.start_time || 0) / maxTime) * 100;
                        const widthPct = Math.max((((m.completion_time || 0) - (m.start_time || 0)) / maxTime) * 100, 3);
                        return (
                          <div
                            key={m.message_id}
                            style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
                            className="absolute top-0 bottom-0 bg-gradient-to-r from-rose-600 to-rose-500 border-r border-rose-900 text-white flex items-center justify-center text-[11px] font-bold shadow-sm"
                            title={`M${m.message_id} (P1) | Wait: ${m.waiting_time}s | Tx: ${m.start_time}s-${m.completion_time}s`}
                          >
                            M{m.message_id}
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Lane 2: Non-critical Ambulance (P2) */}
                  <div className="mb-3">
                    <div className="flex justify-between items-center text-[11px] text-amber-400 font-bold mb-1">
                      <span>🟡 Lane 2: Non-critical Ambulance (P2)</span>
                      <span className="text-[10px] text-slate-500 font-normal">Secondary Priority Queue</span>
                    </div>
                    <div className="relative h-8 bg-slate-950 border border-slate-800/70 rounded overflow-hidden">
                      {activeResults.filter((m) => m.priority === 2).map((m) => {
                        const leftPct = ((m.start_time || 0) / maxTime) * 100;
                        const widthPct = Math.max((((m.completion_time || 0) - (m.start_time || 0)) / maxTime) * 100, 3);
                        return (
                          <div
                            key={m.message_id}
                            style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
                            className="absolute top-0 bottom-0 bg-gradient-to-r from-amber-600 to-amber-500 border-r border-amber-900 text-white flex items-center justify-center text-[11px] font-bold shadow-sm"
                            title={`M${m.message_id} (P2) | Wait: ${m.waiting_time}s | Tx: ${m.start_time}s-${m.completion_time}s`}
                          >
                            M{m.message_id}
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Lane 3: Normal User (P3) */}
                  <div>
                    <div className="flex justify-between items-center text-[11px] text-blue-400 font-bold mb-1">
                      <span>🔵 Lane 3: Normal User (P3)</span>
                      <span className="text-[10px] text-slate-500 font-normal">Best Effort Background Queue</span>
                    </div>
                    <div className="relative h-8 bg-slate-950 border border-slate-800/70 rounded overflow-hidden">
                      {activeResults.filter((m) => m.priority === 3).map((m) => {
                        const leftPct = ((m.start_time || 0) / maxTime) * 100;
                        const widthPct = Math.max((((m.completion_time || 0) - (m.start_time || 0)) / maxTime) * 100, 3);
                        return (
                          <div
                            key={m.message_id}
                            style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
                            className="absolute top-0 bottom-0 bg-gradient-to-r from-blue-600 to-blue-500 border-r border-blue-900 text-white flex items-center justify-center text-[11px] font-bold shadow-sm"
                            title={`M${m.message_id} (P3) | Wait: ${m.waiting_time}s | Tx: ${m.start_time}s-${m.completion_time}s`}
                          >
                            M{m.message_id}
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Time Axis Legend */}
                  <div className="flex justify-between items-center text-[10px] text-slate-500 mt-2 pt-2 border-t border-slate-800/60">
                    <span>0.00s</span>
                    <span className="text-slate-400">Shared Channel Time (seconds) →</span>
                    <span>{maxTime.toFixed(2)}s</span>
                  </div>
                </div>

                {/* EXACT REQUIRED TABLE:
                    Transmission Order | Message ID | Source | Emergency Level | Priority | Waiting Time */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-bold text-white">
                      Transmission Order & Waiting Time Table
                    </h3>
                    <span className="text-xs text-slate-400 font-mono">
                      Active: {schedulingMode === 'FIFO' ? 'FIFO' : 'Priority Scheduling'}
                    </span>
                  </div>

                  <div className="overflow-x-auto border border-slate-800 rounded-lg max-h-60 overflow-y-auto">
                    <table className="w-full text-xs text-left">
                      <thead className="bg-slate-900 text-slate-300 font-semibold uppercase tracking-wider text-[11px] border-b border-slate-800 sticky top-0">
                        <tr>
                          <th className="py-2.5 px-4">Transmission Order</th>
                          <th className="py-2.5 px-4">Message ID</th>
                          <th className="py-2.5 px-4">Source</th>
                          <th className="py-2.5 px-4">Emergency Level</th>
                          <th className="py-2.5 px-4">Priority</th>
                          <th className="py-2.5 px-4">Waiting Time</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 font-mono">
                        {activeResults.map((m, idx) => (
                          <tr key={m.message_id} className="hover:bg-slate-900/50 transition">
                            <td className="py-2 px-4 font-bold text-slate-400">#{idx + 1}</td>
                            <td className="py-2 px-4 font-bold text-white">M{m.message_id}</td>
                            <td className="py-2 px-4 font-sans text-slate-200">{m.source_type}</td>
                            <td className="py-2 px-4 font-sans">
                              {m.emergency_level === 'Critical' && (
                                <span className="px-2 py-0.5 rounded text-[10px] bg-rose-500/20 text-rose-300 border border-rose-500/40 font-semibold">
                                  Critical
                                </span>
                              )}
                              {m.emergency_level === 'Non-critical' && (
                                <span className="px-2 py-0.5 rounded text-[10px] bg-amber-500/20 text-amber-300 border border-amber-500/40 font-semibold">
                                  Non-critical
                                </span>
                              )}
                              {m.emergency_level === 'None' && (
                                <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-400">
                                  None
                                </span>
                              )}
                            </td>
                            <td className="py-2 px-4">
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                  m.priority === 1
                                    ? 'bg-rose-600 text-white'
                                    : m.priority === 2
                                    ? 'bg-amber-600 text-white'
                                    : 'bg-slate-700 text-slate-300'
                                }`}
                              >
                                Priority {m.priority}
                              </span>
                            </td>
                            <td className="py-2 px-4 text-cyan-300 font-bold">
                              {m.waiting_time?.toFixed(2)} s
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            );
          })()}
        </section>

        {/* SECTION 4: PERFORMANCE METRICS */}
        <section className="bg-slate-950 border border-slate-800 rounded-xl p-6 shadow-lg">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-emerald-400" />
                Section 4: Performance Metrics ({schedulingMode})
              </h2>
              <p className="text-xs text-slate-400">
                Key Communication and Network Systems (CNS) parameters measured over the single channel.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-slate-900 border border-slate-800 p-3.5 rounded-lg">
              <span className="text-[11px] text-slate-400 block font-medium">Avg Waiting Time</span>
              <div className="text-xl font-bold font-mono text-cyan-400 mt-1">
                {activeMetrics.avg_waiting_time} <span className="text-xs text-slate-400">s</span>
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-3.5 rounded-lg">
              <span className="text-[11px] text-slate-400 block font-medium">Avg Total Delay</span>
              <div className="text-xl font-bold font-mono text-blue-400 mt-1">
                {activeMetrics.avg_delay} <span className="text-xs text-slate-400">s</span>
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-3.5 rounded-lg">
              <span className="text-[11px] text-slate-400 block font-medium">Channel Throughput</span>
              <div className="text-xl font-bold font-mono text-emerald-400 mt-1">
                {activeMetrics.throughput} <span className="text-xs text-slate-400">msgs/s</span>
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-3.5 rounded-lg">
              <span className="text-[11px] text-slate-400 block font-medium">Packet Loss Rate</span>
              <div className="text-xl font-bold font-mono text-rose-400 mt-1">
                {activeMetrics.loss_rate_percent} <span className="text-xs text-slate-400">%</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-3">
            <div className="bg-slate-900/60 border border-slate-800 p-3 rounded-lg flex items-center justify-between">
              <div>
                <span className="text-[11px] text-slate-400 block">Ambulance Avg Wait (All)</span>
                <span className="text-base font-bold font-mono text-slate-200">
                  {activeMetrics.ambulance_avg_wait} s
                </span>
              </div>
              <Activity className="w-5 h-5 text-amber-500/70" />
            </div>

            <div className="bg-slate-900/60 border border-rose-950/40 p-3 rounded-lg flex items-center justify-between">
              <div>
                <span className="text-[11px] text-rose-300 block font-medium">Critical Ambulance Avg Wait (P1)</span>
                <span className="text-base font-bold font-mono text-rose-400">
                  {activeMetrics.critical_ambulance_avg_wait} s
                </span>
              </div>
              <ShieldAlert className="w-5 h-5 text-rose-500" />
            </div>

            <div className="bg-slate-900/60 border border-slate-800 p-3 rounded-lg flex items-center justify-between">
              <div>
                <span className="text-[11px] text-slate-400 block">Normal-User Avg Wait (P3)</span>
                <span className="text-base font-bold font-mono text-slate-300">
                  {activeMetrics.normal_user_avg_wait} s
                </span>
              </div>
              <Users className="w-5 h-5 text-slate-500" />
            </div>
          </div>
        </section>

        {/* SECTION 5: FIFO VS PRIORITY COMPARISON */}
        {schedulingMode === 'Compare Both' && (
          <section className="bg-slate-950 border border-slate-800 rounded-xl p-6 shadow-lg space-y-6">
            <div>
              <div className="flex items-center gap-2 text-rose-400 font-mono text-xs uppercase font-semibold">
                <Sliders className="w-4 h-4" />
                <span>Side-by-Side Analysis</span>
              </div>
              <h2 className="text-lg font-bold text-white mt-1">
                Section 5: FIFO vs. Priority Scheduling Comparison
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                Direct scientific evaluation using the same packet arrivals and channel loss realization.
              </p>
            </div>

            {/* Side-by-side Table */}
            <div className="overflow-x-auto border border-slate-800 rounded-lg">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-900 text-slate-300 font-semibold uppercase tracking-wider text-[11px] border-b border-slate-800">
                  <tr>
                    <th className="py-3 px-4">Performance Metric</th>
                    <th className="py-3 px-4 text-blue-400">FIFO Scheduling</th>
                    <th className="py-3 px-4 text-emerald-400">Priority Scheduling</th>
                    <th className="py-3 px-4 text-slate-400">Difference / Impact</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/70 font-mono">
                  <tr className="hover:bg-slate-900/40">
                    <td className="py-2.5 px-4 font-sans font-medium text-slate-200">
                      Average Waiting Time (Overall)
                    </td>
                    <td className="py-2.5 px-4 text-slate-300">{fifoData.metrics.avg_waiting_time} s</td>
                    <td className="py-2.5 px-4 text-slate-300">{prioData.metrics.avg_waiting_time} s</td>
                    <td className="py-2.5 px-4 font-sans text-slate-400">
                      {Math.abs(fifoData.metrics.avg_waiting_time - prioData.metrics.avg_waiting_time) < 0.01
                        ? 'Identical total workload'
                        : `${(prioData.metrics.avg_waiting_time - fifoData.metrics.avg_waiting_time).toFixed(3)} s`}
                    </td>
                  </tr>

                  <tr className="hover:bg-slate-900/40">
                    <td className="py-2.5 px-4 font-sans font-medium text-slate-200">
                      Average Total Turnaround Delay
                    </td>
                    <td className="py-2.5 px-4 text-slate-300">{fifoData.metrics.avg_delay} s</td>
                    <td className="py-2.5 px-4 text-slate-300">{prioData.metrics.avg_delay} s</td>
                    <td className="py-2.5 px-4 font-sans text-slate-400">
                      {Math.abs(fifoData.metrics.avg_delay - prioData.metrics.avg_delay) < 0.01
                        ? 'Preserved system latency'
                        : `${(prioData.metrics.avg_delay - fifoData.metrics.avg_delay).toFixed(3)} s`}
                    </td>
                  </tr>

                  <tr className="hover:bg-slate-900/40">
                    <td className="py-2.5 px-4 font-sans font-medium text-slate-200">
                      Channel Throughput
                    </td>
                    <td className="py-2.5 px-4 text-slate-300">{fifoData.metrics.throughput} msgs/s</td>
                    <td className="py-2.5 px-4 text-slate-300">{prioData.metrics.throughput} msgs/s</td>
                    <td className="py-2.5 px-4 font-sans text-slate-400">Equal transmission capacity</td>
                  </tr>

                  <tr className="hover:bg-slate-900/40">
                    <td className="py-2.5 px-4 font-sans font-medium text-slate-200">
                      Packet Loss Rate (Simulated)
                    </td>
                    <td className="py-2.5 px-4 text-slate-300">{fifoData.metrics.loss_rate_percent}%</td>
                    <td className="py-2.5 px-4 text-slate-300">{prioData.metrics.loss_rate_percent}%</td>
                    <td className="py-2.5 px-4 font-sans text-slate-400">Physical loss is priority-agnostic</td>
                  </tr>

                  <tr className="hover:bg-slate-900/40 bg-rose-950/20">
                    <td className="py-2.5 px-4 font-sans font-bold text-rose-300">
                      Critical Ambulance Avg Wait (P1)
                    </td>
                    <td className="py-2.5 px-4 text-rose-400 font-bold">{fifoData.metrics.critical_ambulance_avg_wait} s</td>
                    <td className="py-2.5 px-4 text-emerald-400 font-bold">{prioData.metrics.critical_ambulance_avg_wait} s</td>
                    <td className="py-2.5 px-4 font-sans text-emerald-400 font-bold flex items-center gap-1">
                      <TrendingDown className="w-4 h-4" />
                      {fifoData.metrics.critical_ambulance_avg_wait > 0
                        ? `${(
                            ((fifoData.metrics.critical_ambulance_avg_wait - prioData.metrics.critical_ambulance_avg_wait) /
                              fifoData.metrics.critical_ambulance_avg_wait) *
                            100
                          ).toFixed(1)}% reduction in emergency delay`
                        : 'Immediate transmission'}
                    </td>
                  </tr>

                  <tr className="hover:bg-slate-900/40 bg-slate-900/30">
                    <td className="py-2.5 px-4 font-sans font-medium text-slate-300">
                      Normal-User Avg Wait (P3)
                    </td>
                    <td className="py-2.5 px-4 text-slate-400">{fifoData.metrics.normal_user_avg_wait} s</td>
                    <td className="py-2.5 px-4 text-amber-400">{prioData.metrics.normal_user_avg_wait} s</td>
                    <td className="py-2.5 px-4 font-sans text-amber-400/90 flex items-center gap-1">
                      <TrendingUp className="w-4 h-4" />
                      Delay absorbed by low-priority traffic
                    </td>
                  </tr>

                  <tr className="hover:bg-slate-900/40">
                    <td className="py-2.5 px-4 font-sans font-medium text-slate-200">
                      Critical Msgs Before 1st Normal
                    </td>
                    <td className="py-2.5 px-4 text-slate-400">{fifoData.metrics.critical_transmitted_before_first_normal}</td>
                    <td className="py-2.5 px-4 text-emerald-400 font-bold">{prioData.metrics.critical_transmitted_before_first_normal}</td>
                    <td className="py-2.5 px-4 font-sans text-slate-400">Preemption of non-critical queue</td>
                  </tr>
                </tbody>
              </table>
            </div>

            {/* Visual Charts */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-2">
              {/* Chart 1: Waiting Time Comparison */}
              <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 flex flex-col justify-between">
                <div>
                  <h4 className="text-xs font-bold text-slate-200 mb-1 flex items-center gap-1.5">
                    <BarChart3 className="w-4 h-4 text-cyan-400" />
                    1. Waiting Time Comparison (s)
                  </h4>
                  <p className="text-[11px] text-slate-400 mb-4">
                    Compares wait time experienced by Critical P1 vs Normal P3.
                  </p>
                </div>

                <div className="space-y-3 font-mono text-xs">
                  <div>
                    <div className="flex justify-between text-[11px] text-slate-300 mb-1">
                      <span>Critical (P1) Wait</span>
                      <span>FIFO: {fifoData.metrics.critical_ambulance_avg_wait}s | Prio: {prioData.metrics.critical_ambulance_avg_wait}s</span>
                    </div>
                    <div className="w-full h-3 bg-slate-950 rounded-full overflow-hidden flex gap-0.5">
                      <div
                        className="bg-blue-500 h-full rounded"
                        style={{
                          width: `${Math.min(
                            (fifoData.metrics.critical_ambulance_avg_wait /
                              Math.max(fifoData.metrics.critical_ambulance_avg_wait, prioData.metrics.critical_ambulance_avg_wait, 1)) *
                              100,
                            100
                          )}%`,
                        }}
                      />
                      <div
                        className="bg-rose-500 h-full rounded"
                        style={{
                          width: `${Math.min(
                            (prioData.metrics.critical_ambulance_avg_wait /
                              Math.max(fifoData.metrics.critical_ambulance_avg_wait, prioData.metrics.critical_ambulance_avg_wait, 1)) *
                              100,
                            100
                          )}%`,
                        }}
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-[11px] text-slate-300 mb-1">
                      <span>Normal User (P3) Wait</span>
                      <span>FIFO: {fifoData.metrics.normal_user_avg_wait}s | Prio: {prioData.metrics.normal_user_avg_wait}s</span>
                    </div>
                    <div className="w-full h-3 bg-slate-950 rounded-full overflow-hidden flex gap-0.5">
                      <div
                        className="bg-blue-500 h-full rounded"
                        style={{
                          width: `${Math.min(
                            (fifoData.metrics.normal_user_avg_wait /
                              Math.max(fifoData.metrics.normal_user_avg_wait, prioData.metrics.normal_user_avg_wait, 1)) *
                              100,
                            100
                          )}%`,
                        }}
                      />
                      <div
                        className="bg-amber-500 h-full rounded"
                        style={{
                          width: `${Math.min(
                            (prioData.metrics.normal_user_avg_wait /
                              Math.max(fifoData.metrics.normal_user_avg_wait, prioData.metrics.normal_user_avg_wait, 1)) *
                              100,
                            100
                          )}%`,
                        }}
                      />
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between text-[10px] text-slate-400 mt-4 pt-2 border-t border-slate-800">
                  <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded bg-blue-500" /> FIFO
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded bg-rose-500" /> Priority (P1)
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded bg-amber-500" /> Priority (P3)
                  </span>
                </div>
              </div>

              {/* Chart 2: Average Delay Comparison */}
              <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 flex flex-col justify-between">
                <div>
                  <h4 className="text-xs font-bold text-slate-200 mb-1 flex items-center gap-1.5">
                    <BarChart3 className="w-4 h-4 text-emerald-400" />
                    2. Average Delay Comparison (s)
                  </h4>
                  <p className="text-[11px] text-slate-400 mb-4">
                    Turnaround time from arrival to completion over the channel.
                  </p>
                </div>

                <div className="flex items-end justify-center gap-8 h-28 pt-2">
                  <div className="flex flex-col items-center gap-1.5">
                    <span className="font-mono text-xs text-blue-400">{fifoData.metrics.avg_delay}s</span>
                    <div
                      className="w-12 bg-blue-600 rounded-t"
                      style={{
                        height: `${Math.max((fifoData.metrics.avg_delay / Math.max(fifoData.metrics.avg_delay, prioData.metrics.avg_delay, 1)) * 75, 10)}px`,
                      }}
                    />
                    <span className="text-[11px] text-slate-400">FIFO</span>
                  </div>

                  <div className="flex flex-col items-center gap-1.5">
                    <span className="font-mono text-xs text-emerald-400">{prioData.metrics.avg_delay}s</span>
                    <div
                      className="w-12 bg-emerald-600 rounded-t"
                      style={{
                        height: `${Math.max((prioData.metrics.avg_delay / Math.max(fifoData.metrics.avg_delay, prioData.metrics.avg_delay, 1)) * 75, 10)}px`,
                      }}
                    />
                    <span className="text-[11px] text-slate-400">Priority</span>
                  </div>
                </div>

                <div className="text-[10px] text-slate-400 mt-4 pt-2 border-t border-slate-800 text-center">
                  Total average delay remains balanced across identical workloads.
                </div>
              </div>

              {/* Chart 3: Throughput Comparison */}
              <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 flex flex-col justify-between">
                <div>
                  <h4 className="text-xs font-bold text-slate-200 mb-1 flex items-center gap-1.5">
                    <BarChart3 className="w-4 h-4 text-purple-400" />
                    3. Throughput Comparison (msgs/s)
                  </h4>
                  <p className="text-[11px] text-slate-400 mb-4">
                    Rate of successfully delivered packets across simulation time.
                  </p>
                </div>

                <div className="flex items-end justify-center gap-8 h-28 pt-2">
                  <div className="flex flex-col items-center gap-1.5">
                    <span className="font-mono text-xs text-blue-400">{fifoData.metrics.throughput}</span>
                    <div
                      className="w-12 bg-blue-600 rounded-t"
                      style={{
                        height: `${Math.max((fifoData.metrics.throughput / Math.max(fifoData.metrics.throughput, prioData.metrics.throughput, 1)) * 75, 10)}px`,
                      }}
                    />
                    <span className="text-[11px] text-slate-400">FIFO</span>
                  </div>

                  <div className="flex flex-col items-center gap-1.5">
                    <span className="font-mono text-xs text-purple-400">{prioData.metrics.throughput}</span>
                    <div
                      className="w-12 bg-purple-600 rounded-t"
                      style={{
                        height: `${Math.max((prioData.metrics.throughput / Math.max(fifoData.metrics.throughput, prioData.metrics.throughput, 1)) * 75, 10)}px`,
                      }}
                    />
                    <span className="text-[11px] text-slate-400">Priority</span>
                  </div>
                </div>

                <div className="text-[10px] text-slate-400 mt-4 pt-2 border-t border-slate-800 text-center">
                  Throughput is governed by channel bandwidth and transmission delay.
                </div>
              </div>
            </div>

            {/* 4. Sequence Diff */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-4">
              <h4 className="text-xs font-bold text-slate-200 mb-2">
                4. Message Transmission Order Comparison
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">
                <div className="bg-slate-950 p-2.5 rounded border border-slate-800">
                  <span className="text-slate-500 block text-[11px] mb-1">FIFO Sequence:</span>
                  <span className="text-slate-300">
                    {fifoData.metrics.transmission_order.map((id) => `M${id}`).join(' -> ')}
                  </span>
                </div>
                <div className="bg-slate-950 p-2.5 rounded border border-slate-800">
                  <span className="text-emerald-400 block text-[11px] mb-1">Priority Sequence:</span>
                  <span className="text-emerald-300 font-semibold">
                    {prioData.metrics.transmission_order.map((id) => `M${id}`).join(' -> ')}
                  </span>
                </div>
              </div>
            </div>
          </section>
        )}
      </div>
    )}

        {/* ========================================================================= */}
        {/* TAB 2: PREDEFINED LOAD EXPERIMENTS (LOW, MEDIUM, HIGH) */}
        {/* ========================================================================= */}
        {activeTab === 'experiments' && (
          <div className="space-y-8">
            <section className="bg-slate-950 border border-slate-800 rounded-xl p-6 shadow-xl relative overflow-hidden">
              <div className="flex items-center gap-2 text-rose-400 font-mono text-xs uppercase font-semibold mb-2">
                <BarChart3 className="w-4 h-4" />
                <span>Controlled Traffic Experiments</span>
              </div>
              <h2 className="text-2xl font-extrabold text-white tracking-tight">
                Predefined Network Load Experiments
              </h2>
              <p className="text-slate-300 text-sm mt-2 leading-relaxed max-w-4xl">
                Three controlled experiments evaluate FIFO and Priority Scheduling under strictly equivalent channel conditions.
                Channel transmission time is held constant at <strong>1.0s</strong>, packet-loss probability is fixed at <strong>2.0%</strong>, and both schedulers operate on identical arrival timestamps.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-5 text-xs">
                <div className="bg-slate-900 border border-slate-800 p-3.5 rounded-lg">
                  <div className="font-bold text-cyan-400 text-sm">Experiment 1: Low Load</div>
                  <div className="text-slate-400 mt-1">8 messages over 20s (Sparse traffic, utilization ρ ≈ 0.40)</div>
                  <div className="text-[11px] text-slate-500 mt-2 font-mono">Contention: Minimal queueing</div>
                </div>

                <div className="bg-slate-900 border border-slate-800 p-3.5 rounded-lg">
                  <div className="font-bold text-amber-400 text-sm">Experiment 2: Medium Load</div>
                  <div className="text-slate-400 mt-1">15 messages over 15s (Moderate traffic, utilization ρ ≈ 1.00)</div>
                  <div className="text-[11px] text-slate-500 mt-2 font-mono">Contention: Moderate queue buildup</div>
                </div>

                <div className="bg-slate-900 border border-slate-800 p-3.5 rounded-lg">
                  <div className="font-bold text-rose-400 text-sm">Experiment 3: High Load</div>
                  <div className="text-slate-400 mt-1">25 messages over 12s (Heavy congestion, arrival rate &gt; capacity)</div>
                  <div className="text-[11px] text-slate-500 mt-2 font-mono">Contention: Severe buffer backlog</div>
                </div>
              </div>
            </section>

            {/* RESULTS TABLE */}
            <section className="bg-slate-950 border border-slate-800 rounded-xl p-6 shadow-lg">
              <div className="mb-4">
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Sliders className="w-5 h-5 text-cyan-400" />
                  Comprehensive Experiment Results Table
                </h3>
                <p className="text-xs text-slate-400">
                  Exact numerical simulation results comparing FIFO and Priority Scheduling across all three load levels.
                </p>
              </div>

              <div className="overflow-x-auto border border-slate-800 rounded-lg">
                <table className="w-full text-xs text-left">
                  <thead className="bg-slate-900 text-slate-300 font-semibold uppercase tracking-wider text-[11px] border-b border-slate-800">
                    <tr>
                      <th className="py-3 px-3">Experiment</th>
                      <th className="py-3 px-3">Scheduling Method</th>
                      <th className="py-3 px-3">Average Waiting Time</th>
                      <th className="py-3 px-3">Average Delay</th>
                      <th className="py-3 px-3">Throughput</th>
                      <th className="py-3 px-3">Packet Loss Rate</th>
                      <th className="py-3 px-3">Ambulance Avg Wait</th>
                      <th className="py-3 px-3 text-rose-300">Critical Ambulance Avg Wait</th>
                      <th className="py-3 px-3 text-blue-300">Normal User Avg Wait</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/70 font-mono">
                    {predefinedExperiments.map((exp) => (
                      <React.Fragment key={exp.name}>
                        {/* FIFO Row */}
                        <tr className="hover:bg-slate-900/40 bg-slate-950">
                          <td rowSpan={2} className="py-3 px-3 font-sans font-bold text-slate-200 border-r border-slate-800 align-middle">
                            <div>{exp.name}</div>
                            <div className="text-[11px] text-slate-400 font-normal font-mono">{exp.title}</div>
                          </td>
                          <td className="py-2.5 px-3 font-sans font-semibold text-blue-400 flex items-center gap-1.5">
                            <span className="w-2 h-2 rounded-full bg-blue-500" /> FIFO
                          </td>
                          <td className="py-2.5 px-3 text-slate-300">{exp.fifo.metrics.avg_waiting_time} s</td>
                          <td className="py-2.5 px-3 text-slate-300">{exp.fifo.metrics.avg_delay} s</td>
                          <td className="py-2.5 px-3 text-slate-300">{exp.fifo.metrics.throughput} msgs/s</td>
                          <td className="py-2.5 px-3 text-slate-400">{exp.fifo.metrics.loss_rate_percent}%</td>
                          <td className="py-2.5 px-3 text-slate-300">{exp.fifo.metrics.ambulance_avg_wait} s</td>
                          <td className="py-2.5 px-3 font-bold text-rose-400 bg-rose-950/20">{exp.fifo.metrics.critical_ambulance_avg_wait} s</td>
                          <td className="py-2.5 px-3 text-slate-400">{exp.fifo.metrics.normal_user_avg_wait} s</td>
                        </tr>

                        {/* Priority Row */}
                        <tr className="hover:bg-slate-900/60 bg-slate-900/30 border-b-2 border-slate-800">
                          <td className="py-2.5 px-3 font-sans font-semibold text-emerald-400 flex items-center gap-1.5">
                            <span className="w-2 h-2 rounded-full bg-emerald-500" /> Priority
                          </td>
                          <td className="py-2.5 px-3 text-slate-300">{exp.prio.metrics.avg_waiting_time} s</td>
                          <td className="py-2.5 px-3 text-slate-300">{exp.prio.metrics.avg_delay} s</td>
                          <td className="py-2.5 px-3 text-slate-300">{exp.prio.metrics.throughput} msgs/s</td>
                          <td className="py-2.5 px-3 text-slate-400">{exp.prio.metrics.loss_rate_percent}%</td>
                          <td className="py-2.5 px-3 text-slate-300">{exp.prio.metrics.ambulance_avg_wait} s</td>
                          <td className="py-2.5 px-3 font-bold text-emerald-400 bg-emerald-950/20">{exp.prio.metrics.critical_ambulance_avg_wait} s</td>
                          <td className="py-2.5 px-3 font-bold text-amber-400 bg-amber-950/20">{exp.prio.metrics.normal_user_avg_wait} s</td>
                        </tr>
                      </React.Fragment>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            {/* COMPARATIVE PLOTS */}
            <section className="bg-slate-950 border border-slate-800 rounded-xl p-6 shadow-lg space-y-6">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-emerald-400" />
                  Comparative Performance Plots
                </h3>
                <p className="text-xs text-slate-400">
                  Visual plots comparing FIFO and Priority Scheduling across increasing traffic loads.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Plot 1: Critical Ambulance Waiting Time */}
                <div className="bg-slate-900 border border-slate-800 p-4 rounded-lg flex flex-col justify-between">
                  <div>
                    <h4 className="text-xs font-bold text-slate-200 mb-1 flex items-center gap-1.5">
                      <ShieldAlert className="w-4 h-4 text-rose-500" />
                      Plot 1: Critical Ambulance (P1) Waiting Time (s)
                    </h4>
                    <p className="text-[11px] text-slate-400 mb-4">
                      Shows how emergency packet queuing delay is impacted as load escalates.
                    </p>
                  </div>

                  <div className="space-y-4 font-mono text-xs">
                    {predefinedExperiments.map((exp) => (
                      <div key={exp.name} className="space-y-1">
                        <div className="flex justify-between text-[11px] text-slate-300 font-sans">
                          <span className="font-semibold">{exp.title}</span>
                          <span className="text-slate-400 font-mono">
                            FIFO: <span className="text-rose-400 font-bold">{exp.fifo.metrics.critical_ambulance_avg_wait}s</span> | Prio: <span className="text-emerald-400 font-bold">{exp.prio.metrics.critical_ambulance_avg_wait}s</span>
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-12 text-[10px] text-slate-500">FIFO</div>
                          <div className="flex-1 bg-slate-950 h-3 rounded overflow-hidden">
                            <div
                              className="bg-blue-600 h-full rounded"
                              style={{ width: `${Math.min((exp.fifo.metrics.critical_ambulance_avg_wait / 10) * 100, 100)}%` }}
                            />
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-12 text-[10px] text-emerald-400">Priority</div>
                          <div className="flex-1 bg-slate-950 h-3 rounded overflow-hidden">
                            <div
                              className="bg-emerald-500 h-full rounded"
                              style={{ width: `${Math.min((exp.prio.metrics.critical_ambulance_avg_wait / 10) * 100, 100)}%` }}
                            />
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="flex justify-between text-[10px] text-slate-500 mt-4 pt-2 border-t border-slate-800">
                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-blue-600" /> FIFO</span>
                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-emerald-500" /> Priority (P1)</span>
                  </div>
                </div>

                {/* Plot 2: Normal User Waiting Time */}
                <div className="bg-slate-900 border border-slate-800 p-4 rounded-lg flex flex-col justify-between">
                  <div>
                    <h4 className="text-xs font-bold text-slate-200 mb-1 flex items-center gap-1.5">
                      <Users className="w-4 h-4 text-blue-400" />
                      Plot 2: Normal User (P3) Waiting Time (s)
                    </h4>
                    <p className="text-[11px] text-slate-400 mb-4">
                      Shows the waiting penalty absorbed by low-priority traffic under priority scheduling.
                    </p>
                  </div>

                  <div className="space-y-4 font-mono text-xs">
                    {predefinedExperiments.map((exp) => (
                      <div key={exp.name} className="space-y-1">
                        <div className="flex justify-between text-[11px] text-slate-300 font-sans">
                          <span className="font-semibold">{exp.title}</span>
                          <span className="text-slate-400 font-mono">
                            FIFO: <span className="text-slate-300 font-bold">{exp.fifo.metrics.normal_user_avg_wait}s</span> | Prio: <span className="text-amber-400 font-bold">{exp.prio.metrics.normal_user_avg_wait}s</span>
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-12 text-[10px] text-slate-500">FIFO</div>
                          <div className="flex-1 bg-slate-950 h-3 rounded overflow-hidden">
                            <div
                              className="bg-blue-600 h-full rounded"
                              style={{ width: `${Math.min((exp.fifo.metrics.normal_user_avg_wait / 12) * 100, 100)}%` }}
                            />
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-12 text-[10px] text-amber-400">Priority</div>
                          <div className="flex-1 bg-slate-950 h-3 rounded overflow-hidden">
                            <div
                              className="bg-amber-500 h-full rounded"
                              style={{ width: `${Math.min((exp.prio.metrics.normal_user_avg_wait / 12) * 100, 100)}%` }}
                            />
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="flex justify-between text-[10px] text-slate-500 mt-4 pt-2 border-t border-slate-800">
                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-blue-600" /> FIFO</span>
                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-amber-500" /> Priority (P3)</span>
                  </div>
                </div>

                {/* Plot 3: Average Delay */}
                <div className="bg-slate-900 border border-slate-800 p-4 rounded-lg flex flex-col justify-between">
                  <div>
                    <h4 className="text-xs font-bold text-slate-200 mb-1 flex items-center gap-1.5">
                      <Clock className="w-4 h-4 text-cyan-400" />
                      Plot 3: Overall Average Turnaround Delay (s)
                    </h4>
                    <p className="text-[11px] text-slate-400 mb-4">
                      Total average latency across all packets in the system.
                    </p>
                  </div>

                  <div className="space-y-4 font-mono text-xs">
                    {predefinedExperiments.map((exp) => (
                      <div key={exp.name} className="space-y-1">
                        <div className="flex justify-between text-[11px] text-slate-300 font-sans">
                          <span className="font-semibold">{exp.title}</span>
                          <span className="text-slate-400 font-mono">
                            FIFO: {exp.fifo.metrics.avg_delay}s | Prio: {exp.prio.metrics.avg_delay}s
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-12 text-[10px] text-slate-500">FIFO</div>
                          <div className="flex-1 bg-slate-950 h-3 rounded overflow-hidden">
                            <div
                              className="bg-blue-600 h-full rounded"
                              style={{ width: `${Math.min((exp.fifo.metrics.avg_delay / 14) * 100, 100)}%` }}
                            />
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-12 text-[10px] text-cyan-400">Priority</div>
                          <div className="flex-1 bg-slate-950 h-3 rounded overflow-hidden">
                            <div
                              className="bg-cyan-500 h-full rounded"
                              style={{ width: `${Math.min((exp.prio.metrics.avg_delay / 14) * 100, 100)}%` }}
                            />
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="text-[10px] text-slate-500 mt-4 pt-2 border-t border-slate-800 text-center">
                    Overall average delay is nearly identical between algorithms for the same workload.
                  </div>
                </div>

                {/* Plot 4: Channel Throughput */}
                <div className="bg-slate-900 border border-slate-800 p-4 rounded-lg flex flex-col justify-between">
                  <div>
                    <h4 className="text-xs font-bold text-slate-200 mb-1 flex items-center gap-1.5">
                      <Zap className="w-4 h-4 text-purple-400" />
                      Plot 4: Channel Throughput (msgs/s)
                    </h4>
                    <p className="text-[11px] text-slate-400 mb-4">
                      Delivered messages per unit simulation time.
                    </p>
                  </div>

                  <div className="space-y-4 font-mono text-xs">
                    {predefinedExperiments.map((exp) => (
                      <div key={exp.name} className="space-y-1">
                        <div className="flex justify-between text-[11px] text-slate-300 font-sans">
                          <span className="font-semibold">{exp.title}</span>
                          <span className="text-slate-400 font-mono">
                            FIFO: {exp.fifo.metrics.throughput} | Prio: {exp.prio.metrics.throughput} msgs/s
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-12 text-[10px] text-slate-500">FIFO</div>
                          <div className="flex-1 bg-slate-950 h-3 rounded overflow-hidden">
                            <div
                              className="bg-purple-600 h-full rounded"
                              style={{ width: `${Math.min((exp.fifo.metrics.throughput / 1.5) * 100, 100)}%` }}
                            />
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-12 text-[10px] text-purple-400">Priority</div>
                          <div className="flex-1 bg-slate-950 h-3 rounded overflow-hidden">
                            <div
                              className="bg-purple-400 h-full rounded"
                              style={{ width: `${Math.min((exp.prio.metrics.throughput / 1.5) * 100, 100)}%` }}
                            />
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="text-[10px] text-slate-400 mt-4 pt-2 border-t border-slate-800 text-center">
                    Throughput is bounded by physical channel capacity and packet service rate.
                  </div>
                </div>
              </div>
            </section>
          </div>
        )}
      </main>
    </div>
  );
}

