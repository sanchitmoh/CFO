"use client";

import { useEffect, useRef, type ReactNode } from "react";
import Link from "next/link";
import { useAuth } from "@clerk/nextjs";
import {
  Activity,
  ArrowRight,
  BellRing,
  Bot,
  ChevronRight,
  FileSpreadsheet,
  GitBranch,
  Layers3,
  Radar,
  ShieldCheck,
  TrendingUp,
  Wallet,
} from "lucide-react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import styles from "./HomeLanding.module.css";

gsap.registerPlugin(ScrollTrigger);

const proofStats = [
  { value: "18 mo", label: "runway clarity in one view" },
  { value: "6 desks", label: "forecasting to tax operations" },
  { value: "< 1 min", label: "from signal to next action" },
];

const featureCards = [
  {
    icon: TrendingUp,
    tone: "gold",
    eyebrow: "Forecasting",
    title: "Scenario planning that feels operational, not theoretical.",
    body: "Model hiring, burn, revenue, and cost changes with a command surface built for actual decisions.",
  },
  {
    icon: Radar,
    tone: "blue",
    eyebrow: "Anomaly watch",
    title: "Catch financial drift before it becomes a closing surprise.",
    body: "Spot odd movement, missing context, and spend variance with a calmer view of what changed and why.",
  },
  {
    icon: Wallet,
    tone: "green",
    eyebrow: "Budgets and goals",
    title: "Keep teams aligned to thresholds, runway, and the metrics that matter next.",
    body: "Turn financial guardrails into visible operating rhythm instead of buried spreadsheet rules.",
  },
  {
    icon: ShieldCheck,
    tone: "gold",
    eyebrow: "Controls",
    title: "Approvals, audit, and role-aware workflows in the same environment.",
    body: "Review who changed what, route decisions with confidence, and preserve context around every financial action.",
  },
  {
    icon: FileSpreadsheet,
    tone: "blue",
    eyebrow: "Reporting",
    title: "Board-ready reporting without the familiar scramble.",
    body: "Move from live numbers to investor views, exports, and narrative-ready reporting with less rework.",
  },
  {
    icon: GitBranch,
    tone: "green",
    eyebrow: "Operations",
    title: "Vendors, invoices, tax, and scenarios connected instead of scattered.",
    body: "Bring the finance back office into the same command layer so workflows stop fragmenting across tabs.",
  },
];

const commandLoop = [
  {
    step: "01",
    title: "Ingest the live picture",
    body: "Transactions, budgets, goals, approvals, and reporting modules stay close enough to keep decisions grounded.",
  },
  {
    step: "02",
    title: "Surface what changed",
    body: "Anomalies, budget pressure, and runway shifts rise to the top with the right tone and urgency.",
  },
  {
    step: "03",
    title: "Act from one command layer",
    body: "Forecast, review, approve, and communicate the next move without bouncing between disconnected tools.",
  },
];

const orbitCards = [
  {
    label: "Runway",
    value: "18.4 mo",
    detail: "after planned hiring",
  },
  {
    label: "Spend drift",
    value: "-8.2%",
    detail: "caught before close",
  },
  {
    label: "Approvals",
    value: "14 queued",
    detail: "with audit context",
  },
];

function WorkspaceEntryLink({
  className,
  children,
}: {
  className: string;
  children: ReactNode;
}) {
  return (
    // Use a document navigation here so Clerk middleware can complete
    // its dev-mode handshake or redirect flow before entering protected routes.
    <a href="/dashboard" className={className}>
      {children}
    </a>
  );
}

