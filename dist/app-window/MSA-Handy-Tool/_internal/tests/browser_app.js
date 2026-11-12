import {mountType1} from '/type1.js';
import {mountStudy} from '/msa.js';

const container = document.getElementById('view');
const message = document.getElementById('app-message');
const buttons = [...document.querySelectorAll('.study-navigation button')];
const studies = new Set(buttons.map(button => button.dataset.study));
let currentStudy;
let currentView;
let busy = false;

function setBusy(value) {
  busy = value;
  buttons.forEach(button => { button.disabled = value; });
}

async function showStudy(study) {
  if (!studies.has(study) || study === currentStudy || busy) return;
  if (currentView?.hasWork() && !confirm('Changing studies clears the current inputs and results. Continue?')) return;
  setBusy(true);
  message.hidden = true;
  try {
    const response = await fetch(`/${study}`);
    if (!response.ok) throw new Error('Could not load the study view.');
    const page = new DOMParser().parseFromString(await response.text(), 'text/html');
    const main = page.querySelector('main');
    const style = page.querySelector('style');
    if (!main || !style) throw new Error('Invalid study view.');
    currentView?.dispose();
    container.replaceChildren(main);
    document.getElementById('view-style').textContent = style.textContent;
    currentStudy = study;
    buttons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.study === study)));
    history.replaceState(null, '', `/app#${study}`);
    currentView = study === 'type1' ? mountType1(container, setBusy) : mountStudy(container, study, setBusy);
  } catch (error) {
    message.textContent = String(error.message || error);
    message.hidden = false;
    setBusy(false);
  }
}

buttons.forEach(button => button.addEventListener('click', () => showStudy(button.dataset.study)));
const initialStudy = location.hash.slice(1);
showStudy(studies.has(initialStudy) ? initialStudy : 'type1');