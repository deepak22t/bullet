const $ = (id) => document.getElementById(id);

function setAnalysisState(isWorking) {
  const btn = $("analyzeBtn");
  const statusText = $("statusText");
  const status = $("status");

  if (isWorking) {
    btn.disabled = true;
    statusText.textContent = "Processing...";
    status.style.opacity = "0.5";
  } else {
    btn.disabled = false;
    statusText.textContent = "System Ready";
    status.style.opacity = "1";
  }
}

async function analyzeScript() {
  const payload = {
    title: $("title").value.trim(),
    scene: $("scene").value.trim(),
    dialogue: $("dialogue").value.trim(),
  };

  setAnalysisState(true);

  try {
    const res = await fetch("/v1/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    renderResults(data);
  } catch (error) {
    console.error("Analysis failed:", error);
  } finally {
    setAnalysisState(false);
  }
}

function renderResults(data) {
  $("emptyState").classList.add("hidden");
  $("resultsView").classList.remove("hidden");
  $("rawOutput").textContent = JSON.stringify(data, null, 2);

  // Summary
  $("summaryText").textContent = data.summary?.summary || data.summary || "No summary available.";

  // Metrics
  const score = data.engagement?.engagement_score_0_100 ?? 0;
  $("engagementScore").textContent = `${score}%`;
  
  // FIXED: Handle nested or flat tone structure
  const tone = data.emotion?.overall_tone || "Neutral";
  $("overallTone").textContent = tone;

  // Emotional Arc
  const arcTimeline = $("arcTimeline");
  arcTimeline.innerHTML = "";
  const beats = data.emotion?.arc_beats || [];

  if (beats.length === 0) {
    arcTimeline.innerHTML = '<p style="font-size: 12px; color: #555;">No narrative beats detected.</p>';
  } else {
    beats.forEach((beat) => {
      const item = document.createElement("div");
      item.className = "timeline-item";
      item.innerHTML = `
        <div class="beat-label">${beat.label}</div>
        <div class="beat-summary">${beat.summary}</div>
        <div class="beat-emotions">
          ${(beat.dominant_emotions || []).map(e => `<span class="emotion-tag">${e}</span>`).join("")}
        </div>
      `;
      arcTimeline.appendChild(item);
    });
  }

  // Factors
  const factorsList = $("factorsList");
  factorsList.innerHTML = "";
  const factors = data.engagement?.factors || [];
  
  factors.forEach((f) => {
    const div = document.createElement("div");
    div.className = "factor-item";
    div.innerHTML = `
      <div class="factor-info">
        <span>${f.name.replace(/_/g, " ")}</span>
        <span>${f.score_0_100}%</span>
      </div>
      <div class="progress-bar">
        <div class="progress-fill" style="width: ${f.score_0_100}%"></div>
      </div>
    `;
    factorsList.appendChild(div);
  });

  // Improvements
  const improvementsList = $("improvementsList");
  improvementsList.innerHTML = "";
  (data.improvements || []).forEach((imp) => {
    const card = document.createElement("div");
    card.className = "improvement-card";
    card.innerHTML = `
      <span class="category-badge">${imp.category}</span>
      <div class="improvement-suggestion">${imp.suggestion}</div>
      <div class="improvement-rationale">${imp.rationale}</div>
    `;
    improvementsList.appendChild(card);
  });

  // Cliffhanger
  const cliffData = data.engagement?.cliffhanger;
  if (cliffData && cliffData.moment) {
    $("cliffhangerCard").classList.remove("hidden");
    $("cliffhangerContent").textContent = cliffData.moment;
  } else {
    $("cliffhangerCard").classList.add("hidden");
  }

  if (window.lucide) lucide.createIcons();
}

document.addEventListener("DOMContentLoaded", () => {
  $("analyzeBtn").addEventListener("click", analyzeScript);
});
