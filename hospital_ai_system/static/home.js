document.addEventListener("DOMContentLoaded", () => {
  const patientToggle = document.getElementById("patientToggle");
  const doctorToggle = document.getElementById("doctorToggle");
  const adminToggle = document.getElementById("adminToggle");
  const roleField = document.getElementById("roleField");

  const loginOut = document.getElementById("loginOut");
  const registerOut = document.getElementById("registerOut");

  const openRegisterBtn = document.getElementById("openRegisterBtn");
  const registerModal = document.getElementById("registerModal");
  const closeRegisterBtn = document.getElementById("closeRegisterBtn");
  const cancelRegisterBtn = document.getElementById("cancelRegisterBtn");

  function setActiveRole(role) {
    roleField.value = role;
    patientToggle.classList.toggle("active", role === "patient");
    doctorToggle.classList.toggle("active", role === "doctor");
    adminToggle.classList.toggle("active", role === "admin");
    openRegisterBtn.style.display = (role === "patient") ? "inline-flex" : "none";
  }

  patientToggle.addEventListener("click", () => setActiveRole("patient"));
  doctorToggle.addEventListener("click", () => setActiveRole("doctor"));
  adminToggle.addEventListener("click", () => setActiveRole("admin"));
  setActiveRole("patient");

  openRegisterBtn.addEventListener("click", () => UI.openModal(registerModal));
  closeRegisterBtn.addEventListener("click", () => UI.closeModal(registerModal));
  cancelRegisterBtn.addEventListener("click", () => UI.closeModal(registerModal));
  registerModal.addEventListener("click", (e) => { if (e.target === registerModal) UI.closeModal(registerModal); });

  document.getElementById("loginForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    UI.setText(loginOut, "");

    const btn = document.getElementById("loginBtn");
    btn.disabled = true;

    try {
      const payload = Object.fromEntries(new FormData(e.target).entries());
      const r = await UI.api("/login", { method: "POST", body: JSON.stringify(payload) });

      UI.popup("success", "Login successful", `Logged in as ${r.role}. Redirecting...`);
      setTimeout(() => {
        if (r.role === "patient") window.location.href = "/patient";
        else if (r.role === "doctor") window.location.href = "/doctor";
        else window.location.href = "/admin";
      }, 450);
    } catch (err) {
      UI.popup("error", "Login failed", String(err));
      UI.setText(loginOut, String(err));
    } finally {
      btn.disabled = false;
    }
  });

  document.getElementById("registerForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    UI.setText(registerOut, "");

    const btn = document.getElementById("registerBtn");
    btn.disabled = true;

    try {
      const payload = Object.fromEntries(new FormData(e.target).entries());
      await UI.api("/register/patient", { method: "POST", body: JSON.stringify(payload) });
      await UI.api("/login", { method: "POST", body: JSON.stringify({ username: payload.username, password: payload.password, role: "patient" }) });

      UI.closeModal(registerModal);
      UI.popup("success", "Account created", "Registration complete. Redirecting...");
      setTimeout(() => window.location.href = "/patient", 450);
    } catch (err) {
      UI.popup("error", "Registration failed", String(err));
      UI.setText(registerOut, String(err));
    } finally {
      btn.disabled = false;
    }
  });
});