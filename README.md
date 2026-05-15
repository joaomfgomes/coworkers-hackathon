# AI-Powered RFP Response Automation

Reads an RFP document and automatically generates:
- `Requirements_Analysis.xlsx` — all extracted requirements with solution mapping and complexity
- `Response_Deck.pptx` — a ready-to-present 46-slide proposal deck

Built for **Hackathon UC1 — HR Digital Transformation**.

---

## How to run

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create a `.env` file

Create a file named `.env` in the project root with the following content:

```env
ANTHROPIC_API_KEY=sk-ant-...

# Optional — override the defaults shown below
LLM_MODEL=claude-3-5-haiku-20241022
CLIENT_NAME=CLIENT
PROJECT_NAME=EnABLEHR — HR Digital Transformation
VENDOR_NAME=Accenture
DECK_VERSION=v0.1 DRAFT
```

> `ANTHROPIC_API_KEY` is the only required variable. Get one at https://console.anthropic.com.

### 3. Run

**Option A — Command line**

```bash
# Quick demo with the built-in sample RFP
python main.py --demo

# Your own RFP file
python main.py --input path/to/rfp.docx

# Multiple files (RFP + annexes)
python main.py --input rfp.docx annex.pdf
```

Supported formats: `.docx`, `.pdf`, `.pptx`

**Option B — Web UI**

```bash
python app.py
```

Open [http://localhost:3112](http://localhost:3112) in your browser, drag and drop your RFP file, and download the outputs when done.

---

## Outputs

Both files are saved to the `outputs/` folder.

| File | What it contains |
|------|-----------------|
| `Requirements_Analysis.xlsx` | All requirements extracted from the RFP, each mapped to a solution, with complexity and RICEFW estimates |
| `Response_Deck.pptx` | Full proposal deck — scope, architecture, approach, project plan, assumptions, credentials, appendix |

---

## Images

### `agent-architecture.png`
Diagram of the 6-agent pipeline that processes the RFP step by step:
**Ingestion → Extraction → Mapping → Architecture → Writing → Assembly**

Each stage hands its output to the next. The Knowledge Base feeds into the Mapping stage to match requirements to SAP BTP solutions.

### `design-decisions-architecture-comparison.png`
Side-by-side comparison of two design approaches:
- **Left — Sequential pipeline** (what was built): simple, one agent at a time
- **Right — Master/subagent** (alternative): a central orchestrator runs agents in parallel, which would be faster but more complex

This image documents *why* the sequential approach was chosen for the hackathon.

---

## How to view the HTML presentation

The file `presentation-rfp-versao-final.html` is a standalone interactive slide deck (in Portuguese) that pitches the project.

**To open it:**

1. Download or clone the repository
2. Find the file `presentation-rfp-versao-final.html` in the root folder
3. Double-click it — it opens directly in any browser (Chrome, Firefox, Edge, Safari)

No server, no install needed.

**Navigation:**
- Use the **arrow keys** (← →) to move between slides
- Or click the **dots** at the bottom of the screen
- There are **7 slides** in total

---

## Project structure

```
├── main.py                  # CLI entry point
├── app.py                   # Web UI (Flask, port 3112)
├── config.py                # All configuration (reads from .env)
├── requirements.txt         # Python dependencies
│
├── agents/
│   ├── ingestion_agent.py   # Parses DOCX / PDF / PPTX into sections
│   ├── extractor_agent.py   # Extracts requirements using Claude
│   ├── mapper_agent.py      # Maps requirements to solutions (Knowledge Base + Claude)
│   ├── architect_agent.py   # Designs the platform architecture
│   ├── writer_agent.py      # Generates slide content using Claude
│   └── assembler_agent.py   # Builds the final PPTX
│
├── models/
│   └── schemas.py           # Data models shared between all agents
│
├── knowledge_base/
│   ├── solutions.json       # SAP BTP solution catalogue (8 entries)
│   └── kb.py                # Knowledge base loader
│
├── utils/
│   └── llm.py               # Anthropic API wrapper
│
└── samples/
    ├── sample_rfp.docx      # Synthetic demo RFP (used by --demo)
    └── generate_sample_rfp.py  # Script to regenerate the demo file
```
