"""Rebuild four fictional three-page proposals and explicit human-authored fixtures."""
import hashlib
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
PROFILES = [
    dict(name="Apex Systems", date="2026-10-20", experience=8, scores=[9,7,6,9,8],
         tagline="Enterprise architecture. Strong controls. Premium investment.",
         technical="The solution uses a modular API gateway, event-driven services and an offline retry queue for CRM and ERP integrations.",
         technical_detail="Two connector prototypes will be demonstrated before build approval. PostgreSQL provides tenant isolation; Redis caches read-heavy views. Load tests target 1,000 concurrent agents and a 95th-percentile response below 500 ms. The design includes versioned REST APIs and a reconciliation dashboard for failed transactions.",
         implementation="Delivery takes 16 weeks: discovery in weeks 1-3, build in weeks 4-10, migration in weeks 11-13 and acceptance in weeks 14-16.",
         plan_detail="A delivery manager, two integration engineers, three application developers and a QA lead form the core team. The buyer supplies a product owner and test users. Acceptance requires 98% migration accuracy and closure of critical defects. A two-week contingency sits within the final phase; dedicated training capacity is not priced separately.",
         price="Three-year total cost is USD 420,000, excluding taxes and buyer-side network upgrades.",
         prices=[["Implementation", "$180,000", "One time"],["Subscription", "$65,000", "Each year x 3"],["Migration", "$25,000", "One time"],["Training", "$20,000", "One time"],["3-year total", "$420,000", "Excludes taxes"]],
         assumptions="Includes 250 named agents, two integrations and migration of two million records. Additional integrations cost USD 18,000 each. Subscription includes platform hosting and support. Renewal increases after year three are capped at 6% annually. Travel and buyer hardware are excluded.",
         security="Controls include SAML SSO, role-based access, AES-256 storage encryption, TLS 1.3 transport and 365-day audit logs.",
         security_detail="A fictional independent control assessment AS-26-14 lists quarterly access reviews and annual penetration testing. This is a training claim, not a real certification. Recovery objectives are RPO 1 hour and RTO 4 hours, tested every six months. Data stays in the agreed region; a signed DPA and deletion certificate are proposed before production.",
         support="Support is available 24/7 for critical incidents, with a 30-minute response target and a named service manager.",
         support_detail="Nine comparable fictional projects were delivered in five years. Fictional references: Maple Freight (320 agents) and Cedar Utilities (210 agents). Reference contact details are intentionally omitted. The support SLA promises a response, not a guaranteed fix time. Monthly service reviews and quarterly resilience tests are included.",
         risks=["Highest three-year price in this cohort.","Training capacity and resolution SLA need clarification."],
         summary="Strong technical and security evidence, with a premium total cost and a moderate delivery schedule.",
         reasons=["Specific integrations, performance targets and reconciliation design.","Defined stages and acceptance checks, but training detail is limited.","Transparent total cost and exclusions, but premium pricing.","Concrete identity, encryption, retention and recovery controls; external assurance remains a claim.","Round-the-clock critical support and comparable projects; resolution commitment is absent."]),
    dict(name="BrightPath Tech", date="2026-10-18", experience=3, scores=[6,6,9,3,4],
         tagline="Lean scope. Fast launch. Lowest initial commitment.",
         technical="A hosted web application will provide ticket queues, email ingestion and a standard CRM connector; ERP integration uses a nightly CSV export.",
         technical_detail="The platform targets 150 concurrent users at launch. The proposal does not include a load-test report or offline processing design. A single application instance serves the pilot. The buyer must supply a clean ERP export format, and changes to its format are billable. A public API is planned but not committed in the first release.",
         implementation="The proposed eight-week schedule allocates one week to discovery, four to configuration, two to testing and one to launch.",
         plan_detail="The team consists of one project lead, two full-stack developers and a part-time tester. Buyer feedback is required within one business day. There is no explicit migration reconciliation threshold or contingency allocation. User training consists of two remote sessions. A slip in buyer decisions moves the go-live date.",
         price="Three-year total cost is USD 156,000, including a fixed implementation fee and three annual subscriptions.",
         prices=[["Implementation", "$45,000", "One time"],["Subscription", "$35,000", "Each year x 3"],["Migration", "$6,000", "One time"],["Training", "$0", "Two sessions included"],["3-year total", "$156,000", "Excludes taxes"]],
         assumptions="Includes 150 named users and one standard connector. Each additional user costs USD 12 per month. Historical data cleansing is the buyer's responsibility. ERP CSV scripting is included; a real-time ERP connector is excluded. Travel, taxes and bespoke reporting are excluded. Subscription prices are fixed for the initial three-year term.",
         security="The application uses HTTPS and daily backups; access is controlled by passwords and administrator-managed user roles.",
         security_detail="No formal certification, penetration-test report, SSO commitment or audit retention period is supplied. Backup storage location and restoration time remain to be agreed. BrightPath states that a data processing agreement can be negotiated after selection. The proposal does not specify breach notification time or regional hosting boundaries.",
         support="Support is provided on business days from 09:00 to 17:00, with a one-business-day response target.",
         support_detail="Two fictional small-business deployments are described, each with fewer than 50 users. The only fictional reference, Pine Retail, has not agreed to a reference call. Out-of-hours coverage is a separately priced option and no rate is provided. Product documentation and recorded training are included.",
         risks=["Security and compliance evidence is limited.","Aggressive timeline has no explicit contingency.","Limited experience at the requested scale."],
         summary="Lowest price and a short schedule, offset by limited compliance detail, integration depth and support coverage.",
         reasons=["Core functions are covered but ERP integration is batch-only and scale evidence is limited.","A clear short schedule exists, but contingency and acceptance thresholds are missing.","Lowest transparent three-year price; exclusions should still be priced before award.","Only basic transport, backup and role controls are specified.","Business-hours response and small reference projects provide limited enterprise assurance."]),
    dict(name="NexaWorks", date="2026-10-19", experience=8, scores=[8,9,8,8,9],
         tagline="Balanced value. Measurable delivery. Accountable support.",
         technical="The platform integrates CRM and ERP through versioned REST adapters with idempotent retries and a monitored dead-letter queue.",
         technical_detail="A containerized service tier supports 500 concurrent agents; staging load tests are included at 1.5 times that volume. An adapter catalogue records field mappings and transformation owners. Data is partitioned by business unit, with an operational dashboard for failed messages. Offline mobile use is outside the base scope.",
         implementation="The 12-week plan includes signed stage gates at weeks 2, 6, 9 and 12, with named owners, rollback rehearsal and a two-week contingency.",
         plan_detail="A RACI assigns the delivery lead, architect, two integration engineers, two developers, QA engineer and buyer product owner. Gates cover design approval, tested integrations, migration reconciliation and business acceptance. Acceptance requires 99.5% reconciliation, zero open critical defects and 95% user-test completion. Two migration rehearsals, role-specific training and a four-week hypercare period are included.",
         price="Three-year total cost is USD 288,000, including integration, training, hosting and four weeks of hypercare.",
         prices=[["Implementation", "$108,000", "One time"],["Subscription", "$52,000", "Each year x 3"],["Migration", "$16,000", "One time"],["Training", "$8,000", "One time"],["3-year total", "$288,000", "Excludes taxes"]],
         assumptions="Includes 250 agents, CRM and ERP adapters, and two million migrated records. Annual subscription covers hosting and support. Prices are fixed for three years; future increases are capped at 5%. Bespoke mobile development and source-system remediation are excluded. Change requests require an agreed estimate and written buyer approval.",
         security="Security includes SAML SSO, MFA for administrators, encryption at rest and in transit, and immutable audit logs retained for 180 days.",
         security_detail="The fictional assurance pack NW-2026 lists a penetration-test remediation summary; a full report is available under NDA in this training scenario. A regional hosting commitment, DPA, 24-hour breach notice and 30-day deletion process are proposed. Quarterly restoration exercises target RPO 4 hours and RTO 8 hours. No formal ISO certificate is supplied.",
         support="A dedicated service manager provides 24/7 critical support, a 15-minute response target and a four-hour workaround target.",
         support_detail="Seven comparable fictional projects include Oak Logistics (280 agents) and Meadow Services (240 agents), with reference calls offered during due diligence. Monthly reviews report uptime, backlog and incident trends. Named backup staff cover holidays, and a knowledge-transfer package is handed over before hypercare ends. Service credits apply to missed response targets.",
         risks=["Full independent assurance documents require due diligence.","Offline mobile functionality is excluded."],
         summary="Balanced technical and commercial value, with the strongest staged delivery controls and a specific support model.",
         reasons=["Explicit adapter reliability and load targets; offline use is excluded.","Named gates, measurable acceptance and contingency make delivery unusually clear.","Transparent inclusive total cost with controlled changes and renewal caps.","Detailed controls and incident terms; certification evidence is not supplied.","Specific response and workaround targets, service management and relevant references."]),
    dict(name="Orbit Digital", date="2026-10-17", experience=9, scores=[5,7,7,7,9],
         tagline="Established delivery history. Flexible integration scope.",
         technical="The proposal offers a configurable customer-service platform; CRM and ERP integration methods will be agreed during discovery.",
         technical_detail="The platform supports queue management, dashboards and a searchable knowledge base. The architecture diagram is described but not supplied. The proposal does not commit to API protocols, message retry semantics, migration mappings or concurrency targets. Orbit expects its integration partner to confirm feasibility after a paid discovery workshop.",
         implementation="Delivery is planned over 14 weeks with discovery, configuration, migration, acceptance testing and a two-week hypercare period.",
         plan_detail="A senior programme manager, solution consultant, two configuration specialists and one tester are allocated. Integration engineers are subject to discovery outcomes. Milestones occur at weeks 3, 7, 11 and 14; buyer sign-off is required at each. Acceptance criteria are to be negotiated. A risk register is reviewed weekly but schedule contingency is not quantified.",
         price="The estimated three-year total is USD 312,000; custom integration changes are charged at USD 1,200 per consultant day.",
         prices=[["Implementation", "$120,000", "One time estimate"],["Subscription", "$58,000", "Each year x 3"],["Migration", "$12,000", "One time estimate"],["Training", "$6,000", "One time"],["3-year total", "$312,000", "Before change requests"]],
         assumptions="Includes 250 agents and ten integration consulting days. Additional integration days require written approval. Hosting and business-hours service management are included; critical support is covered by the subscription. Taxes and on-site travel are excluded. No maximum integration overrun or renewal increase is committed.",
         security="The service supports SSO, encrypted storage, quarterly access reviews and a 90-day audit trail.",
         security_detail="Orbit describes an annual external assessment, but no report identifier or certification is included. Backups are retained for 30 days and restoration is tested annually. RTO is one business day; RPO is 24 hours. A standard DPA is offered, with regional storage location to be agreed. Subprocessor details are available on request.",
         support="Orbit reports 18 comparable fictional deployments and offers 24/7 critical response within 30 minutes, with named escalation owners.",
         support_detail="Three fictional references are offered: Birch Manufacturing (450 agents), Elm Transport (310 agents) and Willow Care (290 agents). Each reference description states implementation dates and scope. Quarterly training, monthly reviews and a dedicated account lead are included. A four-hour workaround objective is stated for critical incidents.",
         risks=["Integration architecture and effort are unresolved.","Commercial total may rise with discovery-driven changes.","Security assurance documents and data region need confirmation."],
         summary="Strong comparable experience and support, but vague integration commitments weaken technical confidence and cost certainty.",
         reasons=["Core platform scope is stated, but integration methods and capacity targets are deferred.","Named roles and milestones exist; acceptance and contingency need definition.","A usable total estimate is present, with material exposure to extra integration days.","Several concrete controls are described, but assurance and residency are unresolved.","Extensive relevant project history and specific escalation commitments."]),
]