export function HomeLanding() {
  const { isSignedIn } = useAuth();
  const rootRef = useRef<HTMLElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<HTMLDivElement>(null);
  const prismRef = useRef<HTMLDivElement>(null);
  const shadowRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const root = rootRef.current;
    const stage = stageRef.current;
    const scene = sceneRef.current;
    const prism = prismRef.current;
    const shadow = shadowRef.current;

    if (!root || !stage || !scene || !prism || !shadow) {
      return;
    }

    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;

    const baseRotateX = -16;
    const baseRotateY = 20;

    const ctx = gsap.context(() => {
      if (prefersReducedMotion) {
        gsap.set("[data-hero], [data-reveal]", { autoAlpha: 1, y: 0 });
        return;
      }

      gsap.set("[data-hero]", { autoAlpha: 0, y: 28 });
      gsap.to("[data-hero]", {
        autoAlpha: 1,
        y: 0,
        duration: 0.95,
        stagger: 0.08,
        ease: "power3.out",
      });

      gsap.set(scene, {
        rotateX: baseRotateX,
        rotateY: baseRotateY,
        transformPerspective: 1800,
        transformOrigin: "50% 50%",
      });

      gsap.to(prism, {
        rotateY: "+=360",
        duration: 22,
        repeat: -1,
        ease: "none",
      });

      gsap.to(scene, {
        y: -16,
        duration: 4.8,
        repeat: -1,
        yoyo: true,
        ease: "sine.inOut",
      });

      gsap.to(shadow, {
        scaleX: 1.08,
        opacity: 0.4,
        duration: 4.8,
        repeat: -1,
        yoyo: true,
        ease: "sine.inOut",
      });

      gsap.utils
        .toArray<HTMLElement>("[data-orbit]")
        .forEach((element, index) => {
          gsap.to(element, {
            y: index % 2 === 0 ? -16 : 16,
            x: index % 2 === 0 ? 8 : -10,
            duration: 3.6 + index * 0.4,
            repeat: -1,
            yoyo: true,
            ease: "sine.inOut",
          });
        });

      gsap.utils.toArray<HTMLElement>("[data-band]").forEach((element, index) => {
        gsap.fromTo(
          element,
          { scale: 0.94, autoAlpha: 0.38 },
          {
            scale: 1.04 + index * 0.03,
            autoAlpha: 0.72,
            duration: 4.2 + index * 0.4,
            repeat: -1,
            yoyo: true,
            ease: "sine.inOut",
          },
        );
      });

      gsap.utils
        .toArray<HTMLElement>("[data-reveal]")
        .forEach((element) => {
          gsap.fromTo(
            element,
            { autoAlpha: 0, y: 36 },
            {
              autoAlpha: 1,
              y: 0,
              duration: 0.9,
              ease: "power3.out",
              scrollTrigger: {
                trigger: element,
                start: "top 82%",
                once: true,
              },
            },
          );
        });
    }, root);

    if (prefersReducedMotion) {
      return () => ctx.revert();
    }

    const rotateYTo = gsap.quickTo(scene, "rotateY", {
      duration: 0.65,
      ease: "power3.out",
    });
    const rotateXTo = gsap.quickTo(scene, "rotateX", {
      duration: 0.65,
      ease: "power3.out",
    });
    const stageXTo = gsap.quickTo(stage, "x", {
      duration: 0.65,
      ease: "power3.out",
    });
    const stageYTo = gsap.quickTo(stage, "y", {
      duration: 0.65,
      ease: "power3.out",
    });
    const shadowXTo = gsap.quickTo(shadow, "x", {
      duration: 0.65,
      ease: "power3.out",
    });
    const shadowYTo = gsap.quickTo(shadow, "y", {
      duration: 0.65,
      ease: "power3.out",
    });

    const handlePointerMove = (event: PointerEvent) => {
      const rect = stage.getBoundingClientRect();
      const x = (event.clientX - rect.left) / rect.width - 0.5;
      const y = (event.clientY - rect.top) / rect.height - 0.5;

      rotateYTo(baseRotateY + x * 20);
      rotateXTo(baseRotateX - y * 18);
      stageXTo(x * 10);
      stageYTo(y * 12);
      shadowXTo(x * 28);
      shadowYTo(y * 16);
    };

    const handlePointerLeave = () => {
      rotateYTo(baseRotateY);
      rotateXTo(baseRotateX);
      stageXTo(0);
      stageYTo(0);
      shadowXTo(0);
      shadowYTo(0);
    };

    stage.addEventListener("pointermove", handlePointerMove);
    stage.addEventListener("pointerleave", handlePointerLeave);

    return () => {
      stage.removeEventListener("pointermove", handlePointerMove);
      stage.removeEventListener("pointerleave", handlePointerLeave);
      ctx.revert();
    };
  }, []);

  return (
    <main ref={rootRef} className={styles.page}>
      <div className={styles.backdrop} aria-hidden="true" />
      <div className={styles.radialLeft} aria-hidden="true" />
      <div className={styles.radialRight} aria-hidden="true" />

      <div className={styles.shell}>
        <nav className={styles.nav} data-hero>
          <Link href="/" className={styles.brand}>
            <span className={styles.brandMark}>
              <Bot size={18} />
            </span>
            <span>
              <strong>AI CFO</strong>
              <small>Financial Intelligence</small>
            </span>
          </Link>

          <div className={styles.navLinks}>
            <a href="#features">Features</a>
            <a href="#workflow">Workflow</a>
            <a href="#access">Access</a>
          </div>

          <div className={styles.navActions}>
            {!isSignedIn ? (
              <>
              <Link href="/sign-in" className={styles.ghostButton}>
                Sign in
              </Link>
              <Link href="/sign-up" className={styles.primaryButton}>
                Start free
              </Link>
              </>
            ) : (
              <WorkspaceEntryLink className={styles.primaryButton}>
                Open dashboard
              </WorkspaceEntryLink>
            )}
          </div>
        </nav>

        <section className={styles.hero}>
          <div className={styles.heroCopy}>
            <span className={styles.kicker} data-hero>
              Old-money precision for modern finance teams
            </span>

            <h1 className={styles.title} data-hero>
              The financial command center that makes clarity look expensive.
            </h1>

            <p className={styles.lead} data-hero>
              AI CFO brings forecasting, budgets, anomalies, approvals,
              operations, and reporting into one beautifully controlled
              workspace built for founders and finance operators who want fewer
              noisy tabs and stronger decisions.
            </p>

            <div className={styles.heroActions} data-hero>
              {!isSignedIn ? (
                <>
                <Link href="/sign-up" className={styles.primaryButton}>
                  Create workspace
                  <ArrowRight size={16} />
                </Link>
                <Link href="/sign-in" className={styles.secondaryButton}>
                  Explore access
                </Link>
                </>
              ) : (
                <WorkspaceEntryLink className={styles.primaryButton}>
                  Continue to workspace
                  <ArrowRight size={16} />
                </WorkspaceEntryLink>
              )}
            </div>

            <div className={styles.proofGrid} data-hero>
              {proofStats.map((stat) => (
                <article key={stat.label} className={styles.proofCard}>
                  <strong>{stat.value}</strong>
                  <span>{stat.label}</span>
                </article>
              ))}
            </div>
          </div>

          <div className={styles.heroVisual} data-hero>
            <div ref={stageRef} className={styles.stage}>
              <div ref={shadowRef} className={styles.stageShadow} />

              <div ref={sceneRef} className={styles.scene}>
                <div ref={prismRef} className={styles.prism} aria-hidden="true">
                  <div className={`${styles.face} ${styles.faceFront}`}>
                    <span>Forecasting</span>
                    <strong>Runway</strong>
                  </div>
                  <div className={`${styles.face} ${styles.faceBack}`}>
                    <span>Approvals</span>
                    <strong>Controls</strong>
                  </div>
                  <div className={`${styles.face} ${styles.faceLeft}`}>
                    <span>Reporting</span>
                    <strong>Board</strong>
                  </div>
                  <div className={`${styles.face} ${styles.faceRight}`}>
                    <span>Anomalies</span>
                    <strong>Signals</strong>
                  </div>
                  <div className={`${styles.face} ${styles.faceTop}`}>
                    <span>Budgets</span>
                    <strong>Discipline</strong>
                  </div>
                  <div className={`${styles.face} ${styles.faceBottom}`}>
                    <span>Scenario</span>
                    <strong>Branches</strong>
                  </div>
                </div>

                <div className={`${styles.band} ${styles.bandOne}`} data-band />
                <div className={`${styles.band} ${styles.bandTwo}`} data-band />
                <div className={`${styles.band} ${styles.bandThree}`} data-band />
              </div>

              <article
                className={`${styles.orbitCard} ${styles.orbitCardOne}`}
                data-orbit
              >
                <span>{orbitCards[0].label}</span>
                <strong>{orbitCards[0].value}</strong>
                <small>{orbitCards[0].detail}</small>
              </article>

              <article
                className={`${styles.orbitCard} ${styles.orbitCardTwo}`}
                data-orbit
              >
                <span>{orbitCards[1].label}</span>
                <strong>{orbitCards[1].value}</strong>
                <small>{orbitCards[1].detail}</small>
              </article>

              <article
                className={`${styles.orbitCard} ${styles.orbitCardThree}`}
                data-orbit
              >
                <span>{orbitCards[2].label}</span>
                <strong>{orbitCards[2].value}</strong>
                <small>{orbitCards[2].detail}</small>
              </article>
            </div>
          </div>
        </section>

        <section className={styles.ribbon} data-reveal>
          <div className={styles.ribbonLabel}>
            <Layers3 size={18} />
            What lives inside the workspace
          </div>
          <div className={styles.ribbonItems}>
            <span>Forecasting</span>
            <span>Budgets</span>
            <span>Goals</span>
            <span>Anomalies</span>
            <span>Approvals</span>
            <span>Tax</span>
            <span>Invoices</span>
            <span>Reports</span>
          </div>
        </section>

        <section id="features" className={styles.section}>
          <div className={styles.sectionHeading} data-reveal>
            <span className={styles.sectionEyebrow}>Features</span>
            <h2>Every high-friction finance surface, composed into one calm system.</h2>
            <p>
              Built to match the app you already have, but presented in a
              cleaner public narrative that makes the product feel intentional
              before anyone signs in.
            </p>
          </div>

          <div className={styles.featureGrid}>
            {featureCards.map(({ icon: Icon, tone, eyebrow, title, body }) => (
              <article
                key={title}
                className={`${styles.featureCard} ${styles[`tone${tone[0].toUpperCase()}${tone.slice(1)}`]}`}
                data-reveal
              >
                <div className={styles.featureIcon}>
                  <Icon size={18} />
                </div>
                <span className={styles.featureEyebrow}>{eyebrow}</span>
                <h3>{title}</h3>
                <p>{body}</p>
                <span className={styles.featureLink}>
                  Layered into the same command view
                  <ChevronRight size={15} />
                </span>
              </article>
            ))}
          </div>
        </section>

        <section id="workflow" className={styles.workflowSection}>
          <div className={styles.sectionHeading} data-reveal>
            <span className={styles.sectionEyebrow}>Command Loop</span>
            <h2>Designed around how modern finance teams actually move.</h2>
            <p>
              Not a marketing collage of disconnected tools. A cleaner operating
              sequence from signal to decision to communication.
            </p>
          </div>

          <div className={styles.workflowGrid}>
            {commandLoop.map((item) => (
              <article key={item.step} className={styles.workflowCard} data-reveal>
                <span className={styles.workflowStep}>{item.step}</span>
                <h3>{item.title}</h3>
                <p>{item.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="access" className={styles.ctaSection} data-reveal>
          <div className={styles.ctaPanel}>
            <div>
              <span className={styles.sectionEyebrow}>Access</span>
              <h2>Step into the workspace with the same gold-threaded system already powering the app.</h2>
              <p>
                Start with a public front door that feels premium, then move
                straight into the existing Clerk sign-in and sign-up flow
                without changing its behavior.
              </p>
            </div>

            <div className={styles.ctaActions}>
              {!isSignedIn ? (
                <>
                <Link href="/sign-up" className={styles.primaryButton}>
                  Start your workspace
                  <ArrowRight size={16} />
                </Link>
                <Link href="/sign-in" className={styles.secondaryButton}>
                  Sign in
                </Link>
                </>
              ) : (
                <WorkspaceEntryLink className={styles.primaryButton}>
                  Open dashboard
                  <ArrowRight size={16} />
                </WorkspaceEntryLink>
              )}
            </div>
          </div>

          <div className={styles.ctaSignals}>
            <div className={styles.signalCard}>
              <Activity size={18} />
              <span>Live runway and performance visibility</span>
            </div>
            <div className={styles.signalCard}>
              <BellRing size={18} />
              <span>Alerts, approvals, and next-step coordination</span>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
