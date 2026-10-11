import {
  Activity,
  ArrowRight,
  CheckCircle2,
  CloudRain,
  Gauge,
  LogIn,
  MapPin,
  Radio,
  ShieldAlert,
  Waves,
} from "lucide-react";

interface PublicLandingProps {
  authConfigured: boolean;
  authenticated: boolean;
  authLoading: boolean;
  onAuthAction: () => void;
  onOpenDashboard: () => void;
}

const capabilities = [
  {
    icon: Gauge,
    title: "Water-level telemetry",
    description:
      "Receive validated sensor readings, preserve device history, and surface threshold incidents through one operational contract.",
    status: "Simulator-backed today",
  },
  {
    icon: ShieldAlert,
    title: "Incident operations",
    description:
      "Review severity, location, evidence, and lifecycle state without mixing simulated readings with official observations.",
    status: "Available in the console",
  },
  {
    icon: MapPin,
    title: "Underpass awareness",
    description:
      "Compare forecast rainfall with reviewed hotspot thresholds when an approved historical dataset is installed.",
    status: "Dataset-gated capability",
  },
  {
    icon: Radio,
    title: "Field observations",
    description:
      "Accept time-bounded, explicitly unverified reports with location, road status, and operator notes.",
    status: "Backend support prepared",
  },
];

export function PublicLanding({
  authConfigured,
  authenticated,
  authLoading,
  onAuthAction,
  onOpenDashboard,
}: PublicLandingProps) {
  return (
    <div className="public-site">
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      <header className="public-header">
        <button className="public-brand" type="button" aria-label="HydroSense home">
          <span className="public-brand-mark" aria-hidden="true">
            <Waves size={22} />
          </span>
          <span>
            <strong>HydroSense</strong>
            <small>Urban water intelligence</small>
          </span>
        </button>
        <nav className="public-nav" aria-label="Public navigation">
          <a href="#capabilities">Capabilities</a>
          <a href="#operations">Operations</a>
          <a href="#limitations">Data policy</a>
        </nav>
        <div className="public-header-actions">
          {authConfigured && (
            <button
              className="button-secondary"
              type="button"
              onClick={onAuthAction}
              disabled={authLoading}
            >
              <LogIn size={17} aria-hidden="true" />
              {authLoading ? "Checking access" : authenticated ? "Operator signed in" : "Operator sign in"}
            </button>
          )}
          <button className="button-primary" type="button" onClick={onOpenDashboard}>
            Open dashboard <ArrowRight size={17} aria-hidden="true" />
          </button>
        </div>
      </header>

      <main id="main-content">
        <section className="public-hero" aria-labelledby="public-hero-title">
          <div className="public-hero-grid" aria-hidden="true" />
          <div className="public-hero-copy">
            <p className="eyebrow">Environmental monitoring for field operations</p>
            <h1 id="public-hero-title">HydroSense</h1>
            <p className="public-hero-lede">
              A decision-support workspace for water-level telemetry, incident response,
              underpass-risk awareness, and community field observations.
            </p>
            <div className="public-hero-actions">
              <button className="button-primary button-large" type="button" onClick={onOpenDashboard}>
                Enter monitoring console <ArrowRight size={18} aria-hidden="true" />
              </button>
              <a className="text-link" href="#limitations">
                Review operating limits
              </a>
            </div>
          </div>
          <div className="public-hero-status" aria-label="Current product scope">
            <span><CheckCircle2 size={16} aria-hidden="true" /> Cloud telemetry pipeline implemented</span>
            <span><Activity size={16} aria-hidden="true" /> Simulator clearly labelled</span>
            <span><CloudRain size={16} aria-hidden="true" /> Risk requires reviewed data</span>
          </div>
        </section>

        <section className="public-intro" id="capabilities" aria-labelledby="capabilities-title">
          <div>
            <p className="eyebrow">One operational picture</p>
            <h2 id="capabilities-title">Built around evidence, not reassuring placeholders.</h2>
          </div>
          <p>
            HydroSense keeps telemetry, forecasts, historical evidence, and public reports distinct.
            Missing inputs remain visible as unavailable or unknown rather than being converted into a safe condition.
          </p>
        </section>

        <section className="capability-list" aria-label="HydroSense capabilities">
          {capabilities.map(({ icon: Icon, title, description, status }, index) => (
            <article className="capability-row" key={title}>
              <span className="capability-index">0{index + 1}</span>
              <Icon size={22} aria-hidden="true" />
              <div>
                <h3>{title}</h3>
                <p>{description}</p>
              </div>
              <span className="capability-status">{status}</span>
            </article>
          ))}
        </section>

        <section className="operations-band" id="operations" aria-labelledby="operations-title">
          <div className="operations-copy">
            <p className="eyebrow">Operational console</p>
            <h2 id="operations-title">Scan current state, then move directly to the work.</h2>
            <p>
              The console prioritizes system availability, latest telemetry, incidents, underpass data,
              field reports, and actionable errors. Mutation controls respect the configured operator sign-in boundary.
            </p>
            <button className="button-primary" type="button" onClick={onOpenDashboard}>
              View operational dashboard <ArrowRight size={17} aria-hidden="true" />
            </button>
          </div>
          <div className="console-preview" aria-label="Preview of the HydroSense monitoring console">
            <div className="console-preview-head">
              <span>Delhi monitoring desk</span>
              <span className="preview-state"><span /> Core API ready</span>
            </div>
            <div className="preview-summary">
              <div><small>Latest reading</small><strong>Awaiting telemetry</strong></div>
              <div><small>Underpass risk</small><strong>Dataset dependent</strong></div>
              <div><small>Image analysis</small><strong>Not connected</strong></div>
            </div>
            <div className="preview-workspace">
              <div className="preview-chart" aria-hidden="true">
                <span /><span /><span /><span /><span /><span />
              </div>
              <div className="preview-queue">
                <strong>Response queue</strong>
                <p>Incidents remain tied to source, location, severity, and lifecycle state.</p>
              </div>
            </div>
          </div>
        </section>

        <section className="limitations-band" id="limitations" aria-labelledby="limitations-title">
          <div>
            <p className="eyebrow">Operating boundary</p>
            <h2 id="limitations-title">Decision support, not an official safety declaration.</h2>
          </div>
          <div className="limitations-copy">
            <p>
              Underpass markers and risk tiers appear only when a reviewed hotspot, threshold, event,
              and evaluation dataset is installed. Forecast failure produces an unknown state.
            </p>
            <p>
              Physical sensor calibration, automated image assessment, municipal integrations, and alert delivery
              remain separate milestones until they are implemented and verified end to end.
            </p>
          </div>
        </section>
      </main>

      <footer className="public-footer">
        <span>HydroSense</span>
        <span>Prototype environmental decision support</span>
      </footer>
    </div>
  );
}
