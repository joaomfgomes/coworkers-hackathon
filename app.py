"""
app.py — Flask web UI for the RFP Automation Pipeline
Run:  python app.py
Open: http://localhost:3112
"""
import io
import os
import sys
import queue
import threading
import uuid
from glob import glob

from flask import Flask, Response, jsonify, request, send_from_directory, stream_with_context
from werkzeug.utils import secure_filename

import config

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
ALLOWED_EXT = {".docx", ".pdf", ".pptx"}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

job = {"status": "idle", "log_queue": None, "outputs": {}, "error": None}
run_lock = threading.Lock()


# ── Stdout capture ────────────────────────────────────────────────────────────

class QueueStream(io.RawIOBase):
    def __init__(self, q):
        self.q = q

    def write(self, b):
        if isinstance(b, (bytes, bytearray)):
            b = b.decode("utf-8", errors="replace")
        if b:
            self.q.put(b)
        return len(b)

    def flush(self):
        pass


# ── Pipeline worker ───────────────────────────────────────────────────────────

def _run_pipeline_thread(input_files):
    old_stdout = sys.stdout
    sys.stdout = QueueStream(job["log_queue"])
    try:
        from main import run_pipeline
        run_pipeline(input_files)
        pptx_files = sorted(
            glob(str(config.OUTPUTS_DIR / "*.pptx")),
            key=os.path.getmtime,
            reverse=True,
        )
        job["outputs"] = {
            "xlsx": "Requirements_Analysis.xlsx",
            "pptx": os.path.basename(pptx_files[0]) if pptx_files else "Response_Deck.pptx",
        }
        job["status"] = "done"
    except Exception as exc:
        job["error"] = str(exc)
        job["status"] = "error"
    finally:
        sys.stdout = old_stdout
        job["log_queue"].put(None)  # sentinel → close SSE stream


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return HOME_HTML


@app.route("/run", methods=["POST"])
def run_job():
    with run_lock:
        if job["status"] == "running":
            return jsonify({"error": "Pipeline already running"}), 409

        # Optional config overrides
        client_name  = request.form.get("client_name",  "").strip()
        project_name = request.form.get("project_name", "").strip()
        if client_name:
            config.CLIENT_NAME = client_name
        if project_name:
            config.PROJECT_NAME = project_name

        # Resolve input files
        demo = request.form.get("demo") == "1"
        if demo:
            input_files = [str(config.SAMPLES_DIR / "sample_rfp.docx")]
        else:
            files = request.files.getlist("files")
            if not files or files[0].filename == "":
                return jsonify({"error": "No files provided"}), 400
            input_files = []
            for f in files:
                ext = os.path.splitext(f.filename)[1].lower()
                if ext not in ALLOWED_EXT:
                    return jsonify({"error": f"Unsupported file type: {ext}"}), 400
                filename = f"{uuid.uuid4().hex}_{secure_filename(f.filename)}"
                dest = os.path.join(UPLOAD_DIR, filename)
                f.save(dest)
                input_files.append(dest)

        job["status"]    = "running"
        job["log_queue"] = queue.Queue()
        job["outputs"]   = {}
        job["error"]     = None

    t = threading.Thread(target=_run_pipeline_thread, args=(input_files,), daemon=True)
    t.start()
    return jsonify({"ok": True})


@app.route("/stream")
def stream():
    def generate():
        q = job["log_queue"]
        if q is None:
            return
        while True:
            try:
                line = q.get(timeout=30)
            except queue.Empty:
                yield "data: \n\n"  # heartbeat
                continue
            if line is None:
                yield "data: [DONE]\n\n"
                break
            for part in line.splitlines():
                if part:
                    yield f"data: {part}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/status")
def status():
    return jsonify({
        "status":  job["status"],
        "outputs": job["outputs"],
        "error":   job["error"],
    })


@app.route("/download/<path:filename>")
def download(filename):
    return send_from_directory(config.OUTPUTS_DIR, filename, as_attachment=True)


# ── HTML ──────────────────────────────────────────────────────────────────────

