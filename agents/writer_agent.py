"""
Agent 5 — Deck Content Writer Agent

Generates structured DeckContent JSON for every slide section of the
46-slide response deck. Inputs: ArchitectureDescription + RequirementsAnalysis.
"""
from __future__ import annotations
import json
from datetime import date
from typing import List

from models.schemas import (
    ArchitectureDescription, RequirementsAnalysis, DeckContent,
    RoleResponsibility, Assumption, Credential, PlanPhase
)
from utils.llm import llm_json, llm_call
import config


# ── Default / synthetic content (fallback) ───────────────────────────────────

_DEFAULT_ROLES = [
    RoleResponsibility(
        role="Project Owner (PO)",
        responsibilities=["Define and prioritise backlog", "Sign off on deliverables", "Escalation point for scope changes"],
        outcomes=["Approved sprint backlog", "Accepted deliverables", "Change log maintained"],
        responsible_party="Client",
    ),
    RoleResponsibility(
        role="Project Manager (PM)",
        responsibilities=["Day-to-day project coordination", "Risk & issue management", "Status reporting"],
        outcomes=["Weekly status report", "Risk register", "Project plan updated"],
        responsible_party="Vendor",
    ),
    RoleResponsibility(
        role="Business Analyst (BA)",
        responsibilities=["Requirements gathering", "Process documentation", "UAT coordination"],
        outcomes=["Validated requirements", "Process maps", "UAT sign-off"],
        responsible_party="Vendor",
    ),
    RoleResponsibility(
        role="Solution Architect",
        responsibilities=["Architecture design", "Technical decisions", "Integration patterns"],
        outcomes=["Architecture document", "Integration spec", "ADRs"],
        responsible_party="Vendor",
    ),
    RoleResponsibility(
        role="Scrum Master",
        responsibilities=["Facilitate agile ceremonies", "Remove impediments", "Track velocity"],
        outcomes=["Sprint velocity", "Retrospective outcomes", "Burndown charts"],
        responsible_party="Vendor",
    ),
    RoleResponsibility(
        role="Development Team",
        responsibilities=["Build and unit-test features", "Code reviews", "Bug fixes"],
        outcomes=["Deployed features", "Unit test coverage", "Release notes"],
        responsible_party="Vendor",
    ),
]

_DEFAULT_ASSUMPTIONS = [
    Assumption(category="Platform", text="SAP BTP licenses are available and provisioned before project kick-off."),
    Assumption(category="Platform", text="SAP SuccessFactors is already deployed and accessible via standard APIs."),
    Assumption(category="Scope", text="The scope covers only the requirements defined in the RFP; any additional features are out of scope."),
    Assumption(category="Scope", text="Data migration covers current active employees only; historical records are excluded unless explicitly agreed."),
    Assumption(category="Methodology", text="The project follows Agile/Scrum with 2-week sprints and regular sprint reviews with the client."),
    Assumption(category="Methodology", text="Client product owner is available for backlog grooming and sprint reviews throughout the project."),
    Assumption(category="Team Schedule", text="Vendor team operates Monday–Friday, CET business hours. Onsite availability is agreed per sprint."),
    Assumption(category="Exclusions", text="Third-party system integrations beyond those listed in the RFP are excluded from this proposal."),
    Assumption(category="Exclusions", text="End-user training and change management are excluded unless included in a separate workstream."),
]

_DEFAULT_CREDENTIALS = [
    Credential(
        industry="Financial Services",
        project="HR Digital Transformation — Global Bank",
        description="Designed and implemented a self-service HR portal on SAP BTP for 45,000 employees across 12 countries, replacing legacy paper-based processes.",
        outcomes=["80% reduction in HR ticket volume", "Go-live in 9 months", "NPS score of 72 post-launch", "Reusable component library shared across 3 markets"],
    ),
    Credential(
        industry="Manufacturing",
        project="SAP SuccessFactors Integration — Industrial Group",
        description="Delivered end-to-end integration between SAP SuccessFactors and 6 third-party HR tools using SAP Integration Suite, enabling real-time data sync.",
        outcomes=["Zero data inconsistency incidents post-migration", "API response time < 200ms", "Integration reused for 2 subsequent acquisitions"],
    ),
    Credential(
        industry="Public Sector",
        project="HR Automation & Chatbot — Government Agency",
        description="Built a conversational HR assistant handling 60% of employee queries automatically, integrated with legacy HR systems via RPA.",
        outcomes=["60% deflection rate from HR helpdesk", "4x RPA bots deployed", "Fully compliant with GDPR and national data protection law"],
    ),
    Credential(
        industry="Retail",
        project="Workforce Management Platform — European Retailer",
        description="Implemented a custom workforce scheduling and absence management application on SAP BTP CAP, serving 28,000 store employees.",
        outcomes=["25% reduction in scheduling errors", "Mobile-first UI adopted by 95% of users in 2 months", "Integrated with SAP Time Management"],
    ),
]

