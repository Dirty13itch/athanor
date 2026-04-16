# Human-in-the-Loop Patterns for Autonomous Systems

**Date:** 2026-02-25
**Status:** Research complete
**Supports:** GWT Phase 3+ (ADR-017), Dashboard UX, Agent Escalation Protocol
**Depends on:** ADR-008 (Agent Framework), ADR-017 (Meta-Orchestrator)

---

## Summary

This document surveys human-in-the-loop (HITL) patterns across ten domains -- self-driving vehicles, algorithmic trading, RLHF, drone teleoperation, recommendation systems, goal-setting frameworks, attention management, trust calibration, feedback loop design, and emerging 2025-2026 patterns -- and extracts design principles applicable to a one-person homelab running 8 autonomous AI agents.

The central tension: Shaun needs to see what agents are doing, give feedback, steer direction, and approve high-stakes decisions -- without micromanaging. He is an orchestrator, not an operator. The system must respect his limited attention while keeping him genuinely in control.

Ten cross-cutting design principles emerge from the research:

1. **Exception-based intervention, not continuous monitoring**
2. **Graduated autonomy with adjustable levels**
3. **Intent/goal-based direction, not task-based micromanagement**
4. **Prevent the rubber stamp through meaningful friction**
5. **Implicit feedback is more sustainable than explicit**
6. **Attention is finite -- filter ruthlessly**
7. **Trust calibration through transparency and track record**
8. **Feedback visibility -- show impact**
9. **Ambient awareness over active monitoring**
10. **Graceful degradation without the human**

---

## Domain 1: Self-Driving Vehicle Intervention Models

### How It Works

The autonomous vehicle industry has converged on three distinct human oversight models:

**Waymo (Level 4 -- Fleet Response):** Waymo operates fully driverless vehicles with a remote "Fleet Response" center staffed by approximately 70 agents worldwide across four geographically redundant locations (Arizona, Michigan, two cities in the Philippines). The ratio is roughly 1 human per 41 vehicles. Vehicles initiate contact when encountering uncertain situations -- a "phone-a-friend" model. Fleet response agents see real-time camera feeds, a 3D representation of what the car perceives, and can rewind feeds to understand the scene. Critically, agents provide *context and suggestions*, not direct control. The autonomous system "evaluates the input from fleet response and independently remains in control of driving." The vehicle can reject human guidance that conflicts with its safety assessment.

