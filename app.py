from __future__ import annotations

import csv
import json
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html import unescape
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
CACHE_DIR = ROOT / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

MU_EARTH_KM3_S2 = 398600.4418
EARTH_RADIUS_KM = 6378.137
CELESTRAK_GP = "https://celestrak.org/NORAD/elements/gp.php"
SOCRATES_URL = "https://celestrak.org/SOCRATES/table-socrates.php"


GROUPS = {
    "active": "Satélites ativos",
    "stations": "Estações espaciais",
    "starlink": "Starlink",
    "gps-ops": "GPS operacional",
    "geo": "Geossíncronos",
    "cubesat": "CubeSats",
    "iridium-NEXT": "Iridium NEXT",
    "weather": "Meteorológicos",
}


@dataclass
class Satellite:
    norad_id: str
    name: str
    epoch: datetime
    mean_motion: float
    eccentricity: float
    inclination: float
    raan: float
    arg_perigee: float
    mean_anomaly: float
    period_min: float
    perigee_km: float
    apogee_km: float


def http_get(url: str, cache_name: str, ttl_seconds: int = 1800) -> str:
    cache_path = CACHE_DIR / cache_name
    if cache_path.exists() and time.time() - cache_path.stat().st_mtime < ttl_seconds:
        return cache_path.read_text(encoding="utf-8")

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "OrbitalGuardian/1.0 educational collision-alert app"},
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            text = response.read().decode("utf-8", errors="replace")
            cache_path.write_text(text, encoding="utf-8")
            return text
    except urllib.error.URLError:
        if cache_path.exists():
            return cache_path.read_text(encoding="utf-8")
        raise


def parse_epoch(value: str) -> datetime:
    value = value.strip().replace("Z", "+00:00")
    if "." in value and "+" not in value:
        value += "+00:00"
    if "+" not in value and value.endswith("UTC"):
        value = value[:-3].strip() + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def to_float(row: dict[str, str], key: str, default: float = 0.0) -> float:
    try:
        return float(row.get(key, default) or default)
    except ValueError:
        return default


def satellite_from_row(row: dict[str, str]) -> Satellite | None:
    try:
        norad_id = str(row["NORAD_CAT_ID"]).strip()
        name = row.get("OBJECT_NAME", row.get("OBJECT_NAME_1", "UNKNOWN")).strip()
        mean_motion = to_float(row, "MEAN_MOTION")
        eccentricity = to_float(row, "ECCENTRICITY")
        if mean_motion <= 0:
            return None
        n_rad_s = mean_motion * 2 * math.pi / 86400.0
        semi_major = (MU_EARTH_KM3_S2 / (n_rad_s * n_rad_s)) ** (1.0 / 3.0)
        perigee = semi_major * (1 - eccentricity) - EARTH_RADIUS_KM
        apogee = semi_major * (1 + eccentricity) - EARTH_RADIUS_KM
        return Satellite(
            norad_id=norad_id,
            name=name,
            epoch=parse_epoch(row["EPOCH"]),
            mean_motion=mean_motion,
            eccentricity=eccentricity,
            inclination=to_float(row, "INCLINATION"),
            raan=to_float(row, "RA_OF_ASC_NODE"),
            arg_perigee=to_float(row, "ARG_OF_PERICENTER"),
            mean_anomaly=to_float(row, "MEAN_ANOMALY"),
            period_min=1440.0 / mean_motion,
            perigee_km=perigee,
            apogee_km=apogee,
        )
    except (KeyError, ValueError):
        return None


def fetch_satellites(group: str) -> list[Satellite]:
    if group not in GROUPS:
        group = "active"
    params = urllib.parse.urlencode({"GROUP": group, "FORMAT": "csv"})
    text = http_get(f"{CELESTRAK_GP}?{params}", f"gp_{group}.csv", 1800)
    rows = csv.DictReader(text.splitlines())
    satellites = [sat for row in rows if (sat := satellite_from_row(row))]
    return satellites


def solve_kepler(mean_anomaly: float, eccentricity: float) -> float:
    anomaly = mean_anomaly
    for _ in range(12):
        delta = (anomaly - eccentricity * math.sin(anomaly) - mean_anomaly) / (
            1 - eccentricity * math.cos(anomaly)
        )
        anomaly -= delta
        if abs(delta) < 1e-10:
            break
    return anomaly


