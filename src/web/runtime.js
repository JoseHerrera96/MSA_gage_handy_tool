let runtimePromise;
const adapters = new Map();
const wait = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));

async function initializeWithRetry() {
  let lastError;
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    try {
      return await initialize();
    } catch (error) {
      lastError = error;
      if (attempt < 3) await wait(attempt * 500);
    }
  }
  throw lastError;
}

export function getRuntime() {
  if (!runtimePromise) runtimePromise = initializeWithRetry().catch(error => { runtimePromise = undefined; throw error; });
  return runtimePromise;
}

export function loadStudy(study) {
  if (!['grr', 'paired'].includes(study)) throw new Error('Invalid study');
  if (!adapters.has(study)) {
    adapters.set(study, (async () => {
      const python = await getRuntime();
      const adapterName = study === 'grr' ? 'gage_rr' : 'paired';
      const path = `/src/web/adapters/${adapterName}.py`;
      const response = await fetch(path);
      if (!response.ok) throw new Error(`Could not load ${path}`);
      python.FS.writeFile(`/project${path}`, await response.text(), {encoding: 'utf8'});
      await python.runPythonAsync(`import json, base64, io, zipfile\n${study}_adapter = runpy.run_path('/project/src/web/adapters/${adapterName}.py')\nbrowser_examples = examples\ndef make_example_zip(data):\n    buffer = io.BytesIO()\n    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:\n        for name, text in json.loads(data).items():\n            archive.writestr(name, text)\n    return base64.b64encode(buffer.getvalue()).decode('ascii')`);
      return python;
    })().catch(error => { adapters.delete(study); throw error; }));
  }
  return adapters.get(study);
}

async function initialize() {
  const config = await (await fetch('/runtime-config.json')).json();
  const indexURL = new URL(config.indexURL, location.href).href;
  const {loadPyodide} = await import(`${indexURL}pyodide.mjs`);
  const python = await loadPyodide({indexURL});
  await python.loadPackage(['numpy', 'pandas', 'scipy', 'matplotlib']);
  const paths = ['__init__', 'calculations', 'data_parser', 'input_examples', 'paired_ttest', 'paired_visualization', 'presentation', 'study_config', 'visualization']
    .map(name => `/src/gage_tracer/${name}.py`);
  paths.push('/src/web/adapters/type1.py');
  const sources = await Promise.all(paths.map(async path => {
    const response = await fetch(path);
    if (!response.ok) throw new Error(`Could not load ${path}`);
    return [path, await response.text()];
  }));
  for (const [path, contents] of sources) {
    const destination = `/project${path}`;
    python.FS.mkdirTree(destination.slice(0, destination.lastIndexOf('/')));
    python.FS.writeFile(destination, contents, {encoding: 'utf8'});
  }
  await python.runPythonAsync("import sys, runpy; sys.path.insert(0, '/project/src'); type1_adapter = runpy.run_path('/project/src/web/adapters/type1.py'); from gage_tracer import input_examples as examples; examples = vars(examples)");
  return python;
}
