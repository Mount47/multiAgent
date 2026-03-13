const { useEffect, useMemo, useRef, useState, useCallback } = React;

/* ═══════════════════════════════════════════════════════
   Workflow Graph Data (matches config/workflows.yaml)
   ═══════════════════════════════════════════════════════ */

const NODE_W = 154;
const NODE_H = 48;
const NODE_R = 8;

const NODES = [
  { id: "requirements_analysis", label: "Requirements",  agent: "PM",       x: 173, y: 15  },
  { id: "architecture_design",   label: "Architecture",   agent: "Architect", x: 173, y: 105 },
  { id: "coding",                label: "Coding",         agent: "Coder",     x: 173, y: 195 },
  { id: "testing",               label: "Testing",        agent: "Tester",    x: 173, y: 285 },
  { id: "code_review",           label: "Code Review",    agent: "Reviewer",  x: 48,  y: 390 },
  { id: "revision",              label: "Revision",       agent: "Coder",     x: 298, y: 390 },
  { id: "approved",              label: "Approved",       agent: null,        x: 48,  y: 500 },
];

// Edge endpoints computed from node centers
const cx = (n) => n.x + NODE_W / 2;
const cy = (n) => n.y + NODE_H / 2;
const bot = (n) => ({ x: cx(n), y: n.y + NODE_H });
const top_ = (n) => ({ x: cx(n), y: n.y });
const right_ = (n) => ({ x: n.x + NODE_W, y: cy(n) });
const left_ = (n) => ({ x: n.x, y: cy(n) });

const N = Object.fromEntries(NODES.map((n) => [n.id, n]));

const EDGES = [
  { id: "e0", from: "requirements_analysis", to: "architecture_design", label: "" },
  { id: "e1", from: "architecture_design",   to: "coding",              label: "" },
  { id: "e2", from: "coding",                to: "testing",             label: "" },
  { id: "e3", from: "testing",               to: "code_review",         label: "passed",   guard: "tests_passed" },
  { id: "e4", from: "testing",               to: "revision",            label: "failed",   guard: "tests_failed" },
  { id: "e5", from: "code_review",           to: "approved",            label: "approved",  guard: "review_approved" },
  { id: "e6", from: "code_review",           to: "revision",            label: "revise",   guard: "review_revision_needed" },
  { id: "e7", from: "revision",              to: "testing",             label: "" },
];

function edgePath(edge) {
  const s = N[edge.from];
  const t = N[edge.to];

  // Straight vertical edges (e0, e1, e2)
  if (edge.from === "requirements_analysis" || edge.from === "architecture_design" || edge.from === "coding") {
    const p1 = bot(s), p2 = top_(t);
    return `M ${p1.x},${p1.y} L ${p2.x},${p2.y}`;
  }
  // testing → code_review (diagonal left)
  if (edge.id === "e3") {
    const p1 = { x: cx(s) - 30, y: s.y + NODE_H };
    const p2 = { x: cx(t) + 20, y: t.y };
    return `M ${p1.x},${p1.y} C ${p1.x},${p1.y + 40} ${p2.x},${p2.y - 40} ${p2.x},${p2.y}`;
  }
  // testing → revision (diagonal right)
  if (edge.id === "e4") {
    const p1 = { x: cx(s) + 30, y: s.y + NODE_H };
    const p2 = { x: cx(t) - 20, y: t.y };
    return `M ${p1.x},${p1.y} C ${p1.x},${p1.y + 40} ${p2.x},${p2.y - 40} ${p2.x},${p2.y}`;
  }
  // code_review → approved (straight down)
  if (edge.id === "e5") {
    const p1 = bot(s), p2 = top_(t);
    return `M ${p1.x},${p1.y} L ${p2.x},${p2.y}`;
  }
  // code_review → revision (horizontal right)
  if (edge.id === "e6") {
    const p1 = right_(s), p2 = left_(t);
    return `M ${p1.x},${p1.y} L ${p2.x},${p2.y}`;
  }
  // revision → testing (curved back up)
  if (edge.id === "e7") {
    const p1 = { x: t.x + NODE_W + 4, y: cy(t) };
    const p2 = top_(s);
    return `M ${p2.x},${p2.y} C ${p2.x + 80},${p2.y - 60} ${p1.x + 30},${p1.y + 50} ${p1.x},${p1.y}`;
  }
  // fallback
  const p1 = bot(s), p2 = top_(t);
  return `M ${p1.x},${p1.y} L ${p2.x},${p2.y}`;
}

function edgeLabelPos(edge) {
  const s = N[edge.from];
  const t = N[edge.to];
  if (edge.id === "e3") return { x: (cx(s) - 30 + cx(t) + 20) / 2 - 18, y: (s.y + NODE_H + t.y) / 2 + 4 };
  if (edge.id === "e4") return { x: (cx(s) + 30 + cx(t) - 20) / 2 + 2,  y: (s.y + NODE_H + t.y) / 2 + 4 };
  if (edge.id === "e5") return { x: cx(s) - 38, y: (bot(s).y + top_(t).y) / 2 + 4 };
  if (edge.id === "e6") return { x: (right_(s).x + left_(t).x) / 2 - 14, y: cy(s) - 8 };
  return { x: 0, y: 0 };
}

