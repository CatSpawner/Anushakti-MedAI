document.addEventListener("DOMContentLoaded", () => {
  const dashCards = document.getElementById("dashCards");
  const notice = document.getElementById("mustLoginNotice");

  const modal = document.getElementById("patientModal");
  const closeBtn = document.getElementById("closePatientModalBtn");
  const closeBtn2 = document.getElementById("closePatientModalBtn2");
  const patientDetailOut = document.getElementById("patientDetailOut");
  const patientModalSub = document.getElementById("patientModalSub");

  const updateOut = document.getElementById("updateOut");
  const completeCheckbox = document.getElementById("completeCheckbox");

  const mrDoctorSelect = document.getElementById("mr_doctor_id");
  const manualReassignOut = document.getElementById("manualReassignOut");

  let cachedDoctors = [];

  function openModal() { UI.openModal(modal); }
  function closeModal() { UI.closeModal(modal); }
  closeBtn.addEventListener("click", closeModal);
  closeBtn2.addEventListener("click", closeModal);
  modal.addEventListener("click", (e) => { if (e.target === modal) closeModal(); });

  async function loadDoctorListOnce() {
    if (cachedDoctors.length) return;
    cachedDoctors = await UI.api("/doctor/doctors");
  }

  function badgeClass(priority){
    const p = String(priority || "").toLowerCase();
    if (p === "emergency" || p === "high") return "bad";
    if (p === "medium") return "warn";
    return "good";
  }

  function renderCards(data) {
    const wrap = document.createElement("div");
    wrap.className = "cards";

    if (!data.assigned_patients || data.assigned_patients.length === 0) {
      const d = document.createElement("div");
      d.className = "item";
      d.style.cursor = "default";
      d.textContent = "No waiting patients assigned.";
      wrap.appendChild(d);
      return wrap;
    }

    for (const a of data.assigned_patients) {
      const item = document.createElement("div");
      item.className = "item";
      item.addEventListener("click", () => openAppointment(a.appointment_id));

      const top = document.createElement("div");
      top.className = "itemTop";

      const left = document.createElement("div");
      left.innerHTML = `
        <div style="font-weight:950;">#${a.appointment_id} • ${a.patient_name}</div>
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
        <div><div class="k">Queue</div><div class="v">${a.queue_position}</div></div>
        <div><div class="k">Wait</div><div class="v">${a.predicted_wait_minutes} min</div></div>
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
      const data = await UI.api("/doctor/dashboard");
      dashCards.appendChild(renderCards(data));
      notice.style.display = "none";
    } catch (err) {
      notice.style.display = "block";
      notice.textContent = String(err);
      UI.popup("error", "Doctor dashboard error", String(err));
    }
  }

  function populateDoctorList(selectedDoctorName) {
    mrDoctorSelect.innerHTML = "";
    for (const d of cachedDoctors) {
      const opt = document.createElement("option");
      opt.value = String(d.id);
      opt.textContent = `${d.full_name} — ${d.department}`;
      if (selectedDoctorName && d.full_name === selectedDoctorName) opt.selected = true;
      mrDoctorSelect.appendChild(opt);
    }
  }

  async function openAppointment(appointmentId) {
    UI.setText(patientDetailOut, "");
    UI.setText(updateOut, "");
    UI.setText(manualReassignOut, "");
    completeCheckbox.checked = false;

    try {
      await loadDoctorListOnce();
      const d = await UI.api(`/doctor/appointments/${appointmentId}`);

      patientModalSub.textContent = `Appointment #${d.appointment_id} • ${d.patient_name}`;
      UI.setText(patientDetailOut, `Symptoms:\n\n${d.symptoms}`);

      document.getElementById("upd_appointment_id").value = String(d.appointment_id);
      document.getElementById("upd_department").value = d.department;
      document.getElementById("upd_queue_position").value = String(d.queue_position);
      document.getElementById("upd_predicted_wait_minutes").value = String(d.predicted_wait_minutes);
      document.getElementById("upd_severity").value = String(d.severity);
      document.getElementById("upd_priority").value = String(d.priority);

      document.getElementById("mr_appointment_id").value = String(d.appointment_id);
      populateDoctorList(d.assigned_doctor || "");

      openModal();
    } catch (err) {
      UI.popup("error", "Cannot open appointment", String(err));
    }
  }

  document.getElementById("updateApptForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    UI.setText(updateOut, "");
    const saveBtn = document.getElementById("saveBtn");
    saveBtn.disabled = true;

    try {
      const apptId = Number(document.getElementById("upd_appointment_id").value);
      const payload = {
        department: document.getElementById("upd_department").value,
        queue_position: Number(document.getElementById("upd_queue_position").value),
        predicted_wait_minutes: Number(document.getElementById("upd_predicted_wait_minutes").value),
        severity: Number(document.getElementById("upd_severity").value),
        priority: document.getElementById("upd_priority").value
      };

      await UI.api(`/doctor/appointments/${apptId}`, { method: "PUT", body: JSON.stringify(payload) });

      if (completeCheckbox.checked) {
        await UI.api(`/doctor/appointments/${apptId}/complete`, {
          method: "POST",
          body: JSON.stringify({ completed: true })
        });
      }

      UI.popup("success", "Saved", "Appointment updated successfully.");
      await loadDash();
    } catch (err) {
      UI.popup("error", "Update failed", String(err));
      UI.setText(updateOut, String(err));
    } finally {
      saveBtn.disabled = false;
    }
  });

  document.getElementById("manualReassignForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    UI.setText(manualReassignOut, "");
    try {
      const apptId = Number(document.getElementById("mr_appointment_id").value);
      const doctorId = Number(document.getElementById("mr_doctor_id").value);

      const r = await UI.api(`/doctor/appointments/${apptId}/manual_reassign`, {
        method: "POST",
        body: JSON.stringify({ doctor_id: doctorId })
      });

      UI.setText(manualReassignOut, `Reassigned to: ${r.new_doctor} (${r.department})`);
      UI.popup("success", "Reassigned", "Appointment reassigned successfully.");
      await loadDash();
    } catch (err) {
      UI.popup("error", "Reassign failed", String(err));
      UI.setText(manualReassignOut, String(err));
    }
  });

  document.getElementById("dashBtn").addEventListener("click", loadDash);

  document.getElementById("logoutBtn").addEventListener("click", async () => {
    await UI.api("/logout", { method: "POST", body: JSON.stringify({}) }).catch(() => {});
    window.location.href = "/";
  });

  loadDash();
});