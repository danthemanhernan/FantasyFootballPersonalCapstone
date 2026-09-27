const rootId = "fantasy-football-hud-root";
const markerLayerId = "fantasy-football-hud-markers";

const escapeHtml = (value) => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

const ensureRoot = () => {
  let root = document.getElementById(rootId);
  if (!root) {
    root = document.createElement("aside");
    root.id = rootId;
    root.className = "fantasy-hud-root";
    document.body.append(root);
  }
  return root;
};

const renderHud = (payload) => {
  const root = ensureRoot();
  const players = Array.isArray(payload.players) ? payload.players : [];
  root.innerHTML = `
    <section class="fantasy-hud-panel">
      <header><span>FANTASY HUD · LIVE</span><button aria-label="Hide HUD">×</button></header>
      <div class="fantasy-hud-team">
        <h3>${escapeHtml(payload.team_name || "My fantasy team")}</h3>
        ${players.map((player) => `
          <div class="fantasy-hud-player">
            <b>${escapeHtml(player.position)}</b>
            <span>${escapeHtml(player.name)} · ${escapeHtml(player.team)}</span>
            <output>${Number(player.fantasyPoints || 0).toFixed(1)}</output>
          </div>`).join("")}
      </div>
      ${players.length ? "" : '<p class="fantasy-hud-empty">Sync a league from the extension popup.</p>'}
    </section>`;
  root.querySelector("button")?.addEventListener("click", () => root.remove());
};

const renderDetections = (detections) => {
  let layer = document.getElementById(markerLayerId);
  if (!layer) {
    layer = document.createElement("div");
    layer.id = markerLayerId;
    layer.className = "fantasy-hud-marker-layer";
    document.body.append(layer);
  }
  layer.innerHTML = detections
    .filter((detection) => detection.confidence >= 0.5)
    .map((detection) => `<div class="fantasy-hud-marker" style="left:${detection.x}px;top:${detection.y}px;width:${detection.width}px;height:${detection.height}px"><span>${escapeHtml(detection.label)} · ${Math.round(detection.confidence * 100)}%</span></div>`)
    .join("");
};

chrome.runtime.onMessage.addListener((message) => {
  if (message?.type === "FANTASY_HUD_UPDATE") renderHud(message.payload || {});
  if (message?.type === "FANTASY_HUD_VISION_DETECTIONS") {
    renderDetections(Array.isArray(message.detections) ? message.detections : []);
  }
});
