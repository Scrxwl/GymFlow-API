"""Instância principal FastAPI da GymFlow API — Gestão de Treinos e Acompanhamento Físico."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from .database import SessionLocal, engine, init_db_and_seed
from .exceptions import create_problem_response, register_exception_handlers
from .routers import auth, executions, students, workouts
from .schemas import InvalidParam

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>GymFlow API — Painel Interativo de Demonstração (P2)</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen font-sans">
  <header class="border-b border-purple-900/60 bg-slate-900/80 backdrop-blur sticky top-0 z-10">
    <div class="max-w-6xl mx-auto px-6 py-4 flex flex-wrap items-center justify-between gap-4">
      <div class="flex items-center gap-3">
        <span class="h-10 w-10 rounded-xl bg-purple-600 flex items-center justify-center font-bold text-xl shadow-lg shadow-purple-600/30">GF</span>
        <div>
          <h1 class="text-xl font-bold text-white">GymFlow API — Live Demo (SDD + ORM + JWT/RBAC)</h1>
          <p class="text-xs text-slate-400">João Gabriel Cardoso • Rodrigo de Azevedo Jr. • Thales de Oliveira Silva</p>
        </div>
      </div>
      <div class="flex items-center gap-3">
        <a href="/docs" target="_blank" class="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-sm font-semibold transition">Abrir Swagger UI (/docs)</a>
        <a href="https://3f9huyoq5b.apidog.io/readme-2508436m0" target="_blank" class="px-4 py-2 rounded-lg border border-slate-700 hover:bg-slate-800 text-sm transition">Contrato Apidog</a>
      </div>
    </div>
  </header>

  <main class="max-w-6xl mx-auto px-6 py-8 space-y-8">
    <!-- 1. Painel de Autenticação JWT & RBAC -->
    <section class="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
      <div class="flex flex-wrap items-center justify-between gap-4 mb-4">
        <div>
          <h2 class="text-lg font-bold text-purple-400">1. Autenticação Stateless JWT (HS256) & Papéis RBAC</h2>
          <p class="text-sm text-slate-400">Faça login com 1 clique para alternar entre <code class="text-purple-300">PERSONAL</code> e <code class="text-emerald-300">STUDENT</code>.</p>
        </div>
        <div class="flex flex-wrap gap-2">
          <button onclick="loginAs('carlos@gymflow.dev', 'Personal@2026')" class="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-sm font-semibold transition">Login como PERSONAL (Carlos)</button>
          <button onclick="loginAs('rodrigo@gymflow.dev', 'Aluno@2026')" class="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-sm font-semibold transition">Login como STUDENT (Rodrigo)</button>
          <button onclick="testRbac403()" class="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-sm font-semibold transition">Testar Bloqueio RBAC (403 RFC 9457)</button>
        </div>
      </div>
      <div id="authStatus" class="text-xs font-mono bg-slate-950 border border-slate-800 rounded-xl p-4 text-slate-300 overflow-x-auto">
        Nenhum token ativo. Clique em um dos botões acima para autenticar.
      </div>
    </section>

    <!-- 2. Conteúdo Extra: Analytics Biométrico (IMC) + RPE Borg -->
    <section class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6">
        <span class="text-xs uppercase tracking-wider text-purple-400 font-semibold">Conteúdo Extra • Biometria</span>
        <h3 class="text-2xl font-bold mt-1" id="bmiValue">--</h3>
        <p class="text-sm text-slate-400 mt-1" id="bmiClass">IMC calculado via endpoint /analytics</p>
      </div>
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6">
        <span class="text-xs uppercase tracking-wider text-emerald-400 font-semibold">Engajamento & Volume</span>
        <h3 class="text-2xl font-bold mt-1" id="execCount">--</h3>
        <p class="text-sm text-slate-400 mt-1" id="totalMinutes">Sessões de treino registradas no SQLite</p>
      </div>
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6">
        <span class="text-xs uppercase tracking-wider text-amber-400 font-semibold">Intensidade Média (Escala Borg)</span>
        <h3 class="text-2xl font-bold mt-1" id="avgRpe">--</h3>
        <p class="text-sm text-slate-400 mt-1">Percepção Subjetiva de Esforço (RPE 1 a 10)</p>
      </div>
    </section>

    <!-- 3. Relacionamento 1:N (Workouts -> Routines -> Exercises) & Check-in RPE -->
    <section class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-bold text-purple-400">2. Fichas de Treino (ORM 1:N com selectinload)</h2>
          <button onclick="loadDashboardData()" class="text-xs px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700">Atualizar</button>
        </div>
        <div id="workoutsContainer" class="space-y-3 text-sm text-slate-300">
          Faça login para carregar as fichas de treino e seus exercícios aninhados.
        </div>
      </div>

      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
        <h2 class="text-lg font-bold text-emerald-400">3. Registrar Check-in de Treino (Escala RPE 1–10)</h2>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="text-xs text-slate-400">Duração (minutos)</label>
            <input id="durationInput" type="number" value="55" min="5" max="300" class="w-full mt-1 px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-sm" />
          </div>
          <div>
            <label class="text-xs text-slate-400">Nota RPE Borg (1 a 10)</label>
            <input id="rpeInput" type="number" value="8" min="1" max="10" class="w-full mt-1 px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-sm" />
          </div>
        </div>
        <div>
          <label class="text-xs text-slate-400">Feedback do Aluno</label>
          <input id="feedbackInput" type="text" value="Excelente treino! Progredi carga no supino." class="w-full mt-1 px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-sm" />
        </div>
        <button onclick="submitExecution()" class="w-full py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 font-semibold text-sm transition">Enviar Check-in (POST /api/v1/routines/{id}/executions)</button>
        <pre id="apiResponseLog" class="text-xs font-mono bg-slate-950 border border-slate-800 rounded-xl p-4 text-slate-300 overflow-x-auto max-h-60">Aguardando requisição...</pre>
      </div>
    </section>
  </main>

  <script>
    let currentToken = "";
    const STUDENT_ID = "22222222-2222-2222-2222-222222222222";
    const ROUTINE_ID = "44444444-4444-4444-4444-444444444444";

    async function loginAs(email, password) {
      const res = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });
      const data = await res.json();
      if (res.ok) {
        currentToken = data.accessToken;
        document.getElementById("authStatus").innerHTML =
          `✅ Autenticado como <b>${data.user.name}</b> (${data.user.email}) | Role RBAC: <b class="text-purple-400">${data.user.role}</b><br>JWT: ${currentToken.substring(0, 64)}...`;
        document.getElementById("apiResponseLog").textContent = JSON.stringify(data, null, 2);
        await loadDashboardData();
      } else {
        document.getElementById("apiResponseLog").textContent = JSON.stringify(data, null, 2);
      }
    }

    async function loadDashboardData() {
      if (!currentToken) return;
      const headers = { "Authorization": `Bearer ${currentToken}` };

      const anaRes = await fetch(`/api/v1/students/${STUDENT_ID}/analytics`, { headers });
      if (anaRes.ok) {
        const ana = await anaRes.json();
        document.getElementById("bmiValue").textContent = `${ana.bmi} kg/m²`;
        document.getElementById("bmiClass").textContent = `${ana.bmiClassification} (${ana.weightKg}kg / ${ana.heightCm}cm)`;
        document.getElementById("execCount").textContent = `${ana.totalExecutions} check-in(s)`;
        document.getElementById("totalMinutes").textContent = `${ana.totalDurationMinutes} minutos totais acumulados`;
        document.getElementById("avgRpe").textContent = `RPE ${ana.averageRpeScore} / 10`;
      }

      const wkRes = await fetch("/api/v1/workouts", { headers });
      if (wkRes.ok) {
        const wkData = await wkRes.json();
        const container = document.getElementById("workoutsContainer");
        container.innerHTML = wkData.data.map(plan => `
          <div class="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
            <div class="flex items-center justify-between">
              <span class="font-bold text-white">${plan.title}</span>
              <span class="text-xs px-2 py-0.5 rounded bg-purple-900/60 text-purple-300">${plan.status}</span>
            </div>
            <p class="text-xs text-slate-400">${plan.description || ""}</p>
            ${plan.routines.map(r => `
              <div class="pl-3 border-l-2 border-purple-600/50 mt-2">
                <div class="font-semibold text-purple-300 text-xs">${r.name} (${r.dayOfWeek || "Livre"})</div>
                <ul class="mt-1 space-y-1 text-xs text-slate-300">
                  ${r.exercises.map(ex => `<li>• <b>${ex.name}</b> [${ex.muscleGroup}] — ${ex.sets}x ${ex.reps} (${ex.weightKg || 0}kg, descanso ${ex.restSeconds}s)</li>`).join("")}
                </ul>
              </div>
            `).join("")}
          </div>
        `).join("");
      }
    }

    async function submitExecution() {
      const durationMinutes = parseInt(document.getElementById("durationInput").value, 10);
      const rpeScore = parseInt(document.getElementById("rpeInput").value, 10);
      const feedback = document.getElementById("feedbackInput").value;
      const res = await fetch(`/api/v1/routines/${ROUTINE_ID}/executions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(currentToken ? { "Authorization": `Bearer ${currentToken}` } : {})
        },
        body: JSON.stringify({ durationMinutes, rpeScore, feedback })
      });
      const data = await res.json();
      document.getElementById("apiResponseLog").textContent = JSON.stringify(data, null, 2);
      if (res.ok) await loadDashboardData();
    }

    async function testRbac403() {
      await loginAs("rodrigo@gymflow.dev", "Aluno@2026");
      const res = await fetch(`/api/v1/students/${STUDENT_ID}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${currentToken}` }
      });
      const data = await res.json();
      document.getElementById("apiResponseLog").textContent =
        `Status HTTP: ${res.status} (Bloqueio RBAC RFC 9457)\\n` + JSON.stringify(data, null, 2);
    }
  </script>
</body>
</html>
"""


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Cria as tabelas SQLite e executa o seed inicial na inicialização."""
    db = SessionLocal()
    try:
        init_db_and_seed(db, target_engine=engine)
    finally:
        db.close()
    yield


app = FastAPI(
    title="GymFlow API — Gestão de Treinos e Acompanhamento Físico",
    description=(
        "API RESTful com SQLAlchemy 2.0 ORM, Autenticação Stateless JWT/RBAC "
        "(PERSONAL & STUDENT) e tratamento de erros RFC 9457 (Problem Details)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def malformed_json_middleware(request: Request, call_next) -> JSONResponse:
    """Intercepta JSON malformado no body e retorna 400 Bad Request no padrão RFC 9457."""
    if request.method in ("POST", "PUT", "PATCH"):
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type.lower():
            raw_body = await request.body()
            if raw_body:
                try:
                    json.loads(raw_body)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    return create_problem_response(
                        request=request,
                        status_code=400,
                        detail="O corpo da requisição contém um JSON sintaticamente malformado.",
                        invalid_params=[
                            InvalidParam(name="body", reason="JSON inválido ou corrompido.")
                        ],
                    )
    return await call_next(request)


register_exception_handlers(app)

app.include_router(auth.router)
app.include_router(students.router)
app.include_router(workouts.router)
app.include_router(executions.router)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def interactive_dashboard() -> HTMLResponse:
    """[Conteúdo Extra] Painel Web interativo para demonstração funcional ao vivo na apresentação da P2."""
    return HTMLResponse(content=DASHBOARD_HTML)


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "GymFlow API", "version": "1.0.0"}
