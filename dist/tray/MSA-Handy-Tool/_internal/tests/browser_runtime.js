let runtimePromise;
const adapters = new Map();

export function getRuntime() {
  if (!runtimePromise) runtimePromise = initialize().catch(error => { runtimePromise = undefined; throw error; });
  return runtimePromise;
}

export function loadStudy(study) {
  if (!['grr', 'paired'].includes(study)) throw new Error('Invalid study');
  if (!adapters.has(study)) {
    adapters.set(study, (async () => {
      const python = await getRuntime();
      const path = `/tests/${study}_browser_poc.py`;
      const response = await fetch(path);
      if (!response.ok) throw new Error(`Could not load ${path}`);
      python.FS.writeFile(`/project${path}`, await response.text(), {encoding: 'utf8'});
      await python.runPythonAsync(`import json, base64, io, zipfile\n${study}_adapter = runpy.run_path('/project/tests/${study}_browser_poc.py')\nbrowser_examples = examples\ndef make_example_zip(data):\n    buffer = io.BytesIO()\n    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:\n        for name, text in json.loads(data).items():\n            archive.writestr(name, text)\n    return base64.b64encode(buffer.getvalue()).decode('ascii')`);
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
  const paths = ['__init__', 'calculations', 'data_parser', 'paired_ttest', 'paired_visualization', 'presentation', 'study_config', 'visualization']
    .map(name => `/src/gage_tracer/${name}.py`);
  paths.push('/src/app/components/input_examples.py', '/tests/type1_browser_poc.py');
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
  await python.runPythonAsync("import sys, runpy; sys.path.insert(0, '/project/src'); type1_adapter = runpy.run_path('/project/tests/type1_browser_poc.py'); examples = runpy.run_path('/project/src/app/components/input_examples.py')");
  return python;
}