import { useEffect, useState } from "react";
import { Hud } from "./components/Hud";
import type { ScoringRules } from "./scoring";
import {
  applyEvent,
  nextEvent,
  playersAtCursor,
  samplePlayers,
} from "./simulator";
import {
  browserStorage,
  defaultSnapshot,
  loadSnapshot,
  saveSnapshot,
  SNAPSHOT_KEY,
  type PersistedSnapshot,
} from "./storage";
import type { Player, SimulatedEvent } from "./types";

const describeEvent = (event: SimulatedEvent) => {
  if (event.kind === "pass")
    return "Complete pass for " + event.yards + " yards";
  if (event.kind === "rush") return "Rush for " + event.yards + " yards";
  return event.description;
};

export default function App() {
  const [players, setPlayers] = useState<Player[]>(samplePlayers);
  const [eventIndex, setEventIndex] = useState(0);
  const [latestEvent, setLatestEvent] = useState("Waiting for kickoff...");
  const [touchdownMessage, setTouchdownMessage] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [scoringRules, setScoringRules] = useState<ScoringRules>(
    () => defaultSnapshot().scoringRules,
  );
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const snapshot = loadSnapshot(browserStorage);
    setScoringRules(snapshot.scoringRules);
    setEventIndex(snapshot.simulator.eventIndex);
    setPlayers(
      playersAtCursor(snapshot.simulator.eventIndex, snapshot.scoringRules),
    );
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    const snapshot: PersistedSnapshot = {
      version: 2,
      scoringRules,
      simulator: { eventIndex },
    };
    saveSnapshot(browserStorage, snapshot, SNAPSHOT_KEY);
  }, [eventIndex, scoringRules, hydrated]);

  useEffect(() => {
    if (!running) return;
    const timer = window.setInterval(() => {
      const event = nextEvent(eventIndex);
      setPlayers((current) => applyEvent(current, event, scoringRules));
      setLatestEvent(describeEvent(event));
      setTouchdownMessage(
        event.kind === "touchdown" ? event.description : null,
      );
      setEventIndex((current) => current + 1);
    }, 2500);
    return () => window.clearInterval(timer);
  }, [running, eventIndex, scoringRules]);

  const reset = () => {
    setPlayers(samplePlayers);
    setEventIndex(0);
    setLatestEvent("Waiting for kickoff...");
    setTouchdownMessage(null);
    setRunning(false);
    setScoringRules(defaultSnapshot().scoringRules);
  };

  const toggleScoring = () => {
    const nextRules = {
      ...scoringRules,
      receptionPoints: scoringRules.receptionPoints === 0 ? 1 : 0,
    };
    setScoringRules(nextRules);
    setPlayers(playersAtCursor(eventIndex, nextRules));
  };

  return (
    <div className="app-shell">
      <Hud
        players={players}
        latestEvent={latestEvent}
        touchdownMessage={touchdownMessage}
      />
      <div className="controls">
        <button onClick={() => setRunning((value) => !value)}>
          {running ? "Pause" : "Start simulation"}
        </button>
        <button className="secondary" onClick={toggleScoring}>
          {scoringRules.receptionPoints === 0
            ? "Use PPR scoring"
            : "Use standard scoring"}
        </button>
        <button className="secondary" onClick={reset}>
          Reset
        </button>
      </div>
    </div>
  );
}
