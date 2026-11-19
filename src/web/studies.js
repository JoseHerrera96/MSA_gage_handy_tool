import {loadStudy} from '/runtime.js';

export function mountStudy(root = document, study = 'grr', onBusyChange = () => {}) {
const element = id => root.querySelector(`#${id}`);
const format = () => root.querySelector('input[name="format"]:checked').value;
const distribution = () => element("distribution").value;
const status = element("status");
const analyzeButton = element("analyze");
let python;
let ready = false;
let overview;
let disposed = false;
onBusyChange(true);

element("title").textContent = study === "grr" ? "Gage R&R (Crossed) ANOVA Analysis" : "Paired t Test for the Mean of Two Systems";
document.title = `${element("title").textContent} | MSA Handy Tool`;
element("distribution-label").hidden = study !== "grr";

function setStatus(message, error = false) {
  status.textContent = message;
  status.classList.toggle("error", error);
}

function fileInputs() { return [...element("files").querySelectorAll('input[type="file"]')]; }
function canAnalyze() { return ready && fileInputs().length > 0 && fileInputs().every(input => input.files.length === 1); }
function dropGlobal(name) { if (python.globals.has(name)) python.globals.delete(name); }
function setBusy(busy) {
  root.querySelectorAll('input, select, button').forEach(control => control.disabled = busy);
  analyzeButton.disabled = busy || !canAnalyze();
  element("example").disabled = busy || !ready;
  onBusyChange(busy);
}
function invalidate() {
  element("results").hidden = true;
  if (python && ready) dropGlobal("current_state");
  overview = undefined;
  if (ready) setStatus("Ready");
  analyzeButton.disabled = !canAnalyze();
}
function buildFiles() {
  const labels = study === "paired" ? ["System A measurements", "System B measurements"]
    : distribution() === "parts" ? Array.from({length: 10}, (_, index) => `Part ${index + 1}`)
    : distribution() === "operators" ? Array.from({length: 3}, (_, index) => `Operator ${index + 1}`)
    : ["Gage R&R data"];
  const reportHint = element("report-count-hint");
  reportHint.hidden = false;
  reportHint.textContent = study === "paired" ? "Recommended: at least 10 parts measured by both systems."
    : distribution() === "parts" ? "90 reports total (9 per part)."
    : distribution() === "operators" ? "90 reports total (30 per operator)."
    : "90 reports total.";
  const container = element("files");
  container.replaceChildren();
  labels.forEach(labelText => {
    const label = document.createElement("label");
    label.textContent = labelText;
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".txt,text/plain";
    input.setAttribute("aria-describedby", "report-count-hint");
    input.addEventListener("change", invalidate);
    label.appendChild(input);
    container.appendChild(label);
  });
  element("order-label").hidden = study !== "grr" || distribution() !== "single";
  invalidate();
}
function addMetric(label, value) {
  const item = document.createElement("div");
  item.className = "metric";
  const term = document.createElement("dt");
  term.textContent = label;
  const definition = document.createElement("dd");
  definition.textContent = String(value);
  item.append(term, definition);
  element("metrics").appendChild(item);
}
function addTable(title, data, collapsible = false) {
  const heading = document.createElement("h3");
  heading.textContent = title;
  const wrapper = document.createElement("div");
  wrapper.className = "table-wrap";
  const table = document.createElement("table");
  const header = table.createTHead().insertRow();
  data.columns.forEach(column => { const cell = document.createElement("th"); cell.scope = "col"; cell.textContent = column; header.appendChild(cell); });
  const body = table.createTBody();
  data.data.forEach(row => { const tableRow = body.insertRow(); row.forEach(value => { tableRow.insertCell().textContent = value == null ? "" : String(value); }); });
  wrapper.appendChild(table);
  if (collapsible) {
    const details = document.createElement("details");
    details.className = "data-preview";
    const summary = document.createElement("summary");
    summary.textContent = title;
    details.append(summary, wrapper);
    element("tables").appendChild(details);
  } else {
    element("tables").append(heading, wrapper);
  }
}
function download(contents, name, mime, binary = false) {
  const data = binary ? Uint8Array.from(atob(contents), character => character.charCodeAt(0)) : contents;
  const url = URL.createObjectURL(new Blob([data], {type: mime}));
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function addExport(label, exportFormat, name, mime, binary = false) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "secondary";
  button.textContent = label;
  button.addEventListener("click", async () => {
    setBusy(true);
    setStatus("Generating export...");
    try {
      python.globals.set("export_format", exportFormat);
      python.globals.set("selected_report", element("report").value);
      const contents = await python.runPythonAsync(`${study}_adapter['${study}_export'](current_state, export_format, selected_report)`);
      download(contents, name, mime, binary);
      setStatus("Export ready.");
    } catch (error) {
      setStatus(`Unable to generate export. ${String(error.message || error).trim().split("\n").pop()}`, true);
    } finally {
      dropGlobal("export_format");
      dropGlobal("selected_report");
      setBusy(false);
    }
  });
  element("exports").appendChild(button);
}
function safeReportNode(node) {
  if (node.nodeType === Node.TEXT_NODE) return document.createTextNode(node.textContent);
  if (node.nodeType !== Node.ELEMENT_NODE || ["SCRIPT", "STYLE"].includes(node.tagName)) return document.createDocumentFragment();
  const allowed = new Set(["DIV", "ARTICLE", "P", "H1", "H2", "H3", "UL", "LI", "STRONG", "EM", "TABLE", "THEAD", "TBODY", "TR", "TH", "TD", "IMG"]);
  const copy = allowed.has(node.tagName) ? document.createElement(node.tagName.toLowerCase()) : document.createDocumentFragment();
  if (node.tagName === "IMG") {
    const source = node.getAttribute("src") || "";
    if (!/^data:image\/png;base64,[A-Za-z0-9+/=]+$/.test(source)) return document.createDocumentFragment();
    copy.src = source;
    copy.alt = node.getAttribute("alt") || "Report chart";
  } else {
    for (const child of node.childNodes) copy.appendChild(safeReportNode(child));
  }
  return copy;
}
function addPairedReport(report, container) {
  const tabs = document.createElement("div");
  tabs.className = "report-tabs";
  tabs.setAttribute("role", "group");
  tabs.setAttribute("aria-label", "Paired report sections");
  const panels = [];
  for (const [id, label] of [["summary", "Summary Report"], ["diagnostic", "Diagnostic Report"], ["card", "Report Card"]]) {
    const source = report.querySelector(`section#${id}`);
    if (!source) throw new Error(`Missing ${label}.`);
    const panel = document.createElement("div");
    panel.className = "report-panel";
    for (const child of source.childNodes) panel.appendChild(safeReportNode(child));
    const tab = document.createElement("button");
    tab.type = "button";
    tab.textContent = label;
    tab.addEventListener("click", () => {
      panels.forEach(item => { item.panel.hidden = item.panel !== panel; item.tab.setAttribute("aria-pressed", String(item.panel === panel)); });
    });
    panels.push({panel, tab});
    tabs.appendChild(tab);
  }
  container.replaceChildren(tabs, ...panels.map(item => item.panel));
  panels[0].tab.click();
}
async function addChartPreview() {
  const container = element("charts");
  let chartContent = container;
  if (study === "grr") {
    const details = document.createElement("details");
    details.className = "chart-section";
    details.open = true;
    const summary = document.createElement("summary");
    summary.textContent = "Gage R&R charts";
    chartContent = document.createElement("div");
    details.append(summary, chartContent);
    container.appendChild(details);
  }
  async function generateCharts() {
    setStatus("Generating charts...");
    if (study === "grr") chartContent.textContent = "Generating charts...";
    try {
      python.globals.set("selected_report", element("report").value);
      const html = await python.runPythonAsync(`${study}_adapter['${study}_export'](current_state, 'dashboard', selected_report)`);
      const report = new DOMParser().parseFromString(html, "text/html");
      const images = [...report.querySelectorAll('img')].filter(image => /^data:image\/png;base64,[A-Za-z0-9+/=]+$/.test(image.getAttribute("src") || ""));
      if (!images.length) throw new Error("No charts found in the report.");
      if (study === "paired") {
        addPairedReport(report, container);
      } else {
        const preview = document.createElement("div");
        preview.className = "chart-preview";
        for (const [index, image] of images.entries()) {
          const figure = document.createElement("figure");
          const caption = document.createElement("figcaption");
          caption.textContent = image.getAttribute("alt") || `Chart ${index + 1}`;
          const chart = document.createElement("img");
          chart.alt = caption.textContent;
          chart.src = image.getAttribute("src");
          figure.append(caption, chart);
          preview.appendChild(figure);
        }
        chartContent.replaceChildren(preview);
      }
      setStatus("Charts ready.");
    } catch (error) {
      setStatus(`Unable to generate charts. ${String(error.message || error).trim().split("\n").pop()}`, true);
      if (study === "grr") {
        const retry = document.createElement("button");
        retry.type = "button";
        retry.className = "secondary";
        retry.textContent = "Retry charts";
        retry.addEventListener("click", async () => {
          setBusy(true);
          try { await generateCharts(); } finally { setBusy(false); }
        });
        chartContent.replaceChildren(retry);
      }
    } finally {
      dropGlobal("selected_report");
    }
  }
  if (study === "grr") {
    await generateCharts();
  } else {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "secondary";
    button.textContent = "Show full report";
    button.addEventListener("click", async () => {
      setBusy(true);
      try { await generateCharts(); } finally { setBusy(false); }
    });
    container.appendChild(button);
  }
}
async function renderReport() {
  const selected = element("report").value;
  element("metrics").replaceChildren();
  element("tables").replaceChildren();
  element("charts").replaceChildren();
  element("exports").replaceChildren();
  element("notice").hidden = true;
  if (selected === "__overview__") {
    if (study === "grr") {
      addMetric("Characteristics", overview.characteristics.length);
      for (const label of ["PASS", "MARGINAL", "FAIL"]) addMetric(label, overview.counts[label]);
      element("context").textContent = `10 parts / 3 operators / 3 trials | ${overview.reports} reports`;
    } else {
      addMetric("Characteristics", overview.characteristics.length);
      addMetric("Significant after Holm", overview.significant);
      addMetric("With diagnostic warnings", overview.warnings);
      element("context").textContent = "";
      element("notice").textContent = "Holm-adjusted p-values account for multiple characteristics. No significant difference detected is not evidence that the systems are equivalent.";
      element("notice").hidden = false;
    }
    addTable("Study overview", overview.table);
    addExport("Download study overview HTML", "overview", study === "grr" ? "Gage_RR_Study_Overview.html" : "Paired_T_Test_Study_Overview.html", "text/html;charset=utf-8");
  } else {
    python.globals.set("selected_report", selected);
    let detail;
    try { detail = JSON.parse(await python.runPythonAsync(`type1_adapter['browser_json'](${study}_adapter['${study}_detail'](current_state, selected_report))`)); }
    finally { dropGlobal("selected_report"); }
    element("context").textContent = overview.numeric ? "Numeric series" : selected;
    if (study === "grr") {
      addMetric("Total Gage R&R", `${detail.display_metrics.total_grr_pct}%`);
      addMetric("NDC", detail.metrics.ndc);
      addMetric("Study Variation", detail.display_metrics.study_variation);
      const row = overview.table.data.find(item => item[0] === selected);
      addMetric("Verdict", row[1]);
      for (const [key, title] of [["anova_table_with_interaction", "ANOVA Table With Interaction"], ["anova_table", "Final ANOVA Table"], ["variance_components", "Variance Components"], ["gage_evaluation", "Gage Evaluation"]]) addTable(title, detail.tables[key]);
      addTable("Data preview", detail.data, true);
      element("notice").textContent = `Interaction ${detail.metrics.pooled_interaction ? "pooled" : "not pooled"} (p = ${detail.display_metrics.interaction_p_value}).`;
      element("notice").hidden = false;
    } else {
      for (const [label, value] of [["Sample size", detail.metrics.N], ["Mean difference", detail.display_metrics.Mean_D], ["T-Statistic", detail.display_metrics.T_Value], ["P-Value", detail.display_metrics.P_Value]]) addMetric(label, value);
      element("notice").textContent = `95% CI: [${detail.display_metrics.CI_Lower}, ${detail.display_metrics.CI_Upper}]. Outliers: ${detail.diagnostics.Outlier_Count}; normality: ${detail.diagnostics.Normality_Status}; sample size: ${detail.diagnostics.Sample_Size_Status}. A nonsignificant result does not establish equivalence.`;
      element("notice").hidden = false;
      addTable("Paired observations preview", detail.table);
    }
    addExport("Download data", "data", study === "grr" ? "gage rr data.txt" : "paired data.txt", "text/tab-separated-values;charset=utf-8");
    addExport("Download dashboard HTML", "dashboard", study === "grr" ? "Gage_RR_Dashboard.html" : "Paired_T_Test_Dashboard.html", "text/html;charset=utf-8");
    await addChartPreview();
  }
  if (!overview.numeric) addExport("Download all reports (.zip)", "zip", study === "grr" ? "Gage_RR_HTML_Reports.zip" : "Paired_T_Test_HTML_Reports.zip", "application/zip", true);
}

root.querySelectorAll('input[name="format"]').forEach(input => input.addEventListener("change", () => { element("markers").hidden = format() !== "custom"; invalidate(); }));
element("distribution").addEventListener("change", buildFiles);
element("order").addEventListener("change", invalidate);
for (const id of ["start-marker", "end-marker"]) element(id).addEventListener("input", invalidate);
element("report").addEventListener("change", async () => { setBusy(true); try { await renderReport(); } catch (error) { setStatus(String(error), true); } finally { setBusy(false); } });

analyzeButton.addEventListener("click", async () => {
  if (!canAnalyze()) return;
  invalidate();
  setBusy(true);
  setStatus("Processing data...");
  try {
    const files = await Promise.all(fileInputs().map(async input => [input.files[0].name, await input.files[0].text()]));
    python.globals.set("upload_json", JSON.stringify(files));
    python.globals.set("report_format", format());
    python.globals.set("distribution", distribution());
    python.globals.set("report_order", element("order").value);
    python.globals.set("start_marker", element("start-marker").value);
    python.globals.set("end_marker", element("end-marker").value);
    const expression = study === "grr"
      ? "grr_adapter['analyze_grr'](uploaded_files, report_format, distribution, report_order, start_marker, end_marker)"
      : "paired_adapter['analyze_paired'](uploaded_files[0][1], uploaded_files[1][1], report_format, start_marker, end_marker, uploaded_files[0][0], uploaded_files[1][0])";
    const output = await python.runPythonAsync(`uploaded_files = json.loads(upload_json)\ncurrent_state = ${expression}\ntype1_adapter['browser_json'](${study}_adapter['${study}_overview'](current_state))`);
    overview = JSON.parse(output);
    const report = element("report");
    report.replaceChildren();
    if (!overview.numeric) report.add(new Option("Study Overview", "__overview__"));
    overview.characteristics.forEach(characteristic => report.add(new Option(overview.numeric ? "Numeric series" : characteristic, characteristic)));
    await renderReport();
    element("results").hidden = false;
    setStatus("Analysis complete.");
  } catch (error) {
    dropGlobal("current_state");
    setStatus(`Unable to process the uploaded files. ${String(error.message || error).trim().split("\n").pop()}`, true);
  } finally {
    for (const key of ["upload_json", "uploaded_files", "report_format", "distribution", "report_order", "start_marker", "end_marker"]) dropGlobal(key);
    setBusy(false);
  }
});

element("example").addEventListener("click", async () => {
  setBusy(true);
  try {
    python.globals.set("example_format", format());
    python.globals.set("example_distribution", study === "grr" ? distribution() : "single");
    python.globals.set("example_order", element("order").value);
    const example = JSON.parse(await python.runPythonAsync(`type1_adapter['browser_json'](browser_examples['build_input_examples']('${study}', example_format, example_distribution, example_order))`));
    const names = Object.keys(example);
    if (names.length === 1) download(example[names[0]], names[0], "text/plain;charset=utf-8");
    else {
      python.globals.set("example_json", JSON.stringify(example));
      const archive = await python.runPythonAsync("make_example_zip(example_json)");
      download(archive, `${study}_examples.zip`, "application/zip", true);
    }
    setStatus(format() === "custom" ? "Example ready. Use REPORT for both markers." : "Example ready.");
  } catch (error) { setStatus(`Could not create example. ${String(error.message || error).trim().split("\n").pop()}`, true); }
  finally { for (const key of ["example_format", "example_distribution", "example_order", "example_json"]) dropGlobal(key); setBusy(false); }
});

buildFiles();
async function initialize() {
  try {
    python = await loadStudy(study);
    if (disposed) return;
    ready = true;
    setStatus("Ready");
    setBusy(false);
  } catch (error) { if (!disposed) { python = undefined; setStatus(`Could not initialize browser processing. ${error.message || error}`, true); setBusy(false); } }
}
initialize();
return {
  hasWork: () => fileInputs().some(input => input.files.length > 0) || !element("results").hidden,
  dispose: () => { disposed = true; invalidate(); fileInputs().forEach(input => { input.value = ""; }); ready = false; },
};
}

if (location.pathname === '/grr' || location.pathname === '/paired') mountStudy(document, location.pathname.slice(1));