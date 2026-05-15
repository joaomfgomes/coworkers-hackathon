"""
main.py — RFP Automation Pipeline Orchestrator

Usage:
    # With a real RFP file:
    python main.py --input path/to/rfp.docx

    # With the synthetic demo RFP:
    python main.py --demo

    # With multiple files:
    python main.py --input rfp.docx annex.docx

    # With a PDF:
    python main.py --input rfp.pdf

Environment:
    ANTHROPIC_API_KEY  — required
    LLM_MODEL          — optional (default: claude-3-5-haiku-20241022)
    CLIENT_NAME        — optional (default: CLIENT)
    PROJECT_NAME       — optional (default: EnABLEHR HR Digital Transformation)
"""
import argparse
import sys
import time
import pathlib

# ── Agents ────────────────────────────────────────────────────────────────────
from agents import ingestion_agent
from agents import extractor_agent
from agents import mapper_agent
from agents import architect_agent
from agents import writer_agent
from agents import assembler_agent

import config


def _banner(msg: str) -> None:
    line = "─" * 60
    print(f"\n{line}")
    print(f"  {msg}")
    print(f"{line}")


def run_pipeline(input_files: list[str]) -> None:
    total_start = time.time()

    # ─────────────────────────────────────────────────────────────────────────
    _banner("AGENT 1 — Document Ingestion")
    t0 = time.time()
    ingested = ingestion_agent.run(input_files)
    print(f"  Done in {time.time() - t0:.1f}s — {len(ingested.sections)} sections")

    # ─────────────────────────────────────────────────────────────────────────
    _banner("AGENT 2 — Requirements Extraction")
    t0 = time.time()
    analysis = extractor_agent.run(ingested)
    print(f"  Done in {time.time() - t0:.1f}s — {len(analysis.requirements)} requirements extracted")

    # ─────────────────────────────────────────────────────────────────────────
    _banner("AGENT 3 — Solution Mapping")
    t0 = time.time()
    enriched = mapper_agent.run(analysis)
    print(f"  Done in {time.time() - t0:.1f}s")

    # ─────────────────────────────────────────────────────────────────────────
    _banner("AGENT 4 — Architecture Design")
    t0 = time.time()
    arch = architect_agent.run(enriched)
    print(f"  Done in {time.time() - t0:.1f}s — {len(arch.services)} services · {len(arch.feature_matrix)} features")

    # ─────────────────────────────────────────────────────────────────────────
    _banner("AGENT 5 — Deck Content Writing")
    t0 = time.time()
    deck_content = writer_agent.run(arch, enriched)
    print(f"  Done in {time.time() - t0:.1f}s")

    # ─────────────────────────────────────────────────────────────────────────
    _banner("AGENT 6 — Deck Assembly (PPTX)")
    t0 = time.time()
    pptx_path = assembler_agent.run(deck_content, arch)
    print(f"  Done in {time.time() - t0:.1f}s")

    # ─────────────────────────────────────────────────────────────────────────
    elapsed = time.time() - total_start
    print(f"\n{'═' * 60}")
    print(f"  ✅  PIPELINE COMPLETE  ({elapsed:.0f}s total)")
    print(f"{'═' * 60}")
    print(f"\n  Stage 1 output:  {config.OUTPUTS_DIR / 'Requirements_Analysis.xlsx'}")
    print(f"  Stage 2 output:  {pptx_path}")
    print()


def _ensure_demo_rfp() -> str:
    """Generate the synthetic sample RFP if it doesn't exist yet."""
    sample_path = config.SAMPLES_DIR / "sample_rfp.docx"
    if not sample_path.exists():
        print("  Generating synthetic demo RFP …")
        from samples.generate_sample_rfp import create_sample_rfp
        create_sample_rfp(str(sample_path))
    else:
        print(f"  Using existing demo RFP: {sample_path.name}")
    return str(sample_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI-Powered RFP Response Automation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--input", nargs="+", metavar="FILE",
        help="One or more RFP input files (DOCX, PDF, or PPTX)",
    )
    group.add_argument(
        "--demo", action="store_true",
        help="Run with the synthetic demo RFP",
    )
    args = parser.parse_args()

    print("\n" + "═" * 60)
    print("  AI-POWERED RFP RESPONSE AUTOMATION")
    print("  Hackathon UC1 — Multi-Agent Pipeline")
    print("═" * 60)
    print(f"\n  Client:  {config.CLIENT_NAME}")
    print(f"  Project: {config.PROJECT_NAME}")
    print(f"  Model:   {config.LLM_MODEL}")
    print(f"  Output:  {config.OUTPUTS_DIR}")

    if not config.ANTHROPIC_API_KEY:
        print("\n  ❌ ERROR: ANTHROPIC_API_KEY is not set.")
        print("     Add it to a .env file or export it:  export ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)

    if args.demo:
        input_files = [_ensure_demo_rfp()]
    else:
        input_files = args.input
        for f in input_files:
            if not pathlib.Path(f).exists():
                print(f"\n  ❌ ERROR: File not found: {f}")
                sys.exit(1)

    print(f"\n  Input files: {[pathlib.Path(f).name for f in input_files]}")

    run_pipeline(input_files)


if __name__ == "__main__":
    main()
