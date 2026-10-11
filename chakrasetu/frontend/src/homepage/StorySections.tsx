import { Wrench, ArrowRight, ArrowUpRight, ShieldCheck, Truck, Factory, Zap, Battery, Leaf } from "lucide-react";
import type { DecisionPolicy } from "../decisionTypes";
export function StorySections({policy,signedIn,onOpen}:{policy:DecisionPolicy|null;signedIn:boolean;onOpen:(page:string)=>void}){
return <>
      <section className="why-section home-section">
          <span className="home-kicker">02 / WHY THE NETWORK MATTERS</span>
          <div className="why-layout">
            <h2>
              The battery isn’t the only
              <br />
              <em>thing that needs a connection.</em>
            </h2>
            <div>
              <p className="home-large-copy">
                A workshop may have the pack. A specialist may have the tools. A
                recycler may have capacity. The useful next step depends on
                bringing them together.
              </p>
              <p>
                Technical histories are often incomplete. Inspection capability
                varies. Chemistries, conditions and handling requirements
                differ. Without a coordinated chain, a suitable destination can
                still be out of reach.
              </p>
              <p>
                ChakraSetu connects the information, the organizations and the
                physical handoffs, so each next step fits the battery’s
                condition and the receiver’s actual scope.
              </p>
            </div>
          </div>
          <div className="fragment-chain">
            <span>
              <Wrench />A workshop has a pack
            </span>
            <ArrowRight />
            <span>
              <ShieldCheck />A specialist has evidence
            </span>
            <ArrowRight />
            <span>
              <Truck />A carrier has the right scope
            </span>
            <ArrowRight />
            <span>
              <Factory />A receiver has capacity
            </span>
          </div>
        </section>
        <section className="engine-section home-section" id="engine">
          <div className="home-section-heading">
            <div>
              <span className="home-kicker">03 / AN EXPLAINABLE DECISION</span>
              <h2>
                Evidence leads.
                <br />
                <em>Economics follows.</em>
              </h2>
            </div>
            <p>
              There is no single score that makes a battery safe, and no
              universal health threshold that decides its destination.
            </p>
          </div>
          <div className="engine-sequence">
            {[
              [
                "01",
                "Owner report",
                "Known specifications, condition, preliminary PBS and available inspection findings.",
              ],
              [
                "02",
                "Qualified evidence",
                "Application-specific assessments retain their procedure, source, reviewer and limitations.",
              ],
              [
                "03",
                "Hard gates",
                "Handling concern and technical suitability restrict the candidate pathways before ranking.",
              ],
              [
                "04",
                "A capable chain",
                "Receiver qualifications, carrier scope, geography, service windows and available capacity.",
              ],
              [
                "05",
                "Comparable economics",
                "Current offers and documented costs on the same perspective, currency and horizon.",
              ],
              [
                "06",
                "An accountable next step",
                "Recommendation, alternatives, missing information and a preserved decision history.",
              ],
            ].map(([n, t, d]) => (
              <div key={n}>
                <span>{n}</span>
                <h3>{t}</h3>
                <p>{d}</p>
              </div>
            ))}
          </div>
          <p className="engine-note">
            <ShieldCheck size={22} />
            <span>
              {policy
                ? `The initial ${policy.policy.automotive_screen_soh}% and ${policy.policy.second_life_screen_soh}% SoH bands are configurable screening aids.`
                : "SoH screening bands are configurable."}{" "}
              Low SoH prompts questions about repairability and application
              suitability. It never automatically sends a battery to recycling.
            </span>
          </p>
        </section>
        <section className="outcomes-section home-section">
          <span className="home-kicker">04 / MORE THAN ONE WAY FORWARD</span>
          <h2>
            The best pathway fits
            <br />
            <em>the battery in front of you.</em>
          </h2>
          <div className="outcomes-grid">
            {[
              [
                Zap,
                "Continued use",
                "For a defined vehicle application with the required evidence and validation.",
              ],
              [
                Wrench,
                "Refurbishment",
                "A documented repair, compatible expertise and post-repair requalification.",
              ],
              [
                Battery,
                "A second life",
                "A separately tracked product matched to an intended application and accepting customer.",
              ],
              [
                Factory,
                "Material recovery",
                "Appropriate treatment, measured material lots and documented downstream destinations.",
              ],
              [
                ShieldCheck,
                "Specialist assessment",
                "Controlled review when condition, technical evidence or handling instructions are uncertain.",
              ],
            ].map(([Icon, title, description], i) => {
              const I = Icon as typeof Zap;
              return (
                <article key={i}>
                  <I size={26} />
                  <h3>{String(title)}</h3>
                  <p>{String(description)}</p>
                </article>
              );
            })}
          </div>
          <p className="muted">
            Reuse is not always preferable. A safe, technically suitable and
            economically justified recycling pathway can be the right next step.
          </p>
        </section>
        <section
          className="participants-section home-section"
          id="participants"
        >
          <div className="home-section-heading">
            <div>
              <span className="home-kicker">
                05 / A NETWORK OF DIFFERENT STRENGTHS
              </span>
              <h2>
                Different roles.
                <br />
                <em>One coordinated journey.</em>
              </h2>
            </div>
            <p>
              An organization can hold multiple roles. Each activity has its own
              reviewed chemistry, condition, safety, geography and capacity
              scope.
            </p>
          </div>
          <div className="participant-list">
            {[
              "Originators & workshops",
              "Buyers & aggregation hubs",
              "Diagnostic specialists",
              "Transporters",
              "Refurbishers & remanufacturers",
              "Second-life integrators & customers",
              "Recyclers, processors & refiners",
              "Network operators & reviewers",
            ].map((p, i) => (
              <div key={p}>
                <span>{String(i + 1).padStart(2, "0")}</span>
                <h3>{p}</h3>
                <ArrowUpRight size={20} />
              </div>
            ))}
          </div>
          <button
            className="home-secondary"
            onClick={() => onOpen(signedIn ? "Account & access" : "Join")}
          >
            Build your organization profile
            <ArrowRight size={18} />
          </button>
        </section>
        <section className="impact-section home-section">
          <div className="impact-symbol">
            <Leaf size={64} />
            <span>
              REPAIR
              <br />
              REUSE
              <br />
              RECOVER
            </span>
          </div>
          <div>
            <span className="home-kicker">
              06 / CIRCULARITY THAT CAN BE FOLLOWED
            </span>
            <h2>
              Keep useful value in motion.
              <br />
              <em>Keep its story with it.</em>
            </h2>
            <p>
              Better assessment can identify viable continued use. Better
              matching can connect batteries with the right expertise. Better
              coordination can make every movement and eventual disposition
              visible.
            </p>
            <p>
              Registrations, recommendations, booked routes, physical handovers
              and completed processing are different milestones. Outcomes are
              counted only when the corresponding evidence is recorded.
            </p>
            <p className="impact-note">
              The intended impact: fewer information gaps, more appropriate
              routing and a clearer path to recover useful materials.
            </p>
          </div>
        </section>
  
</>;
}
