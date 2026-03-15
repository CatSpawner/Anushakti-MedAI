document.addEventListener("DOMContentLoaded", () => {
  const notice = document.getElementById("mustLoginNotice");
  const doctorGrid = document.getElementById("doctorGrid");
  const doctorsOut = document.getElementById("adminDoctorsOut");

  const refreshBtn = document.getElementById("refreshBtn");
  const logoutBtn = document.getElementById("logoutBtn");

  const adminDoctorModal = document.getElementById("adminDoctorModal");
  const closeAdminDoctorModalBtn = document.getElementById("closeAdminDoctorModalBtn");
  const closeAdminDoctorModalBtn2 = document.getElementById("closeAdminDoctorModalBtn2");
  const adminDoctorModalSub = document.getElementById("adminDoctorModalSub");

  const docInfoBox = document.getElementById("docInfoBox");
  const doctorAppointmentsTable = document.getElementById("doctorAppointmentsTable");

  const docUpdateForm = document.getElementById("docUpdateForm");
  const docPasswordForm = document.getElementById("docPasswordForm");
  const deactivateDoctorBtn = document.getElementById("deactivateDoctorBtn");

  const reassignDoctorSelect = document.getElementById("reassignDoctorSelect");
  const reassignBtn = document.getElementById("reassignBtn");
  const reassignHint = document.getElementById("reassignHint");

  const addDoctorModal = document.getElementById("addDoctorModal");
  const closeAddDoctorModalBtn = document.getElementById("closeAddDoctorModalBtn");
  const closeAddDoctorModalBtn2 = document.getElementById("closeAddDoctorModalBtn2");
  const addDoctorForm = document.getElementById("addDoctorForm");
  const addDoctorOut = document.getElementById("addDoctorOut");
  const addDoctorBtn = document.getElementById("addDoctorBtn");

  const appointmentsOut = document.getElementById("appointmentsOut");
  const auditOut = document.getElementById("auditOut");
  const loadAppointmentsBtn = document.getElementById("loadAppointmentsBtn");
  const loadAuditBtn = document.getElementById("loadAuditBtn");

  let cachedDoctors = [];
  let openedDoctorId = null;
  let selectedAppointmentId = null;

  if (!doctorGrid) {
    alert("Admin UI Error: doctorGrid not found. Replace admin.html exactly.");
    return;
  }

  function escapeHtml(s){
    return String(s ?? "")
      .replaceAll("&","&amp;")
      .replaceAll("<","&lt;")
      .replaceAll(">","&gt;")
      .replaceAll('"',"&quot;");
  }

  function showTopError(err) {
    if (notice) {
      notice.style.display = "block";
      notice.textContent = String(err);
    }
  }
  function clearTopError() {
    if (notice) {
      notice.style.display = "none";
      notice.textContent = "";
    }
  }

  function openModal(el){ UI.openModal(el); }
  function closeModal(el){ UI.closeModal(el); }

  function renderEmpty(msg) {
    const d = document.createElement("div");
    d.className = "emptyState";
    d.textContent = msg;
    return d;
  }

  function renderDoctorCard(d) {
    const card = document.createElement("div");
    card.className = "docCard" + (d.is_active ? "" : " docInactive");
    card.innerHTML = `
      <div class="docCardTop">
        <div style="min-width:0;">
          <div class="docName">${escapeHtml(d.full_name)}</div>
          <div class="docMeta">${escapeHtml(d.department)} • @${escapeHtml(d.username)} ${d.is_active ? "" : "• INACTIVE"}</div>
        </div>
        <div class="badge ${d.is_active ? "good" : "warn"}">${d.is_active ? "Active" : "Inactive"}</div>
      </div>
      <div class="docStats">
        <div class="statPill"><div class="muted tiny">Waiting</div><b>${d.waiting_count}</b></div>
        <div class="statPill"><div class="muted tiny">Completed</div><b>${d.completed_count}</b></div>
      </div>
    `;
    card.addEventListener("click", () => openDoctor(d.doctor_id));
    return card;
  }

  function renderAddDoctorCard() {
    const card = document.createElement("div");
    card.className = "docCard addCard";
    card.textContent = "+ Add Doctor";
    card.addEventListener("click", () => {
      UI.setText(addDoctorOut, "");
      addDoctorForm.reset();
      openModal(addDoctorModal);
    });
    return card;
  }

  async function loadDoctors() {
    doctorGrid.innerHTML = "";
    if (doctorsOut) doctorsOut.style.display = "none";
    clearTopError();

    try {
      cachedDoctors = await UI.api("/admin/doctors");

      if (!Array.isArray(cachedDoctors) || cachedDoctors.length === 0) {
        doctorGrid.appendChild(renderEmpty("No doctors found. Use Add Doctor to create one."));
        doctorGrid.appendChild(renderAddDoctorCard());
        return;
      }

      for (const d of cachedDoctors) doctorGrid.appendChild(renderDoctorCard(d));
      doctorGrid.appendChild(renderAddDoctorCard());
    } catch (err) {
      showTopError(err);
      if (doctorsOut) {
        doctorsOut.style.display = "block";
        doctorsOut.textContent = "Doctors not loading. Make sure you are logged in as admin on 127.0.0.1.\n\n" + String(err);
      }
      UI.popup("error", "Doctors load failed", String(err));
    }
  }

  function setSelectedAppointment(id) {
    selectedAppointmentId = id;
    reassignBtn.disabled = !selectedAppointmentId;
    reassignHint.textContent = selectedAppointmentId ? `Selected appointment #${selectedAppointmentId}` : "No appointment selected.";
  }

  function fillReassignDoctors() {
    reassignDoctorSelect.innerHTML = "";
    for (const d of cachedDoctors.filter(x => x.is_active)) {
      const opt = document.createElement("option");
      opt.value = String(d.doctor_id);
      opt.textContent = `${d.full_name} — ${d.department}`;
      reassignDoctorSelect.appendChild(opt);
    }
  }

  function renderKVRows(rows) {
    const box = document.createElement("div");
    box.className = "kvbox";

    for (const [k, v] of rows) {
      const ke = document.createElement("div");
      ke.className = "k";
      ke.textContent = String(k);

      const ve = document.createElement("div");
      ve.className = "v";
      ve.textContent = String(v ?? "");

      box.appendChild(ke);
      box.appendChild(ve);
    }
    return box;
  }

  async function openDoctor(doctorId) {
    openedDoctorId = doctorId;
    setSelectedAppointment(null);

    try {
      const data = await UI.api(`/admin/doctors/${doctorId}`);
      const doc = data.doctor;

      adminDoctorModalSub.textContent = `${doc.full_name} • ${doc.department} • @${doc.username}`;

      docInfoBox.innerHTML = "";
      docInfoBox.appendChild(renderKVRows([
        ["Doctor ID", doc.doctor_id],
        ["Username", doc.username],
        ["Active", doc.is_active ? "Yes" : "No"],
        ["Department", doc.department],
        ["Created", UI.formatDate(doc.created_at)],
      ]));

      document.getElementById("doc_id_update").value = String(doc.doctor_id);
      document.getElementById("doc_full_name").value = doc.full_name;
      document.getElementById("doc_department").value = doc.department;

      document.getElementById("doc_id_password").value = String(doc.doctor_id);
      document.getElementById("doc_new_password").value = "";

      deactivateDoctorBtn.disabled = !doc.is_active;

      fillReassignDoctors();

      doctorAppointmentsTable.innerHTML = "";
      if (!data.appointments || data.appointments.length === 0) {
        doctorAppointmentsTable.appendChild(renderEmpty("No appointments assigned yet."));
      } else {
        const columns = [
          { label: "Appt#", key: "appointment_id" },
          { label: "Patient", key: "patient_name" },
          { label: "Status", key: "status" },
          { label: "Priority", key: "priority" },
          { label: "Severity", key: "severity" },
          { label: "Queue", key: "queue_position" },
          { label: "Wait", key: "predicted_wait_minutes", render: r => `${r.predicted_wait_minutes} min` },
          { label: "Created", key: "created_at", render: r => UI.formatDate(r.created_at) },
          { label: "Symptoms", key: "symptoms" },
        ];

        const table = UI.renderTable(columns, data.appointments);
        doctorAppointmentsTable.appendChild(table);

        const trs = Array.from(table.querySelectorAll("tbody tr"));
        trs.forEach((tr, idx) => {
          tr.addEventListener("click", () => {
            trs.forEach(x => x.classList.remove("trSelected"));
            tr.classList.add("trSelected");
            setSelectedAppointment(data.appointments[idx].appointment_id);
          });
        });
      }

      openModal(adminDoctorModal);
    } catch (err) {
      UI.popup("error", "Doctor detail failed", String(err));
    }
  }

  // Modal close
  closeAdminDoctorModalBtn?.addEventListener("click", () => closeModal(adminDoctorModal));
  closeAdminDoctorModalBtn2?.addEventListener("click", () => closeModal(adminDoctorModal));
  adminDoctorModal?.addEventListener("click", (e) => { if (e.target === adminDoctorModal) closeModal(adminDoctorModal); });

  closeAddDoctorModalBtn?.addEventListener("click", () => closeModal(addDoctorModal));
  closeAddDoctorModalBtn2?.addEventListener("click", () => closeModal(addDoctorModal));
  addDoctorModal?.addEventListener("click", (e) => { if (e.target === addDoctorModal) closeModal(addDoctorModal); });

  // Update doctor
  docUpdateForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = document.getElementById("docSaveBtn");
    btn.disabled = true;
    try {
      const id = Number(document.getElementById("doc_id_update").value);
      const payload = {
        full_name: document.getElementById("doc_full_name").value,
        department: document.getElementById("doc_department").value,
      };
      await UI.api(`/admin/doctors/${id}`, { method: "PUT", body: JSON.stringify(payload) });
      UI.popup("success", "Updated", "Doctor updated successfully.");
      await loadDoctors();
      await openDoctor(id);
    } catch (err) {
      UI.popup("error", "Update failed", String(err));
    } finally {
      btn.disabled = false;
    }
  });

  // Reset password
  docPasswordForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = document.getElementById("docPwdBtn");
    btn.disabled = true;
    try {
      const id = Number(document.getElementById("doc_id_password").value);
      const payload = { password: document.getElementById("doc_new_password").value };
      await UI.api(`/admin/doctors/${id}/password`, { method: "PUT", body: JSON.stringify(payload) });
      UI.popup("success", "Password updated", "Doctor password updated.");
      document.getElementById("doc_new_password").value = "";
    } catch (err) {
      UI.popup("error", "Password update failed", String(err));
    } finally {
      btn.disabled = false;
    }
  });

  // Deactivate doctor
  deactivateDoctorBtn.addEventListener("click", async () => {
    if (!openedDoctorId) return;
    try {
      await UI.api(`/admin/doctors/${openedDoctorId}/deactivate`, { method: "POST", body: JSON.stringify({}) });
      UI.popup("success", "Deactivated", "Doctor has been deactivated.");
      await loadDoctors();
      closeModal(adminDoctorModal);
    } catch (err) {
      UI.popup("error", "Deactivate failed", String(err));
    }
  });

  // Reassign selected appointment
  reassignBtn.addEventListener("click", async () => {
    if (!selectedAppointmentId) return;
    try {
      const newDoctorId = Number(reassignDoctorSelect.value);
      await UI.api("/admin/reassign", {
        method: "POST",
        body: JSON.stringify({ appointment_id: selectedAppointmentId, new_doctor_id: newDoctorId }),
      });
      UI.popup("success", "Reassigned", `Appointment #${selectedAppointmentId} reassigned.`);
      await loadDoctors();
      await openDoctor(openedDoctorId);
    } catch (err) {
      UI.popup("error", "Reassign failed", String(err));
    }
  });

  // Add doctor
  addDoctorForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    UI.setText(addDoctorOut, "");
    addDoctorBtn.disabled = true;

    const payload = {
      username: document.getElementById("add_username").value,
      password: document.getElementById("add_password").value,
      full_name: document.getElementById("add_full_name").value,
      department: document.getElementById("add_department").value,
    };

    try {
      await UI.api("/admin/doctors", { method: "POST", body: JSON.stringify(payload) });
      UI.popup("success", "Doctor created", `${payload.full_name} created successfully.`);
      closeModal(addDoctorModal);
      await loadDoctors();
    } catch (err) {
      UI.popup("error", "Create doctor failed", String(err));
      UI.setText(addDoctorOut, String(err));
    } finally {
      addDoctorBtn.disabled = false;
    }
  });

  // Appointments list
  loadAppointmentsBtn.addEventListener("click", async () => {
    appointmentsOut.innerHTML = "";
    try {
      const rows = await UI.api("/admin/appointments");
      if (!rows.length) { appointmentsOut.appendChild(renderEmpty("No appointments found.")); return; }

      const columns = [
        { label: "Appt#", key: "appointment_id" },
        { label: "Patient", key: "patient_name" },
        { label: "Doctor", key: "doctor_name" },
        { label: "Status", key: "status" },
        { label: "Priority", key: "priority" },
        { label: "Severity", key: "severity" },
        { label: "Dept", key: "department" },
        { label: "Created", key: "created_at", render: r => UI.formatDate(r.created_at) },
        { label: "Symptoms", key: "symptoms" },
      ];

      appointmentsOut.appendChild(UI.renderTable(columns, rows));
    } catch (err) {
      UI.popup("error", "Load appointments failed", String(err));
    }
  });

  // Simple audit log
  function auditMessage(row) {
    const a = row.action;
    const d = row.detail || {};
    if (a === "admin_create_doctor") return `Created doctor: ${d.full_name} (${d.department}) @${d.username}`;
    if (a === "admin_update_doctor") return `Updated doctor details (doctor_id=${d.doctor_id ?? ""})`;
    if (a === "admin_update_doctor_password") return `Reset doctor password (doctor_id=${d.doctor_id ?? ""})`;
    if (a === "admin_deactivate_doctor") return `Deactivated doctor: @${d.username} (doctor_id=${d.doctor_id})`;
    if (a === "admin_reassign_appointment") return `Reassigned appointment #${row.appointment_id}`;
    if (a === "doctor_update") return `Doctor updated appointment #${row.appointment_id}`;
    if (a === "doctor_complete") return `Doctor completed appointment #${row.appointment_id}`;
    if (a === "doctor_reassign") return `Doctor reassigned appointment #${row.appointment_id}`;
    return `${a} ${row.appointment_id ? `(appointment #${row.appointment_id})` : ""}`;
  }

  loadAuditBtn.addEventListener("click", async () => {
    auditOut.innerHTML = "";
    try {
      const rows = await UI.api("/admin/audit_logs");
      if (!rows.length) { auditOut.appendChild(renderEmpty("No audit logs yet.")); return; }

      for (const r of rows) {
        const item = document.createElement("div");
        item.className = "auditItem";
        item.innerHTML = `
          <div class="auditTop">
            <div>${escapeHtml(auditMessage(r))}</div>
            <div class="auditActor">${escapeHtml(r.actor)}</div>
          </div>
          <div class="auditMeta">${escapeHtml(UI.formatDate(r.created_at))}</div>
        `;
        auditOut.appendChild(item);
      }
    } catch (err) {
      UI.popup("error", "Load audit failed", String(err));
    }
  });

  refreshBtn.addEventListener("click", () => loadDoctors());

  logoutBtn.addEventListener("click", async () => {
    await UI.api("/logout", { method: "POST", body: JSON.stringify({}) }).catch(() => {});
    window.location.href = "/";
  });

  // START
  loadDoctors();
});