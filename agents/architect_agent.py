"""
Agent 4 — Architecture Designer Agent

Takes the enriched RequirementsAnalysis and synthesises:
  • A high-level architecture narrative
  • Platform services list (with descriptions)
  • Feature × Service matrix
  • Principles alignment statement
"""
from __future__ import annotations
import json
from typing import List, Dict
from collections import defaultdict

from models.schemas import (
    RequirementsAnalysis, ArchitectureDescription,
    PlatformService, FeatureServiceMatrixRow
)
from knowledge_base.kb import get_all
from utils.llm import llm_json, llm_call
import config


# ── System prompts ────────────────────────────────────────────────────────────

_SYSTEM_NARRATIVE = """You are a senior cloud architect writing the architecture section of a proposal.
Given a list of feature groups and their proposed solutions, write:
1. A 3-4 sentence high-level architecture narrative
2. The platform name (e.g. "SAP Business Technology Platform" or equivalent)
3. Cloud vs on-premise boundary description (1-2 sentences)
4. A principles alignment paragraph (how the solution aligns with modern IT architecture principles)

Return a JSON object:
{
  "narrative": "...",
  "platform_name": "...",
  "cloud_boundary": "...",
  "principles_alignment": "..."
}
No other text."""

_SYSTEM_SERVICES = """You are a senior SAP/cloud architect writing service descriptions for a proposal.
For each platform service provided, write a 2-3 sentence description covering:
- What the service does
- Why it was chosen for this RFP

Return a JSON array of objects:
{
  "name": "Service Name",
  "platform": "Platform Name",
  "description": "2-3 sentences",
  "features": ["feature group 1", "feature group 2"]
}
No other text."""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _group_by_feature(analysis: RequirementsAnalysis) -> Dict[str, List]:
    """Group requirements by feature_group."""
    groups: Dict[str, List] = defaultdict(list)
    for req in analysis.requirements:
        groups[req.feature_group].append(req)
    return dict(groups)


def _collect_services_from_kb(feature_groups: Dict[str, List]) -> List[Dict]:
    """Get all KB entries referenced by the feature groups."""
    from knowledge_base.kb import feature_group_lookup, retrieve_top
    seen_solutions: set[str] = set()
    services: List[Dict] = []
    for fg, reqs in feature_groups.items():
        solution = reqs[0].solution if reqs and reqs[0].solution else None
        kb = feature_group_lookup(fg)
        if kb and kb["solution"] not in seen_solutions:
            seen_solutions.add(kb["solution"])
            services.append(kb)
        elif solution and solution not in seen_solutions:
            # Best effort — use the solution name from the req
            seen_solutions.add(solution)
            services.append({
                "solution": solution,
                "platform": "SAP Business Technology Platform",
                "services": [solution],
                "description": f"Service supporting {fg}.",
                "feature_group": fg,
            })
    return services


def _build_feature_matrix(feature_groups: Dict[str, List],
                           service_list: List[PlatformService]) -> List[FeatureServiceMatrixRow]:
    """Build feature × service matrix rows."""
    service_names = [s.name for s in service_list]
    rows: List[FeatureServiceMatrixRow] = []
    from knowledge_base.kb import feature_group_lookup

    for item_num, (fg, reqs) in enumerate(feature_groups.items(), start=1):
        req_ids = [r.req_id for r in reqs]
        solution = reqs[0].solution if reqs and reqs[0].solution else "Custom Development"
        kb = feature_group_lookup(fg)
        services_used = kb.get("services", []) if kb else [solution]

        # Map service names to the service_list
        matched = [s for s in service_names if any(used.lower() in s.lower() for used in services_used)]
        if not matched:
            matched = service_names[:1]  # fallback

        rows.append(FeatureServiceMatrixRow(
            item_num=item_num,
            feature=fg,
            req_ids=req_ids,
            solution=solution,
            services=matched,
        ))
    return rows


# ── Public interface ──────────────────────────────────────────────────────────

def run(analysis: RequirementsAnalysis) -> ArchitectureDescription:
    """Synthesise architecture from enriched requirements."""
    print(f"  [Architect] Analysing {len(analysis.requirements)} requirements …")

    feature_groups = _group_by_feature(analysis)
    kb_services    = _collect_services_from_kb(feature_groups)

    # Build feature-solution summary for the LLM
    feature_summary = json.dumps([
        {
            "feature_group": fg,
            "solution": reqs[0].solution,
            "req_count": len(reqs),
        }
        for fg, reqs in feature_groups.items()
    ], indent=2)

    # ── Step 1: Generate narrative + platform meta ──────────────────────────
    print("  [Architect] Generating architecture narrative …")
    try:
        meta = llm_json(
            system=_SYSTEM_NARRATIVE,
            user=f"Feature groups and solutions:\n{feature_summary}",
            max_tokens=1024,
        )
        narrative            = meta.get("narrative", "")
        platform_name        = meta.get("platform_name", "SAP Business Technology Platform")
        cloud_boundary       = meta.get("cloud_boundary", "")
        principles_alignment = meta.get("principles_alignment", "")
    except Exception as e:
        print(f"  [Architect] Warning: narrative generation failed: {e}")
        narrative            = "The proposed solution leverages a cloud-first platform to deliver integrated HR capabilities."
        platform_name        = "SAP Business Technology Platform"
        cloud_boundary       = "Core HR data remains on-premise in SAP SuccessFactors while custom applications run on SAP BTP cloud."
        principles_alignment = "The solution adheres to open standards, API-first design, and security-by-design principles."

    # ── Step 2: Generate platform service descriptions ──────────────────────
    print("  [Architect] Generating service descriptions …")
    services_input = json.dumps([
        {
            "name": s.get("solution", ""),
            "platform": s.get("platform", platform_name),
            "feature_group": s.get("feature_group", ""),
            "description": s.get("description", ""),
        }
        for s in kb_services
    ], indent=2)

    try:
        raw_services = llm_json(
            system=_SYSTEM_SERVICES,
            user=f"Platform name: {platform_name}\n\nServices to describe:\n{services_input}",
            max_tokens=2048,
        )
        if not isinstance(raw_services, list):
            raw_services = [raw_services]
        platform_services = [
            PlatformService(
                name=s.get("name", ""),
                platform=s.get("platform", platform_name),
                description=s.get("description", ""),
                features=s.get("features", []),
            )
            for s in raw_services
        ]
    except Exception as e:
        print(f"  [Architect] Warning: service descriptions failed: {e}")
        platform_services = [
            PlatformService(
                name=s.get("solution", "Service"),
                platform=s.get("platform", platform_name),
                description=s.get("description", "Platform service supporting HR requirements."),
                features=[s.get("feature_group", "")],
            )
            for s in kb_services
        ]

    # ── Step 3: Build feature × service matrix ──────────────────────────────
    print("  [Architect] Building feature-service matrix …")
    feature_matrix = _build_feature_matrix(feature_groups, platform_services)

    arch = ArchitectureDescription(
        narrative=narrative,
        platform_name=platform_name,
        services=platform_services,
        feature_matrix=feature_matrix,
        principles_alignment=principles_alignment,
        cloud_boundary=cloud_boundary,
    )

    print(f"  [Architect] → {len(platform_services)} services · {len(feature_matrix)} feature groups")
    return arch
