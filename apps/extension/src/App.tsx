import { useEffect, useState } from "react";
import { Hud } from "./components/Hud";
import { EspnProvider } from "./providers/espn";
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

const apiBaseUrl = "http://127.0.0.1:8000";

const emptyStats = () => ({
  passingYards: 0,
  rushingYards: 0,
  receivingYards: 0,
  receptions: 0,
  passingTouchdowns: 0,
  rushingTouchdowns: 0,
  receivingTouchdowns: 0,
  interceptions: 0,
});

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
  const [espnStatus, setEspnStatus] = useState("ESPN roster not loaded");
  const [leagueId, setLeagueId] = useState("");
  const [teamId, setTeamId] = useState("");
  const [season, setSeason] = useState(2026);

  const loadLiveRoster = async () => {
    const selectedLeagueId = leagueId.trim();
    const selectedTeamId = teamId.trim();
    if (!selectedLeagueId || !selectedTeamId) {
      setEspnStatus("Enter both an ESPN league ID and team ID");
      return;
    }
    setEspnStatus("Loading ESPN roster...");
    try {
      const roster = await new EspnProvider().loadRoster({ leagueId: selectedLeagueId, season });
      const selectedTeam = roster.teams.find((team) => team.id === selectedTeamId);
      if (!selectedTeam) {
        throw new Error(`ESPN team ID ${selectedTeamId} was not found in ${roster.leagueName}`);
      }
      const teamPlayers = roster.players.filter(
        (player) => player.source.teamId === selectedTeamId,
      );
      if (teamPlayers.length === 0) {
        throw new Error(`No players found for ${selectedTeam.name} (team ID ${selectedTeamId})`);
      }
      const hudPlayers: Player[] = teamPlayers.map((player) => ({
        id: player.id,
        name: player.name,
        position: player.position,
        team: player.team,
        stats: emptyStats(),
        fantasyPoints: 0,
      }));
      setPlayers(hudPlayers);

      const payload = {
        league_id: selectedLeagueId,
        season,
        team_id: selectedTeamId,
        league_name: roster.leagueName,
        team_name: selectedTeam.name,
        players: teamPlayers.map((player) => ({
          player_id: player.source.playerId,
          name: player.name,
          position: player.position,
          pro_team: player.team,
        })),
      };
      const response = await fetch(`${apiBaseUrl}/sync/espn-roster`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error(`Backend sync returned HTTP ${response.status}`);

      const [activeTab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (activeTab?.id !== undefined) {
        await chrome.tabs.sendMessage(activeTab.id, {
          type: "FANTASY_HUD_UPDATE",
          payload: { ...payload, players: hudPlayers },
        }).catch(() => undefined);
      }
      console.log("Live ESPN roster:", roster);
      setEspnStatus(
        `Synced ${teamPlayers.length} players from ${selectedTeam.name} in ${roster.leagueName}`,
      );
    } catch (error) {
      console.error("ESPN request failed:", error);
      setEspnStatus(error instanceof Error ? error.message : "ESPN request failed");
    }
  };

  const demoVisionMarkers = async () => {
    const [activeTab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (activeTab?.id === undefined) return;
    const detections = players.slice(0, 3).map((player, index) => ({
      label: player.name,
      confidence: 0.92 - index * 0.06,
      x: 160 + index * 260,
      y: 240 + (index % 2) * 130,
      width: 110,
      height: 210,
    }));
    await chrome.tabs.sendMessage(activeTab.id, {
      type: "FANTASY_HUD_VISION_DETECTIONS",
      detections,
    }).catch(() => undefined);
    setEspnStatus("Injected demo vision detections into the active YouTube tab");
  };

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
      <section className="league-settings" aria-label="ESPN league settings">
        <label>
          League ID
          <input value={leagueId} onChange={(event) => setLeagueId(event.target.value)} />
        </label>
        <label>
          Team ID
          <input value={teamId} onChange={(event) => setTeamId(event.target.value)} />
        </label>
        <label>
          Season
          <input
            type="number"
            value={season}
            onChange={(event) => setSeason(Number(event.target.value))}
          />
        </label>
      </section>
      <div className="controls">
        <button onClick={() => setRunning((value) => !value)}>
          {running ? "Pause" : "Start simulation"}
        </button>
        <button className="secondary" onClick={loadLiveRoster}>
          Load ESPN roster
        </button>
        <button className="secondary" onClick={demoVisionMarkers}>
          Demo vision markers
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
      <p className="sync-status" aria-live="polite">{espnStatus}</p>
    </div>
  );
}
