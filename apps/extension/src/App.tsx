import { useEffect, useState } from "react";
import { applyEvent, createEvent, nextEvent, samplePlayers } from "./simulator";
import type { Player, SimulatedEvent } from "./types";
import { Hud } from "./components/Hud";

const describeEvent = (event: SimulatedEvent) => {
  if (event.kind === "pass") return "Complete pass for " + event.yards + " yards";
  if (event.kind === "rush") return "Rush for " + event.yards + " yards";
  return event.description;
};

export default function App() {
  const [players, setPlayers] = useState<Player[]>(samplePlayers);
  const [eventIndex, setEventIndex] = useState(0);
  const [latestEvent, setLatestEvent] = useState("Waiting for kickoff...");
  const [touchdownMessage, setTouchdownMessage] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    if (!running) return;
    const timer = window.setInterval(() => {
      const event = nextEvent(eventIndex);
      setPlayers((current) => applyEvent(current, event));
      setLatestEvent(describeEvent(event));
      setTouchdownMessage(event.kind === "touchdown" ? event.description : null);
      setEventIndex((current) => current + 1);
    }, 2500);
    return () => window.clearInterval(timer);
  }, [running, eventIndex]);

  const reset = () => {
    setPlayers(samplePlayers);
    setEventIndex(0);
    setLatestEvent("Waiting for kickoff...");
    setTouchdownMessage(null);
    setRunning(false);
  };

  return (
    <div className="app-shell">
      <Hud players={players} latestEvent={latestEvent} touchdownMessage={touchdownMessage} />
      <div className="controls">
        <button onClick={() => setRunning((value) => !value)}>{running ? "Pause" : "Start simulation"}</button>
        <button className="secondary" onClick={reset}>Reset</button>
      </div>
    </div>
  );
}