_DEFAULT_PLAN_PHASES = [
    PlanPhase(phase="Discovery & Planning",        start_month=1, duration_months=1),
    PlanPhase(phase="Sprint 1–2 (Foundation)",      start_month=2, duration_months=2),
    PlanPhase(phase="Sprint 3–6 (Core Build)",       start_month=4, duration_months=3),
    PlanPhase(phase="Sprint 7–8 (Integration & UAT)", start_month=7, duration_months=2),
    PlanPhase(phase="Go-Live & Stabilization",       start_month=9, duration_months=1),
    PlanPhase(phase="Post Go-Live Hypercare",         start_month=10, duration_months=2),
]


# ── LLM-assisted content generation ──────────────────────────────────────────

def _generate_governance(platform_name: str) -> str:
    try:
        return llm_call(
            system="You are a project manager writing the governance section of a proposal. Be concise (4-6 sentences). Write plain text only — no markdown, no bullet points, no headers, no bold or italic markers.",
            user=f"Write the governance and communication model for a {platform_name} HR transformation project. Cover: time zones (CET), weekly status calls, sprint reviews, escalation model (project level → steering committee), and functional resource interaction.",
            max_tokens=400,
        )
    except Exception:
        return (
            "The project operates in CET business hours with weekly status calls every Monday. "
            "Sprint reviews are held bi-weekly with the client product owner and key stakeholders. "
            "Issues are escalated first to the Project Manager, then to the Steering Committee if unresolved within 48 hours. "
            "A RACI matrix governs all functional interactions between vendor and client teams."
        )


def _generate_team_structure(platform_name: str) -> str:
    try:
        return llm_call(
            system="You are writing a project proposal. Be concise (3-4 sentences). Write plain text only — no markdown, no bullet points, no headers, no bold or italic markers.",
            user=f"Describe the delivery method and team structure for a {platform_name} HR transformation project. Mention Agile/Scrum, team roles, onsite/nearshore split.",
            max_tokens=300,
        )
    except Exception:
        return (
            "The project follows Agile/Scrum with 2-week sprints. "
            "The delivery team consists of a Project Manager, Solution Architect, Business Analyst, Scrum Master, and a development squad of 3–5 engineers. "
            "Onsite presence is provided for key workshops and go-live; remaining delivery is nearshore."
        )


# ── Public interface ──────────────────────────────────────────────────────────

def run(arch: ArchitectureDescription, analysis: RequirementsAnalysis) -> DeckContent:
    """Generate all slide content as a DeckContent object."""
    print("  [Writer] Generating deck content …")

    # Governance & team
    print("  [Writer] LLM: governance & team structure …")
    governance     = _generate_governance(arch.platform_name)
    team_structure = _generate_team_structure(arch.platform_name)

    today = date.today().strftime("%B %Y")

    content = DeckContent(
        # Cover (Slide 1)
        client_name   = config.CLIENT_NAME,
        project_name  = config.PROJECT_NAME,
        version       = config.DECK_VERSION,
        authors       = [config.VENDOR_NAME + " Delivery Team"],
        date          = today,
        status        = "DRAFT",

        # Principles (Slide 6)
        principles_text = arch.principles_alignment,

        # Project setup (Slide 15)
        delivery_method = "Agile / Scrum — 2-week sprints",
        team_structure  = team_structure,
        locations       = "Onsite (client workshops & go-live) + Nearshore (daily delivery)",

        # Governance (Slide 16)
        governance = governance,

        # Roles & Responsibilities (Slides 17-19)
        roles = _DEFAULT_ROLES,

        # Plan (Slide 21)
        plan_phases = _DEFAULT_PLAN_PHASES,
        plan_note   = "This timeline is preliminary and subject to refinement during the Discovery phase.",

        # Assumptions (Slides 28-31)
        assumptions = _DEFAULT_ASSUMPTIONS,

        # Credentials (Slides 33-39)
        credentials = _DEFAULT_CREDENTIALS,

        # Appendix (Slides 41-46)
        appendix_items = [
            "Artefact complexity definitions: Low (≤1 day), Medium (2-5 days), High (>5 days)",
            "Integration specification: REST API, OAuth 2.0, JSON payloads",
            "RICEFW object inventory — to be completed during Discovery",
            "Glossary of terms and abbreviations",
            "Reference architecture diagram (detailed)",
            "Technology version matrix",
        ],
    )

    print("  [Writer] → DeckContent generated ✓")
    return content
