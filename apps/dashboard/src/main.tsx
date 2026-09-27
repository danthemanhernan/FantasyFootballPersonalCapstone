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
type PushMessage = { kind: "snapshot"; sequence: number; state: Snapshot };

const apiUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const websocketUrl = apiUrl.replace(/^http/, "ws") + "/ws/dashboard";

function App() {
  const [snapshot, setSnapshot] = useState<Snapshot>({ teams: [] });
  const [connection, setConnection] = useState("connecting");

  useEffect(() => {
    let socket: WebSocket | undefined;
    let retry: number | undefined;
    let disposed = false;

    const connect = () => {
      if (disposed) return;
      setConnection("connecting");
      socket = new WebSocket(websocketUrl);
      socket.onopen = () => setConnection("live");
      socket.onmessage = (event) => {
        const message = JSON.parse(event.data) as PushMessage;
        if (message.kind === "snapshot") setSnapshot(message.state);
      };
      socket.onerror = () => socket?.close();
      socket.onclose = () => {
        setConnection("reconnecting");
        retry = window.setTimeout(connect, 1500);
      };
    };

    fetch(`${apiUrl}/dashboard`)
      .then((response) => response.json())
      .then((state: Snapshot) => setSnapshot(state))
      .catch(() => setConnection("offline"));
    connect();
    return () => {
      disposed = true;
      if (retry !== undefined) window.clearTimeout(retry);
      socket?.close();
    };
  }, []);

  const playerCount = snapshot.teams.reduce((total, team) => total + team.players.length, 0);

  return (
    <main>
      <header className="hero">
        <div>
          <p className="eyebrow">FANTASY OPERATIONS</p>
          <h1>Sunday Command Center</h1>
          <p className="lede">Every league, roster, and live signal in one place.</p>
        </div>
        <span className={`status ${connection}`}>{connection}</span>
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