def position_eci(sat: Satellite, when: datetime) -> tuple[float, float, float]:
    dt_seconds = (when - sat.epoch).total_seconds()
    n_rad_s = sat.mean_motion * 2 * math.pi / 86400.0
    semi_major = (MU_EARTH_KM3_S2 / (n_rad_s * n_rad_s)) ** (1.0 / 3.0)
    eccentricity = sat.eccentricity
    mean_anomaly = math.radians(sat.mean_anomaly) + n_rad_s * dt_seconds
    mean_anomaly = mean_anomaly % (2 * math.pi)
    eccentric_anomaly = solve_kepler(mean_anomaly, eccentricity)

    x_orb = semi_major * (math.cos(eccentric_anomaly) - eccentricity)
    y_orb = semi_major * math.sqrt(max(0.0, 1 - eccentricity * eccentricity)) * math.sin(
        eccentric_anomaly
    )

    raan = math.radians(sat.raan)
    inc = math.radians(sat.inclination)
    argp = math.radians(sat.arg_perigee)

    cos_o, sin_o = math.cos(raan), math.sin(raan)
    cos_i, sin_i = math.cos(inc), math.sin(inc)
    cos_w, sin_w = math.cos(argp), math.sin(argp)

    x = (cos_o * cos_w - sin_o * sin_w * cos_i) * x_orb + (
        -cos_o * sin_w - sin_o * cos_w * cos_i
    ) * y_orb
    y = (sin_o * cos_w + cos_o * sin_w * cos_i) * x_orb + (
        -sin_o * sin_w + cos_o * cos_w * cos_i
    ) * y_orb
    z = (sin_w * sin_i) * x_orb + (cos_w * sin_i) * y_orb
    return (x, y, z)


def distance_km(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def risk_level(distance: float) -> str:
    if distance < 1:
        return "Crítico"
    if distance < 5:
        return "Alto"
    if distance < 10:
        return "Moderado"
    if distance < 20:
        return "Atenção"
    return "Baixo"


def object_family(name: str) -> str:
    upper = name.upper()
    if any(token in upper for token in ("ISS", "ZARYA", "POISK", "NAUKA", "PRICHAL")):
        return "ISS_COMPLEX"
    if any(token in upper for token in ("CSS", "TIANHE", "WENTIAN", "MENGTIAN", "TIANZHOU", "SHENZHOU")):
        return "CHINESE_STATION_COMPLEX"
    return upper


def should_ignore_pair(sat_a: Satellite, sat_b: Satellite, distance: float) -> bool:
    if sat_a.norad_id == sat_b.norad_id:
        return True
    same_family = object_family(sat_a.name) == object_family(sat_b.name)
    same_orbit = (
        abs(sat_a.period_min - sat_b.period_min) < 0.01
        and abs(sat_a.inclination - sat_b.inclination) < 0.01
        and abs(sat_a.raan - sat_b.raan) < 0.01
    )
    return distance < 0.1 and (same_family or same_orbit)


def scan_conjunctions(
    satellites: list[Satellite], hours: int, step_minutes: int, threshold_km: float
) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    steps = max(1, int(hours * 60 / step_minutes))
    best_pairs: dict[tuple[str, str], dict[str, Any]] = {}

    for step in range(steps + 1):
        when = now + timedelta(minutes=step * step_minutes)
        positions = [(sat, position_eci(sat, when)) for sat in satellites]
        for i in range(len(positions)):
            sat_a, pos_a = positions[i]
            for j in range(i + 1, len(positions)):
                sat_b, pos_b = positions[j]
                if abs(sat_a.period_min - sat_b.period_min) > 35:
                    continue
                distance = distance_km(pos_a, pos_b)
                if should_ignore_pair(sat_a, sat_b, distance):
                    continue
                if distance <= threshold_km:
                    key = tuple(sorted((sat_a.norad_id, sat_b.norad_id)))
                    current = best_pairs.get(key)
                    if current is None or distance < current["distance_km"]:
                        best_pairs[key] = {
                            "satellite_1": sat_a.name,
                            "norad_1": sat_a.norad_id,
                            "satellite_2": sat_b.name,
                            "norad_2": sat_b.norad_id,
                            "distance_km": round(distance, 3),
                            "tca_utc": when.isoformat().replace("+00:00", "Z"),
                            "risk": risk_level(distance),
                            "relative_period_delta_min": round(
                                abs(sat_a.period_min - sat_b.period_min), 3
                            ),
                        }
    return sorted(best_pairs.values(), key=lambda item: item["distance_km"])[:250]


def strip_tags(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value)).strip()


def fetch_socrates(order: str = "MINRANGE", max_rows: int = 50) -> dict[str, Any]:
    params = urllib.parse.urlencode({"NAME": ",", "ORDER": order, "MAX": max_rows})
    html = http_get(f"{SOCRATES_URL}?{params}", f"socrates_{order}_{max_rows}.html", 3600)
    current = re.search(r"Data current as of\s+([^<]+)", html)
    interval = re.search(r"Computation Interval:\s+([^<]+)", html)
    records: list[dict[str, Any]] = []

    text = strip_tags(unescape(html))
    pattern = re.compile(
        r"GP Data\s+(\d+)\s+(.+?)\s+([-+]?\d+\.\d+)\s+"
        r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)\s+"
        r"([\d.]+)\s+([\d.]+)\s+50 km All\s+(\d+)\s+(.+?)\s+"
        r"([-+]?\d+\.\d+)\s+([\d.E+-]+)\s+([\d.]+)"
    )
    for match in pattern.finditer(text):
        records.append(
            {
                "norad_1": match.group(1),
                "satellite_1": match.group(2).strip(),
                "dse_1": float(match.group(3)),
                "tca_utc": match.group(4),
                "distance_km": float(match.group(5)),
                "relative_speed_km_s": float(match.group(6)),
                "norad_2": match.group(7),
                "satellite_2": match.group(8).strip(),
                "dse_2": float(match.group(9)),
                "max_probability": match.group(10),
                "dilution_km": float(match.group(11)),
                "risk": risk_level(float(match.group(5))),
            }
        )

    return {
        "source": f"{SOCRATES_URL}?{params}",
        "data_current_as_of": current.group(1).strip() if current else "desconhecido",
        "computation_interval": interval.group(1).strip() if interval else "desconhecido",
        "records": records[:max_rows],
    }


