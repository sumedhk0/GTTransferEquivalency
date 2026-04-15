const MAX_ROWS = 500;

const els = {
  q: document.getElementById("q"),
  state: document.getElementById("state"),
  cc: document.getElementById("cc"),
  status: document.getElementById("status"),
  tbody: document.querySelector("#results tbody"),
  updated: document.getElementById("updated"),
};

let rows = [];

function flatten(data) {
  const out = [];
  for (const s of data.schools) {
    for (const c of s.courses) {
      out.push({
        school: s.name,
        state: s.state || "",
        is_cc: s.is_community_college === true,
        ext_course: `${c.ext_subj} ${c.ext_num}`,
        ext_title: c.ext_title,
        gt_course: `${c.gt_subj} ${c.gt_num}`,
        gt_credits: c.gt_credits,
        _hay: (
          s.name + " " +
          (c.ext_subj + c.ext_num) + " " +
          (c.ext_subj + " " + c.ext_num) + " " +
          c.ext_title + " " +
          (c.gt_subj + c.gt_num) + " " +
          (c.gt_subj + " " + c.gt_num)
        ).toLowerCase(),
      });
    }
  }
  return out;
}

function populateStates() {
  const states = [...new Set(rows.map(r => r.state).filter(Boolean))].sort();
  for (const s of states) {
    const opt = document.createElement("option");
    opt.value = s;
    opt.textContent = s;
    els.state.appendChild(opt);
  }
}

function render() {
  const qRaw = els.q.value.trim().toLowerCase();
  const q = qRaw.replace(/\s+/g, " ");
  const state = els.state.value;
  const ccOnly = els.cc.checked;

  let matched = 0;
  const out = [];
  for (const r of rows) {
    if (state && r.state !== state) continue;
    if (ccOnly && !r.is_cc) continue;
    if (q && !r._hay.includes(q)) continue;
    matched++;
    if (out.length < MAX_ROWS) out.push(r);
  }

  els.tbody.innerHTML = out.map(r => `
    <tr>
      <td>${esc(r.school)}</td>
      <td>${esc(r.state)}</td>
      <td>${esc(r.ext_course)}</td>
      <td>${esc(r.ext_title)}</td>
      <td>${esc(r.gt_course)}</td>
      <td class="num">${esc(r.gt_credits)}</td>
    </tr>`).join("");

  if (matched === 0) {
    els.status.textContent = "No matches.";
  } else if (matched > MAX_ROWS) {
    els.status.textContent = `Showing ${MAX_ROWS} of ${matched.toLocaleString()} matches — narrow your search.`;
  } else {
    els.status.textContent = `${matched.toLocaleString()} match${matched === 1 ? "" : "es"}.`;
  }
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}

function debounce(fn, ms) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

async function main() {
  try {
    const resp = await fetch("data.json", { cache: "no-cache" });
    const data = await resp.json();
    rows = flatten(data);
    populateStates();
    if (data.generated_at) {
      els.updated.textContent = `Last updated ${new Date(data.generated_at).toLocaleString()}`;
    } else {
      els.updated.textContent = "Awaiting first nightly refresh";
    }
    els.q.addEventListener("input", debounce(render, 150));
    els.state.addEventListener("change", render);
    els.cc.addEventListener("change", render);
    render();
  } catch (e) {
    els.status.textContent = `Failed to load data: ${e.message}`;
  }
}

main();