def generate():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Deck", fontName="Helvetica", fontSize=11, leading=16, textColor=colors.HexColor("#527080"), spaceAfter=16))
    styles["Title"].fontSize, styles["Title"].leading = 28, 34
    styles["Title"].alignment = TA_LEFT
    styles["Title"].textColor = colors.HexColor("#13354a")
    styles["Heading2"].textColor = colors.HexColor("#087f79")
    styles["BodyText"].fontSize, styles["BodyText"].leading, styles["BodyText"].spaceAfter = 10, 15, 12
    out = ROOT / "samples"
    manifest = []
    for p in PROFILES:
        slug = p["name"].lower().replace(" ", "_")
        path = out / "proposals" / f"{slug}.pdf"
        story = []
        def para(text, style="BodyText"):
            story.append(Paragraph(text, styles[style]))
        def section(title, text):
            para(title, "Heading2")
            para(text)
        para("FICTIONAL SUPPLIER PROPOSAL · CLASSROOM USE", "Deck")
        para(p["name"], "Title")
        para(p["tagline"], "Deck")
        section("01 / Executive summary", "Response to the same fictional procurement request: implement a customer-service platform for 250 agents, integrate CRM and ERP, migrate two million records, and provide secure operations and support for three years. The buyer seeks clear delivery, commercial and service commitments. All organizations, projects, assurance documents and references in this proposal are invented.")
        section("Understanding the requirement", "The buyer needs a single view of service requests, reliable exchange with sales and finance systems, measurable migration acceptance and auditable access to customer information. The proposed scope and its limitations are set out below.")
        section("Proposed solution", p["technical"] + " " + p["technical_detail"])
        para(f"Submitted: {p['date']} | Procurement reference: TRAINING-RFP-026", "Deck")
        story.append(PageBreak())
        para("02 / Delivery & commercials", "Title")
        section("Implementation and milestones", p["implementation"] + " " + p["plan_detail"])
        section("Commercial offer", p["price"])
        table = Table([["Cost item", "USD", "Basis"]] + p["prices"], colWidths=[2.1*inch,1.2*inch,3.0*inch])
        table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#13354a")),
            ("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
            ("FONTSIZE",(0,0),(-1,-1),9),("BOTTOMPADDING",(0,0),(-1,-1),11),
            ("TOPPADDING",(0,0),(-1,-1),11),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.HexColor("#eef5f7"),colors.white]),
            ("LINEBELOW",(0,-1),(-1,-1),1,colors.HexColor("#087f79"))]))
        story.extend([table, Spacer(1,16)])
        section("Assumptions and exclusions", p["assumptions"])
        story.append(PageBreak())
        para("03 / Assurance & service", "Title")
        section("Security and compliance", p["security"] + " " + p["security_detail"])
        section("Support, experience and references", p["support"] + " " + p["support_detail"])
        section("Risks and buyer dependencies", "Buyer access to source systems, nominated subject-matter experts and timely test decisions are required. Claims in this proposal require verification before award. " + " ".join(p["risks"]))
        section("Evidence limitations", "This fictional proposal is not an independently verified audit or a real commercial offer. Supporting reference calls, assurance documents and contract terms are to be reviewed during due diligence. No real confidential supplier information is included.")
        def footer(canvas, doc):
            canvas.setStrokeColor(colors.HexColor("#d4e2e8"))
            canvas.line(48,44,564,44)
            canvas.setFont("Helvetica",8)
            canvas.setFillColor(colors.HexColor("#527080"))
            canvas.drawString(48,30,f"{p['name']} | Fictional classroom proposal")
            canvas.drawRightString(564,30,f"{doc.page} / 3")
        SimpleDocTemplate(str(path),pagesize=(612,792),leftMargin=48,rightMargin=48,topMargin=42,bottomMargin=60,
                          title=f"{p['name']} - Fictional RFP Proposal",author="RFP Intelligence Demo").build(story,onFirstPage=footer,onLaterPages=footer)
        fixture = {"supplier_name":p["name"],"criteria":[
            {"criterion_id":i+1,"score":score,"max_score":10,"justification":p["reasons"][i],
             "evidence":p[key],"evidence_page":page} for i,(score,key,page) in
            enumerate(zip(p["scores"],["technical","implementation","price","security","support"],[1,2,2,3,3]))],
            "risks":p["risks"],"overall_summary":p["summary"]}
        (out / "evaluations" / f"{slug}.json").write_text(json.dumps(fixture,indent=2))
        manifest.append({"supplier_name":p["name"],"submission_date":p["date"],"experience_rating":p["experience"],
                         "pdf_file":path.name,"evaluation_file":f"{slug}.json","sha256":hashlib.sha256(path.read_bytes()).hexdigest()})
    (out / "manifest.json").write_text(json.dumps(manifest,indent=2))
    print("Created four three-page proposals and human-authored demo scorecards.")


if __name__ == "__main__":
    generate()
