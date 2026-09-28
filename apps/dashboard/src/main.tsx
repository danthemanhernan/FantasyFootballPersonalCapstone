import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

type Player = { player_id: string; name: string; position: string; pro_team: string };
type FantasyTeam = {
  league_id: string;
  team_id: string;
  league_name: string;
  team_name: string;
  season: number;
  points: number;
  players: Player[];
};
type Snapshot = { teams: FantasyTeam[] };
type PushMessage =
  | { kind: "snapshot"; sequence: number; state: Snapshot }
  | { kind: "projection_delta"; sequence: number; delta: Record<string, unknown> };

const apiUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const websocketUrl = apiUrl.replace(/^http/, "ws") + "/ws/dashboard";

function App() {
  const [snapshot, setSnapshot] = useState<Snapshot>({ teams: [] });
  const [connection, setConnection] = useState("offline");
  const [token, setToken] = useState(() => localStorage.getItem("fantasy-hud.token") || "");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authStatus, setAuthStatus] = useState("");

  useEffect(() => {
    if (!token) return;
    let socket: WebSocket | undefined;
    let retry: number | undefined;
    let disposed = false;

    const connect = () => {
      if (disposed) return;
      setConnection("connecting");
      socket = new WebSocket(`${websocketUrl}?token=${encodeURIComponent(token)}`);
      socket.onopen = () => setConnection("live");
      socket.onmessage = (event) => {
        const message = JSON.parse(event.data) as PushMessage;
        if (message.kind === "snapshot") setSnapshot(message.state);
        if (message.kind === "projection_delta") {
          fetch(`${apiUrl}/dashboard`, { headers: { Authorization: `Bearer ${token}` } })
            .then((response) => response.json())
            .then((state: Snapshot) => setSnapshot(state));
        }
      };
      socket.onerror = () => socket?.close();
      socket.onclose = () => {
        if (disposed) return;
        setConnection("reconnecting");
        retry = window.setTimeout(connect, 1500);
      };
    };

    fetch(`${apiUrl}/dashboard`, { headers: { Authorization: `Bearer ${token}` } })
      .then((response) => response.json())
      .then((state: Snapshot) => setSnapshot(state))
      .catch(() => setConnection("offline"));
    connect();
    return () => {
      disposed = true;
      if (retry !== undefined) window.clearTimeout(retry);
      socket?.close();
    };
  }, [token]);

  const authenticate = async (mode: "register" | "login") => {
    setAuthStatus("Working...");
    const response = await fetch(
      `${apiUrl}${mode === "register" ? "/accounts/register" : "/auth/token"}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      },
    );
    if (!response.ok) {
      setAuthStatus(`Authentication failed (${response.status})`);
      return;
    }
    const result = await response.json() as { access_token: string };
    localStorage.setItem("fantasy-hud.token", result.access_token);
    setToken(result.access_token);
    setAuthStatus("");
  };

  if (!token) {
    return (
      <main className="auth-shell">
        <section className="auth-card">
          <p className="eyebrow">FANTASY OPERATIONS</p>
          <h1>Sunday Command Center</h1>
          <p className="lede">Create a local account to isolate and protect your leagues.</p>
          <label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} /></label>
          <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>
          <div className="auth-actions">
            <button onClick={() => authenticate("login")}>Sign in</button>
            <button className="secondary" onClick={() => authenticate("register")}>Create account</button>
          </div>
          <p>{authStatus}</p>
        </section>
      </main>
    );
  }

  const playerCount = snapshot.teams.reduce((total, team) => total + team.players.length, 0);

  return (
    <main>
      <header className="hero">
        <div>
          <p className="eyebrow">FANTASY OPERATIONS</p>
          <h1>Sunday Command Center</h1>
          <p className="lede">Every league, roster, and live signal in one place.</p>
        </div>
        <div className="session-controls">
          <span className={`status ${connection}`}>{connection}</span>
          <button className="secondary" onClick={() => {
            localStorage.removeItem("fantasy-hud.token");
            setToken("");
          }}>Sign out</button>
        </div>
      </header>

      <section className="metrics">
        <article><strong>{snapshot.teams.length}</strong><span>Tracked teams</span></article>
        <article><strong>{playerCount}</strong><span>Rostered players</span></article>
        <article><strong>{new Set(snapshot.teams.map((team) => team.league_id)).size}</strong><span>Leagues</span></article>
      </section>

      <section className="league-grid">
        {snapshot.teams.map((team) => (
          <article className="team-card" key={`${team.league_id}:${team.team_id}`}>
            <header>
              <div><p>{team.league_name}</p><h2>{team.team_name}</h2></div>
              <strong>{team.points.toFixed(1)} FP</strong>
            </header>
            <div className="roster">
              {team.players.map((player) => (
                <div className="player" key={player.player_id}>
                  <b>{player.position}</b><span>{player.name}</span><small>{player.pro_team}</small>
                </div>
              ))}
            </div>
          </article>
        ))}
        {snapshot.teams.length === 0 && (
          <article className="empty">
            <h2>No synced teams yet</h2>
            <p>Start the backend, then use the Chrome extension to sync an ESPN team.</p>
          </article>
        )}
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);
