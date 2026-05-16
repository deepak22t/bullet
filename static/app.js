const $ = (id) => document.getElementById(id);

function setStatus(text) {
  const el = $("statusText");
  if (el) el.innerText = text;
}

function setStatusState(state) {
  const dot = $("statusDot");
  if (!dot) return;
  dot.classList.remove("busy", "bad");
  if (state === "busy") dot.classList.add("busy");
  if (state === "bad") dot.classList.add("bad");
}

function setLoading(isLoading) {
  const btn = $("analyzeBtn");
  const label = btn ? btn.querySelector("span") : null;

  if (isLoading) {
    btn.disabled = true;
    btn.classList.add("loading");
    if (label) label.innerText = "Analyzing...";
    setStatusState("busy");
  } else {
    btn.disabled = false;
    btn.classList.remove("loading");
    if (label) label.innerText = "Analyze";
    setStatusState("ok");
  }
}

function simulateProgress() {
  const steps = [
    "Analyzing emotion...",
    "Evaluating engagement...",
    "Generating suggestions...",
    "Finalizing results..."
  ];

  let i = 0;

  const interval = setInterval(() => {
    if (i < steps.length) {
      setStatus(steps[i]);
      i++;
    } else {
      clearInterval(interval);
    }
  }, 1200);

  return interval;
}

let lastData = null;

function displayResult(data) {
  lastData = data;
  const empty = $("emptyState");
  const view = $("resultsView");
  if (empty) empty.classList.add("hidden");
  if (view) view.classList.remove("hidden");

  const summaryEl = $("summaryText");
  if (summaryEl) summaryEl.innerText = data.summary || "";

  const s = Number(data?.engagement?.engagement_score_0_100 ?? 0);

  const toneEl = $("overallTone");
  if (toneEl) toneEl.innerText = data?.emotion?.overall_tone || "-";

  const chips = $("dominantEmotions");
  if (chips) {
    const emotions = data?.emotion?.dominant_emotions || [];
    chips.innerHTML = emotions.slice(0, 10).map((e) => `<span class="chip">${escapeHtml(e)}</span>`).join("");
  }

  const arc = $("arcTimeline");
  if (arc) {
    const beats = data?.emotion?.arc_beats || [];
    arc.innerHTML = beats.map((b) => {
      const tags = (b.dominant_emotions || []).slice(0, 6).map((e) => `<span class="chip">${escapeHtml(e)}</span>`).join("");
      const transition = b.transition ? `<div class="beat-trans">${escapeHtml(b.transition)}</div>` : "";
      return `
        <div class="beat">
          <div class="beat-label">${escapeHtml(b.label || "")}</div>
          <div class="beat-summary">${escapeHtml(b.summary || "")}</div>
          ${transition}
          <div class="beat-tags">${tags}</div>
        </div>
      `;
    }).join("");
  }

  const factorsList = $("factorsList");
  if (factorsList) {
    // Dynamic Factors mapping for the list view
    const factors = data?.engagement?.factors || [];
    factorsList.innerHTML = factors.map((f) => {
      const score = Number(f.score_0_100 ?? 0);
      const pct = Math.max(0, Math.min(100, score));
      return `
        <div class="row">
          <div class="row-top">
            <div class="row-name">${escapeHtml(humanizeFactorName(f.name || ""))}</div>
            <div class="row-score">${pct}%</div>
          </div>
          <div class="row-bar"><div class="row-fill" style="width:${pct}%"></div></div>
          <div class="row-text">${escapeHtml(f.rationale || "")}</div>
        </div>
      `;
    }).join("");
  }

  const cliffCard = $("cliffhangerCard");
  const cliffContent = $("cliffhangerContent");
  const cliff = data?.engagement?.cliffhanger || null;
  if (cliffCard && cliffContent) {
    if (cliff && (cliff.moment || cliff.why_it_works)) {
      cliffCard.classList.remove("hidden");
      cliffContent.innerHTML = `
        <div><b>Moment:</b> ${escapeHtml(cliff.moment || "")}</div><br/>
        <div><b>Why it works:</b> ${escapeHtml(cliff.why_it_works || "")}</div>
      `;
    } else {
      cliffCard.classList.add("hidden");
      cliffContent.innerHTML = "";
    }
  }

  const improvementsList = $("improvementsList");
  if (improvementsList) {
    const items = data?.improvements || [];
    improvementsList.innerHTML = items.map((i) => `
      <div class="imp">
        <div class="imp-cat">${escapeHtml(i.category || "")}</div>
        <div class="imp-sug">${escapeHtml(i.suggestion || "")}</div>
        <div class="imp-rat">${escapeHtml(i.rationale || "")}</div>
      </div>
    `).join("");
  }

  const raw = $("rawOutput");
  if (raw) raw.innerText = JSON.stringify(data, null, 2);

  renderCharts(data);
}

