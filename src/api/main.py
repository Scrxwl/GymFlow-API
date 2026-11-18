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
    <div class="max-w-7xl mx-auto px-6 py-4 flex flex-wrap items-center justify-between gap-4">
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

  <main class="max-w-7xl mx-auto px-6 py-8 space-y-8">
    <!-- 1. Painel de Autenticação JWT & RBAC -->
    <section class="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
      <div class="flex flex-wrap items-center justify-between gap-4 mb-4">
        <div>
          <h2 class="text-lg font-bold text-purple-400">1. Autenticação Stateless JWT (HS256) & Papéis RBAC</h2>
          <p class="text-sm text-slate-400">Alterne entre <code class="text-purple-300">PERSONAL</code> (pode criar/editar/excluir treinos e alunos) e <code class="text-emerald-300">STUDENT</code> (apenas visualiza e faz check-in RPE).</p>
        </div>
        <div class="flex flex-wrap gap-2">
          <button onclick="loginAs('carlos@gymflow.dev', 'Personal@2026')" class="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-sm font-semibold transition">👨‍🏫 Login como PERSONAL (Carlos)</button>
          <button onclick="loginAs('rodrigo@gymflow.dev', 'Aluno@2026')" class="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-sm font-semibold transition">🏃 Login como STUDENT (Rodrigo)</button>
          <button onclick="testRbac403()" class="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-sm font-semibold transition">🛡️ Simular Bloqueio RBAC (403 RFC 9457)</button>
        </div>
      </div>
      <div id="authStatus" class="text-xs font-mono bg-slate-950 border border-slate-800 rounded-xl p-4 text-slate-300 overflow-x-auto">
        Autenticando automaticamente como PERSONAL...
      </div>
    </section>

    <!-- 2. Conteúdo Extra: Analytics Biométrico (IMC) + RPE Borg -->
    <section class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-5">
        <span class="text-xs uppercase tracking-wider text-purple-400 font-semibold">Aluno Selecionado</span>
        <h3 class="text-xl font-bold mt-1" id="studentNameCard">Rodrigo Aluno</h3>
        <p class="text-xs text-slate-400 mt-1" id="studentGoalCard">Meta: HYPERTROPHY</p>
      </div>
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-5">
        <span class="text-xs uppercase tracking-wider text-purple-400 font-semibold">Biometria • IMC (Extra)</span>
        <h3 class="text-2xl font-bold mt-1" id="bmiValue">--</h3>
        <p class="text-xs text-slate-400 mt-1" id="bmiClass">Calculado via /analytics</p>
      </div>
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-5">
        <span class="text-xs uppercase tracking-wider text-emerald-400 font-semibold">Engajamento & Volume</span>
        <h3 class="text-2xl font-bold mt-1" id="execCount">--</h3>
        <p class="text-xs text-slate-400 mt-1" id="totalMinutes">Sessões registradas</p>
      </div>
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-5">
        <span class="text-xs uppercase tracking-wider text-amber-400 font-semibold">Intensidade Média (Borg)</span>
        <h3 class="text-2xl font-bold mt-1" id="avgRpe">--</h3>
        <p class="text-xs text-slate-400 mt-1">Escala RPE (1 a 10)</p>
      </div>
    </section>

    <!-- 3. Painel Principal: Fichas de Treino + Edição pelo Personal -->
    <section class="grid grid-cols-1 lg:grid-cols-12 gap-6">
      <!-- Coluna Esquerda (7 cols): Lista de Fichas, Rotinas e Exercícios com botões de ação -->
      <div class="lg:col-span-7 bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-5">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 class="text-lg font-bold text-purple-400">2. Fichas de Treino Prescritas (SQLAlchemy 1:N selectinload)</h2>
            <p class="text-xs text-slate-400">Como <b>PERSONAL</b>, você pode editar a ficha, adicionar ou remover exercícios e criar novas fichas.</p>
          </div>
          <button onclick="loadDashboardData()" class="text-xs px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 font-semibold">🔄 Recarregar</button>
        </div>

        <div id="workoutsContainer" class="space-y-4 text-sm text-slate-300">
          Carregando fichas de treino...
        </div>

        <!-- Formulário do PERSONAL: Adicionar Exercício em uma Rotina -->
        <div class="border-t border-slate-800 pt-5 space-y-3">
          <h3 class="text-sm font-bold text-purple-300">➕ Prescrever Novo Exercício na Rotina (POST /api/v1/routines/{id}/exercises)</h3>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div class="sm:col-span-2">
              <label class="text-xs text-slate-400">Rotina Destino</label>
              <select id="exRoutineSelect" class="w-full mt-1 px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs"></select>
            </div>
            <div>
              <label class="text-xs text-slate-400">Grupo Muscular</label>
              <select id="exMuscleInput" class="w-full mt-1 px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs">
                <option value="CHEST">CHEST (Peito)</option>
                <option value="BACK">BACK (Costas)</option>
                <option value="LEGS">LEGS (Pernas)</option>
                <option value="SHOULDERS">SHOULDERS (Ombros)</option>
                <option value="BICEPS">BICEPS (Bíceps)</option>
                <option value="TRICEPS">TRICEPS (Tríceps)</option>
                <option value="CORE">CORE (Abdômen)</option>
                <option value="CARDIO">CARDIO</option>
              </select>
            </div>
          </div>
          <div class="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <div class="col-span-2">
              <label class="text-xs text-slate-400">Nome do Exercício</label>
              <input id="exNameInput" type="text" value="Crucifixo Inclinado com Halteres" class="w-full mt-1 px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs" />
            </div>
            <div>
              <label class="text-xs text-slate-400">Séries</label>
              <input id="exSetsInput" type="number" value="4" min="1" max="20" class="w-full mt-1 px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs" />
            </div>
            <div>
              <label class="text-xs text-slate-400">Repetições</label>
              <input id="exRepsInput" type="text" value="10-12" class="w-full mt-1 px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs" />
            </div>
            <div>
              <label class="text-xs text-slate-400">Carga (kg)</label>
              <input id="exWeightInput" type="number" step="0.5" value="22.5" class="w-full mt-1 px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs" />
            </div>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label class="text-xs text-slate-400">Descanso (seg)</label>
              <input id="exRestInput" type="number" value="75" class="w-full mt-1 px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs" />
            </div>
            <div class="sm:col-span-2">
              <label class="text-xs text-slate-400">Observações Técnicas</label>
              <input id="exNotesInput" type="text" value="Amplitude máxima, controlar fase excêntrica." class="w-full mt-1 px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs" />
            </div>
          </div>
          <button onclick="addExercise()" class="w-full py-2.5 rounded-lg bg-purple-600 hover:bg-purple-500 font-semibold text-xs transition">
            ➕ Adicionar Exercício na Ficha (Exclusivo PERSONAL)
          </button>
        </div>

        <!-- Formulário do PERSONAL: Criar Nova Ficha ou Nova Divisão de Rotina -->
        <div class="border-t border-slate-800 pt-5 space-y-3">
          <h3 class="text-sm font-bold text-purple-300">📋 Criar Nova Divisão de Rotina na Ficha (POST /api/v1/workouts/{id}/routines)</h3>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label class="text-xs text-slate-400">Ficha de Treino</label>
              <select id="routineWorkoutSelect" class="w-full mt-1 px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs"></select>
            </div>
            <div>
              <label class="text-xs text-slate-400">Nome da Divisão</label>
              <input id="routineNameInput" type="text" value="Treino B — Costas e Bíceps" class="w-full mt-1 px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs" />
            </div>
            <div>
              <label class="text-xs text-slate-400">Dia da Semana</label>
              <select id="routineDayInput" class="w-full mt-1 px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs">
                <option value="MONDAY">MONDAY (Segunda)</option>
                <option value="TUESDAY">TUESDAY (Terça)</option>
                <option value="WEDNESDAY" selected>WEDNESDAY (Quarta)</option>
                <option value="THURSDAY">THURSDAY (Quinta)</option>
                <option value="FRIDAY">FRIDAY (Sexta)</option>
                <option value="SATURDAY">SATURDAY (Sábado)</option>
              </select>
            </div>
          </div>
          <button onclick="addRoutine()" class="w-full py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 font-semibold text-xs transition">
            ➕ Adicionar Divisão de Rotina (Treino B/C/D)
          </button>
        </div>
      </div>

      <!-- Coluna Direita (5 cols): Edição do Personal + Check-in RPE do Aluno + Console JSON -->
      <div class="lg:col-span-5 space-y-6">
        <!-- Card Personal: Editar Ficha de Treino & Biometria do Aluno -->
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
          <h2 class="text-lg font-bold text-purple-400">3. Painel do Personal: Editar Treino & Biometria</h2>

          <!-- Editar Metadados do Plano -->
          <div class="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
            <div class="text-xs font-bold text-purple-300">✏️ Atualizar Ficha de Treino (PATCH /api/v1/workouts/{id})</div>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <div class="sm:col-span-2">
                <label class="text-[11px] text-slate-400">Novo Título da Ficha</label>
                <input id="editWorkoutTitle" type="text" value="Mesociclo 01 — Hipertrofia Avançada" class="w-full mt-1 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs" />
              </div>
              <div>
                <label class="text-[11px] text-slate-400">Status</label>
                <select id="editWorkoutStatus" class="w-full mt-1 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs">
                  <option value="ACTIVE">ACTIVE</option>
                  <option value="INACTIVE">INACTIVE</option>
                  <option value="ARCHIVED">ARCHIVED</option>
                </select>
              </div>
            </div>
            <div>
              <label class="text-[11px] text-slate-400">Descrição / Diretrizes da Ficha</label>
              <input id="editWorkoutDesc" type="text" value="Foco em progressão de carga semanal e controle de cadência." class="w-full mt-1 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs" />
            </div>
            <button onclick="updateWorkoutMetadata()" class="w-full py-2 rounded-lg bg-purple-600 hover:bg-purple-500 font-semibold text-xs transition">
              💾 Salvar Alterações na Ficha (PATCH)
            </button>
          </div>

          <!-- Editar Biometria e Meta do Aluno -->
          <div class="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
            <div class="text-xs font-bold text-purple-300">⚖️ Atualizar Peso, Altura e Meta do Aluno (PATCH /api/v1/students/{id})</div>
            <div class="grid grid-cols-3 gap-2">
              <div>
                <label class="text-[11px] text-slate-400">Peso (kg)</label>
                <input id="editStudentWeight" type="number" step="0.1" value="81.0" class="w-full mt-1 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs" />
              </div>
              <div>
                <label class="text-[11px] text-slate-400">Altura (cm)</label>
                <input id="editStudentHeight" type="number" step="1" value="178" class="w-full mt-1 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs" />
              </div>
              <div>
                <label class="text-[11px] text-slate-400">Objetivo</label>
                <select id="editStudentGoal" class="w-full mt-1 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs">
                  <option value="HYPERTROPHY">HYPERTROPHY</option>
                  <option value="WEIGHT_LOSS">WEIGHT_LOSS</option>
                  <option value="CONDITIONING">CONDITIONING</option>
                  <option value="REHABILITATION">REHABILITATION</option>
                  <option value="GENERAL_FITNESS">GENERAL_FITNESS</option>
                </select>
              </div>
            </div>
            <button onclick="updateStudentProfile()" class="w-full py-2 rounded-lg bg-purple-600 hover:bg-purple-500 font-semibold text-xs transition">
              ⚖️ Atualizar Biometria e Recalcular IMC (PATCH)
            </button>
          </div>
        </div>

        <!-- Card Aluno: Check-in RPE -->
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
          <h2 class="text-lg font-bold text-emerald-400">4. Check-in Pós-Treino do Aluno (Escala RPE 1–10)</h2>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="text-xs text-slate-400">Duração (minutos)</label>
              <input id="durationInput" type="number" value="55" min="5" max="300" class="w-full mt-1 px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs" />
            </div>
            <div>
              <label class="text-xs text-slate-400">Nota RPE Borg (1 a 10)</label>
              <input id="rpeInput" type="number" value="8" min="1" max="10" class="w-full mt-1 px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs" />
            </div>
          </div>
          <div>
            <label class="text-xs text-slate-400">Feedback do Aluno</label>
            <input id="feedbackInput" type="text" value="Excelente treino! Progredi carga no supino." class="w-full mt-1 px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs" />
          </div>
          <button onclick="submitExecution()" class="w-full py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 font-semibold text-xs transition">
            ✅ Enviar Check-in (POST /api/v1/routines/{id}/executions)
          </button>
        </div>

        <!-- Console de Resposta JSON -->
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-2">
          <h3 class="text-xs font-bold uppercase tracking-wider text-slate-400">Última Resposta da API (JSON / RFC 9457)</h3>
          <pre id="apiResponseLog" class="text-xs font-mono bg-slate-950 border border-slate-800 rounded-xl p-4 text-slate-300 overflow-x-auto max-h-64">Aguardando requisição...</pre>
        </div>
      </div>
    </section>
  </main>

  <script>
    let currentToken = "";
    let currentWorkoutId = "33333333-3333-3333-3333-333333333333";
    const STUDENT_ID = "22222222-2222-2222-2222-222222222222";
    const DEFAULT_ROUTINE_ID = "44444444-4444-4444-4444-444444444444";

    function logApiResult(status, data) {
      const prefix = status >= 400 ? `❌ HTTP ${status} (RFC 9457 Problem Details)` : `✅ HTTP ${status}`;
      document.getElementById("apiResponseLog").textContent = `${prefix}\n` + JSON.stringify(data, null, 2);
    }

    async function loginAs(email, password) {
      const res = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });
      const data = await res.json();
      if (res.ok) {
        currentToken = data.accessToken;
        const badgeColor = data.user.role === "PERSONAL" ? "text-purple-400" : "text-emerald-400";
        document.getElementById("authStatus").innerHTML =
          `✅ Autenticado como <b>${data.user.name}</b> (${data.user.email}) | Role RBAC: <b class="${badgeColor}">${data.user.role}</b><br>JWT: ${currentToken.substring(0, 72)}...`;
        logApiResult(res.status, data);
        await loadDashboardData();
      } else {
        logApiResult(res.status, data);
      }
    }

    async function loadDashboardData() {
      if (!currentToken) return;
      const headers = { "Authorization": `Bearer ${currentToken}` };

      const anaRes = await fetch(`/api/v1/students/${STUDENT_ID}/analytics`, { headers });
      if (anaRes.ok) {
        const ana = await anaRes.json();
        document.getElementById("studentNameCard").textContent = ana.studentName;
        document.getElementById("studentGoalCard").textContent = `Meta: ${ana.goal}`;
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
        const routineSelect = document.getElementById("exRoutineSelect");
        const workoutSelect = document.getElementById("routineWorkoutSelect");

        routineSelect.innerHTML = "";
        workoutSelect.innerHTML = "";

        if (wkData.data.length > 0) {
          currentWorkoutId = wkData.data[0].id;
        }

        container.innerHTML = wkData.data.map(plan => {
          workoutSelect.innerHTML += `<option value="${plan.id}">${plan.title}</option>`;
          plan.routines.forEach(r => {
            routineSelect.innerHTML += `<option value="${r.id}">${plan.title} ➔ ${r.name}</option>`;
          });

          return `
          <div class="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
            <div class="flex items-center justify-between gap-2">
              <div>
                <span class="font-bold text-white text-base">${plan.title}</span>
                <p class="text-xs text-slate-400 mt-0.5">${plan.description || ""}</p>
              </div>
              <span class="text-xs px-2.5 py-1 rounded-full bg-purple-900/60 text-purple-300 font-semibold">${plan.status}</span>
            </div>
            <div class="space-y-3">
              ${plan.routines.map(r => `
                <div class="p-3 rounded-lg bg-slate-900/90 border border-slate-800/80">
                  <div class="font-semibold text-purple-300 text-xs mb-2 flex items-center justify-between">
                    <span>📌 ${r.name} (${r.dayOfWeek || "Livre"})</span>
                    <span class="text-[11px] text-slate-500">${r.exercises.length} exercício(s)</span>
                  </div>
                  <ul class="space-y-1.5 text-xs text-slate-300">
                    ${r.exercises.map(ex => `
                      <li class="flex items-center justify-between gap-2 bg-slate-950/70 px-3 py-1.5 rounded border border-slate-800/60">
                        <span>• <b>${ex.name}</b> <span class="text-purple-400">[${ex.muscleGroup}]</span> — ${ex.sets}x ${ex.reps} • <b>${ex.weightKg || 0}kg</b> (descanso ${ex.restSeconds}s)</span>
                        <button onclick="deleteExercise('${ex.id}')" title="Remover exercício" class="text-rose-400 hover:text-rose-300 text-xs font-bold px-2 py-0.5 rounded bg-rose-950/50 hover:bg-rose-900/60 transition">🗑️ Excluir</button>
                      </li>
                    `).join("")}
                  </ul>
                </div>
              `).join("")}
            </div>
          </div>`;
        }).join("");
      }
    }

    async function updateWorkoutMetadata() {
      const title = document.getElementById("editWorkoutTitle").value;
      const status = document.getElementById("editWorkoutStatus").value;
      const description = document.getElementById("editWorkoutDesc").value;

      const res = await fetch(`/api/v1/workouts/${currentWorkoutId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          ...(currentToken ? { "Authorization": `Bearer ${currentToken}` } : {})
        },
        body: JSON.stringify({ title, status, description })
      });
      const data = await res.json();
      logApiResult(res.status, data);
      if (res.ok) await loadDashboardData();
    }

    async function updateStudentProfile() {
      const weightKg = parseFloat(document.getElementById("editStudentWeight").value);
      const heightCm = parseFloat(document.getElementById("editStudentHeight").value);
      const goal = document.getElementById("editStudentGoal").value;

      const res = await fetch(`/api/v1/students/${STUDENT_ID}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          ...(currentToken ? { "Authorization": `Bearer ${currentToken}` } : {})
        },
        body: JSON.stringify({ profile: { weightKg, heightCm, goal } })
      });
      const data = await res.json();
      logApiResult(res.status, data);
      if (res.ok) await loadDashboardData();
    }

    async function addExercise() {
      const routineId = document.getElementById("exRoutineSelect").value || DEFAULT_ROUTINE_ID;
      const payload = {
        name: document.getElementById("exNameInput").value,
        muscleGroup: document.getElementById("exMuscleInput").value,
        sets: parseInt(document.getElementById("exSetsInput").value, 10),
        reps: document.getElementById("exRepsInput").value,
        weightKg: parseFloat(document.getElementById("exWeightInput").value),
        restSeconds: parseInt(document.getElementById("exRestInput").value, 10),
        notes: document.getElementById("exNotesInput").value,
        order: 2
      };

      const res = await fetch(`/api/v1/routines/${routineId}/exercises`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(currentToken ? { "Authorization": `Bearer ${currentToken}` } : {})
        },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      logApiResult(res.status, data);
      if (res.ok) await loadDashboardData();
    }

    async function deleteExercise(exerciseId) {
      const res = await fetch(`/api/v1/exercises/${exerciseId}`, {
        method: "DELETE",
        headers: currentToken ? { "Authorization": `Bearer ${currentToken}` } : {}
      });
      if (res.status === 204) {
        logApiResult(204, { message: `Exercício ${exerciseId} removido com sucesso (204 No Content).` });
        await loadDashboardData();
      } else {
        const data = await res.json();
        logApiResult(res.status, data);
      }
    }

    async function addRoutine() {
      const workoutId = document.getElementById("routineWorkoutSelect").value || currentWorkoutId;
      const payload = {
        name: document.getElementById("routineNameInput").value,
        dayOfWeek: document.getElementById("routineDayInput").value,
        order: 2,
        exercises: []
      };

      const res = await fetch(`/api/v1/workouts/${workoutId}/routines`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(currentToken ? { "Authorization": `Bearer ${currentToken}` } : {})
        },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      logApiResult(res.status, data);
      if (res.ok) await loadDashboardData();
    }

    async function submitExecution() {
      const routineId = document.getElementById("exRoutineSelect").value || DEFAULT_ROUTINE_ID;
      const durationMinutes = parseInt(document.getElementById("durationInput").value, 10);
      const rpeScore = parseInt(document.getElementById("rpeInput").value, 10);
      const feedback = document.getElementById("feedbackInput").value;
      const res = await fetch(`/api/v1/routines/${routineId}/executions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(currentToken ? { "Authorization": `Bearer ${currentToken}` } : {})
        },
        body: JSON.stringify({ durationMinutes, rpeScore, feedback })
      });
      const data = await res.json();
      logApiResult(res.status, data);
      if (res.ok) await loadDashboardData();
    }

    async function testRbac403() {
      await loginAs("rodrigo@gymflow.dev", "Aluno@2026");
      const res = await fetch(`/api/v1/students/${STUDENT_ID}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${currentToken}` }
      });
      const data = await res.json();
      logApiResult(res.status, data);
    }

    window.addEventListener("DOMContentLoaded", () => {
      loginAs("carlos@gymflow.dev", "Personal@2026");
    });
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
