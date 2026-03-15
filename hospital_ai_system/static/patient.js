document.addEventListener("DOMContentLoaded", () => {
  const notice = document.getElementById("mustLoginNotice");
  const submitOut = document.getElementById("submitOut");
  const dashCards = document.getElementById("dashCards");
  const tip = document.getElementById("patientTip");
  const submitBtn = document.getElementById("submitBtn");

  function badgeClass(priority){
    const p = String(priority || "").toLowerCase();
    if (p === "emergency" || p === "high") return "bad";
    if (p === "medium") return "warn";
    return "good";
  }

  function renderCards(data) {
    const wrap = document.createElement("div");
    wrap.className = "cards";

    if (!data.appointments || data.appointments.length === 0) {
      const d = document.createElement("div");
      d.className = "item";
      d.style.cursor = "default";
      d.textContent = "No submissions yet.";
      wrap.appendChild(d);
      return wrap;
    }

    for (const a of data.appointments) {
      const item = document.createElement("div");
      item.className = "item";
      item.style.cursor = "default";

      const top = document.createElement("div");
      top.className = "itemTop";

      const left = document.createElement("div");
      left.innerHTML = `
        <div style="font-weight:950;">Appointment #${a.appointment_id}</div>
        <div class="muted tiny" style="margin-top:2px;">${new Date(a.created_at).toLocaleString()}</div>
      `;

      const badge = document.createElement("div");
      badge.className = `badge ${badgeClass(a.priority)}`;
      badge.textContent = `${a.status} • ${a.priority}`;

      top.appendChild(left);
      top.appendChild(badge);

      const kv = document.createElement("div");
      kv.className = "kv2";
      kv.innerHTML = `
        <div><div class="k">Department</div><div class="v">${a.department}</div></div>
        <div><div class="k">Doctor</div><div class="v">${a.assigned_doctor || "Not assigned"}</div></div>
        <div><div class="k">Queue</div><div class="v">${a.queue_position}</div></div>
        <div><div class="k">Wait</div><div class="v">${a.estimated_waiting_time_minutes} min</div></div>
        <div><div class="k">Severity</div><div class="v">${a.severity}/10</div></div>
      `;

      item.appendChild(top);
      item.appendChild(kv);
      wrap.appendChild(item);
    }
    return wrap;
  }

  async function loadDash() {
    dashCards.innerHTML = "";
    try {
      const data = await UI.api("/patient/dashboard");
      tip.textContent = data.tip || "";
      dashCards.appendChild(renderCards(data));
      notice.style.display = "none";
    } catch (err) {
      notice.style.display = "block";
      notice.textContent = String(err);
      UI.popup("error", "Dashboard error", String(err));
    }
  }

  document.getElementById("submitForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    UI.setText(submitOut, "");
    submitBtn.disabled = true;

    try {
      const payload = Object.fromEntries(new FormData(e.target).entries());
      const data = await UI.api("/patient/submit", { method: "POST", body: JSON.stringify(payload) });

      UI.popup(
        "success",
        "Submitted",
        `Assigned: ${data.assigned_doctor}\nDepartment: ${data.department}\nPriority: ${data.priority}`
      );

      if (data.ai_guidance) UI.popup("info", "AI Guidance (Demo)", data.ai_guidance);

      await loadDash();
    } catch (err) {
      UI.popup("error", "Submission failed", String(err));
      UI.setText(submitOut, String(err));
    } finally {
      submitBtn.disabled = false;
    }
  });

  document.getElementById("dashBtn").addEventListener("click", loadDash);

  document.getElementById("logoutBtn").addEventListener("click", async () => {
    await UI.api("/logout", { method: "POST", body: JSON.stringify({}) }).catch(() => {});
    window.location.href = "/";
  });

  loadDash();
});