HOME_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RFP Automation</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: #1a1a2e;
    color: #e0e0e0;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 40px 20px;
  }

  header {
    text-align: center;
    margin-bottom: 36px;
  }
  header h1 {
    font-size: 1.8rem;
    font-weight: 700;
    color: #fff;
    letter-spacing: -0.5px;
  }
  header p {
    color: #9b8fc4;
    margin-top: 6px;
    font-size: 0.95rem;
  }

  .card {
    background: #16213e;
    border: 1px solid #2d2d5e;
    border-radius: 12px;
    padding: 32px;
    width: 100%;
    max-width: 640px;
  }

  .dropzone {
    border: 2px dashed #5b2d8e;
    border-radius: 8px;
    padding: 36px 20px;
    text-align: center;
    cursor: pointer;
    transition: background 0.2s, border-color 0.2s;
    color: #9b8fc4;
    font-size: 0.95rem;
  }
  .dropzone.over { background: #2d1a4e; border-color: #d4a8f5; color: #d4a8f5; }
  .dropzone.has-file { border-color: #58d68d; color: #58d68d; }
  .dropzone input[type=file] { display: none; }

  .fields { margin-top: 20px; display: flex; flex-direction: column; gap: 12px; }
  .fields label { font-size: 0.82rem; color: #9b8fc4; margin-bottom: 4px; display: block; }
  .fields input {
    width: 100%;
    background: #0f0f2a;
    border: 1px solid #2d2d5e;
    border-radius: 6px;
    padding: 9px 12px;
    color: #e0e0e0;
    font-size: 0.9rem;
    outline: none;
    transition: border-color 0.2s;
  }
  .fields input:focus { border-color: #5b2d8e; }

  .actions { margin-top: 24px; display: flex; gap: 12px; }
  button {
    flex: 1;
    padding: 11px 16px;
    border: none;
    border-radius: 7px;
    font-size: 0.92rem;
    font-weight: 600;
    cursor: pointer;
    transition: opacity 0.2s;
  }
  button:disabled { opacity: 0.45; cursor: not-allowed; }
  .btn-primary { background: #5b2d8e; color: #fff; }
  .btn-primary:hover:not(:disabled) { background: #7038aa; }
  .btn-secondary { background: #2d2d5e; color: #d4a8f5; }
  .btn-secondary:hover:not(:disabled) { background: #3a3a7a; }
  .btn-success { background: #1e6e3e; color: #58d68d; }
  .btn-success:hover:not(:disabled) { background: #247a46; }

  #log-section { display: none; margin-top: 24px; }
  #log-section h3 { font-size: 0.85rem; color: #9b8fc4; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; }
  #log {
    background: #0d1117;
    border: 1px solid #2d2d5e;
    border-radius: 6px;
    padding: 14px 16px;
    height: 320px;
    overflow-y: auto;
    font-family: "Cascadia Code", "Fira Code", "Consolas", monospace;
    font-size: 0.78rem;
    line-height: 1.6;
    color: #58d68d;
    white-space: pre-wrap;
    word-break: break-all;
  }

  #done-section { display: none; margin-top: 24px; }
  #done-section h3 { font-size: 1rem; color: #58d68d; margin-bottom: 16px; text-align: center; }
  .downloads { display: flex; gap: 12px; }
  .downloads a {
    flex: 1;
    display: block;
    padding: 11px 16px;
    background: #1e6e3e;
    color: #58d68d;
    text-decoration: none;
    text-align: center;
    border-radius: 7px;
    font-weight: 600;
    font-size: 0.92rem;
    transition: background 0.2s;
  }
  .downloads a:hover { background: #247a46; }

  #error-msg {
    display: none;
    margin-top: 16px;
    padding: 12px 16px;
    background: #3a1212;
    border: 1px solid #8b2222;
    border-radius: 6px;
    color: #f08080;
    font-size: 0.88rem;
  }

  #status-badge {
    display: inline-block;
    font-size: 0.75rem;
    padding: 2px 10px;
    border-radius: 99px;
    background: #2d2d5e;
    color: #9b8fc4;
    margin-left: 10px;
    vertical-align: middle;
  }
  #status-badge.running { background: #4a3200; color: #f5c842; }
  #status-badge.done    { background: #1a3a28; color: #58d68d; }
  #status-badge.error   { background: #3a1212; color: #f08080; }
</style>
</head>
<body>

<header>
  <h1>RFP Response Automation <span id="status-badge">idle</span></h1>
  <p>AI-powered multi-agent pipeline &mdash; SAP BTP / Accenture</p>
</header>

<div class="card">

  <!-- Upload form -->
  <div id="upload-section">
    <div class="dropzone" id="dropzone" onclick="fileInput.click()">
      <div id="drop-label">Drop DOCX / PDF / PPTX here<br><small>or click to browse</small></div>
      <input type="file" id="fileInput" accept=".docx,.pdf,.pptx" multiple>
    </div>

    <div class="fields">
      <div>
        <label for="client_name">Client Name <small>(optional override)</small></label>
        <input id="client_name" type="text" placeholder="e.g. Acme Corp">
      </div>
      <div>
        <label for="project_name">Project Name <small>(optional override)</small></label>
        <input id="project_name" type="text" placeholder="e.g. HR Digital Transformation">
      </div>
    </div>

    <div class="actions">
      <button class="btn-primary" onclick="runPipeline(false)">Run Pipeline</button>
      <button class="btn-secondary" onclick="runPipeline(true)">Use Demo RFP</button>
    </div>
  </div>

  <!-- Live log -->
  <div id="log-section">
    <h3>Pipeline log</h3>
    <pre id="log"></pre>
  </div>

  <!-- Done -->
  <div id="done-section">
    <h3>&#10003; Pipeline complete</h3>
    <div class="downloads">
      <a id="dl-xlsx" href="#" download>Download XLSX</a>
      <a id="dl-pptx" href="#" download>Download PPTX</a>
    </div>
    <div class="actions" style="margin-top:16px">
      <button class="btn-secondary" onclick="reset()">Run Again</button>
    </div>
  </div>

  <!-- Error -->
  <div id="error-msg"></div>

</div>

<script>
const fileInput  = document.getElementById('fileInput');
const dropzone   = document.getElementById('dropzone');
const dropLabel  = document.getElementById('drop-label');
const badge      = document.getElementById('status-badge');
let   eventSource = null;

// ── Drag-and-drop ────────────────────────────────────────────────────────────
dropzone.addEventListener('dragover',  e => { e.preventDefault(); dropzone.classList.add('over'); });
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('over'));
dropzone.addEventListener('drop', e => {
  e.preventDefault();
  dropzone.classList.remove('over');
  fileInput.files = e.dataTransfer.files;
  updateDropLabel();
});
fileInput.addEventListener('change', updateDropLabel);

function updateDropLabel() {
  const names = [...fileInput.files].map(f => f.name).join(', ');
  if (names) {
    dropLabel.textContent = names;
    dropzone.classList.add('has-file');
  }
}

// ── Run pipeline ─────────────────────────────────────────────────────────────
async function runPipeline(demo) {
  const fd = new FormData();
  if (demo) {
    fd.append('demo', '1');
  } else {
    if (!fileInput.files.length) { alert('Please select a file first.'); return; }
    [...fileInput.files].forEach(f => fd.append('files', f));
  }
  const client  = document.getElementById('client_name').value.trim();
  const project = document.getElementById('project_name').value.trim();
  if (client)  fd.append('client_name',  client);
  if (project) fd.append('project_name', project);

  let resp;
  try {
    resp = await fetch('/run', { method: 'POST', body: fd });
  } catch (e) {
    showError('Could not reach server: ' + e.message);
    return;
  }
  const data = await resp.json();
  if (!resp.ok) { showError(data.error || 'Unknown error'); return; }

  showRunning();
  startSSE();
}

// ── SSE streaming ─────────────────────────────────────────────────────────────
function startSSE() {
  const logEl = document.getElementById('log');
  logEl.textContent = '';
  if (eventSource) eventSource.close();
  eventSource = new EventSource('/stream');

  eventSource.onmessage = e => {
    if (e.data === '[DONE]') {
      eventSource.close();
      checkStatus();
      return;
    }
    if (e.data.trim()) {
      logEl.textContent += e.data + '\\n';
      logEl.scrollTop = logEl.scrollHeight;
    }
  };
  eventSource.onerror = () => {
    eventSource.close();
    checkStatus();
  };
}

async function checkStatus() {
  const r = await fetch('/status');
  const d = await r.json();
  if (d.status === 'done')  showDone(d.outputs);
  if (d.status === 'error') showError(d.error);
}

// ── State transitions ─────────────────────────────────────────────────────────
function showRunning() {
  document.getElementById('upload-section').style.display = 'none';
  document.getElementById('done-section').style.display   = 'none';
  document.getElementById('error-msg').style.display      = 'none';
  document.getElementById('log-section').style.display    = 'block';
  setBadge('running', 'running');
}

function showDone(outputs) {
  document.getElementById('log-section').style.display = 'block';
  document.getElementById('done-section').style.display = 'block';
  if (outputs.xlsx) document.getElementById('dl-xlsx').href = '/download/' + outputs.xlsx;
  if (outputs.pptx) document.getElementById('dl-pptx').href = '/download/' + outputs.pptx;
  setBadge('done', 'done');
}

function showError(msg) {
  const el = document.getElementById('error-msg');
  el.textContent = 'Error: ' + msg;
  el.style.display = 'block';
  document.getElementById('log-section').style.display = 'block';
  setBadge('error', 'error');
}

function reset() {
  if (eventSource) { eventSource.close(); eventSource = null; }
  document.getElementById('upload-section').style.display = 'block';
  document.getElementById('done-section').style.display   = 'none';
  document.getElementById('log-section').style.display    = 'none';
  document.getElementById('error-msg').style.display      = 'none';
  document.getElementById('log').textContent = '';
  dropLabel.innerHTML = 'Drop DOCX / PDF / PPTX here<br><small>or click to browse</small>';
  dropzone.classList.remove('has-file');
  setBadge('idle', 'idle');
  fetch('/status');  // fire-and-forget to stay in sync
}

function setBadge(text, cls) {
  badge.textContent = text;
  badge.className   = cls;
}
</script>
</body>
</html>"""


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    print(f"Starting RFP Automation UI on http://localhost:3112")
    app.run(host="0.0.0.0", port=3112, threaded=True, debug=False)
