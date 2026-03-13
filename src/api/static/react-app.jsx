const { useEffect, useMemo, useRef, useState } = React;

function EventItem({ event }) {
  const time = useMemo(() => new Date(event.timestamp).toLocaleTimeString(), [event.timestamp]);
  return (
    <div className="event">
      <div className="meta">[{time}] {event.source}</div>
      <div>{event.content}</div>
    </div>
  );
}

function App() {
  const [taskText, setTaskText] = useState("Build a Python hello world function with tests.");
  const [providers, setProviders] = useState([]);
  const [provider, setProvider] = useState("");
  const [taskId, setTaskId] = useState("-");
  const [status, setStatus] = useState("idle");
  const [events, setEvents] = useState([]);
  const [error, setError] = useState("");
  const wsRef = useRef(null);
  const eventsRef = useRef(null);

  useEffect(() => {
    fetch("/api/providers")
      .then((r) => r.json())
      .then((data) => {
        setProviders(data);
        if (data.length > 0) {
          setProvider(data[0].name);
        }
      })
      .catch((e) => {
        setError(`Load providers failed: ${e.message}`);
      });
  }, []);

  useEffect(() => {
    if (!eventsRef.current) return;
    eventsRef.current.scrollTop = eventsRef.current.scrollHeight;
  }, [events]);

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const statusClass = `status-${status}`;

  const connectStream = (id) => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${window.location.host}/api/tasks/ws/${id}`);
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.type === "event") {
        setEvents((prev) => [...prev, msg]);
      } else if (msg.type === "status") {
        setStatus(msg.status);
        if (msg.error) {
          setError(msg.error);
        }
      }
    };
    ws.onerror = () => {
      setError("WebSocket disconnected.");
    };
    wsRef.current = ws;
  };

  const createTask = async () => {
    setEvents([]);
    setError("");
    try {
      const res = await fetch("/api/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          task: taskText.trim(),
          provider: provider || null,
        }),
      });
      if (!res.ok) {
        const msg = await res.text();
        throw new Error(msg || "create task failed");
      }
      const data = await res.json();
      setTaskId(data.task_id);
      setStatus(data.status);
      connectStream(data.task_id);
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div className="wrap">
      <section className="card">
        <h1>Multi-Agent Console (React)</h1>
        <div className="muted">Create a task and watch real-time agent outputs.</div>
        <label htmlFor="task">Task</label>
        <textarea
          id="task"
          value={taskText}
          onChange={(e) => setTaskText(e.target.value)}
        />
        <label htmlFor="provider">Provider</label>
        <select
          id="provider"
          value={provider}
          onChange={(e) => setProvider(e.target.value)}
        >
          {providers.map((p) => {
            const toolTag = p.capabilities.function_calling ? "tools" : "no-tools";
            return (
              <option key={p.name} value={p.name}>
                {p.name} ({p.model}, {toolTag})
              </option>
            );
          })}
        </select>
        <button onClick={createTask}>Start Task</button>
        <div className="row">
          <span className="muted">Task ID</span>
          <span className="muted">{taskId}</span>
        </div>
        <div className="row">
          <span className="muted">Status</span>
          <span className={statusClass}>{status}</span>
        </div>
        {error ? <div className="status-failed">{error}</div> : null}
      </section>
      <section className="card">
        <div id="events" ref={eventsRef}>
          {events.map((event, idx) => (
            <EventItem key={`${event.timestamp}-${idx}`} event={event} />
          ))}
        </div>
      </section>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);

