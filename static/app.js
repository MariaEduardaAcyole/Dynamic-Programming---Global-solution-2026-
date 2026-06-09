const groupSelect = document.querySelector("#groupSelect");
const limitInput = document.querySelector("#limitInput");
const hoursSelect = document.querySelector("#hoursSelect");
const stepSelect = document.querySelector("#stepSelect");
const thresholdSelect = document.querySelector("#thresholdSelect");
const scanButton = document.querySelector("#scanButton");
const socratesButton = document.querySelector("#socratesButton");
const loadSatellitesButton = document.querySelector("#loadSatellitesButton");
const alertsBody = document.querySelector("#alertsBody");
const socratesBody = document.querySelector("#socratesBody");
const socratesMeta = document.querySelector("#socratesMeta");
const satCount = document.querySelector("#satCount");
const alertCount = document.querySelector("#alertCount");
const minDistance = document.querySelector("#minDistance");
const socratesCount = document.querySelector("#socratesCount");
const sourceStatus = document.querySelector("#sourceStatus");
const canvas = document.querySelector("#orbitCanvas");
const ctx = canvas.getContext("2d");
const satTooltip = document.querySelector("#satTooltip");

let sceneSatellites = [];
let projectedSatellites = [];
let rotationX = -0.38;
let rotationY = 0.72;
let zoom = 1.0;
let dragging = false;
let lastPointer = { x: 0, y: 0 };
let hoveredSatellite = null;

function riskClass(risk) {
  return `pill risk-${risk}`;
}

function fmtKm(value) {
  return `${Number(value).toLocaleString("pt-BR", { maximumFractionDigits: 3 })} km`;
}

async function getJson(url) {
  const response = await fetch(url);
  const data = await response.json();
  if (!response.ok || data.error) {
    throw new Error(data.error || "Falha ao consultar dados");
  }
  return data;
}

function setLoading(button, loading, text) {
  button.disabled = loading;
  if (loading) {
    button.dataset.originalText = button.textContent;
    button.textContent = text;
  } else {
    button.textContent = button.dataset.originalText || button.textContent;
  }
}

function rowEmpty(target, message, colspan = 5) {
  target.innerHTML = `<tr><td colspan="${colspan}">${message}</td></tr>`;
}

function renderAlerts(alerts) {
  if (!alerts.length) {
    rowEmpty(alertsBody, "Nenhuma aproximação abaixo do limite escolhido.");
    return;
  }
  alertsBody.innerHTML = alerts.map((alert) => `
    <tr>
      <td><span class="${riskClass(alert.risk)}">${alert.risk}</span></td>
      <td>${alert.satellite_1}<br><small>NORAD ${alert.norad_1}</small></td>
      <td>${alert.satellite_2}<br><small>NORAD ${alert.norad_2}</small></td>
      <td>${fmtKm(alert.distance_km)}</td>
      <td>${alert.tca_utc}</td>
    </tr>
  `).join("");
}

function renderSocrates(data) {
  const rows = data.records || [];
  socratesMeta.textContent = `Dados: ${data.data_current_as_of}. Intervalo: ${data.computation_interval}.`;
  socratesCount.textContent = rows.length;
  if (!rows.length) {
    rowEmpty(socratesBody, "Não foi possível extrair registros do SOCRATES agora.");
    return;
  }
  socratesBody.innerHTML = rows.map((item) => `
    <tr>
      <td><span class="${riskClass(item.risk)}">${item.risk}</span></td>
      <td>${item.satellite_1}<br><small>NORAD ${item.norad_1}</small></td>
      <td>${item.satellite_2}<br><small>NORAD ${item.norad_2}</small></td>
      <td>${fmtKm(item.distance_km)}</td>
      <td>${item.max_probability}</td>
    </tr>
  `).join("");
}

function rotatePoint(point) {
  const cosY = Math.cos(rotationY);
  const sinY = Math.sin(rotationY);
  const cosX = Math.cos(rotationX);
  const sinX = Math.sin(rotationX);

  const x1 = point.x * cosY + point.z * sinY;
  const z1 = -point.x * sinY + point.z * cosY;
  const y1 = point.y * cosX - z1 * sinX;
  const z2 = point.y * sinX + z1 * cosX;
  return { x: x1, y: y1, z: z2 };
}

function project(point, scale, camera) {
  const depth = camera / (camera - point.z * scale * 0.001);
  return {
    x: canvas.width / 2 + point.x * scale * depth,
    y: canvas.height / 2 + point.y * scale * depth,
    depth,
  };
}

