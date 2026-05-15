# AI-Powered RFP Response Automation

A multi-agent pipeline that reads an RFP document and automatically produces a ready-to-present PowerPoint proposal deck and a requirements analysis spreadsheet.

Built for Hackathon UC1 — HR Digital Transformation (SAP BTP / Accenture).

## How it works

Six agents run in sequence, each handing off structured data to the next:

```
RFP document(s)
      │
      ▼
[Agent 1] Ingestion      — parses DOCX / PDF / PPTX into sections (no LLM)
      │
      ▼
[Agent 2] Extraction     — extracts functional & non-functional requirements via LLM
      │                    → outputs Requirements_Analysis.xlsx
      ▼
[Agent 3] Mapper         — maps each requirement to a solution from the knowledge base
      │                    → enriches Requirements_Analysis.xlsx
      ▼
[Agent 4] Architect      — designs the platform architecture and feature-service matrix
      │
      ▼
[Agent 5] Writer         — generates narrative slide content via LLM
      │
      ▼
[Agent 6] Assembler      — builds the 38-slide PPTX deck
                           → outputs Response_Deck.pptx
```

## Outputs

| File | Description |
|------|-------------|
| `outputs/Requirements_Analysis.xlsx` | All extracted requirements with solution mapping, complexity, and RICEFW estimates |
| `outputs/Response_Deck.pptx` | Full proposal deck — cover, scope, architecture, approach, plan, credentials, appendix |

## Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file at the project root:

```
ANTHROPIC_API_KEY=sk-ant-...

# Optional overrides
LLM_MODEL=claude-haiku-4-5-20251001
CLIENT_NAME=CLIENT
PROJECT_NAME=EnABLEHR — HR Digital Transformation
VENDOR_NAME=Accenture
DECK_VERSION=v0.1 DRAFT
```

## Usage

```bash
# Run with the built-in synthetic demo RFP
python main.py --demo

# Run with a real RFP file
python main.py --input path/to/rfp.docx

# Run with multiple files (e.g. RFP + annexes)
python main.py --input rfp.docx annex1.docx annex2.pdf
```

Supported input formats: `.docx`, `.pdf`, `.pptx`

## Project structure

```
rfp_automation/
├── main.py                      # Pipeline orchestrator
├── config.py                    # Environment & path config
├── requirements.txt
│
├── agents/
│   ├── ingestion_agent.py       # Agent 1 — document parsing
│   ├── extractor_agent.py       # Agent 2 — requirements extraction
│   ├── mapper_agent.py          # Agent 3 — solution mapping
│   ├── architect_agent.py       # Agent 4 — architecture design
│   ├── writer_agent.py          # Agent 5 — slide content generation
│   └── assembler_agent.py       # Agent 6 — PPTX assembly
│
├── models/
│   └── schemas.py               # Pydantic data models shared across agents
│
├── knowledge_base/
│   ├── solutions.json           # SAP BTP solution catalogue with keywords
│   └── kb.py                    # Knowledge base loader
│
├── utils/
│   └── llm.py                   # Anthropic API wrapper
│
└── samples/
    ├── sample_rfp.docx          # Synthetic demo RFP
    └── generate_sample_rfp.py   # Script to regenerate the demo RFP
```

## Knowledge base

`knowledge_base/solutions.json` maps feature groups to SAP BTP services using keyword matching. Each entry covers: solution name, platform, services list, and RICEFW considerations. Extend this file to support additional platforms or solution areas.