/* ═══════════════════════════════════════════════════════
   WorkflowGraph Component (Pure SVG)
   ═══════════════════════════════════════════════════════ */

function WorkflowGraph({ activeState, visitedStates }) {
  const nodeStatus = (id) => {
    if (id === activeState) return "active";
    if (visitedStates.has(id)) return "visited";
    return "idle";
  };

  const edgeStatus = (edge) => {
    // An edge is "active" if its target is the active state
    if (edge.to === activeState && (visitedStates.has(edge.from) || edge.from === activeState)) return "active";
    // An edge is "visited" if both endpoints have been visited
    if (visitedStates.has(edge.from) && visitedStates.has(edge.to)) return "visited";
    return "idle";
  };

  const nodeColors = {
    idle:    { fill: "#15233e", stroke: "#2a3f65", text: "#8097bf", agentBg: "#1a2c4a" },
    active:  { fill: "#122840", stroke: "#49c6e5", text: "#e8eefc", agentBg: "#1a3850" },
    visited: { fill: "#132e20", stroke: "#2f8a5a", text: "#a8dbc0", agentBg: "#1a3d2a" },
  };

  const edgeColors = {
    idle:    "#2a3f65",
    active:  "#49c6e5",
    visited: "#2f8a5a",
  };

  return (
    <svg viewBox="0 0 500 560" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <marker id="ah-idle" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
          <polygon points="0 0.5, 7 3, 0 5.5" fill="#2a3f65" />
        </marker>
        <marker id="ah-active" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
          <polygon points="0 0.5, 7 3, 0 5.5" fill="#49c6e5" />
        </marker>
        <marker id="ah-visited" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
          <polygon points="0 0.5, 7 3, 0 5.5" fill="#2f8a5a" />
        </marker>
      </defs>

      {/* Edges (behind nodes) */}
      {EDGES.map((edge) => {
        const st = edgeStatus(edge);
        return (
          <g key={edge.id}>
            <path
              d={edgePath(edge)}
              stroke={edgeColors[st]}
              strokeWidth={st === "active" ? 2.5 : 1.5}
              fill="none"
              markerEnd={`url(#ah-${st})`}
              style={st === "active" ? { filter: "drop-shadow(0 0 4px #49c6e5)" } : {}}
            />
            {edge.label && (
              <text
                x={edgeLabelPos(edge).x}
                y={edgeLabelPos(edge).y}
                fill={st === "idle" ? "#5a7099" : edgeColors[st]}
                fontSize="11"
                fontWeight="500"
                fontFamily="inherit"
              >
                {edge.label}
              </text>
            )}
          </g>
        );
      })}

      {/* Nodes */}
      {NODES.map((node) => {
        const st = nodeStatus(node.id);
        const c = nodeColors[st];
        const isTerminal = node.id === "approved";
        return (
          <g key={node.id} className={st === "active" ? "node-active-glow" : ""}>
            <rect
              x={node.x} y={node.y}
              width={NODE_W} height={NODE_H}
              rx={NODE_R}
              fill={st === "visited" && isTerminal ? "#2a2a14" : c.fill}
              stroke={st === "visited" && isTerminal ? "#d4a017" : c.stroke}
              strokeWidth={st === "active" ? 2 : 1.2}
            />
            {/* State label */}
            <text
              x={cx(node)} y={node.y + (node.agent ? 19 : 24)}
              textAnchor="middle"
              fill={st === "visited" && isTerminal ? "#ffd166" : c.text}
              fontSize="13"
              fontWeight="600"
              fontFamily="inherit"
            >
              {isTerminal && st === "visited" ? "Approved ✓" : node.label}
            </text>
            {/* Agent badge */}
            {node.agent && (
              <React.Fragment>
                <rect
                  x={cx(node) - 24} y={node.y + 26}
                  width="48" height="16"
                  rx="4"
                  fill={c.agentBg}
                  stroke={c.stroke}
                  strokeWidth="0.5"
                />
                <text
                  x={cx(node)} y={node.y + 38}
                  textAnchor="middle"
                  fill={c.text}
                  fontSize="9.5"
                  fontWeight="500"
                  fontFamily="inherit"
                  opacity="0.85"
                >
                  {node.agent}
                </text>
              </React.Fragment>
            )}
          </g>
        );
      })}
    </svg>
  );
}

/* ═══════════════════════════════════════════════════════
   EventItem Component
   ═══════════════════════════════════════════════════════ */

const AGENT_COLORS = {
  product_manager: "#4a9eff",
  architect: "#c77dff",
  coder: "#41d39c",
  tester: "#ffd166",
  reviewer: "#49c6e5",
};