function drawGlobe(scale) {
  const center = { x: canvas.width / 2, y: canvas.height / 2 };
  const radius = 6378.137 * scale;
  const gradient = ctx.createRadialGradient(
    center.x - radius * 0.28,
    center.y - radius * 0.35,
    radius * 0.1,
    center.x,
    center.y,
    radius
  );
  gradient.addColorStop(0, "#8fe7ff");
  gradient.addColorStop(0.45, "#2d8ad3");
  gradient.addColorStop(1, "#123a5f");

  ctx.fillStyle = gradient;
  ctx.beginPath();
  ctx.arc(center.x, center.y, radius, 0, Math.PI * 2);
  ctx.fill();

  ctx.strokeStyle = "rgba(237, 242, 247, 0.18)";
  ctx.lineWidth = 1;
  for (let latitude = -60; latitude <= 60; latitude += 30) {
    const latRadius = Math.cos(latitude * Math.PI / 180) * radius;
    const y = center.y + Math.sin(latitude * Math.PI / 180) * radius * Math.cos(rotationX);
    ctx.beginPath();
    ctx.ellipse(center.x, y, latRadius, latRadius * 0.22, rotationY * 0.18, 0, Math.PI * 2);
    ctx.stroke();
  }
  for (let longitude = 0; longitude < 180; longitude += 30) {
    ctx.beginPath();
    ctx.ellipse(center.x, center.y, radius * 0.22, radius, rotationY + longitude * Math.PI / 180, 0, Math.PI * 2);
    ctx.stroke();
  }
}

function drawOrbitMap(satellites) {
  sceneSatellites = satellites;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#080c11";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  const maxRadius = Math.max(...satellites.map((sat) => sat.radius_km || 7000), 7800);
  const scale = Math.min(canvas.width, canvas.height) * 0.38 * zoom / maxRadius;
  const camera = 8.5;

  drawGlobe(scale);

  projectedSatellites = satellites.map((sat) => {
    const rotated = rotatePoint(sat);
    const screen = project(rotated, scale, camera);
    return { ...sat, ...screen, zDepth: rotated.z };
  }).sort((a, b) => a.zDepth - b.zDepth);

  projectedSatellites.forEach((sat) => {
    const front = sat.zDepth > -1200;
    const pointRadius = Math.max(2.2, 3.4 * sat.depth);
    ctx.globalAlpha = front ? 0.92 : 0.28;
    ctx.fillStyle = sat.name.includes("STARLINK") ? "#39c6a6" : "#ffd166";
    ctx.beginPath();
    ctx.arc(sat.x, sat.y, pointRadius, 0, Math.PI * 2);
    ctx.fill();
  });

  ctx.globalAlpha = 1;
  ctx.font = "12px Inter, Segoe UI, sans-serif";
  ctx.textBaseline = "middle";
  projectedSatellites
    .filter((sat) => sat.zDepth > -900)
    .slice(-260)
    .forEach((sat) => {
      const isHovered = hoveredSatellite && hoveredSatellite.norad_id === sat.norad_id;
      if (!isHovered && sceneSatellites.length > 260 && !sat.name.includes("ISS") && !sat.name.includes("CSS")) {
        return;
      }
      const label = sceneSatellites.length > 260 && !isHovered ? sat.name.slice(0, 18) : sat.name;
      ctx.fillStyle = isHovered ? "#ffffff" : "rgba(237, 242, 247, 0.78)";
      ctx.fillText(label, sat.x + 8, sat.y);
    });

  ctx.fillStyle = "rgba(237, 242, 247, 0.72)";
  ctx.font = "13px Inter, Segoe UI, sans-serif";
  ctx.fillText(`${satellites.length} satélites | arraste para girar | zoom no scroll`, 18, canvas.height - 22);
}

function findSatelliteAt(canvasX, canvasY) {
  let closest = null;
  let closestDistance = 18;
  projectedSatellites.forEach((sat) => {
    const distance = Math.hypot(sat.x - canvasX, sat.y - canvasY);
    if (distance < closestDistance) {
      closest = sat;
      closestDistance = distance;
    }
  });
  return closest;
}

function canvasPoint(event) {
  const rect = canvas.getBoundingClientRect();
  return {
    x: (event.clientX - rect.left) * (canvas.width / rect.width),
    y: (event.clientY - rect.top) * (canvas.height / rect.height),
    pageX: event.clientX - rect.left,
    pageY: event.clientY - rect.top,
  };
}

