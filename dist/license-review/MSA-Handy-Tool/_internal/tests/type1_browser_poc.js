import {getRuntime} from '/runtime.js';

export function mountType1(root = document, onBusyChange = () => {}) {
const element = id => root.querySelector(`#${id}`);
const fileInput = element("file");
const analyzeButton = element("analyze");
const exampleButton = element("example");
const status = element("status");
const startMarker = element("start-marker");
const endMarker = element("end-marker");
const format = () => root.querySelector('input[name="format"]:checked').value;
let python;
let ready = false;
let urls = [];
let disposed = false;
onBusyChange(true);

function setStatus(message, error = false) {
  status.textContent = message;
  status.classList.toggle("error", error);
}

function invalidate() {
  element("results").hidden = true;
  urls.forEach(url => URL.revokeObjectURL(url));
  urls = [];
  element("tsv").removeAttribute("href");
  element("html").removeAttribute("href");
  if (ready) setStatus("Ready");
  analyzeButton.disabled = !ready || !fileInput.files.length;
}

function setBusy(busy) {
  root.querySelectorAll('input[name="format"], #file, #start-marker, #end-marker').forEach(input => input.disabled = busy);
  analyzeButton.disabled = busy || !ready || !fileInput.files.length;
  exampleButton.disabled = busy || !ready;
  onBusyChange(busy);
}

function render(result) {
  const metrics = result.metrics;
  element("dimensions").textContent = metrics.dimensions;
  element("cg").textContent = metrics.mean_cg;
  element("cgk").textContent = metrics.mean_cgk;
  element("pass-rate").textContent = metrics.pass_rate;
  for (const [id, value] of [["cg-status", metrics.cg_status], ["cgk-status", metrics.cgk_status]]) {
    element(id).textContent = value;
    element(id).classList.toggle("fail", value !== "PASS");
  }
  const counts = result.observations;
  element("observations").textContent = counts.length === 1
    ? `Detected ${counts[0]} complete measurement cycles for each characteristic.`
    : `Characteristics have different observation counts: ${counts.join(", ")}. Check that each report contains the same characteristics.`;
  const passed = metrics.cg_status === "PASS" && metrics.cgk_status === "PASS";
  element("verdict").textContent = passed
    ? `Cg and Cgk both meet the industrial threshold of ${metrics.threshold.toFixed(2)}.`
    : `One or more indices fall below the minimum ${metrics.threshold.toFixed(2)} threshold.`;
  element("verdict").classList.toggle("warning", !passed);
  const head = element("summary").tHead;
  const body = element("summary").tBodies[0];
  head.replaceChildren();
  body.replaceChildren();
  const header = head.insertRow();
  result.table.columns.forEach(column => {
    const cell = document.createElement("th");
    cell.scope = "col";
    cell.textContent = column;
    header.appendChild(cell);
  });
  result.table.data.forEach(row => {
    const tableRow = body.insertRow();
    row.forEach(value => { tableRow.insertCell().textContent = value == null ? "" : String(value); });
  });
  for (const [id, contents, type] of [["tsv", result.tsv, "text/tab-separated-values"], ["html", result.html, "text/html"]]) {
    const url = URL.createObjectURL(new Blob([contents], {type: `${type};charset=utf-8`}));
    urls.push(url);
    element(id).href = url;
  }
  element("results").hidden = false;
}

root.querySelectorAll('input[name="format"]').forEach(input => input.addEventListener("change", () => {
  element("markers").hidden = format() !== "custom";
  invalidate();
}));
for (const input of [fileInput, startMarker, endMarker]) input.addEventListener("change", invalidate);
for (const input of [startMarker, endMarker]) input.addEventListener("input", invalidate);

analyzeButton.addEventListener("click", async () => {
  if (!ready || !fileInput.files.length) return;
  invalidate();
  setBusy(true);
  setStatus("Processing Type 1 Gage Study data...");
  try {
    python.globals.set("uploaded_text", await fileInput.files[0].text());
    python.globals.set("report_format", format());
    python.globals.set("start_marker", startMarker.value);
    python.globals.set("end_marker", endMarker.value);
    python.globals.set("source_name", fileInput.files[0].name);
    const result = await python.runPythonAsync("type1_adapter['browser_json'](type1_adapter['analyze_type1'](uploaded_text, report_format, start_marker, end_marker, source_name))");
    render(JSON.parse(result));
    setStatus("Analysis complete.");
  } catch (error) {
    const message = String(error.message || error).trim().split("\n").pop();
    setStatus(`Unable to process the uploaded file. ${message}`, true);
  } finally {
    for (const key of ["uploaded_text", "report_format", "start_marker", "end_marker", "source_name"]) python.globals.delete(key);
    setBusy(false);
  }
});

exampleButton.addEventListener("click", async () => {
  setBusy(true);
  try {
    python.globals.set("example_format", format());
    const example = await python.runPythonAsync("examples['build_input_examples']('type1', example_format)['type1.txt']");
    const url = URL.createObjectURL(new Blob([example], {type: "text/plain;charset=utf-8"}));
    const link = document.createElement("a");
    link.href = url;
    link.download = "type1_example.txt";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    setStatus(format() === "custom" ? "Example downloaded. Use REPORT for both markers." : "Example downloaded.");
  } catch (error) {
    setStatus(`Could not create example. ${error.message || error}`, true);
  } finally {
    python.globals.delete("example_format");
    setBusy(false);
  }
});

async function initialize() {
  try {
    python = await getRuntime();
    if (disposed) return;
    ready = true;
    setStatus("Ready");
    setBusy(false);
  } catch (error) {
    if (disposed) return;
    python = undefined;
    setStatus(`Could not initialize browser processing. ${error.message || error}`, true);
    setBusy(false);
  }
}
initialize();
return {
  hasWork: () => fileInput.files.length > 0 || !element("results").hidden,
  dispose: () => { disposed = true; invalidate(); fileInput.value = ""; ready = false; },
};
}

if (location.pathname === '/type1') mountType1();