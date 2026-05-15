"""
schemas.py — Pydantic data contracts shared across all agents.

Data flows between agents as serialised JSON using these models.
Any agent that produces data must return one of these models.
Any agent that consumes data must accept one of these models.
"""
from __future__ import annotations
from typing import List, Optional, Dict
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# AGENT 1 OUTPUT — Document Ingestion
# ─────────────────────────────────────────────────────────────────────────────

class DocumentSection(BaseModel):
    """One logical section extracted from an input document."""
    source_file: str            = Field(description="Original filename")
    section_id:  str            = Field(description="e.g. '1', '1.2', 'FA-Group-3'")
    title:       str            = Field(description="Section heading")
    content:     str            = Field(description="Full raw text of this section")
    tables:      List[List[str]] = Field(default_factory=list,
                                         description="Any tables inside the section, rows as string lists")

class IngestedDocument(BaseModel):
    """Full parsed output of one or more input files."""
    sections: List[DocumentSection]


# ─────────────────────────────────────────────────────────────────────────────
# AGENT 2 OUTPUT — Requirements Extractor
# ─────────────────────────────────────────────────────────────────────────────

class Requirement(BaseModel):
    """One functional or non-functional requirement extracted from the RFP."""
    req_id:        str           = Field(description="e.g. FA-1, FA-9, NFR-1")
    title:         str           = Field(description="Short requirement label")
    details:       str           = Field(description="Full description / acceptance criteria")
    feature_group: str           = Field(description="Feature area this requirement belongs to")
    note:          Optional[str] = Field(default=None, description="HR Capability / IT Capability / etc.")
    solution:      Optional[str] = Field(default=None, description="Proposed solution (filled by Agent 3)")
    comment:       Optional[str] = Field(default=None, description="e.g. RICEFW to be considered")
    questions:     Optional[str] = Field(default=None, description="Open clarification questions")
    # Complexity columns (filled by Agent 3)
    n_interfaces:  Optional[int] = Field(default=None)
    n_pages:       Optional[int] = Field(default=None)
    n_screen_panels: Optional[int] = Field(default=None)
    n_ui_int:      Optional[int] = Field(default=None)
    n_biz_services: Optional[int] = Field(default=None)
    n_data_services: Optional[int] = Field(default=None)
    n_db_tables:   Optional[int] = Field(default=None)
    n_db_logic:    Optional[int] = Field(default=None)
    n_workflows:   Optional[int] = Field(default=None)
    n_reports:     Optional[int] = Field(default=None)
    complexity:    Optional[str] = Field(default=None, description="Low / Medium / High")

class RequirementsAnalysis(BaseModel):
    """Stage 1 output: full list of extracted & enriched requirements."""
    requirements: List[Requirement]


# ─────────────────────────────────────────────────────────────────────────────
# AGENT 4 OUTPUT — Architecture Designer
# ─────────────────────────────────────────────────────────────────────────────

class PlatformService(BaseModel):
    """One platform service used in the proposed solution."""
    name:        str = Field(description="Service name, e.g. 'SAP Integration Suite'")
    platform:    str = Field(description="Parent platform, e.g. 'SAP BTP'")
    description: str = Field(description="2–3 sentence description of what it does and why chosen")
    features:    List[str] = Field(default_factory=list, description="Feature groups that use this service")

class FeatureServiceMatrixRow(BaseModel):
    """One row of the Feature × Service matrix (slide 5)."""
    item_num:  int         = Field(description="Row number #1, #2, ...")
    feature:   str         = Field(description="Feature group name")
    req_ids:   List[str]   = Field(description="Requirement IDs covered")
    solution:  str         = Field(description="Proposed solution narrative")
    services:  List[str]   = Field(description="Service names used (mark X in matrix)")

class ArchitectureDescription(BaseModel):
    """Agent 4 output — architecture synthesis."""
    narrative:       str                      = Field(description="High-level architecture narrative paragraph")
    platform_name:   str                      = Field(description="e.g. 'SAP Business Technology Platform'")
    services:        List[PlatformService]
    feature_matrix:  List[FeatureServiceMatrixRow]
    principles_alignment: str                 = Field(description="How solution aligns with IT architecture principles")
    cloud_boundary:  str                      = Field(description="What is cloud vs on-premise")


# ─────────────────────────────────────────────────────────────────────────────
# AGENT 5 OUTPUT — Deck Content Writer
# ─────────────────────────────────────────────────────────────────────────────

class RoleResponsibility(BaseModel):
    role:             str
    responsibilities: List[str]
    outcomes:         List[str]
    responsible_party: str  # "Vendor" | "Client" | "Joint"

class Assumption(BaseModel):
    category: str   # e.g. "Platform", "Scope", "Methodology"
    text:     str

class Credential(BaseModel):
    industry:    str
    project:     str
    description: str
    outcomes:    List[str]

class PlanPhase(BaseModel):
    phase:      str   # "Discovery & Planning", "Sprint 1", etc.
    start_month: int
    duration_months: int

class DeckContent(BaseModel):
    """Agent 5 output — structured content for every slide section."""
    # Cover
    client_name:   str
    project_name:  str
    version:       str
    authors:       List[str]
    date:          str
    status:        str

    # Section 2: scope / feature-solution table (mirrors feature_matrix from arch)
    # (directly sourced from ArchitectureDescription.feature_matrix)

    # Section 3-4: feature-solution tables → use arch.feature_matrix

    # Section 5: service matrix → use arch.feature_matrix + arch.services

    # Section 6: principles alignment
    principles_text: str

    # Section 8: architecture description (reuses arch.narrative)

    # Section 9-13: service descriptions (reuses arch.services)

    # Section 15: project setup
    delivery_method:   str   # "Agile/Scrum"
    team_structure:    str
    locations:         str   # "Onsite / Nearshore"

    # Section 16: governance
    governance:        str   # paragraph: meeting cadence, escalation model

    # Section 17-19: roles & responsibilities
    roles:             List[RoleResponsibility]

    # Section 21: plan
    plan_phases:       List[PlanPhase]
    plan_note:         str   # "This is a preliminary estimate"

    # Section 28-31: assumptions
    assumptions:       List[Assumption]

    # Section 33-39: credentials
    credentials:       List[Credential]

    # Section 41-46: appendix
    appendix_items:    List[str]
