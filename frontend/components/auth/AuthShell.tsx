import type { ReactNode } from "react";
import {
  Activity,
  ArrowUpRight,
  Radar,
  ShieldCheck,
  TrendingUp,
} from "lucide-react";

type AuthMode = "sign-in" | "sign-up";

type AuthShellProps = {
  mode: AuthMode;
  eyebrow: string;
  title: string;
  description: string;
  children: ReactNode;
};

const capabilityCards = [
  {
    icon: TrendingUp,
    title: "Cash runway",
    body: "Keep scenario-tested visibility on burn, hiring pace, and the moments that matter next.",
  },
  {
    icon: Radar,
    title: "Variance watch",
    body: "Spot spend drift, odd patterns, and missing context before they turn into end-of-month surprises.",
  },
  {
    icon: ShieldCheck,
    title: "Controlled access",
    body: "One secure workspace for operators, finance leads, and everyone who needs the same numbers.",
  },
];

const modeNotes: Record<AuthMode, string[]> = {
  "sign-in": [
    "Resume live forecasting",
    "Review anomaly alerts",
    "Pick up where your team left off",
  ],
  "sign-up": [
    "Launch your workspace",
    "Invite the right operators",
    "Start from a cleaner finance rhythm",
  ],
};

export function AuthShell({
  mode,
  eyebrow,
  title,
  description,
  children,
}: AuthShellProps) {
  return (
    <main className="auth-shell">
      <div aria-hidden="true" className="auth-shell__orb auth-shell__orb--left" />
      <div
        aria-hidden="true"
        className="auth-shell__orb auth-shell__orb--right"
      />
      <div aria-hidden="true" className="auth-shell__grid" />

      <div className="auth-shell__inner">
        <section className="auth-shell__panel">
          <div className="auth-shell__panelFrame glass animate-fade-up">
            <div className="auth-shell__panelHeader">
              <div className="auth-shell__eyebrowRow">
                <span className="auth-shell__eyebrow">{eyebrow}</span>
                <span className="auth-shell__securePill">
                  <ShieldCheck size={14} />
                  Secured by Clerk
                </span>
              </div>

              <h1 className="auth-shell__panelTitle">{title}</h1>
              <p className="auth-shell__panelDescription">{description}</p>

              <ul className="auth-shell__noteList" aria-label="Auth page highlights">
                {modeNotes[mode].map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            </div>

            <div className="auth-shell__clerkWrapper">{children}</div>
          </div>
        </section>

        <section className="auth-shell__story">
          <div className="auth-shell__brand animate-fade-up delay-1">
            <span className="auth-shell__brandMark">
              <Activity size={16} />
            </span>
            <span>AI CFO</span>
          </div>

          <div className="auth-shell__headlineBlock animate-fade-up delay-2">
            <p className="auth-shell__kicker">
              Financial command center for teams who want calmer closes and
              clearer decisions.
            </p>
            <h2 className="auth-shell__storyTitle">
              Steer the numbers before the numbers steer you.
            </h2>
            <p className="auth-shell__storyDescription">
              Forecast the next move, catch drift early, and keep every finance
              conversation anchored to the same live picture.
            </p>
          </div>

          <div className="auth-shell__cardGrid animate-fade-up delay-3">
            {capabilityCards.map(({ icon: Icon, title: cardTitle, body }) => (
              <article key={cardTitle} className="auth-shell__card">
                <div className="auth-shell__cardIcon">
                  <Icon size={18} />
                </div>
                <div>
                  <h3 className="auth-shell__cardTitle">{cardTitle}</h3>
                  <p className="auth-shell__cardBody">{body}</p>
                </div>
              </article>
            ))}
          </div>

          <aside className="auth-shell__brief animate-fade-up delay-4">
            <div className="auth-shell__briefHeader">
              <span className="auth-shell__briefLabel">Inside the workspace</span>
              <ArrowUpRight size={16} />
            </div>
            <p className="auth-shell__briefText">
              Live forecasting, scenario planning, budget tracking, approvals,
              and board-ready reporting in one deliberately focused environment.
            </p>
            <div className="auth-shell__briefTags" aria-label="Platform features">
              <span>Forecasting</span>
              <span>Controls</span>
              <span>Reporting</span>
            </div>
          </aside>
        </section>
      </div>
    </main>
  );
}