Source: [Waymo Fleet Response blog post, May 2024](https://waymo.com/blog/2024/05/fleet-response)

**Tesla (Level 2 -- Supervised Autonomy):** Tesla's Full Self-Driving (FSD) requires a human driver to remain attentive at all times. The commercial robotaxi service launched in Austin, Texas in June 2025 with a "supervised" qualifier. This is the opposite model from Waymo: continuous human monitoring of an autonomous system, rather than exception-based intervention.

Source: [InsideEVs - Tesla Robotaxi vs Waymo vs Cruise](https://insideevs.com/news/736709/tesla-robotaxi-waymo-cruise/)

**Performance Metrics:** Waymo recorded one disengagement every 9,793 miles and published peer-reviewed studies showing 85% fewer injury-causing crashes than human drivers. The key insight: as the system matures, "it can solve more ambiguous scenarios independently and needs less help."

Source: [Waymo Independent Audits, November 2025](https://waymo.com/blog/2025/11/independent-audits)

### Extracted Principles for Athanor

1. **Phone-a-friend, not continuous monitoring.** The system asks for help when it needs it; the human does not watch everything. Waymo's 1:41 staffing ratio proves that exception-based intervention scales.
2. **The autonomous system retains authority.** The human provides context; the system decides. This prevents the human from becoming a bottleneck and preserves the system's ability to act safely even with bad human input.
3. **Progressive independence.** As the system improves, it needs less help. Track the intervention rate over time -- it should trend downward.
4. **Rich context at intervention time.** When the system asks for help, it shows the human exactly what it sees (cameras, 3D model, ability to rewind). Don't show a bare text alert -- show the full situation.

---

## Domain 2: Algorithmic Trading Oversight

### How It Works

The algorithmic trading industry manages billions of dollars through autonomous systems with a layered defense model:

**Pre-trade controls (before execution):**
- Order size limits (max shares per order)
- Price collars (max deviation from current market price)
- Position limits (max exposure per asset/sector)
- Velocity logic (max orders per time window)
- Correlation filters (prevent overconcentration in similar assets)

Source: [FIA Best Practices for Automated Trading Risk Controls, 2024](https://www.fia.org/sites/default/files/2024-07/FIA_WP_AUTOMATED%20TRADING%20RISK%20CONTROLS_FINAL_0.pdf)

**Kill switches:** "A control that when activated immediately disables all trading activity for a particular participant or group of participants, typically preventing the ability to enter new orders and cancelling all working orders." The kill switch may also allow risk-reducing orders while preventing risk-increasing orders -- a nuanced emergency stop, not a total shutdown.

Source: [FIA Best Practices](https://www.fia.org/sites/default/files/2024-07/FIA_WP_AUTOMATED%20TRADING%20RISK%20CONTROLS_FINAL_0.pdf)

**Circuit breakers (market-wide):**
- Level 1 (7% decline): 15-minute pause
- Level 2 (13% decline): 15-minute halt
- Level 3 (20% decline): Trading stops for the day

Source: [LuxAlgo - Risk Management Strategies for Algo Trading](https://www.luxalgo.com/blog/risk-management-strategies-for-algo-trading/)

**Real-time monitoring dashboards** track Value at Risk (VaR), maximum drawdown, and other critical metrics continuously. Alerts should be generated within 5 seconds of identifying an event. Experienced traders monitor systems and "can intervene if algorithms deviate from expected behavior or if market conditions change unexpectedly."

Source: [LuxAlgo](https://www.luxalgo.com/blog/risk-management-strategies-for-algo-trading/), [Tradetron Risk Management](https://tradetron.tech/blog/enhancing-risk-management-in-algo-trading-techniques-and-best-practices-with-tradetron)

**The rubber stamp problem in trading:** Despite sophisticated controls, research on systemic failures in algorithmic trading (Knight Capital's $440M loss in 45 minutes, 2012) shows that human oversight fails when the system operates faster than humans can process, when alerts are ambiguous, or when organizational culture discourages stopping the machine.

Source: [PMC - Systemic failures and organizational risk management in algorithmic trading](https://pmc.ncbi.nlm.nih.gov/articles/PMC8978471/)

### Extracted Principles for Athanor

1. **Layered defense, not single-point control.** Pre-execution checks (automated), real-time monitoring (ambient), kill switch (manual), circuit breakers (automatic). Multiple independent safety layers.
2. **Guardrails over gatekeepers.** Define what agents *cannot* do (pre-trade controls) rather than approving everything they want to do. Let the system act freely within boundaries.
3. **Nuanced emergency stop.** A kill switch that allows "risk-reducing" actions while blocking "risk-increasing" ones. Applied to Athanor: a "pause new actions" mode that still lets agents finish in-progress tasks and respond to emergencies.
4. **5-second alert latency.** When something needs human attention, the notification should arrive within seconds, not minutes.

---

## Domain 3: RLHF (Reinforcement Learning from Human Feedback) Interfaces

### How It Works

RLHF interfaces collect human preferences to align AI systems. The research reveals a clear hierarchy of feedback mechanisms:

**Pairwise comparison (most reliable):** Show two outputs, ask which is better. "This relative judgment is generally easier and more reliable for humans to make consistently" than absolute scoring. Inter-annotator agreement is significantly higher for pairwise comparison than Likert scales.

Source: [Uni-RLHF, arXiv:2402.02423](https://arxiv.org/abs/2402.02423), [RLHF survey, arXiv:2312.14925](https://arxiv.org/abs/2312.14925)

**Likert scale (moderate reliability):** Rate quality on a scale. Some early works use 8-step scales with levels of preference. "Achieving inter-annotator calibration and consistency with absolute scores is notoriously difficult, and these scores often need post-processing to be converted into relative preferences."

Source: [RLHF learning resources, Nathan Lambert](https://www.interconnects.ai/p/rlhf-resources)

**Thumbs up/down (simplest but noisiest):** Binary feedback. Easy to give but loses nuance. Most useful when combined with implicit signals.

**Groupwise and context-aware interfaces (2024-2025 innovation):** "Groupwise, context-aware, or decomposed feedback leads to higher label accuracy and lower error rates relative to traditional pairwise or monolithic annotation frameworks." Tools like claim decomposition platforms break complex judgments into simpler components.

Source: [Labellerr - RLHF Tools 2025](https://www.labellerr.com/blog/top-tools-for-rlhf/)

**Natural language correction (highest quality, highest effort):** Explaining why one output is better provides the richest signal but fatigues annotators fastest. Best used sparingly for high-stakes calibration.

**Rubric-based evaluation (2025):** Labelbox released "Evaluation Studio" with rubric evaluation tools. Structured rubrics reduce cognitive load by turning complex quality judgments into checklist-like assessments.

Source: [Labellerr - RLHF Tools 2025](https://www.labellerr.com/blog/top-tools-for-rlhf/)

### The Quality-Fatigue Tradeoff

The fundamental finding across RLHF research: higher-quality feedback mechanisms require more cognitive effort and fatigue annotators faster. The solution is a mixed approach:

| Mechanism | Quality | Effort | Best For |
|-----------|---------|--------|----------|
| Natural language correction | Highest | Highest | Rare calibration events |
| Pairwise comparison | High | Medium | Regular preference tuning |
| Rubric evaluation | High | Medium | Structured quality assessment |
| Likert scale | Medium | Low-Medium | Quick quality ratings |
| Thumbs up/down | Low | Lowest | High-volume, low-stakes feedback |
| Implicit signals | Varies | Zero | Continuous background learning |

Source: [RLHF survey, arXiv:2504.12501v3](https://arxiv.org/html/2504.12501v3)

### Extracted Principles for Athanor

1. **Match feedback effort to decision stakes.** Thumbs up/down for routine agent outputs. Pairwise comparison ("which response was better?") when tuning behavior. Natural language correction only for critical steering decisions.
2. **Implicit feedback first.** The most sustainable feedback is the feedback the human does not have to consciously give. Track which agent outputs Shaun acts on, ignores, or undoes.
3. **Decompose complex judgments.** Don't ask "was this good?" -- ask specific sub-questions: "Was the content relevant? Was the action appropriate? Was the timing right?"
4. **Zero-effort feedback is infinitely sustainable.** Any mechanism that requires explicit action from the human has a fatigue ceiling. Build the system so the *absence* of correction is a signal.

---

## Domain 4: Drone/Robot Teleoperation and Sliding Autonomy

### How It Works

The drone/robotics field uses standardized autonomy levels similar to the automotive industry:

**Sheridan-Verplanck 10-Level Scale (1978):**

| Level | Description |
|-------|-------------|
| 1 | Human does everything |
| 2 | Computer offers alternatives |
| 3 | Computer narrows to a few alternatives |
| 4 | Computer suggests a recommended alternative |
| 5 | Computer executes if human approves |
| 6 | Computer executes; human can veto |
| 7 | Computer executes; informs human |
| 8 | Computer executes; informs human if asked |
| 9 | Computer executes; informs human if it decides to |
| 10 | Computer acts entirely autonomously |

Source: [Sheridan & Verplank, 1978; via ResearchGate](https://www.researchgate.net/figure/Levels-of-Automation-From-Sheridan-Verplank-1978_tbl1_235181550)

This maps to four automation functions identified by Parasuraman, Sheridan, and Wickens (2000):
1. Information acquisition
2. Information analysis
3. Decision and action selection
4. Action implementation

Each function can independently operate at a different automation level.

Source: [Parasuraman, Sheridan, Wickens (2000) - A model for types and levels of human interaction with automation](https://www.researchgate.net/publication/11596569_A_model_for_types_and_levels_of_human_interaction_with_automation_IEEE_Trans_Syst_Man_Cybern_Part_A_Syst_Hum_303_286-297)

**Drone autonomy levels (2024-2025):**
- Level 0: No automation
- Level 1: Low automation (assisted piloting)
- Level 2: Partial automation (automated flight, human monitoring)
- Level 3: Conditional automation (system handles most tasks, human on standby)
- Level 4: High automation (fully autonomous in designated areas)
- Level 5: Full automation (autonomous everywhere, no human needed)

Source: [SUIND - 5 Levels of Drone Autonomy](https://suind.com/2024/11/06/navigating-the-5-levels-of-drone-autonomy-a-look-at-suinds-approach-to-autonomous-systems/)

**Adaptive automation (dynamic level switching):** Research using EEG-based mental workload measurement shows that automation levels can be adjusted dynamically based on operator cognitive load. When the operator is overloaded, the system takes on more tasks automatically. When the operator is underloaded (risk of disengagement), the system deliberately gives back control to maintain engagement.

Source: [Adaptive Automation via EEG, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC5080530/)

### Extracted Principles for Athanor

1. **Per-agent, per-function autonomy levels.** Don't set one autonomy level for the whole system. The media agent might be at Level 8 (acts autonomously, informs if asked) while the home agent controlling physical devices is at Level 5 (executes if human approves). The coding agent writing to disk is at Level 6 (executes, human can veto).
2. **The autonomy slider is the primary control surface.** For each agent, Shaun should be able to slide between "always ask" (Level 5) and "just do it" (Level 9). This is the single most important dashboard control.
3. **Different functions, different levels.** An agent can gather information autonomously (Level 9) but require approval for actions (Level 5). Separate the observation autonomy from the action autonomy.
4. **Dynamic adjustment based on context.** When Shaun is actively using the dashboard, lower the autonomy threshold (more interaction). When he is away, raise it (more independence).

---

## Domain 5: Recommendation System Feedback

### How It Works

The major recommendation platforms have converged on a dual-signal model: heavy reliance on implicit behavioral signals with lightweight explicit feedback as a calibration overlay.

**Netflix:**
- Gives 10x more weight to watched content than thumbs-up/down ratings
- Binary feedback (thumbs) improved engagement accuracy by 200% over the 5-star system
- Added "two thumbs up" for stronger positive signals based on user testing
- 80% of content watched comes from recommendations, saving $1B annually
- "If people don't like a show, they generally just stop watching it" -- explicit negative feedback is rare

Source: [Netflix Recommendation Algorithm Analysis](https://marketingino.com/the-netflix-recommendation-algorithm-how-personalization-drives-80-of-viewer-engagement/), [Netflix Two Thumbs Up announcement](https://variety.com/2022/digital/news/netflix-two-thumbs-up-ratings-1235228641/)

**Spotify:**
- Implicit signals: play counts, skips, playlist additions, listening-session length, repeat listens, playthrough rate
- Explicit signals: library saves, playlist adds, shares, artist follows (weighted more heavily for building user profiles)
- "Semantic IDs" (2025) help AI understand the relationship between content and user history
- Launched "Prompted Playlist" (December 2025) -- direct user control of the algorithm through natural language
- "Exclude From Your Taste Profile" lets users explicitly reject signals

Source: [Spotify Recommendation System Guide 2025](https://www.music-tomorrow.com/blog/how-spotify-recommendation-system-works-complete-guide), [Spotify Prompted Playlists announcement](https://newsroom.spotify.com/2025-12-10/spotify-prompted-playlists-algorithm-gustav-soderstrom/)

**Beyond Explicit and Implicit (2025 research):** A new category -- "intentional implicit feedback" -- has been identified. This captures behaviors users *deliberately* perform expecting algorithmic interpretation, such as strategically swiping past content, conducting targeted searches, or dwelling on posts. Users experience frustration and "browsing fatigue" when this intentional implicit feedback is ignored or interpreted too conservatively.

Source: [Beyond Explicit and Implicit, arXiv:2502.09869v1](https://arxiv.org/html/2502.09869v1)

**User fatigue research (SIGIR 2024):** "User fatigue" in recommendations -- being tired of content too similar to recent history -- is poorly addressed by existing recommenders. The FRec fatigue-aware model improved AUC by up to 0.026 and GAUC by 0.019 compared to state-of-the-art, demonstrating measurable gains from modeling fatigue.

Source: [Modeling User Fatigue for Sequential Recommendation, SIGIR 2024](https://dl.acm.org/doi/10.1145/3626772.3657802)

### Extracted Principles for Athanor

1. **Behavior is the strongest signal.** Which agent outputs Shaun acts on, which he ignores, which he undoes -- these implicit signals are 10x more informative than explicit ratings.
2. **Make explicit feedback effortless.** Netflix's switch from 5-star to binary improved accuracy by 200%. The simplest possible explicit signal is better than a complex one nobody uses.
3. **"Not interested" is more valuable than "interested."** Negative explicit feedback is rare and powerful. Give Shaun a one-tap "stop doing this" mechanism.
4. **Respect intentional implicit signals.** If Shaun consistently ignores a category of agent notification, that is intentional implicit feedback. The system should learn from it, not keep pushing the same type of notification.
5. **Model fatigue explicitly.** If agents keep surfacing the same type of information, reduce its salience over time even if it is technically relevant.

---

## Domain 6: Goal-Setting vs Task-Setting

### How It Works

**Commander's Intent (military doctrine):**

Commander's intent is "a clear, concise statement of what the force must do and the conditions the force must establish with respect to the enemy, terrain, and civil considerations that represent the desired end state." It goes beyond outlining tasks and objectives -- it provides context and articulates expectations about the ultimate goal, empowering individuals throughout the chain of command to "adapt to changing circumstances and make decisions that align with the overarching mission."

The key distinction: task orders specify *what to do*, while intent specifies *why and to what end*. With intent, subordinates can improvise when conditions change without waiting for new orders.

Source: [Wikipedia - Intent (military)](https://en.wikipedia.org/wiki/Intent_(military)), [AgilityPortal - Commander's Intent for Business](https://agilityportal.io/blog/commanders-intent)

**Commander's Intent for Machines (West Point, 2025):**

The Modern War Institute proposes encoding commander's intent into autonomous systems through:
- Natural language processing to extract key tasks and end states from written intent
- Pre-programmed mission parameters loaded before deployment
- Autonomous systems that can revert to assigned missions when communications fail
- Human approval required for lethal action; autonomous execution for reconnaissance and non-lethal tasks

The framework accepts that autonomous systems will sometimes be disconnected from human oversight and must act on internalized goals rather than real-time instructions.

Source: [MWI - Commander's Intent for Machines](https://mwi.westpoint.edu/commanders-intent-for-machines-reimagining-unmanned-systems-control-in-communications-degraded-environments/)

**Mission Command (U.S. Space Force Doctrine, November 2024):**

Mission command emphasizes "competence, mutual trust, shared understanding, commander's intent, mission-type orders, disciplined initiative, and risk acceptance." The human provides goals and constraints; the system figures out how to achieve them.

Source: [Space Doctrine Publication 6-0, Mission Command, November 2024](https://www.starcom.spaceforce.mil/Portals/2/SDP%206-0%20Mission%20Command%20(Nov%202024).pdf)

**OKR-Agent (academic research):**

The OKR-Agent framework applies Objectives and Key Results to AI agent systems. It uses "hierarchical OKR generation" to decompose high-level objectives into sub-objectives, then assigns agents to key results. Each agent "elaborates on designated tasks and decomposes them as necessary, operating recursively and hierarchically."

Source: [Agents meet OKR, arXiv:2311.16542](https://arxiv.org/abs/2311.16542)

**Beyond Mission Command (U.S. Naval Institute, April 2025):**

A shift from "mission command" to "collaborative leadership" -- the human and the system develop shared understanding together, rather than the human transmitting intent downward. This requires bidirectional communication and mutual adjustment.

Source: [Beyond Mission Command, USNI Proceedings April 2025](https://www.usni.org/magazines/proceedings/2025/april/beyond-mission-command-collaborative-leadership)

### Extracted Principles for Athanor

1. **Set goals, not tasks.** Tell agents "keep the media library current and well-organized" rather than "check Sonarr every 15 minutes." The agent decides *how* to achieve the goal.
2. **Include the "why."** Commander's intent includes purpose and end state, not just the objective. "Keep the media library current *because new shows should be available within an hour of airing*" gives the agent context to make judgment calls.
3. **Define constraints, not procedures.** "Never spend more than $X," "Never delete media without asking," "Never change thermostat below 68F when Amanda is home." Boundary conditions are more robust than step-by-step procedures.
4. **Accept disconnected operation.** Like drones with severed communications, agents must be able to act on internalized goals when Shaun is unavailable. The goal specification must be complete enough to guide autonomous behavior.
5. **Collaborative goal refinement.** The best model is not "Shaun gives orders, agents execute" but "Shaun and agents develop shared understanding of what matters." Agents should be able to propose goal modifications based on what they learn.

---

## Domain 7: Attention Management

### How It Works

The research on alert fatigue and notification overload is extensive and quantitatively clear:

**Alert volume statistics:**
- Teams receive 2,000+ alerts weekly with only 3% requiring immediate action
- 67% of alerts are ignored daily
- 85% false positive rate across industries
- 74% of teams experience alert overload
- SOCs face an average of 960 security alerts daily; enterprises with 20,000+ employees see 3,000+
- 70% of SOC analysts with 5 or fewer years experience leave within 3 years (burnout)
- 79% of organizations experience peak alert fatigue during shift transitions when context is lost

Source: [incident.io - Alert Fatigue Solutions for DevOps 2025](https://incident.io/blog/alert-fatigue-solutions-for-dev-ops-teams-in-2025-what-works)

**Signal-to-noise targets:**
- Healthy systems: 30-50% of alerts are actionable
- Below 10% actionable: noise is destroying value
- Minimum 30 days of historical data needed for dynamic baseline training

Source: [incident.io](https://incident.io/blog/alert-fatigue-solutions-for-dev-ops-teams-in-2025-what-works)

**Escalation tiering (recommended):**

| Tier | Response Time | Notification Method |
|------|---------------|---------------------|
| Low | 4 hours | Passive channel (log, dashboard) |
| Medium | 1 hour | Team notification, escalate after 30 min |
| High | 15 minutes | Immediate direct notification |

Source: [incident.io](https://incident.io/blog/alert-fatigue-solutions-for-dev-ops-teams-in-2025-what-works)

**AI-driven mitigation strategies:**
- Alert correlation engines group related notifications, reducing volume
- Dynamic baselines replace static thresholds with learned normal patterns
- Contextual AI pre-investigation reduces investigation time by up to 40%
- Multi-agent systems like Audit-LLM show 40% reduction in false positives

Source: [IBM - Alert Fatigue Reduction with AI Agents](https://www.ibm.com/think/insights/alert-fatigue-reduction-with-ai-agents), [ScienceDirect - Mitigating Alert Fatigue in Cloud Monitoring](https://www.sciencedirect.com/science/article/pii/S138912862400375X)

### Extracted Principles for Athanor

1. **Target: 30-50% of notifications should require action.** If Shaun is ignoring more than half of agent notifications, the system is generating noise.
2. **Three tiers, max.** Critical (push notification, interrupts), Notable (dashboard badge, check when convenient), Background (logged, visible only on request). No more than 3 tiers.
3. **Correlation before notification.** If three agents each notice something related, send one notification, not three. The GWT workspace's competitive selection already does this -- lean into it.
4. **Dynamic baselines.** "Plex has 3 concurrent streams" is not notable if that is normal for Friday night. Learn what is normal and only alert on deviations.
5. **Budget notifications.** For a single operator with a day job, a reasonable daily notification budget is 5-10 "Notable" and 0-2 "Critical." Everything else is Background. This is a hard constraint, not a soft target.

---

## Domain 8: Trust Calibration

### How It Works

Trust calibration research aims to ensure that human trust in an autonomous system matches the system's actual reliability. Both over-trust and under-trust are failure modes:

**Over-trust (automation complacency):**
- "People tend to trust [automated recommendations] even when they have reasons not to" (automation bias)
- Leads to omission errors (not acting because the system did not alert) and commission errors (following incorrect system advice despite contradicting evidence)
- Complacency causes "less task vigilance, leading to missed errors, reduced situation awareness, slower reaction times, increased risk of accidents, and skill degradation"

Source: [(Over)Trusting AI Recommendations, Taylor & Francis](https://www.tandfonline.com/doi/full/10.1080/10447318.2023.2301250), [Wikipedia - Automation bias](https://en.wikipedia.org/wiki/Automation_bias)

**Under-trust (disuse):**
- "A lack of trust in a trustworthy system risks disuse, leading to reduced productivity and lost resources"
- Humans who micromanage a reliable system waste the benefits of automation
- Creates a cycle: micromanagement prevents the system from demonstrating competence, which prevents trust from building

Source: [PMC - Calibrating workers' trust in intelligent automated systems](https://pmc.ncbi.nlm.nih.gov/articles/PMC11573890/)

**The rubber stamp problem:**
- "Rubber-stamp risk occurs when human oversight becomes mere formality -- reviewers approve or sign off without meaningful engagement"
- Root causes: volume overwhelm, model opacity, cognitive fatigue, organizational pressure
- "Attention is a finite resource" -- people do not rubber-stamp because they are lazy but because the system exceeds their cognitive capacity
- Prevention requires structural safeguards: "True oversight requires friction -- the ability to pause, question, and challenge -- not just checkboxes"

Source: [CyberManiacs - Rubber Stamp Risk](https://cybermaniacs.com/cm-blog/rubber-stamp-risk-why-human-oversight-can-become-false-confidence)

**MIT Sloan on avoiding rubber stamps:**
- Do not show AI confidence scores during review (anchors human judgment)
- Use blind review processes where possible
- Rotate reviewers to prevent fatigue
- Conduct regular audits to check if reviewers are rubber-stamping

Source: [MIT Sloan Management Review - AI Explainability](https://sloanreview.mit.edu/article/ai-explainability-how-to-avoid-rubber-stamping-recommendations/)

**What builds trust (research synthesis):**
- Transparency about capabilities and limitations
- Consistent performance over time
- "Meaningful communication" -- systems that explain their reasoning are trusted more appropriately than systems that are merely anthropomorphized
- Track record visibility: showing the system's historical accuracy and reliability
- Human ability to understand *when* the system is likely to fail

Source: [PMC - Meaningful Communication and Trust Calibration](https://pmc.ncbi.nlm.nih.gov/articles/PMC11457490/), [Frontiers - Trust Process for Effective Human-AI Interaction](https://www.frontiersin.org/journals/computer-science/articles/10.3389/fcomp.2025.1662185/full)

**What breaks trust:**
- Single dramatic failure (disproportionate to frequency)
- Opaque decision-making
- System overriding human input without explanation
- Inconsistency between system claims and behavior

Source: [PMC - Trust Calibration Survey](https://pmc.ncbi.nlm.nih.gov/articles/PMC12058881/)

### Extracted Principles for Athanor

1. **Show the track record.** Each agent should display its accuracy/success rate over time. "Media agent: 47 actions this week, 45 successful, 2 corrected by Shaun." This calibrates trust to actual performance.
2. **Explain on demand, not by default.** Constant explanations become noise. But every agent action should have a retrievable explanation: "I did X because Y."
3. **Meaningful friction for high-stakes actions.** Don't ask Shaun to approve every action (rubber stamp). Do require a deliberate, non-trivial interaction for actions that are hard to reverse. The friction itself signals importance.
4. **Never hide failures.** When an agent makes a mistake, surface it prominently. Trust is built by honest error reporting, not by burying mistakes.
5. **Monitor for rubber-stamping.** If Shaun approves 100% of requests from an agent, either the autonomy level should be raised (the approvals are meaningless) or the system should inject a deliberate test case to verify Shaun is still paying attention.

---

## Domain 9: Feedback Loop Design

### How It Works

**Supervisory control vs teaming (PMC, 2025):**

Research distinguishes two models:
- **Supervisory Human Control (SHC):** Humans plan, teach, monitor, intervene, and learn. Focuses on "negative control" -- correcting the system when something goes wrong.
- **Human-Machine Teaming (HMT):** Collaborative model with dynamic task allocation. Requires shared mental models, bidirectional communication, commitment mechanisms, and convention building.

The HMT approach requires four elements for effective collaboration:
1. **Shared mental models:** Common understanding of tasks, roles, capabilities, and limitations
2. **Communication channels:** Bidirectional -- agents convey confidence, intent, discovered information, and emerging limitations
3. **Commitment mechanisms:** Locking in planned actions increases predictability and helps identify deviations
4. **Convention building:** Shared beliefs developed through experience that reduce communication delays

Source: [PMC - Human control of AI systems: from supervision to teaming](https://pmc.ncbi.nlm.nih.gov/articles/PMC12058881/)

**Feedback visibility (recommendation systems):**

The most effective feedback loops show the impact of user feedback:
- Spotify: "Explanations containing meaningful details about the artist or music led to significantly higher user engagement. Users were up to four times more likely to click on recommendations accompanied by explanations."
- Netflix: "When Netflix conducted global tests of 'two thumbs up,' members reported that recommendations were getting better overall." The visible improvement loop (feedback -> better recommendations) drives continued engagement.
- "Non-intrusive visual confirmations -- small icons indicating feedback registration -- help users understand algorithmic learning."

Source: [Spotify Personalization Design](https://newsroom.spotify.com/2023-10-18/how-spotify-uses-design-to-make-personalization-features-delightful/), [Beyond Explicit and Implicit, arXiv:2502.09869v1](https://arxiv.org/html/2502.09869v1)

**Feedback latency:**
- Immediate feedback (within seconds) creates the strongest reinforcement signal
- Batched feedback (daily digests) is appropriate for low-urgency pattern adjustments
- Long-latency feedback (outcome tracking over weeks) is critical for goal-level evaluation

**RLVR (Reinforcement Learning from Verifiable Rewards, 2025):**

A paradigm shift in 2025: instead of relying on human preferences, train against automatically verifiable rewards (math/code puzzles). This is relevant because it suggests Athanor's agents should have *verifiable* metrics wherever possible -- reducing dependence on human feedback for routine quality assessment.

Source: [Karpathy - 2025 LLM Year in Review](https://karpathy.bearblog.dev/year-in-review-2025/)

### Extracted Principles for Athanor

1. **Show the impact.** "Your feedback changed the media agent's behavior: it now prioritizes 4K content." Visible impact drives continued engagement with the feedback mechanism.
2. **Bidirectional communication.** Agents should tell Shaun what they are confident about, what they are uncertain about, and what they have learned. This is not just reporting -- it is building shared understanding.
3. **Verifiable metrics over subjective ratings.** Where possible, measure agent quality through objective metrics (task completion rate, user correction rate, response latency) rather than asking Shaun to rate quality.
4. **Three feedback cadences.** Immediate (real-time corrections), daily (digest of what happened and what changed), weekly (goal-level review of agent performance and direction).
5. **Convention building takes time.** The system and Shaun will develop implicit agreements over weeks of interaction. Design for this: track patterns in Shaun's behavior and let the system adapt, but show *what* it adapted and *why*.

---

## Domain 10: Novel Patterns (2025-2026)

### Emerging Approaches

**Ambient agents:**
"Self-learning, context-aware AI systems that run persistently to anticipate needs and act with minimal explicit command. Rather than text or voice alone, ambient agents use vision, audio, location, biometrics, device telemetry, and other sources to infer what is happening."

According to IDC, 60% of households in developed nations will feature some form of ambient tech by 2026. The shift is from reactive (user commands system) to anticipatory (system predicts what user needs before they ask).

Source: [DigitalOcean - Ambient Agents](https://www.digitalocean.com/community/tutorials/ambient-agents-context-aware-ai), [Promwad - Ambient Computing](https://promwad.com/news/ambient-computing-smart-environments)

**Anticipatory design:**
"Devices are starting to act before the user makes a request, offering reminders, summarizing meetings, or nudging the next best action. Users now demand anticipatory experiences that are able to know what users want before they take conscious action."

Source: [BlogBursts - Age of Anticipatory Design](https://www.blogbursts.in/the-age-of-anticipatory-design-why-emotional-intelligence-is-the-next-frontier-in-ui-ux/), [Bonanza Studios - Predictive UI](https://www.bonanza-studios.com/blog/future-trends-predictive-ui-and-context-aware-ai-interactions)

**Multi-agent system oversight:**
Gartner reported a 1,445% surge in multi-agent system inquiries from Q1 2024 to Q2 2025. Research shows "users are engaging in selective, layered supervision of individual agents or agent clusters, which enables task-specific debugging and oversight." The emerging pattern is not monitoring each agent individually but monitoring the *relationships* between agents.

Source: [Frontiers - Human-AI Interaction in Agentic AI](https://www.frontiersin.org/journals/human-dynamics/articles/10.3389/fhumd.2025.1579166/full), [arxiv - Exploring Human-AI Collaboration with Multi-Agent Tools](https://arxiv.org/html/2510.06224v1)

**Conversational steering:**
Instead of clicking buttons or adjusting sliders, users steer autonomous systems through conversation: "Focus more on quality than speed this week." Spotify's "Prompted Playlist" (December 2025) is an early consumer example -- natural language control of an algorithm.

Source: [Spotify Prompted Playlists](https://newsroom.spotify.com/2025-12-10/spotify-prompted-playlists-algorithm-gustav-soderstrom/)

**Blended teams:**
"In 2026, there will be more AI agent and human agent collaboration, with blended teams -- where humans and AI agents collaborate -- becoming the norm." The shift is from human-as-supervisor to human-as-team-member.

Source: [NoJitter - 2026 Human and AI Agent Collaboration](https://www.nojitter.com/contact-centers/2026-may-be-year-of-human-and-ai-agent-collaboration)

**OpenAI's AI device vision (2026):**
OpenAI announced plans for a physical AI device in 2026 that would reimagine UX beyond screens -- "the future of UX trends" moving toward ambient, always-available AI interaction without the overhead of opening an app or typing a command.

Source: [Fruto Design - OpenAI AI Device UX Trends 2026](https://fruto.design/blog/openai-ai-device-ux-trends-2026)

### Extracted Principles for Athanor

1. **Ambient awareness is the target state.** The dashboard is for active investigation. Normal operation should be ambient: Shaun knows what agents are doing without looking at anything, through peripheral signals (subtle audio cues, ambient display, summary notifications).
2. **Conversational steering over button-clicking.** Shaun should be able to tell the system "focus on media organization this week" in natural language, and agents adjust their priorities accordingly. This is the commander's intent model applied to a homelab.
3. **Monitor relationships, not just agents.** The interesting failures in multi-agent systems are coordination failures, not individual agent failures. Surface when agents contradict each other, duplicate work, or fail to share relevant information.
4. **Anticipatory, not reactive.** The system should learn Shaun's patterns: he checks media on Friday nights, reviews agent activity on weekend mornings, works on EoBQ Sunday afternoons. Prepare relevant information before he asks for it.
5. **The UI should mostly be invisible.** The best human-in-the-loop interface for a one-person system is one that the person barely needs to interact with. The system should handle 95% of decisions autonomously, surface 4% as ambient awareness, and ask about 1%.

---

## Synthesis: Design Principles for Athanor

The ten domains converge on a coherent framework for human-in-the-loop design in a one-person autonomous agent system. What follows is a unified set of principles, organized by theme.

### Theme 1: The Attention Budget

A single operator with a day job has approximately 1-2 hours of active attention per weekday evening and 4-8 hours on weekends. Every interaction the system demands is a withdrawal from this budget.

**Design rules:**
- **Hard notification budget:** Max 5-10 "Notable" and 0-2 "Critical" notifications per day. Everything else is Background (logged, never pushed).
- **Target 30-50% actionable rate.** If more than half of surfaced items need no action, the system is wasting attention.
- **Correlation before notification.** One notification for a situation, not one per agent that noticed it. The GWT workspace handles this naturally.
- **Model notification fatigue.** If Shaun ignores a category 3 times in a row, suppress it until the next weekly review.
- **Respect context.** Don't push notifications during focused work sessions or at 2 AM. Time-aware notification delivery.

### Theme 2: The Autonomy Spectrum

Autonomy is not binary. Different agents, different functions within agents, and different contexts warrant different levels of human involvement.

**Design rules:**
- **Per-agent autonomy levels** using a simplified Sheridan-Verplanck scale:
  - **Level A (Full Auto):** Agent acts and logs. Human sees results on request. *(Embedding, knowledge indexing, routine monitoring)*
  - **Level B (Inform):** Agent acts and notifies. Human sees a summary. *(Media management, HA automation, scheduled tasks)*
  - **Level C (Propose):** Agent recommends an action and waits for approval. *(Spending money, deleting data, changing system config)*
  - **Level D (Manual):** Agent gathers information and presents options. Human decides and initiates. *(New service deployment, hardware changes)*
- **Separate observation autonomy from action autonomy.** Any agent can observe and analyze at Level A. Actions have their own autonomy level.
- **Context-sensitive adjustment.** When Shaun is active on the dashboard, lower the threshold for surfacing information. When he is away, raise it.
- **Escalation protocol already exists.** The current 3-tier escalation (act/notify/ask) maps well to Levels A/B/C. Formalize the mapping.

### Theme 3: Goals Over Tasks

The commander's intent model is directly applicable. Shaun should specify goals and constraints; agents decide how to achieve them.

**Design rules:**
- **Goal specification format:** Each agent has a stated purpose (already in `agent-contracts.md`), measurable key results, and explicit constraints (what they must never do).
- **Intent, not instructions.** "Keep the home comfortable and energy-efficient" rather than "check the thermostat every 5 minutes." The agent determines the method.
- **Include the "why."** Goals should include context: "Keep the home comfortable *because Amanda is sensitive to temperature changes*" gives the agent judgment criteria.
- **Constraints are guardrails.** Define boundaries (max spend, never-delete, always-ask-before-X) rather than step-by-step procedures.
- **Accept disconnected operation.** Goals must be specified completely enough that agents can act for days without human input and still serve Shaun's interests.
- **Collaborative goal refinement.** Agents should be able to propose goal changes: "I notice you always override my 68F thermostat setting to 70F. Should I update the target?"

### Theme 4: The Feedback Loop

Feedback must be sustainable (low-effort), visible (Shaun sees the impact), and multi-cadence (immediate + daily + weekly).

**Design rules:**
- **Implicit feedback is primary.** Track what Shaun acts on, ignores, undoes, and overrides. These behavioral signals require zero effort and are the most sustainable long-term.
- **Explicit feedback is binary.** Thumbs up/down. "Don't do this again." "Do more of this." Netflix proved binary is better than granular.
- **Three cadences:**
  - *Immediate:* Corrections applied now, agent adjusts behavior for this session
  - *Daily digest:* Summary of what happened, what was notable, what the system learned
  - *Weekly review:* Goal-level assessment, autonomy level adjustments, trend analysis
- **Show the impact.** "Based on your corrections this week, the media agent now prioritizes 4K sources. Here's what changed." Visible impact drives continued engagement.
- **Verifiable metrics where possible.** Task completion rate, correction rate, latency, uptime. Objective measures reduce the need for subjective feedback.
- **Zero-effort defaults.** The absence of correction is a positive signal. If Shaun does not undo an action, the system treats it as endorsed.

### Theme 5: Trust Calibration

Trust must match actual capability. Over-trust (rubber-stamping) is as dangerous as under-trust (micromanaging).

**Design rules:**
- **Track record display.** Each agent shows: total actions, success rate, correction rate, trend over time. This is the single most important trust signal.
- **Explain on demand.** Every action has a retrievable justification, but justifications are not shown by default (noise reduction).
- **Meaningful friction for irreversible actions.** The escalation protocol (Level C) should require a non-trivial interaction -- not just "OK" but something that forces Shaun to engage with the decision (show what will happen, what the alternatives are, what the risk is).
- **Detect rubber-stamping.** If approval rate is 100% for an extended period, either raise the autonomy level (remove the approval requirement) or inject a test case.
- **Never hide failures.** Agent mistakes surface prominently with full context: what happened, what went wrong, what the agent learned from it.
- **Progressive trust building.** New agents start at Level C (propose and wait). As they demonstrate reliability, they graduate to Level B (act and inform), then Level A (act and log).

### Theme 6: The Phone-a-Friend Model

The system asks for help when it needs it. The human does not watch everything.

**Design rules:**
- **Exception-based, not continuous.** The dashboard exists for when Shaun wants to look. The system does not require him to look.
- **Rich context at intervention time.** When the system asks for help, it provides the full situation: what happened, what it considered, what it is uncertain about, what the options are.
- **The system retains authority.** Like Waymo's ADS, the agent evaluates human input but is not obligated to follow it blindly. If human input conflicts with safety constraints, the agent should refuse and explain why.
- **Reduce intervention rate over time.** Track how often agents ask for help. This should trend downward as the system learns from Shaun's feedback.
- **One question at a time.** When agents need input, they ask one clear question with a recommended answer. Not "what should I do?" but "I recommend X because Y. Approve or suggest alternative?"

### Theme 7: Ambient Awareness

The ideal state is awareness without active monitoring.

**Design rules:**
- **Dashboard is for investigation, not monitoring.** The home screen shows system health at a glance. Drill-down for details. Not a wall of real-time metrics.
- **Digest over stream.** A morning summary ("overnight: 3 shows downloaded, thermostat adjusted twice, 1 agent correction logged") is more useful than a real-time feed.
- **Anticipatory preparation.** Before Shaun's typical Friday-night media session, prepare: what is new, what has high ratings, what matches his history. Present it without being asked.
- **Learn patterns.** If Shaun checks agent activity every morning at 7 AM, have the daily digest ready at 6:55 AM.
- **Ambient signals.** Consider low-interruption channels: dashboard status colors, a summary available via voice assistant ("Athanor, what happened overnight?"), or a brief notification that serves as an entry point to details.

---

## Implementation Recommendations for Athanor

Based on this research, the following concrete changes are recommended:

### Immediate (fits into existing architecture)

1. **Formalize autonomy levels in `agent-contracts.md`.** Map each agent and each action type to Level A/B/C/D. The existing escalation protocol (act/notify/ask) is already close -- formalize the mapping.

2. **Add a daily digest.** A scheduled task (general-assistant, 6:55 AM) that compiles overnight agent activity into a summary, available via dashboard and voice.

3. **Track implicit feedback.** Log when Shaun: acts on agent output, ignores notifications, undoes agent actions, overrides agent recommendations. Store in the `preferences` or `activity` Qdrant collection.

4. **Notification budgeting.** Add a daily notification counter to the agent framework. When the budget is exhausted, additional notifications go to Background tier only. Start with 10 Notable + 2 Critical per day.

5. **Track record display on dashboard.** Per-agent card showing: total actions (7d), success rate, correction rate, trend arrow.

### Near-term (requires moderate development)

6. **Goal specification system.** Replace per-agent cron schedules with goal statements + constraints. Agents determine their own observation schedules based on goals. Store goals in Redis or Qdrant for persistence.

7. **Conversational steering endpoint.** `POST /v1/goals/steer` accepts natural language: "Focus on media quality this week." The general-assistant interprets and adjusts agent priorities.

8. **Rubber-stamp detection.** Track approval patterns. If an agent's approval rate exceeds 95% over 20+ requests, suggest raising its autonomy level.

9. **Intervention rate tracking.** Prometheus metric per agent: `athanor_agent_interventions_total`. Grafana panel showing trend over time. Goal: downward trend.

10. **Impact visibility.** After Shaun gives explicit feedback, show a follow-up: "This feedback affected 3 subsequent decisions by the media agent."

### Future (aligns with GWT Phase 3-4)

11. **Anticipatory scheduling.** Learn Shaun's temporal patterns and pre-compute relevant information. "Friday 6 PM: prepare media summary. Sunday 2 PM: prepare EoBQ development context."

12. **Dynamic autonomy adjustment.** Raise autonomy levels when Shaun is away (detected via HA presence, dashboard inactivity). Lower when he is actively interacting.

13. **Fatigue-aware notification model.** Track which notification categories Shaun ignores and reduce their salience over time. Reset on weekly review.

14. **Convention library.** Store learned human-agent conventions: "Shaun always approves 4K downloads," "Shaun never wants thermostat below 70F despite the 68F setting." Surface these for explicit confirmation periodically.

15. **Agent confidence communication.** Agents express uncertainty: "I'm 80% confident this is the right action. Here's what makes me uncertain." This supports trust calibration without requiring explanations for every action.

---

## Open Questions

1. **Notification channel.** What is the best channel for Notable notifications? Dashboard badge? Push notification to phone? Voice announcement? This depends on Shaun's preferences and needs user testing.

2. **Approval interface.** For Level C (propose) actions, where does Shaun approve? Dashboard? Phone? Chat? The interface must be accessible from wherever he is.

3. **Implicit feedback reliability.** How to distinguish "Shaun ignored this because it's fine" from "Shaun ignored this because he didn't see it"? Time-based heuristics (if not acted on within X hours, treat as implicit approval) need tuning.

4. **Goal specification language.** How structured should goals be? Natural language is flexible but ambiguous. OKR format is precise but rigid. Need to find the balance for a one-person system.

5. **Trust cold start.** New agents have no track record. Starting at Level C is conservative but may be too restrictive. Consider a "supervised ramp-up" period with higher notification frequency.

---

## References

### Self-Driving Vehicles
- [Waymo Fleet Response blog post, May 2024](https://waymo.com/blog/2024/05/fleet-response)
- [Waymo Independent Audits, November 2025](https://waymo.com/blog/2025/11/independent-audits)
- [InsideEVs - Tesla Robotaxi vs Waymo vs Cruise](https://insideevs.com/news/736709/tesla-robotaxi-waymo-cruise/)
- [Futurism - How Many Remote Operators Waymo Has](https://futurism.com/advanced-transport/waymo-remote-operators)
- [The Last Driver License Holder - Waymo Remote Control](https://thelastdriverlicenseholder.com/2026/02/09/are-waymos-remote-controlled-or-not-the-answer-is-no/)

### Algorithmic Trading
- [FIA Best Practices for Automated Trading Risk Controls, 2024](https://www.fia.org/sites/default/files/2024-07/FIA_WP_AUTOMATED%20TRADING%20RISK%20CONTROLS_FINAL_0.pdf)
- [LuxAlgo - Risk Management Strategies for Algo Trading](https://www.luxalgo.com/blog/risk-management-strategies-for-algo-trading/)
- [Tradetron - Enhancing Risk Management in Algo Trading](https://tradetron.tech/blog/enhancing-risk-management-in-algo-trading-techniques-and-best-practices-with-tradetron)
- [PMC - Systemic failures in algorithmic trading](https://pmc.ncbi.nlm.nih.gov/articles/PMC8978471/)
- [NYIF - Trading System Kill Switch](https://www.nyif.com/articles/trading-system-kill-switch-panacea-or-pandoras-box)
- [FINRA - Algorithmic Trading](https://www.finra.org/rules-guidance/key-topics/algorithmic-trading)

### RLHF Interfaces
- [Uni-RLHF, arXiv:2402.02423](https://arxiv.org/abs/2402.02423)
- [RLHF Survey, arXiv:2312.14925](https://arxiv.org/abs/2312.14925)
- [RLHF Comprehensive Survey, arXiv:2504.12501v3](https://arxiv.org/html/2504.12501v3)
- [Labellerr - RLHF Tools 2025](https://www.labellerr.com/blog/top-tools-for-rlhf/)
- [Nathan Lambert - RLHF Learning Resources](https://www.interconnects.ai/p/rlhf-resources)
- [CMU - RLHF 101 Tutorial](https://blog.ml.cmu.edu/2025/06/01/rlhf-101-a-technical-tutorial-on-reinforcement-learning-from-human-feedback/)
- [Karpathy - 2025 LLM Year in Review](https://karpathy.bearblog.dev/year-in-review-2025/)
- [RLHF Book by Nathan Lambert](https://rlhfbook.com/)

### Drone/Robot Teleoperation
- [Sheridan & Verplank, 1978 - 10 Levels of Automation (via ResearchGate)](https://www.researchgate.net/figure/Levels-of-Automation-From-Sheridan-Verplank-1978_tbl1_235181550)
- [Parasuraman, Sheridan, Wickens (2000) - Model for types and levels of human interaction with automation](https://www.researchgate.net/publication/11596569_A_model_for_types_and_levels_of_human_interaction_with_automation_IEEE_Trans_Syst_Man_Cybern_Part_A_Syst_Hum_303_286-297)
- [SUIND - 5 Levels of Drone Autonomy](https://suind.com/2024/11/06/navigating-the-5-levels-of-drone-autonomy-a-look-at-suinds-approach-to-autonomous-systems/)
- [PMC - Adaptive Automation via EEG-Based Mental Workload](https://pmc.ncbi.nlm.nih.gov/articles/PMC5080530/)
- [HFES Europe - New Level of Automation Taxonomy](https://www.hfes-europe.org/wp-content/uploads/2014/06/Save.pdf)

### Recommendation Systems
- [Spotify Recommendation System Guide 2025](https://www.music-tomorrow.com/blog/how-spotify-recommendation-system-works-complete-guide)
- [Spotify Prompted Playlists, December 2025](https://newsroom.spotify.com/2025-12-10/spotify-prompted-playlists-algorithm-gustav-soderstrom/)
- [Spotify Personalization Design](https://newsroom.spotify.com/2023-10-18/how-spotify-uses-design-to-make-personalization-features-delightful/)
- [Spotify Exclude From Taste Profile](https://newsroom.spotify.com/2023-02-08/exclude-from-your-taste-profile-will-make-your-personalized-recommendations-even-better/)
- [Netflix Recommendation Algorithm Analysis](https://marketingino.com/the-netflix-recommendation-algorithm-how-personalization-drives-80-of-viewer-engagement/)
- [Netflix Two Thumbs Up, Variety](https://variety.com/2022/digital/news/netflix-two-thumbs-up-ratings-1235228641/)
- [Beyond Explicit and Implicit Feedback, arXiv:2502.09869v1](https://arxiv.org/html/2502.09869v1)
- [Modeling User Fatigue for Sequential Recommendation, SIGIR 2024](https://dl.acm.org/doi/10.1145/3626772.3657802)

### Goal-Setting and Commander's Intent
- [Wikipedia - Intent (military)](https://en.wikipedia.org/wiki/Intent_(military))
- [MWI - Commander's Intent for Machines](https://mwi.westpoint.edu/commanders-intent-for-machines-reimagining-unmanned-systems-control-in-communications-degraded-environments/)
- [U.S. Space Force - SDP 6-0 Mission Command, November 2024](https://www.starcom.spaceforce.mil/Portals/2/SDP%206-0%20Mission%20Command%20(Nov%202024).pdf)
- [USNI Proceedings - Beyond Mission Command, April 2025](https://www.usni.org/magazines/proceedings/2025/april/beyond-mission-command-collaborative-leadership)
- [War on the Rocks - U.S. Army, AI, and Mission Command](https://warontherocks.com/2025/03/the-u-s-army-artificial-intelligence-and-mission-command/)
- [AgilityPortal - Commander's Intent for Business](https://agilityportal.io/blog/commanders-intent)
- [OKR-Agent, arXiv:2311.16542](https://arxiv.org/abs/2311.16542)

### Attention Management
- [incident.io - Alert Fatigue Solutions for DevOps 2025](https://incident.io/blog/alert-fatigue-solutions-for-dev-ops-teams-in-2025-what-works)
- [ACM - Alert Fatigue in Security Operations Centres](https://dl.acm.org/doi/10.1145/3723158)
- [IBM - Alert Fatigue Reduction with AI Agents](https://www.ibm.com/think/insights/alert-fatigue-reduction-with-ai-agents)
- [ScienceDirect - Mitigating Alert Fatigue in Cloud Monitoring](https://www.sciencedirect.com/science/article/pii/S138912862400375X)
- [Netdata - What is Alert Fatigue](https://www.netdata.cloud/academy/what-is-alert-fatigue-and-how-to-prevent-it/)
- [Fortune - Customer Survey Overload, December 2025](https://fortune.com/2025/12/28/customer-survey-fatigue-feedback-consumer-experience/)

### Trust Calibration
- [CHI 2023 - Measuring and Understanding Trust Calibrations](https://dl.acm.org/doi/full/10.1145/3544548.3581197)
- [PMC - Calibrating workers' trust in intelligent automated systems](https://pmc.ncbi.nlm.nih.gov/articles/PMC11573890/)
- [PMC - Adaptive trust calibration for human-AI collaboration](https://pmc.ncbi.nlm.nih.gov/articles/PMC7034851/)
- [PMC - Human control of AI systems: from supervision to teaming](https://pmc.ncbi.nlm.nih.gov/articles/PMC12058881/)
- [PMC - Meaningful Communication and Trust Calibration (HATEM)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11457490/)
- [Taylor & Francis - (Over)Trusting AI Recommendations](https://www.tandfonline.com/doi/full/10.1080/10447318.2023.2301250)
- [Frontiers - Trust Process for Human-AI Interaction](https://www.frontiersin.org/journals/computer-science/articles/10.3389/fcomp.2025.1662185/full)
- [CyberManiacs - Rubber Stamp Risk](https://cybermaniacs.com/cm-blog/rubber-stamp-risk-why-human-oversight-can-become-false-confidence)
- [MIT Sloan - AI Explainability and Rubber Stamping](https://sloanreview.mit.edu/article/ai-explainability-how-to-avoid-rubber-stamping-recommendations/)
- [Wikipedia - Automation bias](https://en.wikipedia.org/wiki/Automation_bias)

### Feedback Loop Design
- [PMC - Human control of AI systems: from supervision to teaming](https://pmc.ncbi.nlm.nih.gov/articles/PMC12058881/)
- [NASA NTRS - Challenges for Human-Machine Teaming in Aviation](https://ntrs.nasa.gov/citations/20250002888)
- [NASA - Autonomous Context-Sensitive Task Management](https://ntrs.nasa.gov/api/citations/20180003355/downloads/20180003355.pdf)
- [Advancing Human-Machine Teaming, arXiv:2503.16518v1](https://arxiv.org/html/2503.16518v1)

### Novel Patterns (2025-2026)
- [DigitalOcean - Ambient Agents](https://www.digitalocean.com/community/tutorials/ambient-agents-context-aware-ai)
- [Promwad - Ambient Computing](https://promwad.com/news/ambient-computing-smart-environments)
- [Medium - Ambient Agents and Always-On Intelligence](https://medium.com/@fahey_james/ambient-agents-and-the-future-of-always-on-intelligence-85c21137d070)
- [Fruto Design - OpenAI AI Device UX Trends 2026](https://fruto.design/blog/openai-ai-device-ux-trends-2026)
- [Spotify Prompted Playlists, December 2025](https://newsroom.spotify.com/2025-12-10/spotify-prompted-playlists-algorithm-gustav-soderstrom/)
- [Frontiers - Human-AI Interaction in Agentic AI](https://www.frontiersin.org/journals/human-dynamics/articles/10.3389/fhumd.2025.1579166/full)
- [arxiv - Exploring Human-AI Collaboration with Multi-Agent Tools](https://arxiv.org/html/2510.06224v1)
- [NoJitter - 2026 Human and AI Agent Collaboration](https://www.nojitter.com/contact-centers/2026-may-be-year-of-human-and-ai-agent-collaboration)
- [Gartner surge in multi-agent inquiries via Salesmate](https://www.salesmate.io/blog/future-of-ai-agents/)
- [BlogBursts - Age of Anticipatory Design](https://www.blogbursts.in/the-age-of-anticipatory-design-why-emotional-intelligence-is-the-next-frontier-in-ui-ux/)
- [Bonanza Studios - Predictive UI](https://www.bonanza-studios.com/blog/future-trends-predictive-ui-and-context-aware-ai-interactions)
- [Medium - Proactive Anticipatory UX Prototyping](https://medium.com/@harsh.mudgal_27075/proactive-anticipatory-ux-prototyping-anticipating-needs-before-they-surface-a1dd14b65424)