def json_response(handler: SimpleHTTPRequestHandler, payload: Any, status: int = 200) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class OrbitalHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        parsed = urllib.parse.urlparse(path)
        clean_path = parsed.path
        if clean_path == "/":
            return str(STATIC_DIR / "index.html")
        return str(STATIC_DIR / clean_path.lstrip("/"))

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        try:
            if parsed.path == "/api/groups":
                json_response(self, [{"id": key, "name": value} for key, value in GROUPS.items()])
                return
            if parsed.path == "/api/satellites":
                group = query.get("group", ["active"])[0]
                limit = min(int(query.get("limit", ["500"])[0]), 5000)
                satellites = fetch_satellites(group)[:limit]
                json_response(
                    self,
                    {
                        "group": group,
                        "count": len(satellites),
                        "satellites": [
                            {
                                "norad_id": sat.norad_id,
                                "name": sat.name,
                                "epoch": sat.epoch.isoformat().replace("+00:00", "Z"),
                                "period_min": round(sat.period_min, 3),
                                "perigee_km": round(sat.perigee_km, 1),
                                "apogee_km": round(sat.apogee_km, 1),
                                "inclination": round(sat.inclination, 3),
                                "eccentricity": sat.eccentricity,
                            }
                            for sat in satellites
                        ],
                    },
                )
                return
            if parsed.path == "/api/positions":
                group = query.get("group", ["active"])[0]
                limit = min(int(query.get("limit", ["220"])[0]), 1000)
                when = datetime.now(timezone.utc)
                satellites = fetch_satellites(group)[:limit]
                positioned = []
                for sat in satellites:
                    x, y, z = position_eci(sat, when)
                    radius = math.sqrt(x * x + y * y + z * z)
                    positioned.append(
                        {
                            "norad_id": sat.norad_id,
                            "name": sat.name,
                            "x": round(x, 3),
                            "y": round(y, 3),
                            "z": round(z, 3),
                            "radius_km": round(radius, 3),
                            "altitude_km": round(radius - EARTH_RADIUS_KM, 3),
                            "period_min": round(sat.period_min, 3),
                            "inclination": round(sat.inclination, 3),
                        }
                    )
                json_response(
                    self,
                    {
                        "group": group,
                        "count": len(positioned),
                        "timestamp_utc": when.isoformat().replace("+00:00", "Z"),
                        "earth_radius_km": EARTH_RADIUS_KM,
                        "satellites": positioned,
                    },
                )
                return
            if parsed.path == "/api/scan":
                group = query.get("group", ["starlink"])[0]
                limit = min(int(query.get("limit", ["180"])[0]), 600)
                hours = min(int(query.get("hours", ["12"])[0]), 72)
                step = max(1, min(int(query.get("step", ["10"])[0]), 60))
                threshold = max(1.0, min(float(query.get("threshold", ["20"])[0]), 250.0))
                satellites = fetch_satellites(group)[:limit]
                alerts = scan_conjunctions(satellites, hours, step, threshold)
                json_response(
                    self,
                    {
                        "group": group,
                        "satellites_analyzed": len(satellites),
                        "hours": hours,
                        "step_minutes": step,
                        "threshold_km": threshold,
                        "method": "Propagação Kepleriana aproximada a partir de elementos GP/OMM públicos. Não substitui SGP4 operacional.",
                        "alerts": alerts,
                    },
                )
                return
            if parsed.path == "/api/socrates":
                order = query.get("order", ["MINRANGE"])[0]
                max_rows = min(int(query.get("max", ["50"])[0]), 200)
                json_response(self, fetch_socrates(order, max_rows))
                return
        except Exception as exc:
            json_response(self, {"error": str(exc)}, 500)
            return
        super().do_GET()


def main() -> None:
    host = "127.0.0.1"
    port = 8000
    server = ThreadingHTTPServer((host, port), OrbitalHandler)
    print(f"Orbital Guardian rodando em http://{host}:{port}")
    print("Pressione Ctrl+C para parar.")
    server.serve_forever()


if __name__ == "__main__":
    main()