function showError(err) {
  setStatus("Something went wrong");
  setStatusState("bad");
  console.error(err);
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function humanizeFactorName(name) {
  const n = String(name || "").replaceAll("_", " ").trim();
  if (!n) return "";
  // Capitalize every word for a premium UI look (e.g. "Mystery Hook" instead of "Mystery hook")
  return n.split(" ").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
}

function fitCanvas(canvas) {
  const ratio = window.devicePixelRatio || 1;
  const cssW = Math.max(1, Math.floor(canvas.clientWidth));
  const cssH = Math.max(1, Math.floor(canvas.clientHeight));
  const pxW = Math.floor(cssW * ratio);
  const pxH = Math.floor(cssH * ratio);
  if (canvas.width !== pxW || canvas.height !== pxH) {
    canvas.width = pxW;
    canvas.height = pxH;
  }
  return ratio;
}

function clearCanvas(ctx, canvas) {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
}

function drawGauge(canvas, value) {
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const ratio = fitCanvas(canvas);
  clearCanvas(ctx, canvas);

  const w = canvas.width;
  const h = canvas.height;
  const cx = w / 2;
  const start = Math.PI;
  const end = 2 * Math.PI;
  const pct = Math.max(0, Math.min(100, value)) / 100;

  ctx.lineCap = "round";
  const lw = 12 * ratio;
  ctx.lineWidth = lw;

  const pad = lw / 2 + 10 * ratio;
  const labelH = 30 * ratio;
  const arcH = Math.max(0, h - pad * 2 - labelH);
  const r = Math.max(0, Math.min((w - pad * 2) / 2, arcH));
  const cy = pad + (arcH + r) / 2;
  const labelY = pad + arcH + labelH / 2;

  ctx.strokeStyle = "rgba(255,255,255,0.10)";
  ctx.beginPath();
  ctx.arc(cx, cy, r, start, end);
  ctx.stroke();

  const grad = ctx.createLinearGradient(cx - r, cy, cx + r, cy);
  grad.addColorStop(0, "#6d5efc");
  grad.addColorStop(1, "#22c55e");
  ctx.strokeStyle = grad;
  ctx.beginPath();
  ctx.arc(cx, cy, r, start, start + (end - start) * pct);
  ctx.stroke();

  const percentText = `${Math.round(value)}%`;
  const suffixText = " score";

  ctx.textAlign = "left";
  ctx.textBaseline = "middle";

  ctx.font = `${18 * ratio}px ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif`;
  const percentW = ctx.measureText(percentText).width;

  ctx.font = `${12 * ratio}px ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif`;
  const suffixW = ctx.measureText(suffixText).width;

  const x0 = cx - (percentW + suffixW) / 2;

  ctx.fillStyle = "rgba(255,255,255,0.92)";
  ctx.font = `${18 * ratio}px ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif`;
  ctx.fillText(percentText, x0, labelY);

  ctx.fillStyle = "rgba(255,255,255,0.62)";
  ctx.font = `${12 * ratio}px ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif`;
  ctx.fillText(suffixText, x0 + percentW, labelY);
}

function drawBarChart(canvas, labels, values, barWidthRatio = 0.58) {
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const ratio = fitCanvas(canvas);
  clearCanvas(ctx, canvas);

  const w = canvas.width;
  const h = canvas.height;
  const padX = 14 * ratio;
  const padY = 14 * ratio;
  const chartH = h - padY * 2 - 40 * ratio;
  const chartW = w - padX * 2;

  const maxVal = 100;
  const n = Math.max(1, values.length);
  const slot = chartW / n;
  const barW = Math.max(10 * ratio, slot * barWidthRatio);
  // gap calculation can just be based on slot & barW

  ctx.fillStyle = "rgba(255,255,255,0.10)";
  for (let i = 0; i <= 4; i++) {
    const y = padY + (chartH * i) / 4;
    ctx.fillRect(padX, y, chartW, 1 * ratio);
  }

  ctx.fillStyle = "rgba(96,165,250,0.85)";

  for (let i = 0; i < n; i++) {
    const v = Math.max(0, Math.min(maxVal, Number(values[i] ?? 0)));
    const x = padX + i * slot + (slot - barW) / 2;
    const bh = (v / maxVal) * chartH;
    const y = padY + chartH - bh;
    roundTopRect(ctx, x, y, barW, bh, 10 * ratio);
    ctx.fill();
  }

  ctx.fillStyle = "rgba(255,255,255,0.60)";
  ctx.font = `${11 * ratio}px ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  for (let i = 0; i < n; i++) {
    const x = padX + i * slot + slot / 2;
    const label = String(labels[i] ?? "");
    drawWrappedCenteredText(
      ctx,
      label,
      x,
      padY + chartH + 8 * ratio,
      Math.max(40 * ratio, slot),
      12 * ratio,
      2
    );
  }
}

function drawWrappedCenteredText(ctx, text, cx, y, maxWidth, lineHeight, maxLines) {
  const words = String(text || "").split(/\s+/).filter(Boolean);
  if (!words.length) return;

  const lines = [];
  let line = "";
  for (const w of words) {
    const test = line ? `${line} ${w}` : w;
    if (ctx.measureText(test).width <= maxWidth || !line) {
      line = test;
    } else {
      lines.push(line);
      line = w;
    }
    if (lines.length >= maxLines) break;
  }
  if (lines.length < maxLines && line) lines.push(line);

  for (let i = 0; i < Math.min(lines.length, maxLines); i++) {
    ctx.fillText(lines[i], cx, y + i * lineHeight);
  }
}

function beatIntensity(beat, index) {
  const v = beat?.intensity_0_100;
  if (typeof v === "number" && Number.isFinite(v)) {
    return Math.max(0, Math.min(100, Math.round(v)));
  }

  const emoCount = Array.isArray(beat?.dominant_emotions) ? beat.dominant_emotions.length : 0;
  const t = String(beat?.transition || "").toLowerCase();
  let score = 35 + emoCount * 10 + index * 3;

  const up = ["reveal", "truth", "shock", "twist", "confess", "accident", "realize", "turn", "confront"];
  const down = ["calm", "relief", "resolve", "accept", "quiet"];
  for (const k of up) if (t.includes(k)) score += 12;
  for (const k of down) if (t.includes(k)) score -= 8;

  return Math.max(0, Math.min(100, Math.round(score)));
}

function drawArcChart(canvas, beats) {
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const ratio = fitCanvas(canvas);
  clearCanvas(ctx, canvas);

  const w = canvas.width;
  const h = canvas.height;
  const left = 16 * ratio;
  const right = 12 * ratio;
  const top = 12 * ratio;
  const bottom = 24 * ratio;
  const cw = Math.max(1, w - left - right);
  const ch = Math.max(1, h - top - bottom);

  const pts = (Array.isArray(beats) ? beats : []).map((b, i) => ({
    label: String(b?.label || `Beat ${i + 1}`),
    value: beatIntensity(b, i),
  }));

  if (!pts.length) return;

  ctx.fillStyle = "rgba(255,255,255,0.10)";
  for (let i = 0; i <= 4; i++) {
    const y = top + (ch * i) / 4;
    ctx.fillRect(left, y, cw, 1 * ratio);
  }

  const n = pts.length;
  const step = n > 1 ? cw / (n - 1) : 0;
  const xy = pts.map((p, i) => {
    const x = left + step * i;
    const y = top + ch * (1 - p.value / 100);
    return { ...p, x, y };
  });

  const areaGrad = ctx.createLinearGradient(0, top, 0, top + ch);
  areaGrad.addColorStop(0, "rgba(109,94,252,0.22)");
  areaGrad.addColorStop(1, "rgba(109,94,252,0.00)");
  ctx.fillStyle = areaGrad;
  ctx.beginPath();
  ctx.moveTo(xy[0].x, top + ch);
  for (const p of xy) ctx.lineTo(p.x, p.y);
  ctx.lineTo(xy[xy.length - 1].x, top + ch);
  ctx.closePath();
  ctx.fill();

  const lineGrad = ctx.createLinearGradient(left, 0, left + cw, 0);
  lineGrad.addColorStop(0, "#6d5efc");
  lineGrad.addColorStop(1, "#22c55e");
  ctx.strokeStyle = lineGrad;
  ctx.lineWidth = 3 * ratio;
  ctx.lineJoin = "round";
  ctx.lineCap = "round";
  ctx.beginPath();
  ctx.moveTo(xy[0].x, xy[0].y);
  for (let i = 1; i < xy.length; i++) ctx.lineTo(xy[i].x, xy[i].y);
  ctx.stroke();

  ctx.fillStyle = "rgba(255,255,255,0.9)";
  for (const p of xy) {
    ctx.beginPath();
    ctx.arc(p.x, p.y, 4 * ratio, 0, Math.PI * 2);
    ctx.fill();
  }

  ctx.fillStyle = "rgba(255,255,255,0.60)";
  ctx.font = `${11 * ratio}px ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  for (let i = 0; i < xy.length; i++) {
    const lab = shortLabel(xy[i].label);
    ctx.fillText(lab, xy[i].x, top + ch + 8 * ratio);
  }
}

function roundRect(ctx, x, y, w, h, r) {
  const rr = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + rr, y);
  ctx.lineTo(x + w - rr, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + rr);
  ctx.lineTo(x + w, y + h - rr);
  ctx.quadraticCurveTo(x + w, y + h, x + w - rr, y + h);
  ctx.lineTo(x + rr, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - rr);
  ctx.lineTo(x, y + rr);
  ctx.quadraticCurveTo(x, y, x + rr, y);
  ctx.closePath();
}

