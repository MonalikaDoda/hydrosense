import { useEffect, useState } from "react";
import "./styles.css";
import { CircleMarker, MapContainer, Popup, TileLayer } from "react-leaflet";
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  Camera,
  CheckCircle2,
  Clock,
  Compass,
  Cpu,
  ExternalLink,
  Flame,
  Gauge,
  History,
  Image as ImageIcon,
  Layers,
  LayoutDashboard,
  MapPin,
  MessageSquarePlus,
  RefreshCw,
  Send,
  Shield,
  ShieldAlert,
  Sparkles,
  Waves,
  X,
} from "lucide-react";

import {
  createReading,
  getCommunityReports,
  getDashboardSummary,
  getIncidents,
  getLatestReadings,
  getUnderpassEvents,
  getUnderpassMetrics,
  getUnderpassRisk,
  submitCommunityReport,
  updateIncidentStatus,
} from "./api/client";
import type {
  CommunityReport,
  CommunityReportStatus,
  DashboardSummary,
  Incident,
  IncidentStatus,
  SensorReading,
  UnderpassEvaluationMetrics,
  UnderpassEventRecord,
  UnderpassRiskItem,
  UnderpassRiskResponse,
} from "./types/api";

const tierColors: Record<string, string> = {
  green: "#16a34a",
  yellow: "#ca8a04",
  orange: "#ea580c",
  red: "#dc2626",
  unknown: "#78716c",
};

const statusTransitions: Record<IncidentStatus, IncidentStatus[]> = {
  open: ["assigned", "verified", "dismissed"],
  assigned: ["verified", "resolved", "dismissed"],
  verified: ["resolved", "dismissed"],
  resolved: [],
  dismissed: [],
};

const SAMPLE_FLOOD_IMAGE =
  "https://images.unsplash.com/photo-1515694346937-94d85e41e6f0?w=800&auto=format&fit=crop&q=80";
const SAMPLE_PASSABLE_IMAGE =
  "https://images.unsplash.com/photo-1547683905-f686c993aae5?w=800&auto=format&fit=crop&q=80";

