// ══════════════════════════════════════════════════════════════
//  CONFIGURACIÓN — Cambia esta URL cuando subas el backend
// ══════════════════════════════════════════════════════════════
const API_BASE_URL = "http://localhost:8000/v1";  // Puerto de FastAPI/Uvicorn

// ── Estado global de la sesión ────────────────────────────────
let userState = {
    token: null,
    name: "Invitado",
    email: "",
    wallet: 0.00,
    traction: 0.00,
    coursesCompleted: 0,
    tasksCompleted: 0,
    jobsCompleted: 0,
    payoutMethod: "mobile_money",
    payoutDetail: "",
    linkedin: "",
    portfolio: "",
    skills: ["IA Operativa", "Soporte Digital", "Redacción SEO"],
    history: [],
};

// ══════════════════════════════════════════════════════════════
//  UTILIDADES
// ══════════════════════════════════════════════════════════════

/** Llama a la API con el token JWT en el header */
async function apiFetch(endpoint, options = {}) {
    const headers = { "Content-Type": "application/json", ...options.headers };
    if (userState.token) {
        headers["Authorization"] = `Bearer ${userState.token}`;
    }
    const response = await fetch(`${API_BASE_URL}${endpoint}`, { ...options, headers });
    if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: "Error desconocido" }));

        // FastAPI devuelve errores de validación (422) como una lista de objetos
        if (Array.isArray(err.detail)) {
            const messages = err.detail.map(d => {
                const field = d.loc?.[d.loc.length - 1] || "campo";
                return `${field}: ${d.msg}`;
            });
            throw new Error(messages.join(" | "));
        }

        throw new Error(err.detail || "Error en la solicitud");
    }
    return response.json();
}

/** Muestra un mensaje de error sin alert() */
function showError(message) {
    console.error(message);
    alert(`❌ ${message}`);
}

// ══════════════════════════════════════════════════════════════
//  NAVEGACIÓN (SPA)
// ══════════════════════════════════════════════════════════════
function switchView(viewId) {
    document.querySelectorAll("main > section").forEach(s => s.classList.add("hidden"));
    document.getElementById(viewId).classList.remove("hidden");

    const nav = document.getElementById("main-nav");
    if (viewId === "view-login" || viewId === "view-register") {
        nav.classList.add("hidden");
    } else {
        nav.classList.remove("hidden");
    }

    // Cargar datos del hardware al entrar a esa vista
    if (viewId === "view-hardware") loadHardwareProgress();

    window.scrollTo(0, 0);
}

// ══════════════════════════════════════════════════════════════
//  AUTENTICACIÓN
// ══════════════════════════════════════════════════════════════

/** REGISTRO */
document.getElementById("registerForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const name     = document.getElementById("reg-name").value;
    const email    = document.getElementById("reg-email").value;
    const password = document.getElementById("reg-password").value;

    try {
        await apiFetch("/auth/register", {
            method: "POST",
            body: JSON.stringify({ name, email, password }),
        });
        alert("✅ ¡Cuenta creada con éxito! Ahora inicia sesión.");
        document.getElementById("registerForm").reset();
        switchView("view-login");
    } catch (error) {
        showError(error.message);
    }
});

/** LOGIN */
document.getElementById("loginForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const email    = document.getElementById("login-email").value;
    const password = document.getElementById("login-password").value;

    try {
        // FastAPI espera form-data en el endpoint de login con OAuth2
        const formData = new URLSearchParams();
        formData.append("username", email);
        formData.append("password", password);

        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: formData,
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "Credenciales inválidas");
        }

        const data = await response.json();

        // Guardar token y datos del usuario en el estado
        userState.token            = data.access_token;
        userState.name             = data.user.name;
        userState.email            = data.user.email;
        userState.wallet           = data.user.total_earnings || 0;
        userState.coursesCompleted = data.user.completed_modules?.length || 0;

        // Actualizar UI
        document.getElementById("user-wallet").textContent = `$${userState.wallet.toFixed(2)}`;
        document.getElementById("hub-username").textContent = userState.name.split(" ")[0];
        document.getElementById("loginForm").reset();
        switchView("view-hub");

    } catch (error) {
        showError(error.message);
    }
});

/** CERRAR SESIÓN */
function logout() {
    userState = {
        token: null, name: "Invitado", email: "", wallet: 0.00,
        traction: 0.00, coursesCompleted: 0, tasksCompleted: 0,
        jobsCompleted: 0, payoutMethod: "mobile_money", payoutDetail: "",
        linkedin: "", portfolio: "", skills: [], history: [],
    };
    document.getElementById("user-wallet").textContent = "$0.00";
    switchView("view-login");
}

// ══════════════════════════════════════════════════════════════
//  MICRO-TAREAS
// ══════════════════════════════════════════════════════════════
document.getElementById("taskForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const reward = 0.50;

    try {
        // Enviar a la API
        await apiFetch("/tasks/submit", { method: "POST", body: JSON.stringify({
            submission_url: "https://tarea-completada.local",
            submission_notes: document.querySelector('input[name="evaluation"]:checked')?.value,
        })});
    } catch (_) {
        // Si el backend no está conectado, simula localmente
        console.warn("Simulando tarea local");
    }

    // Actualizar estado local
    userState.wallet       += reward;
    userState.traction     += reward;
    userState.tasksCompleted += 1;

    const timeString = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    userState.history.unshift({ title: "Validar respuesta de Chatbot", date: `Hoy, ${timeString}`, amount: reward });

    // Actualizar UI
    document.getElementById("user-wallet").textContent = `$${userState.wallet.toFixed(2)}`;
    alert("✅ ¡Tarea enviada! Pago sumado a tu balance.");
    document.getElementById("taskForm").reset();
    switchView("view-hub");
});

