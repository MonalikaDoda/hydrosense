import {
  Activity,
  ArrowRight,
  BarChart3,
  CheckCircle2,
  CloudRain,
  Cpu,
  Database,
  ExternalLink,
  FileSearch,
  Gauge,
  History,
  LayoutDashboard,
  LogIn,
  MapPin,
  Server,
  Waves,
} from "lucide-react";

interface PublicLandingProps {
  authConfigured: boolean;
  authenticated: boolean;
  authLoading: boolean;
  onAuthAction: () => void;
  onOpenDashboard: () => void;
}

const REPO_URL = "https://github.com/mukulpythondev/hydrosense";

const howItWorks = [
  {
    step: "01",
    icon: FileSearch,
    title: "Curated event evidence",
    description:
      "Reported waterlogging incidents at Delhi underpasses are reviewed individually, each one linked to its original public source and dated.",
  },
  {
    step: "02",
    icon: BarChart3,
    title: "Rainfall and hotspot analysis",
    description:
      "Hourly rainfall from Open-Meteo is compared against a rain threshold learned for each underpass from its own flood history, with a pooled fallback where evidence is limited.",
  },
  {
    step: "03",
    icon: Gauge,
    title: "Risk information and future telemetry",
    description:
      "Forecast rain is compared to that threshold to produce a risk tier today. Physical ultrasonic sensors are planned to add direct depth readings alongside the forecast.",
  },
];