function updateTooltip(point, satellite) {
  if (!satellite) {
    satTooltip.style.display = "none";
    return;
  }
  satTooltip.style.display = "block";
  satTooltip.style.left = `${point.pageX + 14}px`;
  satTooltip.style.top = `${point.pageY + 14}px`;
  satTooltip.innerHTML = `
    <strong>${satellite.name}</strong><br>
    NORAD ${satellite.norad_id}<br>
    Altitude: ${Number(satellite.altitude_km).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} km<br>
    Inclinação: ${satellite.inclination}°<br>
    Período: ${satellite.period_min} min
  `;
}

async function loadGroups() {
  const groups = await getJson("/api/groups");
  groupSelect.innerHTML = groups.map((group) => (
    `<option value="${group.id}" ${group.id === "starlink" ? "selected" : ""}>${group.name}</option>`
  )).join("");
}

async function runScan() {
  setLoading(scanButton, true, "Analisando...");
  sourceStatus.textContent = "Calculando aproximações";
  try {
    const params = new URLSearchParams({
      group: groupSelect.value,
      limit: limitInput.value,
      hours: hoursSelect.value,
      step: stepSelect.value,
      threshold: thresholdSelect.value,
    });
    const data = await getJson(`/api/scan?${params}`);
    renderAlerts(data.alerts);
    satCount.textContent = data.satellites_analyzed;
    alertCount.textContent = data.alerts.length;
    minDistance.textContent = data.alerts.length ? fmtKm(data.alerts[0].distance_km) : "-";
    sourceStatus.textContent = "Análise concluída";
  } catch (error) {
    rowEmpty(alertsBody, error.message);
    sourceStatus.textContent = "Falha na análise";
  } finally {
    setLoading(scanButton, false);
  }
}

async function loadSocrates() {
  setLoading(socratesButton, true, "Atualizando...");
  try {
    const data = await getJson("/api/socrates?order=MINRANGE&max=50");
    renderSocrates(data);
  } catch (error) {
    rowEmpty(socratesBody, error.message);
    socratesMeta.textContent = "Consulta indisponível.";
  } finally {
    setLoading(socratesButton, false);
  }
}

async function loadSatelliteMap() {
  setLoading(loadSatellitesButton, true, "Carregando...");
  try {
    const params = new URLSearchParams({ group: groupSelect.value, limit: limitInput.value });
    const data = await getJson(`/api/positions?${params}`);
    satCount.textContent = data.count;
    drawOrbitMap(data.satellites);
  } catch (error) {
    sourceStatus.textContent = error.message;
  } finally {
    setLoading(loadSatellitesButton, false);
  }
}

scanButton.addEventListener("click", runScan);
socratesButton.addEventListener("click", loadSocrates);
loadSatellitesButton.addEventListener("click", loadSatelliteMap);

loadGroups()
  .then(() => Promise.all([loadSatelliteMap(), loadSocrates()]))
  .catch((error) => {
    sourceStatus.textContent = error.message;
  });

canvas.addEventListener("pointerdown", (event) => {
  dragging = true;
  lastPointer = { x: event.clientX, y: event.clientY };
  canvas.setPointerCapture(event.pointerId);
});

canvas.addEventListener("pointermove", (event) => {
  if (dragging) {
    const dx = event.clientX - lastPointer.x;
    const dy = event.clientY - lastPointer.y;
    rotationY += dx * 0.008;
    rotationX += dy * 0.008;
    rotationX = Math.max(-1.45, Math.min(1.45, rotationX));
    lastPointer = { x: event.clientX, y: event.clientY };
    drawOrbitMap(sceneSatellites);
    return;
  }
  const point = canvasPoint(event);
  hoveredSatellite = findSatelliteAt(point.x, point.y);
  updateTooltip(point, hoveredSatellite);
  drawOrbitMap(sceneSatellites);
});

canvas.addEventListener("pointerleave", () => {
  hoveredSatellite = null;
  satTooltip.style.display = "none";
  drawOrbitMap(sceneSatellites);
});

canvas.addEventListener("pointerup", (event) => {
  dragging = false;
  canvas.releasePointerCapture(event.pointerId);
});

canvas.addEventListener("wheel", (event) => {
  event.preventDefault();
  zoom *= event.deltaY > 0 ? 0.92 : 1.08;
  zoom = Math.max(0.5, Math.min(2.7, zoom));
  drawOrbitMap(sceneSatellites);
}, { passive: false });
