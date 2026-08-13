import type { Player } from "../types";
import { TouchdownNotification } from "./TouchdownNotification";

type Props = {
  players: Player[];
  latestEvent: string;
  touchdownMessage: string | null;
};

export function Hud({ players, latestEvent, touchdownMessage }: Props) {
  return (
    <main className="hud">
      <header className="hud-header">
        <div>
          <p className="eyebrow">FANTASY FOOTBALL HUD</p>
          <h1>Sunday Night Live</h1>
        </div>
        <span className="live-pill"><span />LIVE</span>
      </header>

      <section className="score-card">
        <div>
          <p className="muted">YOUR TEAM</p>
          <strong>Dan's Dream Team</strong>
        </div>
        <div className="team-score">0 - 0</div>
        <div className="opponent">
          <p className="muted">OPPONENT</p>
          <strong>Sunday Scaries</strong>
        </div>
      </section>

      <TouchdownNotification message={touchdownMessage} />

      <section className="players" aria-label="Fantasy players">
        {players.map((player) => (
          <article className="player-row" key={player.id}>
            <div className="player-badge">{player.position}</div>
            <div className="player-info">
              <strong>{player.name}</strong>
              <span>{player.team}</span>
            </div>
            <output>{player.fantasyPoints.toFixed(1)} <small>FP</small></output>
          </article>
        ))}
      </section>

      <footer className="event-footer">
        <span className="muted">LATEST PLAY</span>
        <span>{latestEvent}</span>
      </footer>
    </main>
  );
}