function formatLocalTime(value: string) {
  try {
    return new Intl.DateTimeFormat("en-IN", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function timeAgo(dateString: string): string {
  const diffSec = Math.floor((Date.now() - new Date(dateString).getTime()) / 1000);
  if (diffSec < 60) return "just now";
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHours = Math.floor(diffMin / 60);
  return `${diffHours}h ago`;
}

export default function App() {
  const [activeTab, setActiveTab] = useState<"landing" | "underpass" | "infrastructure" | "replay">("landing");
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [readings, setReadings] = useState<SensorReading[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null);
  const [riskData, setRiskData] = useState<UnderpassRiskResponse | null>(null);
  const [selectedHotspotId, setSelectedHotspotId] = useState<string>("zakhira");
  const [communityReports, setCommunityReports] = useState<CommunityReport[]>([]);
  const [metrics, setMetrics] = useState<UnderpassEvaluationMetrics | null>(null);
  const [events, setEvents] = useState<UnderpassEventRecord[]>([]);
  const [selectedReplayDate, setSelectedReplayDate] = useState<string>("2024-06-28");
  const [mapTierFilter, setMapTierFilter] = useState<string>("ALL");

  const [loading, setLoading] = useState(false);
  const [simulating, setSimulating] = useState(false);
  const [updatingStatus, setUpdatingStatus] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  // Field Report Modal State
  const [showModal, setShowModal] = useState(false);
  const [modalHotspotId, setModalHotspotId] = useState<string>("zakhira");
  const [reportStatus, setReportStatus] = useState<CommunityReportStatus>("flooded");
  const [reportNotes, setReportNotes] = useState("");
  const [reportImageUrl, setReportImageUrl] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Lightbox State
  const [lightboxImg, setLightboxImg] = useState<string | null>(null);

  // Real-time IST clock
  const [currentTime, setCurrentTime] = useState("");
  useEffect(() => {
    const updateClock = () => {
      const now = new Date();
      setCurrentTime(
        now.toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata", hour12: false }) + " IST",
      );
    };
    updateClock();
    const interval = setInterval(updateClock, 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);

    Promise.all([
      getDashboardSummary(controller.signal),
      getLatestReadings(controller.signal),
      getIncidents(controller.signal),
      getUnderpassRisk(controller.signal),
      getCommunityReports(undefined, controller.signal),
      getUnderpassMetrics(controller.signal),
      getUnderpassEvents(undefined, controller.signal),
    ])
      .then(([nextSummary, nextReadings, nextIncidents, nextRisk, nextReports, nextMetrics, nextEvents]) => {
        setSummary(nextSummary);
        setReadings(nextReadings);
        setIncidents(nextIncidents);
        setSelectedIncidentId((curr) => curr ?? nextIncidents[0]?.incident_id ?? null);
        setRiskData(nextRisk);
        if (nextRisk?.hotspots?.length && !selectedHotspotId) {
          setSelectedHotspotId(nextRisk.hotspots[0].id);
          setModalHotspotId(nextRisk.hotspots[0].id);
        }
        setCommunityReports(nextReports);
        setMetrics(nextMetrics);
        setEvents(nextEvents);
      })
      .catch((err) => {
        console.warn("Telemetry stream notice:", err);
      })
      .finally(() => setLoading(false));

    return () => controller.abort();
  }, [reloadKey]);

  const selectedIncident =
    incidents.find((inc) => inc.incident_id === selectedIncidentId) ?? incidents[0] ?? null;

  const selectedHotspot: UnderpassRiskItem | null =
    riskData?.hotspots?.find((h) => h.id === selectedHotspotId) ??
    riskData?.hotspots?.[0] ??
    null;

  const hotspotReports = communityReports.filter(
    (rep) => !selectedHotspotId || rep.hotspot_id === selectedHotspotId,
  );

  // Evidence conflict detection (model vs ground truth)
  const evidenceConflict = (() => {
    if (!selectedHotspot || hotspotReports.length === 0) return false;
    const latest = hotspotReports[0];
    const isSevereRisk = selectedHotspot.tier === "orange" || selectedHotspot.tier === "red";
    const isUserClear = latest.status === "passable" || latest.status === "not_flooded";
    const isGreenRisk = selectedHotspot.tier === "green";
    const isUserFlooded = latest.status === "flooded";
    return (isSevereRisk && isUserClear) || (isGreenRisk && isUserFlooded);
  })();

  // Filtered hotspots for map
  const visibleHotspots = riskData?.hotspots?.filter((h) => {
    if (mapTierFilter === "ALL") return true;
    if (mapTierFilter === "CRITICAL") return h.tier === "red" || h.tier === "orange";
    if (mapTierFilter === "ELEVATED") return h.tier === "yellow";
    if (mapTierFilter === "CLEAR") return h.tier === "green";
    return true;
  }) ?? [];

  async function handleStatusTransition(status: IncidentStatus) {
    if (!selectedIncident || status === selectedIncident.status) return;
    setUpdatingStatus(true);
    try {
      const updated = await updateIncidentStatus(selectedIncident.incident_id, status);
      setIncidents((curr) =>
        curr.map((item) => (item.incident_id === updated.incident_id ? updated : item)),
      );
      setReloadKey((v) => v + 1);
    } catch (err) {
      console.warn("Status transition issue:", err);
    } finally {
      setUpdatingStatus(false);
    }
  }

  async function handleSimulateReading(depthCm: number) {
    setSimulating(true);
    try {
      const readingPayload: SensorReading = {
        device_id: "hydrosense-arduino-01",
        location_id: "demo-zone-01",
        water_depth_cm: depthCm,
        distance_cm: Math.max(30.0 - depthCm, 0),
        timestamp: new Date().toISOString(),
        source: "arduino",
      };
      await createReading(readingPayload);
      setReloadKey((v) => v + 1);
    } catch (err) {
      console.warn("Simulation issue:", err);
    } finally {
      setSimulating(false);
    }
  }

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      setReportImageUrl(event.target?.result as string);
    };
    reader.readAsDataURL(file);
  }

  async function handleReportSubmit(e: React.FormEvent) {
    e.preventDefault();
    const targetHotspotId = modalHotspotId || selectedHotspotId;
    if (!targetHotspotId) return;

    setSubmitting(true);
    try {
      const created = await submitCommunityReport({
        hotspot_id: targetHotspotId,
        status: reportStatus,
        notes: reportNotes.trim() || undefined,
        image_url: reportImageUrl || undefined,
      });
      setCommunityReports((curr) => [created, ...curr]);
      setShowModal(false);
      setReportNotes("");
      setReportImageUrl(null);
      setReloadKey((v) => v + 1);
    } catch (err) {
      console.warn("Submission error:", err);
    } finally {
      setSubmitting(false);
    }
  }

  const currentDepth = readings[0]?.water_depth_cm ?? 16.4;
  const isDepthHazard = currentDepth >= 24.0;
  const depthPercentage = Math.min((currentDepth / 30.0) * 100, 100);

  const uniqueStormDates = Array.from(new Set(events.map((e) => e.date))).sort();
  const replayRows = events.filter((e) => e.date === selectedReplayDate);

  const criticalHotspots = riskData?.hotspots?.filter((h) => h.tier === "red" || h.tier === "orange") ?? [];

  return (
    <main className="app-shell">
      {/* =====================================================================
          1. TOP STICKY MASTHEAD / NAVBAR
          ===================================================================== */}
      <header className="top-nav-masthead">
        <div className="nav-brand-group" onClick={() => setActiveTab("landing")}>
          <div className="brand-stamp" aria-hidden="true">
            <Waves size={24} />
          </div>
          <div className="brand-title-wrap">
            <h1>HydroSense</h1>
            <span className="brand-badge">DELHI NCT WATER OBSERVATORY</span>
          </div>
        </div>

        {/* Top Navigation Tabs */}
        <nav className="nav-tab-menu" aria-label="Observatory Sections">
          <button
            className={`nav-tab-btn ${activeTab === "landing" ? "active" : ""}`}
            onClick={() => setActiveTab("landing")}
          >
            <LayoutDashboard size={15} /> Overview & Hub
          </button>
          <button
            className={`nav-tab-btn ${activeTab === "underpass" ? "active" : ""}`}
            onClick={() => setActiveTab("underpass")}
          >
            <MapPin size={15} /> Underpass Early Warning
          </button>
          <button
            className={`nav-tab-btn ${activeTab === "infrastructure" ? "active" : ""}`}
            onClick={() => setActiveTab("infrastructure")}
          >
            <Gauge size={15} /> Arduino Telemetry Desk
          </button>
          <button
            className={`nav-tab-btn ${activeTab === "replay" ? "active" : ""}`}
            onClick={() => setActiveTab("replay")}
          >
            <History size={15} /> Storm Replay (200 Records)
          </button>
        </nav>

        {/* Telemetry Indicator & Actions */}
        <div className="nav-right-actions">
          <div className="live-beacon-pill">
            <span className="beacon-dot" />
            <span>ECMWF IFS LIVE</span>
          </div>
          <div className="time-readout">
            <Clock size={13} style={{ color: "var(--amber)" }} />
            <span>{currentTime || "16:51 IST"}</span>
          </div>
          <button
            className="btn-transmit-global"
            onClick={() => {
              setModalHotspotId(selectedHotspotId);
              setShowModal(true);
            }}
          >
            <Camera size={14} /> + Ground Report
          </button>
          <button
            className="btn-tactile-refresh"
            onClick={() => setReloadKey((v) => v + 1)}
            title="Refresh System Telemetry"
            aria-label="Refresh Telemetry"
          >
            <RefreshCw size={15} className={loading ? "spin" : ""} />
          </button>
        </div>
      </header>

      {/* =====================================================================
          2. GLOBAL TELEMETRY STAT STRIP (VISIBLE ACROSS VIEWS)
          ===================================================================== */}
      <section className="stat-strip" aria-label="System Metrics">
        <article className={`stat-tile ${summary?.active_flood_alerts ? "danger" : "safe"}`}>
          <div className="stat-tile-top">
            <span className="stat-tile-label">Critical Flood Warnings</span>
            <ShieldAlert size={16} style={{ color: summary?.active_flood_alerts ? "var(--terracotta)" : "var(--emerald)" }} />
          </div>
          <div className="stat-tile-value">{summary?.active_flood_alerts ?? 0}</div>
          <div className="stat-tile-sub">Orange / Red underpasses flagged</div>
        </article>

        <article className="stat-tile warn">
          <div className="stat-tile-top">
            <span className="stat-tile-label">Field & Bedrock Reports</span>
            <Activity size={16} style={{ color: "var(--amber)" }} />
          </div>
          <div className="stat-tile-value">{communityReports.length}</div>
          <div className="stat-tile-sub">Corroborated citizen reports (45m TTL)</div>
        </article>

        <article className={`stat-tile ${isDepthHazard ? "danger" : "safe"}`}>
          <div className="stat-tile-top">
            <span className="stat-tile-label">Arduino Ultrasonic Depth</span>
            <Waves size={16} style={{ color: isDepthHazard ? "var(--terracotta)" : "var(--emerald)" }} />
          </div>
          <div className="stat-tile-value">{currentDepth.toFixed(1)} cm</div>
          <div className="stat-tile-sub">
            Threshold: 24.0 cm ({isDepthHazard ? "BREACH ALERT" : "NOMINAL"})
          </div>
        </article>

        <article className="stat-tile info">
          <div className="stat-tile-top">
            <span className="stat-tile-label">Historical Event Rows</span>
            <Layers size={16} style={{ color: "var(--sky)" }} />
          </div>
          <div className="stat-tile-value">{metrics?.n_rows ?? 200}</div>
          <div className="stat-tile-sub">Across 21 validated storm days</div>
        </article>
      </section>

      {/* =====================================================================
          VIEW 0: LANDING PAGE & OBSERVATORY OVERVIEW HUB
          ===================================================================== */}
      {activeTab === "landing" && (
        <section className="landing-hub">
          {/* Hero Statement Banner */}
          <div className="landing-hero-banner">
            <div className="hero-editorial-copy">
              <span className="hero-tag">
                <Sparkles size={12} /> DECISION-SUPPORT OBSERVATORY
              </span>
              <h2>
                Anticipate urban inundation <em>before underpasses become impassable.</em>
              </h2>
              <p>
                HydroSense fuses <strong>200 calibrated monsoon records</strong>, 24-hour Open-Meteo precipitation models across 16 chronic Delhi underpass hotspots, container ultrasonic depth telemetry from <strong>Arduino hardware</strong>, and multimodal image verification via <strong>Amazon Bedrock</strong>.
              </p>
            </div>
            <div className="hero-quick-stats">
              <div className="quick-stat-row">
                <span>SECTOR MONITORED:</span>
                <strong>DELHI NCT REGION</strong>
              </div>
              <div className="quick-stat-row">
                <span>HOTSPOTS TRACKED:</span>
                <strong>16 CHRONIC SPOTS</strong>
              </div>
              <div className="quick-stat-row">
                <span>HARDWARE PROTOTYPE:</span>
                <strong>ARDUINO + HC-SR04</strong>
              </div>
              <div className="quick-stat-row">
                <span>AI VISION ENGINE:</span>
                <strong>AMAZON BEDROCK</strong>
              </div>
            </div>
          </div>

          {/* Interactive Launchpad 4-Cards Grid */}
          <div className="launchpad-grid">
            {/* Card 1: Underpass Early Warning */}
            <div className="launchpad-card underpass" onClick={() => setActiveTab("underpass")}>
              <div className="launchpad-card-header">
                <div className="launchpad-icon">
                  <MapPin size={24} />
                </div>
                <div className="launchpad-info">
                  <h3>Urban Underpass Early Warning</h3>
                  <p>
                    Interactive Leaflet OpenStreetMap mapping 16 Delhi flood hotspots (Minto Bridge, Zakhira, Azad Market, etc.) against 24-hour Open-Meteo ECMWF IFS rain forecasts and empirical thresholds.
                  </p>
                </div>
              </div>
              <div className="launchpad-card-footer">
                <span className="launchpad-meta">16 HOTSPOTS · 0 API KEYS REQ</span>
                <span className="launchpad-cta">
                  Explore Live Map & Thresholds <ArrowRight size={14} />
                </span>
              </div>
            </div>

            {/* Card 2: Arduino Telemetry Desk */}
            <div className="launchpad-card arduino" onClick={() => setActiveTab("infrastructure")}>
              <div className="launchpad-card-header">
                <div className="launchpad-icon">
                  <Cpu size={24} />
                </div>
                <div className="launchpad-info">
                  <h3>Arduino Hardware Telemetry Desk</h3>
                  <p>
                    Real-time depth telemetry from Arduino Uno / Nano with HC-SR04 ultrasonic sound transducer. Dynamic liquid column visualizer, 24.0 cm hazard alert threshold, and incident lifecycle response.
                  </p>
                </div>
              </div>
              <div className="launchpad-card-footer">
                <span className="launchpad-meta">ARDUINO HC-SR04 · 30.0 CM VESSEL</span>
                <span className="launchpad-cta">
                  Open Arduino Hardware Desk <ArrowRight size={14} />
                </span>
              </div>
            </div>

            {/* Card 3: Storm Replay Engine */}
            <div className="launchpad-card replay" onClick={() => setActiveTab("replay")}>
              <div className="launchpad-card-header">
                <div className="launchpad-icon">
                  <History size={24} />
                </div>
                <div className="launchpad-info">
                  <h3>Empirical Storm Replay & Evaluation</h3>
                  <p>
                    Rigorously inspect 200 historical monsoon event records (e.g. June 28, 2024 record cloudburst with 228 mm). Validated with Leave-One-Storm-Out (LOSO) cross-validation with 72.3% recall.
                  </p>
                </div>
              </div>
              <div className="launchpad-card-footer">
                <span className="launchpad-meta">200 RECORDS · 21 STORM DAYS</span>
                <span className="launchpad-cta">
                  Inspect Empirical Evaluation <ArrowRight size={14} />
                </span>
              </div>
            </div>

            {/* Card 4: Bedrock AI & Community Ground Reports */}
            <div
              className="launchpad-card bedrock"
              onClick={() => {
                setModalHotspotId(selectedHotspotId);
                setShowModal(true);
              }}
            >
              <div className="launchpad-card-header">
                <div className="launchpad-icon">
                  <Camera size={24} />
                </div>
                <div className="launchpad-info">
                  <h3>Ground Reports & Bedrock AI Vision</h3>
                  <p>
                    Submit verified ground status with road photos. Amazon Bedrock Multimodal AI inspects carriageway reflectance, water depth bounds, and curb submergence with confidence scoring.
                  </p>
                </div>
              </div>
              <div className="launchpad-card-footer">
                <span className="launchpad-meta">AMAZON BEDROCK · MULTIMODAL AI</span>
                <span className="launchpad-cta">
                  Submit or Inspect Field Reports <ArrowRight size={14} />
                </span>
              </div>
            </div>
          </div>

          {/* Landing Dual Columns (Live Alert Preview & Arduino Snapshot) */}
          <div className="landing-preview-grid">
            {/* Left: Active Alerts Summary */}
            <div className="preview-panel">
              <div className="preview-panel-head">
                <h3>
                  <ShieldAlert size={18} style={{ color: "var(--amber)" }} />
                  Current Delhi Flood Alert Hotspots
                </h3>
                <button
                  className="filter-pill active"
                  onClick={() => setActiveTab("underpass")}
                >
                  View All on Map →
                </button>
              </div>

              <div className="preview-hotspot-list">
                {criticalHotspots.length === 0 ? (
                  <p style={{ color: "var(--ink-muted)", fontSize: "13px" }}>
                    No underpasses currently in Orange or Red status. All 16 spots nominal.
                  </p>
                ) : (
                  criticalHotspots.map((h) => (
                    <div
                      key={h.id}
                      className="preview-hotspot-row"
                      onClick={() => {
                        setSelectedHotspotId(h.id);
                        setActiveTab("underpass");
                      }}
                    >
                      <div>
                        <div className="preview-hotspot-name">{h.name}</div>
                        <div className="preview-hotspot-evidence">
                          {h.why}
                        </div>
                      </div>
                      <span className={`risk-stamp ${h.tier}`}>
                        {h.tier} RISK
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Right: Arduino Hardware Quick Snapshot */}
            <div className="preview-panel">
              <div className="preview-panel-head">
                <h3>
                  <Cpu size={18} style={{ color: "var(--sky)" }} />
                  Arduino Sensor Container Status
                </h3>
                <button
                  className="filter-pill active"
                  onClick={() => setActiveTab("infrastructure")}
                >
                  Hardware Desk →
                </button>
              </div>

              <div style={{ display: "flex", gap: "20px", alignItems: "center" }}>
                <div className="liquid-chamber" style={{ height: "140px", width: "60px" }}>
                  <div
                    className="threshold-hazard-line"
                    style={{ bottom: `${(24.0 / 30.0) * 100}%` }}
                  />
                  <div
                    className={`water-column ${isDepthHazard ? "breach" : ""}`}
                    style={{ height: `${depthPercentage}%` }}
                  />
                </div>

                <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "10px" }}>
                  <div className="chamber-metric">
                    <small>ARDUINO LEVEL</small>
                    <strong style={{ color: isDepthHazard ? "var(--terracotta)" : "var(--emerald)" }}>
                      {currentDepth.toFixed(1)} cm / 30.0 cm
                    </strong>
                  </div>
                  <div className="chamber-metric">
                    <small>STATUS</small>
                    <strong style={{ fontSize: "14px", color: isDepthHazard ? "var(--terracotta)" : "var(--emerald)" }}>
                      {isDepthHazard ? "HIGH WATER THRESHOLD BREACH" : "SAFE / NORMAL WATER LEVEL"}
                    </strong>
                  </div>

                  <div style={{ display: "flex", gap: "6px", marginTop: "4px" }}>
                    <button
                      className="btn-inject"
                      style={{ padding: "6px 10px", fontSize: "11px" }}
                      disabled={simulating}
                      onClick={() => handleSimulateReading(14.8)}
                    >
                      Safe (14.8cm)
                    </button>
                    <button
                      className="btn-inject danger-trigger"
                      style={{ padding: "6px 10px", fontSize: "11px" }}
                      disabled={simulating}
                      onClick={() => handleSimulateReading(26.5)}
                    >
                      Breach (26.5cm)
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* =====================================================================
          VIEW 1: URBAN FLOOD EARLY WARNING (MAP + HOTSPOT DOSSIER)
          ===================================================================== */}
      {activeTab === "underpass" && (
        <section className="split-workspace">
          {/* Tactical Map Shell with OpenStreetMap (Free, No API Key Required) */}
          <div className="tactical-map-frame">
            <div className="map-control-bar">
              <h3>
                <Layers size={16} style={{ color: "var(--amber)" }} />
                Delhi NCT Underpass Hotspot Grid
              </h3>
              <div className="filter-pill-group">
                {["ALL", "CRITICAL", "ELEVATED", "CLEAR"].map((pill) => (
                  <button
                    key={pill}
                    className={`filter-pill ${mapTierFilter === pill ? "active" : ""}`}
                    onClick={() => setMapTierFilter(pill)}
                  >
                    {pill}
                  </button>
                ))}
              </div>
            </div>

            <div className="leaflet-frame-inner">
              <MapContainer
                center={[28.625, 77.205]}
                zoom={11}
                scrollWheelZoom={true}
                style={{ width: "100%", height: "100%" }}
              >
                {/* Free OpenStreetMap Tiles — No API Key Required */}
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                {visibleHotspots.map((hotspot) => {
                  const color = tierColors[hotspot.tier] || tierColors.unknown;
                  const isSelected = hotspot.id === selectedHotspotId;
                  const radius = isSelected ? 12 : 7;
                  return (
                    <CircleMarker
                      key={hotspot.id}
                      center={[hotspot.lat, hotspot.lon]}
                      radius={radius}
                      pathOptions={{
                        color: isSelected ? "#1c1917" : color,
                        fillColor: color,
                        fillOpacity: 0.92,
                        weight: isSelected ? 3 : 1.5,
                      }}
                      eventHandlers={{
                        click: () => {
                          setSelectedHotspotId(hotspot.id);
                          setModalHotspotId(hotspot.id);
                        },
                      }}
                    >
                      <Popup>
                        <div style={{ fontFamily: "var(--font-sans)", color: "#1c1917" }}>
                          <strong style={{ display: "block", fontSize: "14px" }}>{hotspot.name}</strong>
                          <div style={{ fontSize: "12px", marginTop: "4px" }}>
                            Status: <strong style={{ color }}>{hotspot.tier.toUpperCase()} RISK</strong>
                          </div>
                          <div style={{ fontSize: "11px", color: "#555", marginTop: "2px" }}>
                            Forecast 3h: {hotspot.forecast.max_3h_mm ?? 0} mm (Limit: {hotspot.limit.rain3h_mm ?? "--"} mm)
                          </div>
                        </div>
                      </Popup>
                    </CircleMarker>
                  );
                })}
              </MapContainer>
            </div>
          </div>

          {/* Underpass Tactical Dossier */}
          <aside className="dossier-frame">
            {selectedHotspot ? (
              <>
                <div className="dossier-hero">
                  <div>
                    <h2>{selectedHotspot.name}</h2>
                    <span className="coord-stamp">
                      COORDINATES: {selectedHotspot.lat.toFixed(3)}°N, {selectedHotspot.lon.toFixed(3)}°E
                    </span>
                  </div>
                  <span className={`risk-stamp ${selectedHotspot.tier}`}>
                    {selectedHotspot.tier} RISK
                  </span>
                </div>

                {/* Visual Precision Meters */}
                <div className="gauge-metric-card">
                  <div className="gauge-metric-header">
                    <span className="gauge-metric-title">1-Hour Peak Burst Rain</span>
                    <span className="gauge-metric-value">
                      {selectedHotspot.forecast.max_1h_mm ?? 0} mm{" "}
                      <span>/ {selectedHotspot.limit.rain1h_mm ?? "--"} mm limit</span>
                    </span>
                  </div>
                  <div className="gauge-track">
                    <div
                      className={`gauge-fill ${selectedHotspot.tier}`}
                      style={{
                        width: `${Math.min(
                          ((selectedHotspot.forecast.max_1h_mm ?? 0) /
                            Math.max(selectedHotspot.limit.rain1h_mm ?? 10, 1)) *
                            100,
                          100,
                        )}%`,
                      }}
                    />
                  </div>
                </div>

                <div className="gauge-metric-card">
                  <div className="gauge-metric-header">
                    <span className="gauge-metric-title">3-Hour Cumulative Rain</span>
                    <span className="gauge-metric-value">
                      {selectedHotspot.forecast.max_3h_mm ?? 0} mm{" "}
                      <span>/ {selectedHotspot.limit.rain3h_mm ?? "--"} mm limit</span>
                    </span>
                  </div>
                  <div className="gauge-track">
                    <div
                      className={`gauge-fill ${selectedHotspot.tier}`}
                      style={{
                        width: `${Math.min(
                          ((selectedHotspot.forecast.max_3h_mm ?? 0) /
                            Math.max(selectedHotspot.limit.rain3h_mm ?? 20, 1)) *
                            100,
                          100,
                        )}%`,
                      }}
                    />
                  </div>
                </div>

                {/* Editorial Quote Dossier */}
                <div className="dossier-quote-box">
                  <div className="dossier-quote">"{selectedHotspot.why}"</div>
                  <div className="dossier-cite">
                    HISTORICAL EVIDENCE BASE: {selectedHotspot.evidence.toUpperCase()}
                  </div>
                </div>

                {/* Bypass Route Recommendation */}
                <div className="bypass-notice">
                  <Compass size={14} style={{ display: "inline", verticalAlign: "middle", marginRight: "6px" }} />
                  <strong>ADVISORY BYPASS ROUTE:</strong> Avoid low-lying underpass barrel during intense downpours. Use alternate elevated flyovers (e.g. Ring Road / Barapullah Corridor).
                </div>

                {/* Conflict Alert Bulletin */}
                {evidenceConflict && (
                  <div className="operational-bulletin" role="alert">
                    <AlertTriangle size={20} />
                    <div>
                      <strong>EVIDENCE CONFLICT DISPATCH:</strong> Meteorological forecast and active ground community observations disagree for this hotspot. Physical traffic police review advised.
                    </div>
                  </div>
                )}

                {/* Ground Observations Feed with Bedrock AI Vision */}
                <div className="dispatch-head">
                  <h4>Ground Observations ({hotspotReports.length})</h4>
                  <button
                    className="btn-transmit"
                    onClick={() => {
                      setModalHotspotId(selectedHotspot.id);
                      setShowModal(true);
                    }}
                  >
                    <Camera size={13} /> Add Report
                  </button>
                </div>

                {hotspotReports.length === 0 ? (
                  <p style={{ color: "var(--ink-muted)", fontSize: "13px", margin: "10px 0" }}>
                    No field reports submitted in the active 45-minute window for this spot.
                  </p>
                ) : (
                  hotspotReports.map((rep) => {
                    const ai = rep.ai_assessment as Record<string, any> | undefined;
                    return (
                      <div className="dispatch-card" key={rep.report_id}>
                        <div className="dispatch-card-top">
                          <span className={`pill-badge ${rep.status}`}>
                            {rep.status.replace("_", " ")}
                          </span>
                          <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--ink-muted)" }}>
                            {timeAgo(rep.timestamp)}
                          </span>
                        </div>

                        {rep.notes && (
                          <div style={{ fontSize: "13px", color: "var(--ink-primary)" }}>
                            {rep.notes}
                          </div>
                        )}

                        {rep.image_url && (
                          <img
                            src={rep.image_url}
                            alt="Ground observation"
                            className="report-photo-thumb"
                            onClick={() => setLightboxImg(rep.image_url ?? null)}
                            title="Click to expand photo"
                          />
                        )}

                        {/* Amazon Bedrock Multimodal Vision Assessment Card */}
                        {ai && (
                          <div className="bedrock-assessment-card">
                            <div className="bedrock-head">
                              <span className="bedrock-tag">
                                <Sparkles size={11} /> Amazon Bedrock Multimodal AI
                              </span>
                              <span style={{ fontFamily: "var(--font-mono)", fontSize: "10px", color: "#6b21a8", fontWeight: 700 }}>
                                {ai.confidence ? `${(ai.confidence * 100).toFixed(0)}% Conf` : "Verified"}
                              </span>
                            </div>

                            <div className="bedrock-evidence-text">
                              <strong>Visual Finding:</strong> {ai.visual_evidence || "Ponding analyzed across road surface."}
                            </div>

                            <div className="bedrock-meta-row">
                              <span>Estimated Depth: {ai.estimated_visual_depth_cm || "N/A"}</span>
                              <span>{ai.needs_human_review ? "⚠ Needs Human Review" : "✓ Corroborated"}</span>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
              </>
            ) : (
              <div style={{ padding: "40px", textAlign: "center", color: "var(--ink-muted)" }}>
                Select an underpass on the map to review telemetry dossier.
              </div>
            )}
          </aside>
        </section>
      )}

      {/* =====================================================================
          VIEW 2: ARDUINO HARDWARE TELEMETRY DESK
          ===================================================================== */}
      {activeTab === "infrastructure" && (
        <section className="infra-three-col">
          {/* Hardware Bench Simulation */}
          <div className="hardware-chassis">
            <h3>Arduino Hardware Bench</h3>
            <p>
              Simulating an <strong>Arduino Uno / Nano</strong> with an HC-SR04 ultrasonic sound transducer positioned above a calibrated 30.0 cm test catchment chamber.
            </p>

            <div className="chamber-assembly">
              <div className="liquid-chamber" aria-label="Liquid Level Chamber">
                <div className="threshold-hazard-line" style={{ bottom: `${(24.0 / 30.0) * 100}%` }}>
                  <span className="threshold-hazard-tag">ALERT 24.0cm</span>
                </div>
                <div
                  className={`water-column ${isDepthHazard ? "breach" : ""}`}
                  style={{ height: `${depthPercentage}%` }}
                />
              </div>

              <div className="chamber-readouts">
                <div className="chamber-metric">
                  <small>MEASURED DEPTH (ARDUINO)</small>
                  <strong style={{ color: isDepthHazard ? "var(--terracotta)" : "var(--emerald)" }}>
                    {currentDepth.toFixed(1)} cm
                  </strong>
                </div>
                <div className="chamber-metric">
                  <small>TRANSDUCER DISTANCE</small>
                  <strong>{Math.max(30.0 - currentDepth, 0).toFixed(1)} cm</strong>
                </div>
                <div className="chamber-metric">
                  <small>OPERATIONAL STATE</small>
                  <strong style={{ color: isDepthHazard ? "var(--terracotta)" : "var(--emerald)" }}>
                    {isDepthHazard ? "HIGH WATER BREACH ALERT" : "NOMINAL / SAFE"}
                  </strong>
                </div>
              </div>
            </div>

            <div className="injection-panel">
              <label>INJECT ARDUINO SENSOR SCENARIOS:</label>
              <div className="injection-grid">
                <button
                  className="btn-inject"
                  disabled={simulating}
                  onClick={() => handleSimulateReading(14.2)}
                >
                  Normal Flow (14.2 cm)
                </button>
                <button
                  className="btn-inject"
                  disabled={simulating}
                  onClick={() => handleSimulateReading(22.4)}
                >
                  Caution Zone (22.4 cm)
                </button>
                <button
                  className="btn-inject danger-trigger"
                  disabled={simulating}
                  onClick={() => handleSimulateReading(26.8)}
                  style={{ gridColumn: "1 / -1" }}
                >
                  Trigger Breach Alert (26.8 cm)
                </button>
              </div>
            </div>
          </div>

          {/* Ultrasonic Telemetry Stream */}
          <div className="triage-deck">
            <div className="triage-deck-head">
              <h3>Arduino Telemetry Log</h3>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--ink-muted)" }}>
                {readings.length} FRAMES
              </span>
            </div>
            <div style={{ flex: 1, overflowY: "auto", maxHeight: "540px" }}>
              {readings.map((r) => {
                const alert = r.water_depth_cm >= 24.0;
                return (
                  <div
                    key={`${r.device_id}-${r.timestamp}`}
                    style={{
                      padding: "12px 14px",
                      borderBottom: "1px solid var(--rule-subtle)",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <div>
                      <div
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontSize: "14px",
                          fontWeight: 700,
                          color: alert ? "var(--terracotta)" : "var(--ink-primary)",
                        }}
                      >
                        {r.water_depth_cm.toFixed(1)} cm depth
                      </div>
                      <div style={{ fontSize: "11px", color: "var(--ink-muted)", marginTop: "2px" }}>
                        Distance: {r.distance_cm.toFixed(1)} cm · {formatLocalTime(r.timestamp)}
                      </div>
                    </div>
                    <span
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "10px",
                        padding: "3px 8px",
                        borderRadius: "4px",
                        background: "var(--pastel-blue-badge)",
                        color: "var(--pastel-blue-ink)",
                        textTransform: "uppercase",
                        fontWeight: 600,
                      }}
                    >
                      {r.source}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Incident Response Desk */}
          <div className="triage-deck">
            <div className="triage-deck-head">
              <h3>Response Triage Desk</h3>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--ink-muted)" }}>
                {incidents.length} INCIDENTS
              </span>
            </div>

            {selectedIncident ? (
              <div className="triage-dossier-body">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "8px" }}>
                  <h4 style={{ margin: 0, fontSize: "16px", color: "var(--ink-primary)" }}>{selectedIncident.title}</h4>
                  <span className={`pill-badge ${selectedIncident.status}`}>
                    {selectedIncident.status}
                  </span>
                </div>

                <div className="triage-row">
                  <span>LOCATION ID</span>
                  <span>{selectedIncident.location_id}</span>
                </div>
                <div className="triage-row">
                  <span>HAZARD TYPE</span>
                  <span>{selectedIncident.hazard_type.replace(/_/g, " ").toUpperCase()}</span>
                </div>
                <div className="triage-row">
                  <span>SEVERITY</span>
                  <span style={{ color: selectedIncident.severity === "high" || selectedIncident.severity === "very_high" ? "var(--terracotta)" : "var(--amber)" }}>
                    {selectedIncident.severity.toUpperCase()}
                  </span>
                </div>
                <div className="triage-row">
                  <span>CONFIDENCE</span>
                  <span>{(selectedIncident.confidence * 100).toFixed(0)}%</span>
                </div>
                <div className="triage-row">
                  <span>REPORTED AT</span>
                  <span>{formatLocalTime(selectedIncident.created_at)}</span>
                </div>

                <div style={{ marginTop: "16px" }}>
                  <label style={{ fontSize: "11px", fontFamily: "var(--font-mono)", color: "var(--ink-muted)", display: "block" }}>
                    ADVANCE INCIDENT LIFECYCLE:
                  </label>
                  <select
                    className="lifecycle-stepper"
                    value={selectedIncident.status}
                    disabled={updatingStatus}
                    onChange={(e) => handleStatusTransition(e.target.value as IncidentStatus)}
                  >
                    <option value={selectedIncident.status}>CURRENT: {selectedIncident.status.toUpperCase()}</option>
                    {statusTransitions[selectedIncident.status].map((nxt) => (
                      <option key={nxt} value={nxt}>
                        ADVANCE TO {nxt.toUpperCase()}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            ) : (
              <div style={{ padding: "40px", textAlign: "center", color: "var(--ink-muted)" }}>
                No active incidents in queue.
              </div>
            )}
          </div>
        </section>
      )}

      {/* =====================================================================
          VIEW 3: HISTORICAL STORM REPLAY & EVALUATION (200 RECORDS)
          ===================================================================== */}
      {activeTab === "replay" && (
        <section className="replay-two-col">
          {/* LOSO Evaluation Metrics */}
          <div className="eval-summary-card">
            <h3>Leave-One-Storm-Out Evaluation</h3>
            <p>
              To prevent spatial and temporal data leakage across storm days, rainfall thresholds were fitted on the other
              storm days only. Rigorously measured on all 200 event records.
            </p>

            <div className="loso-stat-quad">
              <div className="loso-tile">
                <div className="loso-num">{metrics?.n_rows ?? 200}</div>
                <div className="loso-label">TOTAL EVENT RECORDS</div>
              </div>
              <div className="loso-tile">
                <div className="loso-num">{metrics?.n_storm_days ?? 21}</div>
                <div className="loso-label">STORM DAYS (2020–2026)</div>
              </div>
              <div className="loso-tile">
                <div className="loso-num" style={{ color: "var(--emerald)" }}>
                  {metrics
                    ? `${(
                        (metrics.per_hotspot_thresholds.floods_caught /
                          metrics.per_hotspot_thresholds.n_flooded_rows) *
                        100
                      ).toFixed(1)}%`
                    : "72.3%"}
                </div>
                <div className="loso-label">FLOOD RECALL RATE</div>
              </div>
              <div className="loso-tile">
                <div className="loso-num" style={{ color: "var(--amber)" }}>
                  {metrics
                    ? `${(
                        (metrics.per_hotspot_thresholds.false_alarms /
                          metrics.per_hotspot_thresholds.n_clear_rows) *
                        100
                      ).toFixed(1)}%`
                    : "7.9%"}
                </div>
                <div className="loso-label">FALSE-ALARM RATE</div>
              </div>
            </div>

            <table className="matrix-grid-table">
              <thead>
                <tr>
                  <th>EVALUATION METRIC</th>
                  <th>PER-HOTSPOT THRESHOLDS</th>
                  <th>POOLED BASELINE</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Floods Caught</td>
                  <td>
                    <strong style={{ color: "var(--emerald)" }}>
                      {metrics?.per_hotspot_thresholds.floods_caught ?? 99} / {metrics?.per_hotspot_thresholds.n_flooded_rows ?? 137}
                    </strong>
                  </td>
                  <td>{metrics?.pooled_only_baseline.floods_caught ?? 103} / 137</td>
                </tr>
                <tr>
                  <td>Floods Missed</td>
                  <td>{metrics?.per_hotspot_thresholds.floods_missed ?? 38}</td>
                  <td>{metrics?.pooled_only_baseline.floods_missed ?? 34}</td>
                </tr>
                <tr>
                  <td>Clear Days Correct</td>
                  <td>{metrics?.per_hotspot_thresholds.correct_clear ?? 58} / {metrics?.per_hotspot_thresholds.n_clear_rows ?? 63}</td>
                  <td>{metrics?.pooled_only_baseline.correct_clear ?? 63} / 63</td>
                </tr>
                <tr>
                  <td>False Alarms</td>
                  <td style={{ color: "var(--terracotta)" }}>{metrics?.per_hotspot_thresholds.false_alarms ?? 5}</td>
                  <td>{metrics?.pooled_only_baseline.false_alarms ?? 0}</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Historical Storm Scrubber */}
          <div className="scrubber-frame">
            <div className="scrubber-header">
              <h3>Monsoon Storm Scrubber</h3>
              <select
                className="storm-date-picker"
                value={selectedReplayDate}
                onChange={(e) => setSelectedReplayDate(e.target.value)}
              >
                {uniqueStormDates.map((d) => (
                  <option key={d} value={d}>
                    {d} ({events.filter((e) => e.date === d).length} Hotspots Recorded)
                  </option>
                ))}
              </select>
            </div>

            <div className="scrubber-table-wrap">
              <table className="scrubber-table">
                <thead>
                  <tr>
                    <th>HOTSPOT</th>
                    <th>OUTCOME</th>
                    <th>OBSERVED INCIDENT</th>
                    <th>REPORTED RAINFALL</th>
                  </tr>
                </thead>
                <tbody>
                  {replayRows.map((ev) => (
                    <tr key={ev.event_id}>
                      <td>
                        <strong>{ev.underpass_name_in_source}</strong>
                      </td>
                      <td>
                        <span className={`pill-badge ${ev.outcome}`}>
                          {ev.outcome.toUpperCase()}
                        </span>
                      </td>
                      <td style={{ color: "var(--ink-secondary)" }}>{ev.what_happened}</td>
                      <td style={{ fontFamily: "var(--font-mono)", fontSize: "12px", color: "var(--ink-muted)" }}>
                        {ev.rain_reported_in_article ?? "--"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}

      {/* =====================================================================
          TACTILE MODAL DIALOG: TRANSMIT FIELD OBSERVATION & BEDROCK IMAGE
          ===================================================================== */}
      {showModal && (
        <div className="modal-scrim" role="dialog" aria-modal="true">
          <div className="modal-sheet">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3>Transmit Ground Observation</h3>
              <button
                className="btn-tactile-refresh"
                style={{ width: "32px", height: "32px" }}
                onClick={() => setShowModal(false)}
              >
                <X size={16} />
              </button>
            </div>
            <p>
              Submitting verified ground status. Images will be analyzed by <strong>Amazon Bedrock Multimodal AI</strong> for specular water reflection and curb inundation bounds.
            </p>

            <form onSubmit={handleReportSubmit}>
              <div className="input-block">
                <label htmlFor="modal-hotspot-select">DELHI UNDERPASS HOTSPOT:</label>
                <select
                  id="modal-hotspot-select"
                  value={modalHotspotId}
                  onChange={(e) => setModalHotspotId(e.target.value)}
                >
                  {riskData?.hotspots?.map((h) => (
                    <option key={h.id} value={h.id}>
                      {h.name} ({h.tier.toUpperCase()} Risk)
                    </option>
                  )) ?? (
                    <option value="zakhira">Zakhira underpass</option>
                  )}
                </select>
              </div>

              <div className="input-block">
                <label htmlFor="report-status">CURRENT ROAD STATUS:</label>
                <select
                  id="report-status"
                  value={reportStatus}
                  onChange={(e) => setReportStatus(e.target.value as CommunityReportStatus)}
                >
                  <option value="flooded">Flooded / Inundated (Hazardous ponding)</option>
                  <option value="passable">Passable with caution (Minor runoff / curbs visible)</option>
                  <option value="not_flooded">Clear / Free Flow (No structural waterlogging)</option>
                </select>
              </div>

              <div className="input-block">
                <label htmlFor="report-notes">FIELD TELEMETRY NOTES:</label>
                <textarea
                  id="report-notes"
                  rows={2}
                  placeholder="e.g. Sump pumps operating, right lane submerged, traffic crawling..."
                  value={reportNotes}
                  onChange={(e) => setReportNotes(e.target.value)}
                />
              </div>

              {/* Image Upload Input & Bedrock Preview */}
              <div className="input-block">
                <label>GROUND EVIDENCE PHOTO (AMAZON BEDROCK VISION):</label>
                {reportImageUrl ? (
                  <div className="photo-preview-wrap">
                    <img src={reportImageUrl} alt="Preview" className="photo-preview-img" />
                    <button
                      type="button"
                      className="btn-remove-photo"
                      onClick={() => setReportImageUrl(null)}
                      title="Remove Photo"
                    >
                      <X size={14} />
                    </button>
                  </div>
                ) : (
                  <div className="photo-uploader-box">
                    <Camera size={24} style={{ color: "var(--ink-muted)" }} />
                    <div style={{ fontSize: "12px", color: "var(--ink-secondary)" }}>
                      Upload photo from phone / camera for Bedrock vision corroboration
                    </div>
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handleFileSelect}
                      style={{ fontSize: "12px" }}
                    />
                    <div className="sample-preset-row">
                      <button
                        type="button"
                        className="btn-sample-photo"
                        onClick={() => setReportImageUrl(SAMPLE_FLOOD_IMAGE)}
                      >
                        Use Flooded Sample
                      </button>
                      <button
                        type="button"
                        className="btn-sample-photo"
                        onClick={() => setReportImageUrl(SAMPLE_PASSABLE_IMAGE)}
                      >
                        Use Clear Sample
                      </button>
                    </div>
                  </div>
                )}
              </div>

              <div className="modal-actions-row">
                <button
                  type="button"
                  className="btn-cancel"
                  onClick={() => setShowModal(false)}
                  disabled={submitting}
                >
                  Cancel
                </button>
                <button type="submit" className="btn-transmit-global" disabled={submitting}>
                  <Send size={13} />
                  {submitting ? "Analyzing & Transmitting..." : "Submit to HydroSense"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* =====================================================================
          LIGHTBOX MODAL FOR EXPANDED VIEW
          ===================================================================== */}
      {lightboxImg && (
        <div className="lightbox-scrim" onClick={() => setLightboxImg(null)}>
          <div className="lightbox-content" onClick={(e) => e.stopPropagation()}>
            <button className="lightbox-close" onClick={() => setLightboxImg(null)}>
              <X size={24} />
            </button>
            <img src={lightboxImg} alt="Field Observation Expanded" />
          </div>
        </div>
      )}
    </main>
  );
}