// ══════════════════════════════════════════════════════════════
//  HARDWARE — Carga el progreso real desde la API
// ══════════════════════════════════════════════════════════════
async function loadHardwareProgress() {
    const GOAL = 50.00;
    let earned = userState.wallet;
    let percentage = Math.min((earned / GOAL) * 100, 100);

    try {
        // Intentar cargar desde el backend real
        const data = await apiFetch("/payments/my-earnings");
        earned     = data.total_earned;
        percentage = data.hardware_progress.percentage;
    } catch (_) {
        // Si falla, usa el estado local
    }

    document.getElementById("traction-text").textContent =
        `Progreso: $${earned.toFixed(2)} / $${GOAL.toFixed(2)}`;
    document.getElementById("traction-progress").style.width = `${percentage}%`;

    const msg = document.getElementById("hardware-status-msg");
    if (earned >= GOAL) {
        msg.className = "alert alert-success";
        msg.innerHTML = "🎉 ¡Felicidades! Has desbloqueado el financiamiento de hardware.";
    } else {
        msg.className = "alert alert-info";
        msg.innerHTML = `Sigue completando micro-tareas. Te faltan $${(GOAL - earned).toFixed(2)} para desbloquear el formulario.`;
    }
}

// ══════════════════════════════════════════════════════════════
//  DASHBOARD / PERFIL
// ══════════════════════════════════════════════════════════════
async function loadDashboardData() {
    switchView("view-dashboard");

    // Nombre e iniciales
    document.getElementById("profile-name").textContent = userState.name;
    const initials = userState.name.split(" ").map(w => w[0]).join("").toUpperCase().slice(0, 2);
    const initialsEl = document.getElementById("user-initials-large");
    if (initialsEl) initialsEl.textContent = initials || "U";

    // Estadísticas
    document.getElementById("stat-courses").textContent = userState.coursesCompleted;
    document.getElementById("stat-tasks").textContent   = userState.tasksCompleted;
    const statJobs = document.getElementById("stat-jobs");
    if (statJobs) statJobs.textContent = userState.jobsCompleted;

    // Links
    const llEl = document.getElementById("link-linkedin");
    const lpEl = document.getElementById("link-portfolio");
    if (llEl) llEl.value = userState.linkedin;
    if (lpEl) lpEl.value = userState.portfolio;

    // Habilidades
    const skillsContainer = document.getElementById("skills-list");
    if (skillsContainer) {
        skillsContainer.innerHTML = "";
        userState.skills.forEach(skill => {
            const badge = document.createElement("span");
            badge.className = "skill-badge";
            badge.textContent = skill;
            skillsContainer.appendChild(badge);
        });
    }

    // Método de pago
    document.getElementById("payout-method").value = userState.payoutMethod;
    document.getElementById("payout-detail").value = userState.payoutDetail;

    // Historial desde la API
    try {
        const payments = await apiFetch("/payments/my-payments");
        userState.history = payments.map(p => ({
            title: `Pago por tarea`,
            date: new Date(p.created_at).toLocaleDateString("es"),
            amount: p.amount,
        }));
    } catch (_) {
        // Usa el historial local si no hay backend
    }

    renderHistoryList();
}

/** Renderiza el historial de pagos */
function renderHistoryList() {
    const container = document.getElementById("history-container");
    container.innerHTML = "";

    if (userState.history.length === 0) {
        container.innerHTML = `<p class="subtitle" style="text-align:center;padding:1rem;">Sin transacciones aún.</p>`;
        return;
    }

    userState.history.forEach(item => {
        const div = document.createElement("div");
        div.className = "history-item";
        div.innerHTML = `
            <div class="history-details">
                <span class="history-title">${item.title}</span>
                <span class="history-date">${item.date}</span>
            </div>
            <span class="history-amount positive">+$${item.amount.toFixed(2)}</span>
        `;
        container.appendChild(div);
    });
}

/** Guardar método de pago */
document.getElementById("payoutForm").addEventListener("submit", (e) => {
    e.preventDefault();
    userState.payoutMethod = document.getElementById("payout-method").value;
    userState.payoutDetail = document.getElementById("payout-detail").value;
    alert("✅ Datos de cobro guardados.");
});

/** Guardar links del perfil */
function saveLinks() {
    userState.linkedin  = document.getElementById("link-linkedin").value;
    userState.portfolio = document.getElementById("link-portfolio").value;
    alert("✅ ¡Tus enlaces han sido guardados!");
}

// ══════════════════════════════════════════════════════════════
//  IMÁGENES DE PERFIL
// ══════════════════════════════════════════════════════════════
function updateImage(inputElement, targetId) {
    if (inputElement.files && inputElement.files[0]) {
        const reader = new FileReader();
        reader.onload = function (e) {
            const target = document.getElementById(targetId);
            target.style.backgroundImage = `url('${e.target.result}')`;
            if (targetId === "profile-avatar-img") target.innerHTML = "";
        };
        reader.readAsDataURL(inputElement.files[0]);
    }
}

function openLesson() {
    alert("📖 Abriendo módulo optimizado...");
}
