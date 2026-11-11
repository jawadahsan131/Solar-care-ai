import Link from "next/link";

const benefits = [
  {
    number: "01",
    title: "Start with your home",
    text: "Build a room-by-room appliance list, by photo or by hand.",
  },
  {
    number: "02",
    title: "Check every detail",
    text: "Review watts, hours, and typical values before they count.",
  },
  {
    number: "03",
    title: "Compare your options",
    text: "See clear on-grid, hybrid, and off-grid planning estimates.",
  },
];

export default function HomePage() {
  return (
    <main>
      <header className="topbar landing-nav">
        <Link className="brand-lockup" href="/">
          <span className="brand-mark">S</span> Solar Care AI
        </Link>
        <nav className="nav-actions" aria-label="Account">
          <Link className="button button-quiet" href="/login">Log in</Link>
          <Link className="button button-primary" href="/signup">Get started</Link>
        </nav>
      </header>

      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow"><span className="status-dot" /> MADE FOR YOUR HOME</p>
          <h1>A clearer way to plan solar for <em>your home.</em></h1>
          <p className="hero-lede">
            List your appliances, check what they use, and explore a solar setup
            that fits your daily life.
          </p>
          <div className="hero-actions">
            <Link className="button button-primary button-large" href="/signup">
              Plan my home <span aria-hidden="true">→</span>
            </Link>
            <span className="hero-reassurance">Your estimates. Your decisions.</span>
          </div>
          <div className="hero-footnote">
            <span aria-hidden="true">✳</span> Planning estimates, with every value editable.
          </div>
        </div>

        <div className="hero-art" aria-label="Illustration of a home with solar panels">
          <div className="sun-glow" />
          <div className="sun" aria-hidden="true">✳</div>
          <div className="energy-tag"><span /> Solar-ready living</div>
          <div className="house">
            <div className="roof">
              <div className="solar-panel"><i /><i /><i /><i /><i /><i /></div>
            </div>
            <div className="house-body">
              <div className="window window-left"><span /><span /></div>
              <div className="door" />
              <div className="window window-right"><span /><span /></div>
            </div>
          </div>
          <div className="landscape landscape-back" />
          <div className="landscape landscape-front" />
          <div className="floating-note">
            <span className="note-icon">↗</span>
            <span><strong>Know what you need</strong><small>Before you choose a system</small></span>
          </div>
          <div className="plant plant-one"><i /><i /><i /></div>
          <div className="plant plant-two"><i /><i /><i /></div>
        </div>
      </section>

      <section className="steps-section">
        <div className="section-heading">
          <p className="eyebrow">A SIMPLE PLACE TO BEGIN</p>
          <h2>From appliances to a plan.</h2>
        </div>
        <div className="benefit-grid">
          {benefits.map((benefit) => (
            <article className="benefit-card" key={benefit.number}>
              <span className="benefit-number">{benefit.number}</span>
              <h3>{benefit.title}</h3>
              <p>{benefit.text}</p>
            </article>
          ))}
        </div>
      </section>

      <footer className="site-footer">
        <Link className="brand-lockup" href="/">
          <span className="brand-mark">S</span> Solar Care AI
        </Link>
        <p>Thoughtful estimates for a brighter home.</p>
      </footer>
    </main>
  );
}