const architectureSteps = [
  {
    icon: Cpu,
    title: "Arduino Water-Level Monitoring",
    description: "Arduino-based ultrasonic sensor hardware, designed to post readings through the same contract already exercised by today's scenario tests.",
    status: "Hardware pilot: next deployment phase",
  },
  {
    icon: Server,
    title: "Sensor-to-Gateway Architecture",
    description: "API Gateway and AWS Lambda validate and accept readings, incidents, and field reports.",
    status: "Deployed",
  },
  {
    icon: Database,
    title: "Cloud Monitoring Architecture",
    description: "Readings, incidents, and community reports persist in DynamoDB behind a least-privilege execution role.",
    status: "Deployed",
  },
  {
    icon: Waves,
    title: "AI Image Assessment — Nova Lite",
    description: "Community-submitted photos are read by Amazon Bedrock Nova Lite for an advisory, non-certifying assessment.",
    status: "Deployed",
  },
  {
    icon: LayoutDashboard,
    title: "Operational console",
    description: "The dashboard you can open now reads this same API, served from S3 through CloudFront.",
    status: "Deployed",
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
            <small>Delhi underpass flood intelligence</small>
          </span>
        </button>
        <nav className="public-nav" aria-label="Public navigation">
          <a href="#product">Product</a>
          <a href="#how-it-works">How It Works</a>
          <a href="#data-gap">Our Data</a>
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
            Open Dashboard <ArrowRight size={17} aria-hidden="true" />
          </button>
        </div>
      </header>

      <main id="main-content">
        <section className="public-hero" aria-labelledby="public-hero-title">
          <div className="public-hero-grid" aria-hidden="true" />
          <div className="public-hero-copy">
            <p className="eyebrow">Localized flood intelligence for Delhi</p>
            <h1 id="public-hero-title">Know the risk before the water rises.</h1>
            <p className="public-hero-lede">
              HydroSense turns curated historical waterlogging reports and live rainfall data into
              underpass-level flood intelligence for Delhi, so commuters and operators can see which
              crossings are worth a second look before they set out.
            </p>
            <div className="public-hero-actions">
              <button className="button-primary button-large" type="button" onClick={onOpenDashboard}>
                Explore Dashboard <ArrowRight size={18} aria-hidden="true" />
              </button>
              <a className="text-link" href="#how-it-works">
                How It Works
              </a>
            </div>
          </div>
          <div className="public-hero-status" aria-label="Current product scope">
            <span><CheckCircle2 size={16} aria-hidden="true" /> 16 Delhi underpasses under evaluation</span>
            <span><Activity size={16} aria-hidden="true" /> 46 reviewed historical events</span>
            <span><CloudRain size={16} aria-hidden="true" /> Risk requires a usable forecast</span>
          </div>
        </section>

        <section className="product-preview-band" id="product" aria-labelledby="product-preview-title">
          <div className="section-intro">
            <p className="eyebrow">Inside the console</p>
            <h2 id="product-preview-title">A single operational picture, not a reassuring guess.</h2>
            <p>
              The dashboard keeps live telemetry, forecast-driven underpass risk, historical evidence, and
              community field reports in distinct, clearly labelled panels. The layout below mirrors the
              real interface; open the dashboard for current values.
            </p>
          </div>

          <div className="console-mock" aria-label="Static preview of the HydroSense console layout, not live data">
            <div className="console-mock-sidebar">
              <div className="console-mock-brand">
                <Waves size={16} aria-hidden="true" /> HydroSense
              </div>
              <div className="console-mock-tab active"><LayoutDashboard size={14} aria-hidden="true" /> Overview</div>
              <div className="console-mock-tab"><MapPin size={14} aria-hidden="true" /> Underpass risk</div>
              <div className="console-mock-tab"><Gauge size={14} aria-hidden="true" /> Monitoring</div>
              <div className="console-mock-tab"><History size={14} aria-hidden="true" /> Evidence</div>
            </div>
            <div className="console-mock-main">
              <div className="console-mock-stats">
                <div><small>Critical flood warnings</small><strong>--</strong></div>
                <div><small>Community field reports</small><strong>--</strong></div>
                <div><small>Alert threshold</small><strong>--</strong></div>
                <div><small>Historical event rows</small><strong>46</strong></div>
              </div>
              <div className="console-mock-map" aria-hidden="true">
                <span /><span /><span /><span /><span /><span /><span /><span />
              </div>
            </div>
          </div>
          <p className="preview-disclaimer">
            Preview of the interface structure captured from the running application. It is not a live or
            real-time feed; figures update only inside the actual dashboard.
          </p>
          <button className="button-secondary" type="button" onClick={onOpenDashboard}>
            Open the live dashboard <ArrowRight size={16} aria-hidden="true" />
          </button>
        </section>

        <section className="data-gap-band" id="data-gap" aria-labelledby="data-gap-title">
          <div className="section-intro">
            <p className="eyebrow">The data gap</p>
            <h2 id="data-gap-title">Public flood reports are scattered. We structure them.</h2>
            <p>
              News coverage of Delhi waterlogging is real but fragmented across dozens of publishers, with no
              shared location IDs or timestamps. HydroSense reviews those reports underpass by underpass, links
              each one to its source, and pairs the result with Open-Meteo rainfall at that location.
            </p>
          </div>
          <div className="evidence-grid">
            <article className="evidence-card">
              <span className="evidence-tag">Historical evidence</span>
              <strong>46 reviewed events</strong>
              <p>Across 15 distinct storm days and 16 underpasses, each event sourced and dated, not synthesized.</p>
            </article>
            <article className="evidence-card">
              <span className="evidence-tag">Forecast capability</span>
              <strong>24-hour rainfall lookahead</strong>
              <p>
                Live Open-Meteo forecasts are compared to each underpass's learned threshold. A forecast that
                fails to load produces an unknown risk, never a false "clear."
              </p>
            </article>
          </div>
        </section>

        <section className="how-it-works-band" id="how-it-works" aria-labelledby="how-it-works-title">
          <div className="section-intro">
            <p className="eyebrow">How it works</p>
            <h2 id="how-it-works-title">From a news article to a risk tier.</h2>
          </div>
          <div className="step-grid">
            {howItWorks.map(({ step, icon: Icon, title, description }) => (
              <article className="step-card" key={step}>
                <span className="step-number">{step}</span>
                <Icon size={24} aria-hidden="true" />
                <h3>{title}</h3>
                <p>{description}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="architecture-band" id="architecture" aria-labelledby="architecture-title">
          <div className="architecture-grid-texture" aria-hidden="true" />
          <div className="section-intro light">
            <p className="eyebrow">Hardware and cloud architecture</p>
            <h2 id="architecture-title">A sensor-to-cloud path, built one verified stage at a time.</h2>
            <p>
              Each stage below is either deployed today or explicitly marked as still in progress. Nothing here
              is described as complete unless it has been verified end to end.
            </p>
          </div>
          <div className="architecture-flow">
            {architectureSteps.map(({ icon: Icon, title, description, status }, index) => (
              <article className="architecture-step" key={title}>
                <div className="architecture-step-icon">
                  <Icon size={20} aria-hidden="true" />
                </div>
                <h3>{title}</h3>
                <p>{description}</p>
                <span className={`architecture-status ${status === "Deployed" ? "live" : "pending"}`}>
                  {status}
                </span>
                {index < architectureSteps.length - 1 && (
                  <ArrowRight className="architecture-arrow" size={18} aria-hidden="true" />
                )}
              </article>
            ))}
          </div>
        </section>

        <section className="limitations-band" id="limitations" aria-labelledby="limitations-title">
          <div>
            <p className="eyebrow">Trust and limitations</p>
            <h2 id="limitations-title">Decision support, not an official safety declaration.</h2>
          </div>
          <div className="limitations-copy">
            <p>
              Risk tiers are an estimate derived from historical correlation and forecast rainfall, not a
              certified flood prediction. Follow official police closures and municipal guidance.
            </p>
            <p>
              Coverage is incomplete: reported events depend on news coverage, coordinates are approximate, and
              some underpasses rely on a shared pooled threshold rather than their own flood history. When the
              rainfall forecast fails to load, HydroSense reports that risk as unknown, never as zero.
            </p>
          </div>
        </section>

        <section className="final-cta-band" aria-labelledby="final-cta-title">
          <h2 id="final-cta-title">See today&rsquo;s underpass risk for Delhi.</h2>
          <p>Live rainfall, reviewed evidence, and current incident status, in one console.</p>
          <button className="button-primary button-large" type="button" onClick={onOpenDashboard}>
            Open Dashboard <ArrowRight size={18} aria-hidden="true" />
          </button>
        </section>
      </main>

      <footer className="public-footer">
        <span>HydroSense &mdash; Delhi flood decision support platform</span>
        <a href={REPO_URL} target="_blank" rel="noreferrer noopener">
          <ExternalLink size={14} aria-hidden="true" /> View source
        </a>
      </footer>
    </div>
  );
}