function EventItem({ event }) {
  const time = useMemo(() => new Date(event.timestamp).toLocaleTimeString(), [event.timestamp]);
  const color = AGENT_COLORS[event.source] || "#9bb0d9";
  return (
    <div className="event">
      <div className="meta">
        [{time}] <span style={{ color, fontWeight: 600 }}>{event.source}</span>
      </div>
      <div>{event.content}</div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   App Component
   ═══════════════════════════════════════════════════════ */

function App() {
  const [taskText, setTaskText] = useState("Build a Python function that checks if a string is a palindrome, with tests.");
  const [providers, setProviders] = useState([]);
  const [provider, setProvider] = useState("");
  const [taskId, setTaskId] = useState("-");
  const [status, setStatus] = useState("idle");
  const [events, setEvents] = useState([]);
  const [error, setError] = useState("");

  // Workflow graph state
  const [activeState, setActiveState] = useState(null);
  const [visitedStates, setVisitedStates] = useState(new Set());

  const wsRef = useRef(null);
  const eventsRef = useRef(null);

  useEffect(() => {
    fetch("/api/providers")
      .then((r) => r.json())
      .then((data) => {
        setProviders(data);
        if (data.length > 0) setProvider(data[0].name);
      })
      .catch((e) => setError(`Load providers failed: ${e.message}`));
  }, []);

  useEffect(() => {
    if (!eventsRef.current) return;
    eventsRef.current.scrollTop = eventsRef.current.scrollHeight;
  }, [events]);

  useEffect(() => {
    return () => { if (wsRef.current) wsRef.current.close(); };
  }, []);

  const connectStream = useCallback((id) => {
    if (wsRef.current) wsRef.current.close();
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${window.location.host}/api/tasks/ws/${id}`);

    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.type === "event") {
        setEvents((prev) => [...prev, msg]);
      } else if (msg.type === "state_change") {
        setActiveState((prev) => {
          if (prev) setVisitedStates((vs) => new Set([...vs, prev]));
          return msg.state;
        });
      } else if (msg.type === "status") {
        setStatus(msg.status);
        if (msg.status === "completed") {
          // Mark final active state as visited too
          setActiveState((prev) => {
            if (prev) setVisitedStates((vs) => new Set([...vs, prev, "approved"]));
            return "approved";
          });
        }
        if (msg.error) setError(msg.error);
      }
    };

    ws.onerror = () => setError("WebSocket disconnected.");
    wsRef.current = ws;
  }, []);

  const createTask = async () => {
    setEvents([]);
    setError("");
    setActiveState(null);
    setVisitedStates(new Set());
    try {
      const res = await fetch("/api/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task: taskText.trim(), provider: provider || null }),
      });
      if (!res.ok) throw new Error((await res.text()) || "create task failed");
      const data = await res.json();
      setTaskId(data.task_id);
      setStatus(data.status);
      connectStream(data.task_id);
    } catch (e) {
      setError(e.message);
    }
  };

  const statusClass = `status-${status}`;

  return (
    <div className="wrap">
      {/* ── Left: Controls ── */}
      <section className="card">
        <h1>Multi-Agent Console</h1>
        <div className="muted">Create a task and watch agents collaborate in real-time.</div>
        <label htmlFor="task">Task Description</label>
        <textarea id="task" value={taskText} onChange={(e) => setTaskText(e.target.value)} />
        <label htmlFor="provider">Model Provider</label>
        <select id="provider" value={provider} onChange={(e) => setProvider(e.target.value)}>
          {providers.map((p) => (
            <option key={p.name} value={p.name}>
              {p.name} ({p.model})
            </option>
          ))}
        </select>
        <button onClick={createTask}>Start Task</button>
        <div className="row">
          <span className="muted">Task ID</span>
          <span className="muted" style={{ fontSize: 11 }}>{taskId.slice(0, 8)}</span>
        </div>
        <div className="row">
          <span className="muted">Status</span>
          <span className={statusClass}>{status}</span>
        </div>
        {error ? <div className="status-failed" style={{ marginTop: 6, fontSize: 13 }}>{error}</div> : null}
      </section>

      {/* ── Center: Workflow Graph ── */}
      <section className="card graph-panel">
        <h1>Workflow</h1>
        <div className="graph-container">
          <WorkflowGraph activeState={activeState} visitedStates={visitedStates} />
        </div>
      </section>

      {/* ── Right: Events ── */}
      <section className="card events-panel">
        <h1>Agent Output</h1>
        <div id="events" ref={eventsRef}>
          {events.length === 0 && (
            <div className="muted" style={{ textAlign: "center", marginTop: 20 }}>
              Start a task to see agent outputs here.
            </div>
          )}
          {events.map((event, idx) => (
            <EventItem key={`${event.timestamp}-${idx}`} event={event} />
          ))}
        </div>
      </section>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