function roundTopRect(ctx, x, y, w, h, r) {
  const rr = Math.min(r, w / 2, h);
  ctx.beginPath();
  ctx.moveTo(x, y + rr);
  ctx.quadraticCurveTo(x, y, x + rr, y);
  ctx.lineTo(x + w - rr, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + rr);
  ctx.lineTo(x + w, y + h);
  ctx.lineTo(x, y + h);
  ctx.closePath();
}

function buildEmotionCounts(data) {
  const counts = new Map();
  const d1 = data?.emotion?.dominant_emotions || [];
  for (const e of d1) counts.set(e, (counts.get(e) || 0) + 2);

  const beats = data?.emotion?.arc_beats || [];
  for (const b of beats) {
    for (const e of (b.dominant_emotions || [])) counts.set(e, (counts.get(e) || 0) + 1);
  }
  const arr = Array.from(counts.entries()).sort((a, b) => b[1] - a[1]).slice(0, 6);
  return { labels: arr.map((x) => x[0]), values: arr.map((x) => x[1] * 15) };
}

function renderCharts(data) {
  const gauge = $("engagementGauge");
  const score = Number(data?.engagement?.engagement_score_0_100 ?? 0);
  drawGauge(gauge, score);

  // Dynamic factors logic (supports 3, 4, 5+ factors easily)
  const factors = data?.engagement?.factors || [];
  const fLabels = factors.slice(0, 6).map((f) => humanizeFactorName(f.name || "")); // Slice up to 6 just to fit canvas safely
  const fValues = factors.slice(0, 6).map((f) => Number(f.score_0_100 ?? 0));
  drawBarChart($("factorsChart"), fLabels, fValues);

  const emo = buildEmotionCounts(data);
  drawBarChart(
    $("emotionChart"),
    emo.labels.map(shortLabel),
    emo.values.map((v) => Math.min(100, v)),
    0.72
  );

  drawArcChart($("arcChart"), data?.emotion?.arc_beats || []);
}

function shortLabel(s) {
  const x = String(s || "").trim();
  if (x.length <= 10) return x;
  return x.slice(0, 9) + "…";
}

async function analyze() {
  setLoading(true);

  const progressInterval = simulateProgress();

  const payload = {
    input_text: $("inputText").value
  };

  try {
    const res = await fetch("/v1/analyze", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      throw new Error("API request failed");
    }

    const data = await res.json();

    clearInterval(progressInterval);
    setStatus("Done");
    setStatusState("ok");

    displayResult(data);

  } catch (err) {
    clearInterval(progressInterval);
    showError(err);
  }

  setLoading(false);
}

document.addEventListener("DOMContentLoaded", () => {
  const btn = $("analyzeBtn");
  if (btn) btn.addEventListener("click", analyze);
  const input = $("inputText");
  if (input) {
    input.addEventListener("keydown", (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") analyze();
    });
  }

  window.addEventListener("resize", () => {
    if (lastData) renderCharts(lastData);
  });
});