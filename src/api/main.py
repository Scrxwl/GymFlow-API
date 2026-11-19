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
          <h1 class="text-xl font-bold text-white">GymFlow API — Demonstração Interativa (SDD + ORM + JWT/RBAC)</h1>
          <p class="text-xs text-slate-400">João Gabriel Cardoso • Rodrigo de Azevedo Jr. • Thales de Oliveira Silva</p>
        </div>
      </div>
      <div class="flex items-center gap-3">
        <span id="headerUserBadge" class="hidden text-xs px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-300"></span>
        <button id="headerLogoutBtn" onclick="logoutUser()" class="hidden px-3 py-2 rounded-lg bg-rose-600/90 hover:bg-rose-500 text-xs font-semibold transition">🚪 Sair</button>
        <a href="/docs#/Authentication/get_me_api_v1_auth_me_get" target="_blank" class="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-sm font-semibold transition">Documentação Interativa (/docs)</a>
        <a href="https://3f9huyoq5b.apidog.io/readme-2508436m0" target="_blank" class="px-4 py-2 rounded-lg border border-slate-700 hover:bg-slate-800 text-sm transition">Contrato Apidog</a>
      </div>
    </div>
  </header>

  <!-- TELA DE AUTENTICAÇÃO (LOGIN & CADASTRO JWT / RBAC) -->
  <section id="authScreen" class="max-w-6xl mx-auto px-6 py-10">
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
      <!-- Coluna Esquerda (7 cols): Card de Login e Cadastro -->
      <div class="lg:col-span-7 bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-2xl space-y-6">
        <div class="flex items-center justify-between gap-4 border-b border-slate-800 pb-5">
          <div class="flex items-center gap-3">
            <span class="h-12 w-12 rounded-2xl bg-purple-600 flex items-center justify-center font-bold text-2xl shadow-lg shadow-purple-600/30">GF</span>
            <div>
              <h2 class="text-xl font-bold text-white">Autenticação GymFlow API</h2>
              <p class="text-xs text-slate-400">Segurança Stateless via JWT (<code class="text-purple-300">HS256</code>) & Controle de Acesso RBAC</p>
            </div>
          </div>
          <span class="text-xs px-3 py-1 rounded-full bg-purple-950 border border-purple-800/70 text-purple-300 font-semibold">/api/v1/auth</span>
        </div>

        <!-- Abas: Entrar vs Criar Conta -->
        <div class="grid grid-cols-2 gap-2 p-1 rounded-xl bg-slate-950 border border-slate-800">
          <button id="tabLoginBtn" onclick="switchAuthTab('login')" class="py-2.5 rounded-lg bg-purple-600 text-white text-xs font-bold transition shadow">
            🔐 Entrar (POST /auth/login)
          </button>
          <button id="tabRegisterBtn" onclick="switchAuthTab('register')" class="py-2.5 rounded-lg text-slate-400 hover:text-white text-xs font-bold transition">
            ✨ Criar Conta (POST /auth/register)
          </button>
        </div>

        <!-- Banner de Feedback / Erro RFC 9457 -->
        <div id="authFeedbackBanner" class="hidden rounded-xl p-4 text-xs border"></div>

        <!-- FORMULÁRIO 1: LOGIN -->
        <form id="loginForm" onsubmit="handleLoginSubmit(event)" class="space-y-4">
          <div>
            <label class="text-xs font-semibold text-slate-300">E-mail de Acesso</label>
            <input id="loginEmail" type="email" required value="carlos@gymflow.dev" placeholder="exemplo@gymflow.dev"
              class="w-full mt-1.5 px-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 focus:border-purple-500 focus:outline-none text-sm text-white" />
          </div>
          <div>
            <label class="text-xs font-semibold text-slate-300">Senha</label>
            <div class="relative mt-1.5">
              <input id="loginPassword" type="password" required value="Personal@2026" placeholder="••••••••"
                class="w-full px-4 py-2.5 pr-20 rounded-xl bg-slate-950 border border-slate-800 focus:border-purple-500 focus:outline-none text-sm text-white" />
              <button type="button" onclick="togglePasswordInput('loginPassword', this)"
                class="absolute right-2.5 top-1/2 -translate-y-1/2 px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-[11px] text-slate-300 font-semibold">
                Mostrar
              </button>
            </div>
          </div>
          <button type="submit" class="w-full py-3 rounded-xl bg-purple-600 hover:bg-purple-500 font-bold text-sm text-white shadow-lg shadow-purple-600/25 transition">
            🔐 Autenticar e Acessar Dashboard
          </button>
        </form>

        <!-- FORMULÁRIO 2: CADASTRO (REGISTER) -->
        <form id="registerForm" onsubmit="handleRegisterSubmit(event)" class="hidden space-y-4">
          <div>
            <label class="text-xs font-semibold text-slate-300">Papel de Acesso (Controle RBAC)</label>
            <div class="grid grid-cols-2 gap-3 mt-1.5">
              <button type="button" id="roleBtnPersonal" onclick="selectRegisterRole('PERSONAL')"
                class="p-3 rounded-xl border border-purple-500 bg-purple-950/50 text-left transition">
                <div class="text-xs font-bold text-purple-300">👨‍🏫 PERSONAL</div>
                <div class="text-[11px] text-slate-400 mt-0.5">Gerencia alunos, fichas e exercícios (requer CREF)</div>
              </button>
              <button type="button" id="roleBtnStudent" onclick="selectRegisterRole('STUDENT')"
                class="p-3 rounded-xl border border-slate-800 bg-slate-950 text-left transition">
                <div class="text-xs font-bold text-emerald-300">🏃 STUDENT</div>
                <div class="text-[11px] text-slate-400 mt-0.5">Consulta fichas prescritas e registra check-in RPE</div>
              </button>
            </div>
            <input id="regRole" type="hidden" value="PERSONAL" />
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="text-xs font-semibold text-slate-300">Nome Completo</label>
              <input id="regName" type="text" required placeholder="Ex: Fernanda Costa"
                class="w-full mt-1 px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 focus:border-purple-500 focus:outline-none text-xs text-white" />
            </div>
            <div>
              <label class="text-xs font-semibold text-slate-300">E-mail</label>
              <input id="regEmail" type="email" required placeholder="fernanda@gymflow.dev"
                class="w-full mt-1 px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 focus:border-purple-500 focus:outline-none text-xs text-white" />
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="text-xs font-semibold text-slate-300">Senha (mín. 6 caracteres)</label>
              <div class="relative mt-1">
                <input id="regPassword" type="password" required placeholder="Personal@2026"
                  class="w-full px-3.5 py-2.5 pr-16 rounded-xl bg-slate-950 border border-slate-800 focus:border-purple-500 focus:outline-none text-xs text-white" />
                <button type="button" onclick="togglePasswordInput('regPassword', this)"
                  class="absolute right-2 top-1/2 -translate-y-1/2 px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-[10px] text-slate-300">
                  Mostrar
                </button>
              </div>
            </div>
            <div>
              <label class="text-xs font-semibold text-slate-300">Telefone (Opcional)</label>
              <input id="regPhone" type="text" placeholder="+5511988887777"
                class="w-full mt-1 px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 focus:border-purple-500 focus:outline-none text-xs text-white" />
            </div>
          </div>

          <div id="regCrefGroup">
            <label class="text-xs font-semibold text-purple-300">Registro Profissional CREF (Obrigatório para PERSONAL)</label>
            <input id="regCref" type="text" value="123456-G/SP" placeholder="Ex: 123456-G/SP"
              class="w-full mt-1 px-3.5 py-2.5 rounded-xl bg-slate-950 border border-purple-800/70 focus:border-purple-500 focus:outline-none text-xs text-white" />
            <p class="text-[11px] text-slate-400 mt-1">Dica: deixe em branco com o papel PERSONAL para testar o erro <code class="text-rose-400">422 Unprocessable Entity (RFC 9457)</code>.</p>
          </div>

          <button type="submit" class="w-full py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 font-bold text-sm text-white shadow-lg shadow-emerald-600/25 transition">
            ✨ Cadastrar Usuário e Entrar Automaticamente
          </button>
        </form>
      </div>

      <!-- Coluna Direita (5 cols): Acesso Rápido Seed (1-Clique) & Inspetor RFC 9457 -->
      <div class="lg:col-span-5 space-y-6">
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <div>
            <span class="text-xs uppercase tracking-wider text-purple-400 font-semibold">Demonstração Rápida • Seed Inicial</span>
            <h3 class="text-base font-bold text-white mt-1">Acesso em 1 Clique (Contas Pré-Cadastradas)</h3>
            <p class="text-xs text-slate-400 mt-1">Selecione um perfil para autenticar imediatamente ou simular erros padronizados pela RFC 9457.</p>
          </div>

          <!-- Card Seed Personal -->
          <div class="p-4 rounded-xl bg-slate-950 border border-purple-900/60 space-y-3">
            <div class="flex items-center justify-between">
              <div>
                <div class="text-xs font-bold text-purple-300">👨‍🏫 Carlos Personal Trainer</div>
                <div class="text-[11px] font-mono text-slate-400">carlos@gymflow.dev • Personal@2026</div>
              </div>
              <span class="text-[10px] px-2 py-0.5 rounded-full bg-purple-900/60 text-purple-300 font-bold">PERSONAL</span>
            </div>
            <div class="grid grid-cols-2 gap-2">
              <button type="button" onclick="fillLoginCredentials('carlos@gymflow.dev', 'Personal@2026')"
                class="py-1.5 rounded-lg border border-slate-700 hover:bg-slate-800 text-xs font-semibold transition">
                📋 Preencher
              </button>
              <button type="button" onclick="loginAs('carlos@gymflow.dev', 'Personal@2026', true)"
                class="py-1.5 rounded-lg bg-purple-600 hover:bg-purple-500 text-xs font-semibold transition">
                🚀 Entrar Direto
              </button>
            </div>
          </div>

          <!-- Card Seed Student -->
          <div class="p-4 rounded-xl bg-slate-950 border border-emerald-900/60 space-y-3">
            <div class="flex items-center justify-between">
              <div>
                <div id="quickStudentName" class="text-xs font-bold text-emerald-300">🏃 Rodrigo Yoshi</div>
                <div id="quickStudentCreds" class="text-[11px] font-mono text-slate-400">rodrigoyoshi@gymflow.com • aluno123</div>
              </div>
              <span class="text-[10px] px-2 py-0.5 rounded-full bg-emerald-900/60 text-emerald-300 font-bold">STUDENT</span>
            </div>
            <div class="grid grid-cols-2 gap-2">
              <button type="button" onclick="fillQuickStudentCredentials()"
                class="py-1.5 rounded-lg border border-slate-700 hover:bg-slate-800 text-xs font-semibold transition">
                📋 Preencher
              </button>
              <button type="button" onclick="loginQuickStudent()"
                class="py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold transition">
                🚀 Entrar Direto
              </button>
            </div>
          </div>

          <!-- Simular Erro 401 RFC 9457 -->
          <button type="button" onclick="simulateInvalidLogin401()"
            class="w-full py-2.5 rounded-xl bg-rose-950/70 hover:bg-rose-900/70 border border-rose-800/70 text-rose-300 text-xs font-semibold transition">
            🛡️ Simular Credenciais Inválidas (Erro 401 Não Autenticado • RFC 9457)
          </button>
        </div>

        <!-- Console JSON da Tela de Autenticação -->
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-2 shadow-xl">
          <h3 class="text-xs font-bold uppercase tracking-wider text-slate-400">Payload de Autenticação (JWT / RFC 9457)</h3>
          <pre id="authResponseLog" class="text-xs font-mono bg-slate-950 border border-slate-800 rounded-xl p-4 text-slate-300 overflow-x-auto max-h-56">Aguardando autenticação em /api/v1/auth...</pre>
        </div>
      </div>
    </div>
  </section>

  <main id="dashboardScreen" class="hidden max-w-7xl mx-auto px-6 py-8 space-y-8">
    <!-- 1. Painel de Autenticação JWT & RBAC (Exclusivo DEV: Carlos Personal) -->
    <section id="devSessionPanel" class="hidden bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
      <div class="flex flex-wrap items-center justify-between gap-4 mb-4">
        <div>
          <h2 class="text-lg font-bold text-purple-400">1. Sessão Ativa JWT (HS256) & Alternância Rápida de Papel (RBAC — Exclusivo DEV Carlos)</h2>
          <p class="text-sm text-slate-400">
            <code class="text-purple-300">PERSONAL (DEV Carlos)</code>: painel administrativo de sessão e alternância de visão •
            <code class="text-emerald-300">STUDENT</code>: não possui acesso a este painel.
          </p>
        </div>
        <div class="flex flex-wrap gap-2">
          <button onclick="loginAs('carlos@gymflow.dev', 'Personal@2026', true)" class="px-3.5 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-xs font-semibold transition">👨‍🏫 Visão PERSONAL (Carlos)</button>
          <button id="devBtnStudentView" onclick="loginQuickStudent()" class="px-3.5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold transition">🏃 Visão STUDENT (Rodrigo Yoshi)</button>
          <button onclick="fetchCurrentUserMe()" class="px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-semibold transition">👤 GET /auth/me</button>
          <button onclick="testRbac403()" class="px-3.5 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-xs font-semibold transition">🛡️ Testar Bloqueio RBAC (403)</button>
          <button onclick="logoutUser()" class="px-3.5 py-2 rounded-lg border border-rose-800/80 bg-rose-950/50 hover:bg-rose-900/60 text-rose-300 text-xs font-semibold transition">🚪 Trocar Conta / Login</button>
        </div>
      </div>
      <div id="authStatus" class="text-xs font-mono bg-slate-950 border border-slate-800 rounded-xl p-4 text-slate-300 overflow-x-auto">
        Aguardando autenticação...
      </div>
    </section>

    <!-- 2. Conteúdo Extra: Analytics Biométrico (IMC) + RPE Borg -->
    <section class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-5">
        <span class="text-xs uppercase tracking-wider text-purple-400 font-semibold">Perfil do Aluno</span>
        <h3 class="text-xl font-bold mt-1" id="studentNameCard">Rodrigo Yoshi</h3>
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

    <!-- 3. Painel Principal Adaptativo por Role (PERSONAL vs STUDENT) -->
    <section class="grid grid-cols-1 lg:grid-cols-12 gap-6">
      <!-- Coluna Esquerda (7 cols): Ficha de Treino -->
      <div class="lg:col-span-7 bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-5">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 class="text-lg font-bold text-purple-400" id="workoutSectionTitle">2. Minha Ficha de Treino</h2>
            <p class="text-xs text-slate-400" id="workoutSectionSubtitle">Carregada com SQLAlchemy 2.0 selectinload (sem queries N+1).</p>
          </div>
          <button onclick="loadDashboardData()" class="text-xs px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 font-semibold">🔄 Atualizar</button>
        </div>

        <div id="workoutsContainer" class="space-y-4 text-sm text-slate-300">
          Carregando ficha de treino...
        </div>

        <!-- EXCLUSIVO PERSONAL: Formulário para Adicionar Exercício -->
        <div id="personalAddExercisePanel" class="border-t border-slate-800 pt-5 space-y-3">
          <h3 class="text-sm font-bold text-purple-300">➕ Prescrever Novo Exercício na Rotina (Exclusivo PERSONAL)</h3>
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
            ➕ Adicionar Exercício na Ficha
          </button>
        </div>

        <!-- EXCLUSIVO PERSONAL: Criar Nova Divisão de Rotina -->
        <div id="personalAddRoutinePanel" class="border-t border-slate-800 pt-5 space-y-3">
          <h3 class="text-sm font-bold text-purple-300">📋 Criar Nova Divisão de Rotina na Ficha (Exclusivo PERSONAL)</h3>
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

      <!-- Coluna Direita (5 cols): Painel Personal (oculto para Student) + Check-in RPE do Aluno + Console JSON -->
      <div class="lg:col-span-5 space-y-6">
        <!-- EXCLUSIVO PERSONAL: Editar Ficha de Treino & Biometria do Aluno -->
        <div id="personalEditPanel" class="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
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
        <div class="bg-slate-900 border border-emerald-900/50 rounded-2xl p-6 space-y-4">
          <div>
            <h2 class="text-lg font-bold text-emerald-400">Check-in Pós-Treino do Aluno (Escala RPE 1–10)</h2>
            <p class="text-xs text-slate-400">Registre a conclusão da rotina de hoje informando duração, esforço RPE Borg e feedback.</p>
          </div>
          <div>
            <label class="text-xs text-slate-400">Qual rotina você concluiu hoje?</label>
            <select id="checkinRoutineSelect" class="w-full mt-1 px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs"></select>
          </div>
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
            ✅ Realizar Check-in de Treino (POST /api/v1/routines/{id}/executions)
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

  <!-- MODAL DE DEMONSTRAÇÃO DE BLOQUEIO RBAC (403 FORBIDDEN • RFC 9457) -->
  <div id="rbacModal" onclick="handleRbacBackdropClick(event)" class="hidden fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
    <div class="bg-slate-900 border border-rose-800/80 rounded-2xl max-w-2xl w-full p-6 shadow-2xl shadow-rose-950/50 space-y-5 max-h-[90vh] overflow-y-auto">
      <!-- Cabeçalho do Modal -->
      <div class="flex items-start justify-between gap-4 border-b border-slate-800 pb-4">
        <div class="flex items-center gap-3">
          <span class="h-11 w-11 rounded-xl bg-rose-600/20 border border-rose-500/40 text-rose-400 flex items-center justify-center text-xl font-bold shrink-0">🛡️</span>
          <div>
            <div class="flex items-center gap-2">
              <h3 class="text-lg font-bold text-white">Bloqueio RBAC Detectado</h3>
              <span id="rbacModalStatusBadge" class="text-[11px] px-2.5 py-0.5 rounded-full bg-rose-950 border border-rose-700 text-rose-300 font-bold">HTTP 403 Acesso Proibido</span>
            </div>
            <p class="text-xs text-slate-400 mt-0.5">Simulação de acesso não autorizado interceptado por <code class="text-rose-300">require_roles(UserRole.PERSONAL)</code> • Padrão <b>RFC 9457</b></p>
          </div>
        </div>
        <button onclick="closeRbacModal()" class="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-bold transition">✕</button>
      </div>

      <!-- Seletor de Cenários Proibidos para STUDENT -->
      <div class="space-y-2">
        <span class="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">Testar Cenários Restritos a PERSONAL usando Token de STUDENT (Rodrigo):</span>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <button onclick="runRbacScenario('DELETE_STUDENT')" class="px-3 py-2 rounded-xl bg-slate-950 hover:bg-rose-950/40 border border-slate-800 hover:border-rose-700/70 text-left text-xs transition">
            <div class="font-bold text-rose-300">🗑️ DELETE /api/v1/students/{id}</div>
            <div class="text-[11px] text-slate-400">Aluno tentando remover um aluno da carteira</div>
          </button>
          <button onclick="runRbacScenario('LIST_STUDENTS')" class="px-3 py-2 rounded-xl bg-slate-950 hover:bg-rose-950/40 border border-slate-800 hover:border-rose-700/70 text-left text-xs transition">
            <div class="font-bold text-rose-300">📋 GET /api/v1/students</div>
            <div class="text-[11px] text-slate-400">Aluno tentando listar carteira do Personal</div>
          </button>
          <button onclick="runRbacScenario('CREATE_WORKOUT')" class="px-3 py-2 rounded-xl bg-slate-950 hover:bg-rose-950/40 border border-slate-800 hover:border-rose-700/70 text-left text-xs transition">
            <div class="font-bold text-rose-300">🏋️ POST /api/v1/workouts</div>
            <div class="text-[11px] text-slate-400">Aluno tentando prescrever ficha de treino</div>
          </button>
          <button onclick="runRbacScenario('ADD_EXERCISE')" class="px-3 py-2 rounded-xl bg-slate-950 hover:bg-rose-950/40 border border-slate-800 hover:border-rose-700/70 text-left text-xs transition">
            <div class="font-bold text-rose-300">➕ POST /api/v1/routines/{id}/exercises</div>
            <div class="text-[11px] text-slate-400">Aluno tentando adicionar exercício na rotina</div>
          </button>
        </div>
      </div>

      <!-- Resumo da Tentativa & Campos RFC 9457 -->
      <div class="p-4 rounded-xl bg-rose-950/30 border border-rose-900/60 space-y-3 text-xs">
        <div class="flex flex-wrap items-center justify-between gap-2 border-b border-rose-900/40 pb-2.5">
          <div>
            <span class="text-slate-400">Token JWT Utilizado:</span>
            <span id="rbacModalTokenUser" class="font-mono text-emerald-300 font-bold ml-1">rodrigoyoshi@gymflow.com (papel: STUDENT)</span>
          </div>
          <div>
            <span class="text-slate-400">Requisição:</span>
            <code id="rbacModalEndpoint" class="font-mono text-rose-300 font-bold ml-1">DELETE /api/v1/students/...</code>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          <div class="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800">
            <div class="text-[10px] uppercase text-slate-400">RFC 9457 • type</div>
            <div id="rbacModalType" class="font-mono text-rose-400 text-[11px] truncate mt-0.5">https://api.gymflow.dev/errors/forbidden</div>
          </div>
          <div class="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800">
            <div class="text-[10px] uppercase text-slate-400">RFC 9457 • title & status</div>
            <div id="rbacModalTitle" class="font-mono text-white font-bold text-[11px] mt-0.5">Acesso Proibido (403)</div>
          </div>
        </div>

        <div class="p-3 rounded-lg bg-slate-950/90 border border-rose-900/60">
          <div class="text-[10px] uppercase text-rose-400 font-semibold">RFC 9457 • detail (Motivo do Bloqueio RBAC)</div>
          <div id="rbacModalDetail" class="text-slate-200 mt-1 font-medium">Acesso negado.</div>
        </div>
      </div>

      <!-- Payload JSON Completo -->
      <div class="space-y-1.5">
        <div class="flex items-center justify-between text-xs">
          <span class="font-bold uppercase tracking-wider text-slate-400 text-[11px]">Payload Retornado (Content-Type: application/problem+json)</span>
        </div>
        <pre id="rbacModalJson" class="text-xs font-mono bg-slate-950 border border-slate-800 rounded-xl p-4 text-rose-300 overflow-x-auto max-h-48">Executando simulação RBAC...</pre>
      </div>

      <!-- Rodapé do Modal -->
      <div class="flex items-center justify-end gap-3 pt-2 border-t border-slate-800">
        <button onclick="closeRbacModal()" class="px-5 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold transition shadow-lg shadow-rose-600/20">
          Entendido • Fechar Modal
        </button>
      </div>
    </div>
  </div>

  <!-- MODAL DE SIMULAÇÃO DE FALHA DE AUTENTICAÇÃO (401 UNAUTHORIZED • RFC 9457) -->
  <div id="auth401Modal" onclick="handleAuth401BackdropClick(event)" class="hidden fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
    <div class="bg-slate-900 border border-amber-700/80 rounded-2xl max-w-2xl w-full p-6 shadow-2xl shadow-amber-950/40 space-y-5 max-h-[90vh] overflow-y-auto">
      <!-- Cabeçalho do Modal -->
      <div class="flex items-start justify-between gap-4 border-b border-slate-800 pb-4">
        <div class="flex items-center gap-3">
          <span class="h-11 w-11 rounded-xl bg-amber-500/20 border border-amber-500/40 text-amber-400 flex items-center justify-center text-xl font-bold shrink-0">🔐</span>
          <div>
            <div class="flex items-center gap-2">
              <h3 class="text-lg font-bold text-white">Falha de Autenticação Detectada</h3>
              <span id="auth401ModalStatusBadge" class="text-[11px] px-2.5 py-0.5 rounded-full bg-amber-950 border border-amber-700 text-amber-300 font-bold">HTTP 401 Não Autenticado</span>
            </div>
            <p class="text-xs text-slate-400 mt-0.5">Simulação de credenciais inválidas ou token JWT ausente/corrompido • Padrão <b>RFC 9457</b></p>
          </div>
        </div>
        <button onclick="closeAuth401Modal()" class="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-bold transition">✕</button>
      </div>

      <!-- Seletor de Cenários 401 Não Autenticado -->
      <div class="space-y-2">
        <span class="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">Escolha o Cenário de Erro 401 para Simular ao Vivo na API:</span>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <button onclick="runAuth401Scenario('WRONG_PASSWORD')" class="px-3 py-2 rounded-xl bg-slate-950 hover:bg-amber-950/40 border border-slate-800 hover:border-amber-700/70 text-left text-xs transition">
            <div class="font-bold text-amber-300">🔑 Senha Incorreta no Login</div>
            <div class="text-[11px] text-slate-400">POST /api/v1/auth/login (carlos@gymflow.dev)</div>
          </button>
          <button onclick="runAuth401Scenario('UNKNOWN_EMAIL')" class="px-3 py-2 rounded-xl bg-slate-950 hover:bg-amber-950/40 border border-slate-800 hover:border-amber-700/70 text-left text-xs transition">
            <div class="font-bold text-amber-300">📧 E-mail Não Cadastrado</div>
            <div class="text-[11px] text-slate-400">POST /api/v1/auth/login (inexistente@gymflow.dev)</div>
          </button>
          <button onclick="runAuth401Scenario('MISSING_TOKEN')" class="px-3 py-2 rounded-xl bg-slate-950 hover:bg-amber-950/40 border border-slate-800 hover:border-amber-700/70 text-left text-xs transition">
            <div class="font-bold text-amber-300">🚫 Rota Protegida Sem Token JWT</div>
            <div class="text-[11px] text-slate-400">GET /api/v1/auth/me (sem header Authorization)</div>
          </button>
          <button onclick="runAuth401Scenario('TAMPERED_TOKEN')" class="px-3 py-2 rounded-xl bg-slate-950 hover:bg-amber-950/40 border border-slate-800 hover:border-amber-700/70 text-left text-xs transition">
            <div class="font-bold text-amber-300">⚠️ Token JWT Adulterado / Inválido</div>
            <div class="text-[11px] text-slate-400">GET /api/v1/workouts (assinatura HS256 inválida)</div>
          </button>
        </div>
      </div>

      <!-- Resumo da Tentativa & Campos RFC 9457 -->
      <div class="p-4 rounded-xl bg-amber-950/25 border border-amber-900/60 space-y-3 text-xs">
        <div class="flex flex-wrap items-center justify-between gap-2 border-b border-amber-900/40 pb-2.5">
          <div>
            <span class="text-slate-400">Credencial / Header:</span>
            <span id="auth401ModalCredential" class="font-mono text-amber-300 font-bold ml-1">carlos@gymflow.dev / SenhaIncorreta999</span>
          </div>
          <div>
            <span class="text-slate-400">Requisição:</span>
            <code id="auth401ModalEndpoint" class="font-mono text-rose-300 font-bold ml-1">POST /api/v1/auth/login</code>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          <div class="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800">
            <div class="text-[10px] uppercase text-slate-400">RFC 9457 • type</div>
            <div id="auth401ModalType" class="font-mono text-amber-400 text-[11px] truncate mt-0.5">https://api.gymflow.dev/errors/unauthorized</div>
          </div>
          <div class="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800">
            <div class="text-[10px] uppercase text-slate-400">RFC 9457 • title & status</div>
            <div id="auth401ModalTitle" class="font-mono text-white font-bold text-[11px] mt-0.5">Não Autorizado (401)</div>
          </div>
        </div>

        <div class="p-3 rounded-lg bg-slate-950/90 border border-amber-900/60">
          <div class="text-[10px] uppercase text-amber-400 font-semibold">RFC 9457 • detail (Diagnóstico da Falha 401)</div>
          <div id="auth401ModalDetail" class="text-slate-200 mt-1 font-medium">Credenciais inválidas: e-mail ou senha incorretos.</div>
        </div>
      </div>

      <!-- Payload JSON Completo -->
      <div class="space-y-1.5">
        <div class="flex items-center justify-between text-xs">
          <span class="font-bold uppercase tracking-wider text-slate-400 text-[11px]">Payload Retornado (Content-Type: application/problem+json)</span>
        </div>
        <pre id="auth401ModalJson" class="text-xs font-mono bg-slate-950 border border-slate-800 rounded-xl p-4 text-amber-300 overflow-x-auto max-h-48">Executando simulação 401...</pre>
      </div>

      <!-- Rodapé do Modal -->
      <div class="flex items-center justify-end gap-3 pt-2 border-t border-slate-800">
        <button onclick="closeAuth401Modal()" class="px-5 py-2 rounded-xl bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold transition shadow-lg shadow-amber-600/20">
          Entendido • Fechar Modal
        </button>
      </div>
    </div>
  </div>

  <script>
    let currentToken = "";
    let currentRole = "PERSONAL";
    let currentUser = null;
    let currentWorkoutId = "33333333-3333-3333-3333-333333333333";
    let STUDENT_ID = "865e96a4-7b2a-45e3-a2ad-a7f3cd5610bb";
    const DEFAULT_ROUTINE_ID = "44444444-4444-4444-4444-444444444444";

    let quickStudent = {
      id: "865e96a4-7b2a-45e3-a2ad-a7f3cd5610bb",
      name: "Rodrigo Yoshi",
      email: "rodrigoyoshi@gymflow.com",
      password: "aluno123"
    };

    function updateQuickStudentCard(studentObj) {
      quickStudent = { ...quickStudent, ...studentObj };
      if (quickStudent.id) {
        STUDENT_ID = quickStudent.id;
      }
      const nameEl = document.getElementById("quickStudentName");
      const credsEl = document.getElementById("quickStudentCreds");
      const devBtnEl = document.getElementById("devBtnStudentView");
      const modalTokenEl = document.getElementById("rbacModalTokenUser");
      if (nameEl) nameEl.textContent = `🏃 ${quickStudent.name}`;
      if (credsEl) credsEl.textContent = `${quickStudent.email} • ${quickStudent.password}`;
      if (devBtnEl) devBtnEl.textContent = `🏃 Visão STUDENT (${quickStudent.name})`;
      if (modalTokenEl) modalTokenEl.textContent = `${quickStudent.email} (papel: STUDENT)`;
    }

    function fillQuickStudentCredentials() {
      fillLoginCredentials(quickStudent.email, quickStudent.password);
    }

    async function loginQuickStudent() {
      const probe = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: quickStudent.email, password: quickStudent.password })
      });
      if (!probe.ok) {
        updateQuickStudentCard({
          id: "22222222-2222-2222-2222-222222222222",
          name: "Rodrigo Aluno",
          email: "rodrigo@gymflow.dev",
          password: "Aluno@2026"
        });
      }
      await loginAs(quickStudent.email, quickStudent.password, true);
    }

    function logApiResult(status, data) {
      const prefix = status >= 400 ? `❌ HTTP ${status} (Padrão de Erro RFC 9457)` : `✅ HTTP ${status}`;
      const formatted = `${prefix}\n` + JSON.stringify(data, null, 2);
      const dashLog = document.getElementById("apiResponseLog");
      const authLog = document.getElementById("authResponseLog");
      if (dashLog) dashLog.textContent = formatted;
      if (authLog) authLog.textContent = formatted;
    }

    function showAuthFeedback(isError, title, detail, invalidParams) {
      const banner = document.getElementById("authFeedbackBanner");
      if (!banner) return;
      banner.classList.remove(
        "hidden",
        "bg-rose-950/70",
        "border-rose-800",
        "text-rose-200",
        "bg-emerald-950/70",
        "border-emerald-800",
        "text-emerald-200"
      );
      if (isError) {
        banner.classList.add("bg-rose-950/70", "border-rose-800", "text-rose-200");
      } else {
        banner.classList.add("bg-emerald-950/70", "border-emerald-800", "text-emerald-200");
      }

      let paramsHtml = "";
      if (Array.isArray(invalidParams) && invalidParams.length > 0) {
        paramsHtml = `<ul class="mt-2 list-disc list-inside space-y-0.5 text-[11px] font-mono">` +
          invalidParams.map(p => `<li><b>${p.name}</b>: ${p.reason}</li>`).join("") +
          `</ul>`;
      }
      banner.innerHTML = `<div class="font-bold">${isError ? "❌ " : "✅ "}${title}</div><div class="mt-0.5 opacity-90">${detail}</div>${paramsHtml}`;
    }

    function hideAuthFeedback() {
      const banner = document.getElementById("authFeedbackBanner");
      if (banner) banner.classList.add("hidden");
    }

    function switchAuthTab(tab) {
      hideAuthFeedback();
      const isLogin = tab === "login";
      document.getElementById("loginForm").classList.toggle("hidden", !isLogin);
      document.getElementById("registerForm").classList.toggle("hidden", isLogin);

      const loginBtn = document.getElementById("tabLoginBtn");
      const regBtn = document.getElementById("tabRegisterBtn");
      if (isLogin) {
        loginBtn.className = "py-2.5 rounded-lg bg-purple-600 text-white text-xs font-bold transition shadow";
        regBtn.className = "py-2.5 rounded-lg text-slate-400 hover:text-white text-xs font-bold transition";
      } else {
        regBtn.className = "py-2.5 rounded-lg bg-emerald-600 text-white text-xs font-bold transition shadow";
        loginBtn.className = "py-2.5 rounded-lg text-slate-400 hover:text-white text-xs font-bold transition";
      }
    }

    function selectRegisterRole(role) {
      document.getElementById("regRole").value = role;
      const isPersonal = role === "PERSONAL";
      const btnPersonal = document.getElementById("roleBtnPersonal");
      const btnStudent = document.getElementById("roleBtnStudent");
      const crefGroup = document.getElementById("regCrefGroup");

      if (isPersonal) {
        btnPersonal.className = "p-3 rounded-xl border border-purple-500 bg-purple-950/50 text-left transition";
        btnStudent.className = "p-3 rounded-xl border border-slate-800 bg-slate-950 text-left transition";
        crefGroup.classList.remove("hidden");
      } else {
        btnStudent.className = "p-3 rounded-xl border border-emerald-500 bg-emerald-950/50 text-left transition";
        btnPersonal.className = "p-3 rounded-xl border border-slate-800 bg-slate-950 text-left transition";
        crefGroup.classList.add("hidden");
      }
    }

    function togglePasswordInput(inputId, btn) {
      const input = document.getElementById(inputId);
      if (!input) return;
      if (input.type === "password") {
        input.type = "text";
        btn.textContent = "Ocultar";
      } else {
        input.type = "password";
        btn.textContent = "Mostrar";
      }
    }

    function fillLoginCredentials(email, password) {
      switchAuthTab("login");
      document.getElementById("loginEmail").value = email;
      document.getElementById("loginPassword").value = password;
      showAuthFeedback(false, "Credenciais preenchidas", `Pronto para autenticar como ${email}.`);
    }

    async function handleLoginSubmit(event) {
      event.preventDefault();
      const email = document.getElementById("loginEmail").value.trim();
      const password = document.getElementById("loginPassword").value;
      await loginAs(email, password, true);
    }

    async function handleRegisterSubmit(event) {
      event.preventDefault();
      hideAuthFeedback();
      const role = document.getElementById("regRole").value;
      const name = document.getElementById("regName").value.trim();
      const email = document.getElementById("regEmail").value.trim();
      const password = document.getElementById("regPassword").value;
      const phone = document.getElementById("regPhone").value.trim() || null;
      const crefVal = document.getElementById("regCref").value.trim();
      const cref = role === "PERSONAL" ? (crefVal || null) : null;

      const res = await fetch("/api/v1/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, password, role, cref, phone })
      });
      const data = await res.json();
      logApiResult(res.status, data);

      if (res.ok) {
        if (role === "STUDENT") {
          updateQuickStudentCard({ id: data.id, name: data.name, email: data.email, password });
        }
        showAuthFeedback(
          false,
          `Conta criada com sucesso (HTTP ${res.status})`,
          `Usuário ${data.name} (${data.role}) registrado. Autenticando automaticamente...`
        );
        await loginAs(email, password, true);
      } else {
        showAuthFeedback(
          true,
          `${data.title || "Erro no Cadastro"} (HTTP ${res.status})`,
          data.detail || "Falha ao registrar usuário.",
          data.invalidParams
        );
      }
    }

    function openAuth401Modal() {
      document.getElementById("auth401Modal").classList.remove("hidden");
    }

    function closeAuth401Modal() {
      document.getElementById("auth401Modal").classList.add("hidden");
    }

    function handleAuth401BackdropClick(event) {
      if (event.target.id === "auth401Modal") {
        closeAuth401Modal();
      }
    }

    async function runAuth401Scenario(scenarioKey) {
      openAuth401Modal();
      document.getElementById("auth401ModalJson").textContent = "Executando requisição contra a API...";

      let method = "POST";
      let url = "/api/v1/auth/login";
      let headers = { "Content-Type": "application/json" };
      let body = { email: "carlos@gymflow.dev", password: "SenhaIncorreta999" };
      let credentialDesc = "carlos@gymflow.dev / SenhaIncorreta999";

      if (scenarioKey === "UNKNOWN_EMAIL") {
        body = { email: "inexistente@gymflow.dev", password: "QualquerSenha123" };
        credentialDesc = "inexistente@gymflow.dev / QualquerSenha123";
      } else if (scenarioKey === "MISSING_TOKEN") {
        method = "GET";
        url = "/api/v1/auth/me";
        headers = {};
        body = null;
        credentialDesc = "Sem Header Authorization";
      } else if (scenarioKey === "TAMPERED_TOKEN") {
        method = "GET";
        url = "/api/v1/workouts";
        headers = { "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJmYWtlIn0.assinatura_invalida" };
        body = null;
        credentialDesc = "Bearer <token_jwt_adulterado>";
      }

      if (body && document.getElementById("loginEmail")) {
        switchAuthTab("login");
        document.getElementById("loginEmail").value = body.email;
        document.getElementById("loginPassword").value = body.password;
      }

      const res = await fetch(url, {
        method,
        headers,
        ...(body ? { body: JSON.stringify(body) } : {})
      });
      const data = await res.json();

      document.getElementById("auth401ModalStatusBadge").textContent = `HTTP ${res.status} Não Autenticado`;
      document.getElementById("auth401ModalCredential").textContent = credentialDesc;
      document.getElementById("auth401ModalEndpoint").textContent = `${method} ${url}`;
      document.getElementById("auth401ModalType").textContent = data.type || "https://api.gymflow.dev/errors/unauthorized";
      document.getElementById("auth401ModalTitle").textContent = `${data.title || "Não Autenticado"} (${data.status || res.status})`;
      document.getElementById("auth401ModalDetail").textContent = data.detail || "Falha de autenticação.";
      document.getElementById("auth401ModalJson").textContent = JSON.stringify(data, null, 2);

      showAuthFeedback(
        true,
        `${data.title || "Falha na Autenticação"} (HTTP ${res.status})`,
        data.detail || "Credenciais inválidas.",
        data.invalidParams
      );
      logApiResult(res.status, data);
    }

    async function simulateInvalidLogin401() {
      await runAuth401Scenario("WRONG_PASSWORD");
    }

    async function fetchCurrentUserMe() {
      const res = await fetch("/api/v1/auth/me", {
        headers: currentToken ? { "Authorization": `Bearer ${currentToken}` } : {}
      });
      const data = await res.json();
      logApiResult(res.status, data);
    }

    function logoutUser() {
      currentToken = "";
      currentUser = null;
      document.getElementById("dashboardScreen").classList.add("hidden");
      document.getElementById("authScreen").classList.remove("hidden");
      document.getElementById("headerUserBadge").classList.add("hidden");
      document.getElementById("headerLogoutBtn").classList.add("hidden");
      showAuthFeedback(false, "Sessão encerrada", "Token JWT descartado. Faça login novamente ou crie uma nova conta.");
    }

    function applyRoleVisibility() {
      const isPersonal = currentRole === "PERSONAL";
      const isDevCarlos = isPersonal && currentUser && currentUser.email.toLowerCase() === "carlos@gymflow.dev";
      document.getElementById("devSessionPanel").classList.toggle("hidden", !isDevCarlos);
      document.getElementById("personalAddExercisePanel").classList.toggle("hidden", !isPersonal);
      document.getElementById("personalAddRoutinePanel").classList.toggle("hidden", !isPersonal);
      document.getElementById("personalEditPanel").classList.toggle("hidden", !isPersonal);

      document.getElementById("workoutSectionTitle").textContent = isPersonal
        ? "2. Gestão de Fichas de Treino (Visão do Personal Trainer)"
        : "Minha Ficha de Treino (Visão do Aluno — Somente Leitura)";
      document.getElementById("workoutSectionSubtitle").textContent = isPersonal
        ? "Como PERSONAL, você pode editar a ficha, adicionar divisões de rotina e prescrever ou remover exercícios."
        : "Como STUDENT, você visualiza sua ficha prescrita pelo Personal e realiza o check-in pós-treino ao lado.";
    }

    async function loginAs(email, password, enterDashboard = true) {
      const res = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });
      const data = await res.json();
      if (res.ok) {
        currentToken = data.accessToken;
        currentRole = data.user.role;
        currentUser = data.user;
        applyRoleVisibility();

        const badgeColor = currentRole === "PERSONAL" ? "text-purple-400" : "text-emerald-400";
        const modeDesc = currentRole === "PERSONAL"
          ? "Modo Edição Habilitado (Personal Trainer)"
          : "Modo Aluno (Apenas Visualização da Ficha & Check-in RPE)";
        document.getElementById("authStatus").innerHTML =
          `✅ Autenticado como <b>${data.user.name}</b> (${data.user.email}) | Papel RBAC: <b class="${badgeColor}">${currentRole}</b> — <span>${modeDesc}</span>`;

        const headerBadge = document.getElementById("headerUserBadge");
        headerBadge.innerHTML = `🔐 <b>${data.user.name}</b> (<span class="${badgeColor} font-bold">${currentRole}</span>)`;
        headerBadge.classList.remove("hidden");
        document.getElementById("headerLogoutBtn").classList.remove("hidden");

        if (enterDashboard) {
          document.getElementById("authScreen").classList.add("hidden");
          document.getElementById("dashboardScreen").classList.remove("hidden");
        }

        logApiResult(res.status, data);
        await loadDashboardData();
      } else {
        showAuthFeedback(
          true,
          `${data.title || "Falha na Autenticação"} (HTTP ${res.status})`,
          data.detail || "Credenciais inválidas.",
          data.invalidParams
        );
        logApiResult(res.status, data);
      }
    }

    async function loadDashboardData() {
      if (!currentToken) return;
      const headers = { "Authorization": `Bearer ${currentToken}` };
      const isPersonal = currentRole === "PERSONAL";
      const targetStudentId = (!isPersonal && currentUser && currentUser.id) ? currentUser.id : STUDENT_ID;

      const anaRes = await fetch(`/api/v1/students/${targetStudentId}/analytics`, { headers });
      if (anaRes.ok) {
        const ana = await anaRes.json();
        document.getElementById("studentNameCard").textContent = ana.studentName;
        document.getElementById("studentGoalCard").textContent = `Meta: ${ana.goal || "GENERAL_FITNESS"}`;
        document.getElementById("bmiValue").textContent = ana.bmi ? `${ana.bmi} kg/m²` : "--";
        document.getElementById("bmiClass").textContent = ana.bmiClassification
          ? `${ana.bmiClassification} (${ana.weightKg}kg / ${ana.heightCm}cm)`
          : "Perfil biométrico ainda não preenchido";
        document.getElementById("execCount").textContent = `${ana.totalExecutions} check-in(s)`;
        document.getElementById("totalMinutes").textContent = `${ana.totalDurationMinutes} minutos totais acumulados`;
        document.getElementById("avgRpe").textContent = `RPE ${ana.averageRpeScore} / 10`;
      }

      const wkRes = await fetch("/api/v1/workouts", { headers });
      if (wkRes.ok) {
        const wkData = await wkRes.json();
        const container = document.getElementById("workoutsContainer");
        const routineSelect = document.getElementById("exRoutineSelect");
        const checkinRoutineSelect = document.getElementById("checkinRoutineSelect");
        const workoutSelect = document.getElementById("routineWorkoutSelect");

        routineSelect.innerHTML = "";
        checkinRoutineSelect.innerHTML = "";
        workoutSelect.innerHTML = "";

        if (wkData.data.length > 0) {
          currentWorkoutId = wkData.data[0].id;
        } else {
          container.innerHTML = `<div class="p-4 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-400">Nenhuma ficha de treino encontrada para este usuário.</div>`;
          return;
        }

        container.innerHTML = wkData.data.map(plan => {
          workoutSelect.innerHTML += `<option value="${plan.id}">${plan.title}</option>`;
          plan.routines.forEach(r => {
            const optHtml = `<option value="${r.id}">${plan.title} ➔ ${r.name}</option>`;
            routineSelect.innerHTML += optHtml;
            checkinRoutineSelect.innerHTML += optHtml;
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
                        <div>
                          <span>• <b>${ex.name}</b> <span class="text-purple-400">[${ex.muscleGroup}]</span> — ${ex.sets}x ${ex.reps} • <b>${ex.weightKg || 0}kg</b> (descanso ${ex.restSeconds}s)</span>
                          ${ex.notes ? `<div class="text-[11px] text-slate-400 pl-3 mt-0.5">💡 ${ex.notes}</div>` : ""}
                        </div>
                        ${isPersonal ? `<button onclick="deleteExercise('${ex.id}')" title="Remover exercício" class="text-rose-400 hover:text-rose-300 text-xs font-bold px-2 py-0.5 rounded bg-rose-950/50 hover:bg-rose-900/60 transition shrink-0">🗑️ Excluir</button>` : ""}
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
      const routineId = document.getElementById("checkinRoutineSelect").value || DEFAULT_ROUTINE_ID;
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

    function openRbacModal() {
      document.getElementById("rbacModal").classList.remove("hidden");
    }

    function closeRbacModal() {
      document.getElementById("rbacModal").classList.add("hidden");
    }

    function handleRbacBackdropClick(event) {
      if (event.target.id === "rbacModal") {
        closeRbacModal();
      }
    }

    window.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeRbacModal();
        closeAuth401Modal();
      }
    });

    async function runRbacScenario(scenarioKey) {
      openRbacModal();
      document.getElementById("rbacModalJson").textContent = "Autenticando token STUDENT e executando requisição...";

      const loginRes = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: quickStudent.email, password: quickStudent.password })
      });
      const loginData = await loginRes.json();
      const studentToken = loginData.accessToken || currentToken;

      let method = "DELETE";
      let url = `/api/v1/students/${STUDENT_ID}`;
      let body = null;

      if (scenarioKey === "LIST_STUDENTS") {
        method = "GET";
        url = "/api/v1/students";
      } else if (scenarioKey === "CREATE_WORKOUT") {
        method = "POST";
        url = "/api/v1/workouts";
        body = {
          studentId: STUDENT_ID,
          title: "Tentativa de Ficha pelo Aluno",
          status: "ACTIVE",
          startDate: "2026-06-01",
          endDate: "2026-07-01",
          routines: []
        };
      } else if (scenarioKey === "ADD_EXERCISE") {
        method = "POST";
        url = `/api/v1/routines/${DEFAULT_ROUTINE_ID}/exercises`;
        body = {
          name: "Supino Reto",
          muscleGroup: "CHEST",
          sets: 4,
          reps: "10",
          restSeconds: 60,
          weightKg: 60.0,
          order: 1
        };
      }

      const res = await fetch(url, {
        method,
        headers: {
          "Authorization": `Bearer ${studentToken}`,
          ...(body ? { "Content-Type": "application/json" } : {})
        },
        ...(body ? { body: JSON.stringify(body) } : {})
      });
      const data = await res.json();

      document.getElementById("rbacModalStatusBadge").textContent = `HTTP ${res.status} Acesso Proibido`;
      document.getElementById("rbacModalEndpoint").textContent = `${method} ${url}`;
      document.getElementById("rbacModalType").textContent = data.type || "https://api.gymflow.dev/errors/forbidden";
      document.getElementById("rbacModalTitle").textContent = `${data.title || "Acesso Proibido"} (${data.status || res.status})`;
      document.getElementById("rbacModalDetail").textContent = data.detail || "Acesso proibido pelo controle RBAC.";
      document.getElementById("rbacModalJson").textContent = JSON.stringify(data, null, 2);

      logApiResult(res.status, data);
    }

    async function testRbac403() {
      await runRbacScenario("DELETE_STUDENT");
    }
  </script>
</body>
</html>
"""

SWAGGER_DOCS_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>GymFlow API — Documentação Interativa e Guia Passo a Passo (/docs)</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css" />
  <style>
    :root {
      color-scheme: light;
    }
    body {
      margin: 0;
      background: #f8fafc;
      color: #0f172a;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    .gf-topbar {
      background: #0f172a;
      color: #f8fafc;
      border-bottom: 1px solid #334155;
      padding: 14px 24px;
      position: sticky;
      top: 0;
      z-index: 100;
    }
    .gf-topbar-inner {
      max-width: 1280px;
      margin: 0 auto;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }
    .gf-brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .gf-logo {
      width: 38px;
      height: 38px;
      border-radius: 10px;
      background: #7c3aed;
      color: #ffffff;
      font-weight: 800;
      font-size: 16px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .gf-brand h1 {
      margin: 0;
      font-size: 16px;
      font-weight: 700;
      letter-spacing: -0.02em;
    }
    .gf-brand p {
      margin: 2px 0 0;
      font-size: 12px;
      color: #cbd5e1;
    }
    .gf-nav-actions {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
    }
    .gf-status-pill {
      font-size: 12px;
      font-weight: 600;
      padding: 6px 12px;
      border-radius: 8px;
      background: #1e293b;
      border: 1px solid #475569;
      color: #e2e8f0;
    }
    .gf-status-pill.active-personal {
      background: #2e1065;
      border-color: #8b5cf6;
      color: #ddd6fe;
    }
    .gf-status-pill.active-student {
      background: #064e3b;
      border-color: #10b981;
      color: #a7f3d0;
    }
    .gf-link-btn {
      text-decoration: none;
      font-size: 12px;
      font-weight: 600;
      padding: 7px 12px;
      border-radius: 8px;
      background: #1e293b;
      color: #f8fafc;
      border: 1px solid #334155;
      transition: background 0.15s ease;
    }
    .gf-link-btn:hover {
      background: #334155;
    }
    .gf-guide-wrap {
      max-width: 1280px;
      margin: 20px auto 8px;
      padding: 0 20px;
    }
    .gf-guide-panel {
      background: #ffffff;
      border: 1px solid #cbd5e1;
      border-radius: 14px;
      padding: 20px 24px;
      box-shadow: 0 4px 14px rgba(15, 23, 42, 0.05);
    }
    .gf-guide-header {
      display: flex;
      flex-wrap: wrap;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      padding-bottom: 14px;
      border-bottom: 1px solid #e2e8f0;
    }
    .gf-guide-header h2 {
      margin: 0;
      font-size: 18px;
      font-weight: 700;
      color: #0f172a;
      letter-spacing: -0.02em;
    }
    .gf-guide-header p {
      margin: 4px 0 0;
      font-size: 13px;
      color: #334155;
      max-width: 72ch;
      line-height: 1.5;
    }
    .gf-steps-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 16px;
      margin-top: 16px;
    }
    .gf-step-box {
      background: #f8fafc;
      border: 1px solid #cbd5e1;
      border-radius: 12px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 12px;
    }
    .gf-step-title {
      font-size: 14px;
      font-weight: 700;
      color: #1e293b;
      margin: 0 0 6px;
    }
    .gf-step-desc {
      font-size: 12.5px;
      color: #334155;
      margin: 0;
      line-height: 1.5;
    }
    .gf-btn-group {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .gf-btn {
      cursor: pointer;
      border: none;
      border-radius: 8px;
      padding: 8px 12px;
      font-size: 12px;
      font-weight: 700;
      transition: filter 0.15s ease;
    }
    .gf-btn:hover {
      filter: brightness(1.08);
    }
    .gf-btn-personal {
      background: #6d28d9;
      color: #ffffff;
    }
    .gf-btn-student {
      background: #047857;
      color: #ffffff;
    }
    .gf-btn-clear {
      background: #be123c;
      color: #ffffff;
    }
    .gf-btn-focus {
      background: #0f172a;
      color: #ffffff;
    }
    .gf-btn-secondary {
      background: #e2e8f0;
      color: #0f172a;
    }
    .gf-live-result {
      margin-top: 16px;
      background: #0f172a;
      color: #e2e8f0;
      border-radius: 12px;
      padding: 14px 16px;
      font-size: 12px;
    }
    .gf-live-result-header {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      margin-bottom: 8px;
      font-weight: 700;
      color: #cbd5e1;
    }
    .gf-live-pre {
      margin: 0;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 12px;
      line-height: 1.45;
      overflow-x: auto;
      max-height: 220px;
      color: #a7f3d0;
    }
    .gf-live-pre.is-error {
      color: #fda4af;
    }
    .gf-tests-details {
      margin-top: 14px;
      background: #f1f5f9;
      border: 1px solid #cbd5e1;
      border-radius: 10px;
      padding: 10px 14px;
      font-size: 12.5px;
      color: #1e293b;
    }
    .gf-tests-details summary {
      cursor: pointer;
      font-weight: 700;
      color: #0f172a;
    }
    .gf-tests-details ol {
      margin: 8px 0 0;
      padding-left: 20px;
      line-height: 1.6;
    }
    .swagger-ui .topbar {
      display: none !important;
    }
    .swagger-ui .info {
      margin: 20px 0 !important;
    }
    #operations-Authentication-get_me_api_v1_auth_me_get {
      border-width: 2px !important;
      box-shadow: 0 4px 16px rgba(109, 40, 217, 0.12);
    }
  </style>
</head>
<body>
  <header class="gf-topbar">
    <div class="gf-topbar-inner">
      <div class="gf-brand">
        <div class="gf-logo">GF</div>
        <div>
          <h1>GymFlow API — Documentação Interativa e Guia Passo a Passo</h1>
          <p>Fatec Ribeirão Preto • João Gabriel Cardoso • Rodrigo de Azevedo Jr. • Thales de Oliveira Silva</p>
        </div>
      </div>
      <div class="gf-nav-actions">
        <span id="gfAuthBadge" class="gf-status-pill">Sessão JWT: Não autenticada (clique no Passo 1 abaixo)</span>
        <a href="#/Authentication/get_me_api_v1_auth_me_get" onclick="focusGetMeEndpoint()" class="gf-link-btn">Ir para GET /api/v1/auth/me</a>
        <a href="/" class="gf-link-btn">Painel Visual (/)</a>
        <a href="/openapi.json" target="_blank" class="gf-link-btn">Contrato JSON (/openapi.json)</a>
      </div>
    </div>
  </header>

  <section class="gf-guide-wrap">
    <div class="gf-guide-panel">
      <div class="gf-guide-header">
        <div>
          <h2>Guia Passo a Passo: Como Autenticar e Testar <code>GET /api/v1/auth/me</code></h2>
          <p>
            A rota <code>GET /api/v1/auth/me</code> (<code>#/Authentication/get_me_api_v1_auth_me_get</code>) exige um
            <strong>Token JWT (HS256)</strong> válido no cabeçalho <code>Authorization: Bearer &lt;token&gt;</code>.
            Siga os 3 passos abaixo para autenticar em 1 clique ou manualmente e inspecionar as respostas <code>200</code> e <code>401 (RFC 9457)</code>.
          </p>
        </div>
        <button type="button" class="gf-btn gf-btn-focus" onclick="focusGetMeEndpoint()">
          Focar na Rota GET /api/v1/auth/me Abaixo
        </button>
      </div>

      <div class="gf-steps-grid">
        <!-- PASSO 1 -->
        <div class="gf-step-box">
          <div>
            <h3 class="gf-step-title">Passo 1 — Gerar e Aplicar o Token JWT</h3>
            <p class="gf-step-desc">
              Clique em um dos perfis abaixo para autenticar em <code>POST /api/v1/auth/login</code> e preencher
              automaticamente o cadeado de autorização JWT desta página:
            </p>
          </div>
          <div class="gf-btn-group">
            <button type="button" class="gf-btn gf-btn-personal" onclick="quickAuthorizeSwagger('PERSONAL')">
              1A. Autenticar como PERSONAL (Carlos)
            </button>
            <button type="button" class="gf-btn gf-btn-student" onclick="quickAuthorizeSwagger('STUDENT')">
              1B. Autenticar como STUDENT (Rodrigo)
            </button>
          </div>
        </div>

        <!-- PASSO 2 -->
        <div class="gf-step-box">
          <div>
            <h3 class="gf-step-title">Passo 2 — Executar <code>GET /api/v1/auth/me</code></h3>
            <p class="gf-step-desc">
              Com o token aplicado, clique no botão abaixo (ou no botão <strong>Executar Requisição</strong> dentro da rota
              <code>GET /api/v1/auth/me</code>) para consultar os dados do usuário logado:
            </p>
          </div>
          <div class="gf-btn-group">
            <button type="button" class="gf-btn gf-btn-focus" onclick="executeGetMeLive(true)">
              2. Executar GET /api/v1/auth/me Agora (200)
            </button>
            <button type="button" class="gf-btn gf-btn-secondary" onclick="copyCurrentJwtToken()">
              Copiar Token JWT Atual
            </button>
          </div>
        </div>

        <!-- PASSO 3 -->
        <div class="gf-step-box">
          <div>
            <h3 class="gf-step-title">Passo 3 — Testar Bloqueio sem Token (Erro 401 RFC 9457)</h3>
            <p class="gf-step-desc">
              Para comprovar a proteção da rota, remova o token JWT e execute <code>GET /api/v1/auth/me</code> para receber o erro
              padronizado <code>ApiError</code> (<code>application/problem+json</code>):
            </p>
          </div>
          <div class="gf-btn-group">
            <button type="button" class="gf-btn gf-btn-clear" onclick="clearSwaggerAuthAndTest401()">
              3. Remover Token e Simular Erro 401 (RFC 9457)
            </button>
          </div>
        </div>
      </div>

      <!-- Painel de Resultado Ao Vivo -->
      <div class="gf-live-result">
        <div class="gf-live-result-header">
          <span id="gfLiveTitle">Inspetor Rápido de Resposta — GET /api/v1/auth/me</span>
          <span id="gfLiveHeaderSent" style="font-weight:400; font-family:monospace; color:#94a3b8;">Cabeçalho: (nenhum token enviado ainda)</span>
        </div>
        <pre id="gfLiveJson" class="gf-live-pre">Clique em "1A. Autenticar como PERSONAL (Carlos)" ou "2. Executar GET /api/v1/auth/me Agora" para ver o passo a passo em execução real.</pre>
      </div>

      <!-- Explicação Passo a Passo dos Testes Automatizados (pytest) -->
      <details class="gf-tests-details">
        <summary>Ver Passo a Passo Explicado nos Testes Automatizados (<code>pytest -v</code> em <code>src/api/tests/</code>)</summary>
        <ol>
          <li><strong><code>test_auth.py</code> (Autenticação e <code>GET /api/v1/auth/me</code>):</strong> Explica passo a passo o cadastro (<code>POST /register</code>), a emissão do token JWT <code>HS256</code> (<code>POST /login</code>), a consulta autenticada em <code>GET /api/v1/auth/me</code> para <code>PERSONAL</code> e <code>STUDENT</code> (<code>200</code>), e os bloqueios <code>401</code> (sem token, formato inválido ou token adulterado), <code>409</code> (e-mail duplicado) e <code>422</code> (<code>PERSONAL</code> sem <code>cref</code>).</li>
          <li><strong><code>test_students.py</code> (Carteira de Alunos, Perfil 1:1 e IMC/RPE):</strong> Explica passo a passo a listagem paginada com <code>selectinload</code>, cadastro, atualização biométrica, cálculo de IMC (<code>/analytics</code>) e isolamento horizontal RBAC (<code>403</code>).</li>
          <li><strong><code>test_workouts.py</code> (Fichas de Treino, Rotinas e Exercícios 1:N):</strong> Explica passo a passo o carregamento aninhado com <code>selectinload</code> (prevenção de queries N+1), prescrição em cascata e proteção RBAC entre alunos e personais.</li>
          <li><strong><code>test_executions.py</code> (Check-in de Treino com Escala RPE Borg 1–10):</strong> Explica passo a passo o registro de sessão concluída pelo aluno e consulta de histórico com bloqueio de acesso cruzado (<code>403</code>).</li>
          <li><strong><code>test_errors.py</code> (Conformidade RFC 9457):</strong> Explica passo a passo a validação de todos os códigos de erro (<code>400</code>, <code>401</code>, <code>403</code>, <code>404</code>, <code>422</code>) no contrato <code>ApiError</code>.</li>
        </ol>
      </details>
    </div>
  </section>

  <main id="swagger-ui"></main>

  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    let activeSwaggerToken = "";
    let activeUserSummary = "";

    const TRANSLATION_MAP = {
      "Authorize": "Autorizar JWT",
      "Try it out": "Habilitar Teste",
      "Cancel": "Cancelar",
      "Execute": "Executar Requisição",
      "Clear": "Limpar",
      "No parameters": "Nenhum parâmetro de rota ou consulta (utiliza apenas o token JWT no cabeçalho Authorization)",
      "Parameters": "Parâmetros da Requisição",
      "Request body": "Corpo da Requisição (JSON)",
      "Responses": "Respostas HTTP da Rota",
      "Server response": "Resposta Recebida do Servidor (Ao Vivo)",
      "Response body": "Corpo da Resposta (JSON)",
      "Response headers": "Cabeçalhos HTTP da Resposta",
      "Code": "Código HTTP",
      "Description": "Descrição",
      "Links": "Vínculos",
      "No links": "Sem vínculos adicionais",
      "Schemas": "Modelos de Dados (Schemas Pydantic v2)",
      "Example Value": "Valor de Exemplo",
      "Schema": "Estrutura do Modelo",
      "Available authorizations": "Autorização JWT (Bearer Token)",
      "Logout": "Remover Token",
      "Close": "Fechar"
    };

    function translateSwaggerLabels() {
      const selectors = [
        ".swagger-ui .btn",
        ".swagger-ui .opblock-section-header h4",
        ".swagger-ui .responses-wrapper h4",
        ".swagger-ui .opblock-description-wrapper p",
        ".swagger-ui th.col_header",
        ".swagger-ui td.response-col_links",
        ".swagger-ui section.models h4 span",
        ".swagger-ui .tablinks",
        ".swagger-ui .modal-ux-header h3"
      ];
      document.querySelectorAll(selectors.join(",")).forEach(el => {
        if (el.children.length === 0) {
          const text = el.textContent.trim();
          if (TRANSLATION_MAP[text]) {
            el.textContent = TRANSLATION_MAP[text];
          }
        } else if (el.classList.contains("authorize")) {
          const span = el.querySelector("span");
          if (span && span.textContent.trim() === "Authorize") {
            span.textContent = "Autorizar JWT";
          }
        }
      });
    }

    function applyTokenToSwagger(token, userObj) {
      activeSwaggerToken = token || "";
      const badge = document.getElementById("gfAuthBadge");
      if (window.ui) {
        if (activeSwaggerToken) {
          window.ui.preauthorizeApiKey("HTTPBearer", activeSwaggerToken);
        } else if (window.ui.authActions && window.ui.authActions.logout) {
          window.ui.authActions.logout(["HTTPBearer"]);
        }
      }
      if (activeSwaggerToken && userObj) {
        activeUserSummary = `${userObj.name} (${userObj.role})`;
        badge.textContent = `Token JWT Ativo: ${userObj.name} • Papel: ${userObj.role}`;
        badge.className = userObj.role === "PERSONAL"
          ? "gf-status-pill active-personal"
          : "gf-status-pill active-student";
      } else {
        activeUserSummary = "";
        badge.textContent = "Sessão JWT: Sem Token Ativo (Modo 401 Não Autenticado)";
        badge.className = "gf-status-pill";
      }
    }

    function focusGetMeEndpoint() {
      if (window.location.hash !== "#/Authentication/get_me_api_v1_auth_me_get") {
        window.location.hash = "#/Authentication/get_me_api_v1_auth_me_get";
      }
      setTimeout(() => {
        const block = document.getElementById("operations-Authentication-get_me_api_v1_auth_me_get");
        if (block) {
          if (!block.classList.contains("is-open")) {
            const summary = block.querySelector(".opblock-summary");
            if (summary) summary.click();
          }
          block.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      }, 150);
    }

    async function quickAuthorizeSwagger(role) {
      const liveTitle = document.getElementById("gfLiveTitle");
      const liveJson = document.getElementById("gfLiveJson");
      liveTitle.textContent = `Passo 1 em execução: Autenticando perfil ${role} em POST /api/v1/auth/login...`;

      let credentials = [
        { email: "carlos@gymflow.dev", password: "Personal@2026" }
      ];
      if (role === "STUDENT") {
        credentials = [
          { email: "rodrigo@gymflow.dev", password: "Aluno@2026" },
          { email: "rodrigoyoshi@gymflow.com", password: "aluno123" }
        ];
      }

      let loginData = null;
      for (const cred of credentials) {
        const res = await fetch("/api/v1/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(cred)
        });
        loginData = await res.json();
        if (res.ok && loginData.accessToken) {
          break;
        }
      }

      if (loginData && loginData.accessToken) {
        applyTokenToSwagger(loginData.accessToken, loginData.user);
        await executeGetMeLive(false);
        focusGetMeEndpoint();
      } else {
        liveJson.classList.add("is-error");
        liveJson.textContent = JSON.stringify(loginData, null, 2);
      }
    }

    async function executeGetMeLive(scrollToRoute = true) {
      const liveTitle = document.getElementById("gfLiveTitle");
      const liveHeader = document.getElementById("gfLiveHeaderSent");
      const liveJson = document.getElementById("gfLiveJson");

      const headers = {};
      if (activeSwaggerToken) {
        headers["Authorization"] = `Bearer ${activeSwaggerToken}`;
        const shortToken = activeSwaggerToken.slice(0, 28) + "...";
        liveHeader.textContent = `Cabeçalho enviado: Authorization: Bearer ${shortToken}`;
      } else {
        liveHeader.textContent = "Cabeçalho enviado: (sem cabeçalho Authorization)";
      }

      const res = await fetch("/api/v1/auth/me", { method: "GET", headers });
      const data = await res.json();

      if (res.ok) {
        liveTitle.textContent = `Passo 2 Concluído — GET /api/v1/auth/me retornou HTTP ${res.status} (Perfil ${data.role})`;
        liveJson.classList.remove("is-error");
      } else {
        liveTitle.textContent = `Passo 3 Concluído — GET /api/v1/auth/me retornou HTTP ${res.status} (Erro Padronizado RFC 9457)`;
        liveJson.classList.add("is-error");
      }
      liveJson.textContent = JSON.stringify(data, null, 2);

      if (scrollToRoute) {
        focusGetMeEndpoint();
      }
    }

    async function clearSwaggerAuthAndTest401() {
      applyTokenToSwagger("", null);
      await executeGetMeLive(true);
    }

    async function copyCurrentJwtToken() {
      const liveTitle = document.getElementById("gfLiveTitle");
      if (!activeSwaggerToken) {
        liveTitle.textContent = "Nenhum token ativo no momento. Clique primeiro no Passo 1A (PERSONAL) ou 1B (STUDENT).";
        return;
      }
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(activeSwaggerToken);
        liveTitle.textContent = `Token JWT de ${activeUserSummary} copiado para a área de transferência!`;
      }
    }

    window.addEventListener("load", () => {
      window.ui = SwaggerUIBundle({
        url: "/openapi.json",
        dom_id: "#swagger-ui",
        deepLinking: true,
        persistAuthorization: true,
        tryItOutEnabled: true,
        displayRequestDuration: true,
        docExpansion: "list",
        defaultModelsExpandDepth: 1,
        filter: true,
        presets: [
          SwaggerUIBundle.presets.apis
        ],
        onComplete: () => {
          translateSwaggerLabels();
          if (window.location.hash === "#/Authentication/get_me_api_v1_auth_me_get") {
            focusGetMeEndpoint();
          }
        }
      });

      const observer = new MutationObserver(() => {
        translateSwaggerLabels();
      });
      observer.observe(document.getElementById("swagger-ui"), {
        childList: true,
        subtree: true
      });
    });
  </script>
</body>
</html>
"""

OPENAPI_TAGS_METADATA = [
    {
        "name": "Authentication",
        "description": (
            "**Autenticação Stateless via JWT (`HS256`) e Perfil Logado (`/api/v1/auth`)** — "
            "Passo 1: Registre um usuário (`/register`) ou utilize as contas de exemplo no login (`/login`). "
            "Passo 2: Autentique o token JWT no cadeado (ou em 1 clique no topo da página). "
            "Passo 3: Consulte os dados do usuário autenticado em `GET /api/v1/auth/me`."
        ),
    },
    {
        "name": "Students",
        "description": (
            "**Gestão de Alunos, Perfil Biométrico 1:1 e Indicadores IMC/RPE (`/api/v1/students`)** — "
            "Rotas de carteira restritas ao papel `PERSONAL` e consulta individual/biométrica autorizada ao `PERSONAL` responsável ou ao próprio `STUDENT`."
        ),
    },
    {
        "name": "Workouts",
        "description": (
            "**Planos de Treino, Divisões de Rotina (A/B/C) e Exercícios (`/api/v1/workouts`)** — "
            "Carregamento otimizado com `selectinload` no SQLAlchemy 2.0 (sem queries N+1). Prescrição exclusiva para `PERSONAL`; leitura liberada para o `STUDENT` destinatário."
        ),
    },
    {
        "name": "Executions",
        "description": (
            "**Check-in de Treino e Histórico de Esforço RPE Borg 1–10 (`/api/v1/routines/{routineId}/executions`)** — "
            "Registro de sessões concluídas pelo aluno com nota de percepção de esforço e feedback qualitativo."
        ),
    },
    {
        "name": "Health",
        "description": "**Monitoramento de Saúde e Disponibilidade da API (`/health`)**.",
    },
]

PARAM_TITLE_TRANSLATIONS = {
    "page": "Página",
    "limit": "Limite por Página",
    "search": "Busca por Nome ou E-mail",
    "goal": "Objetivo Físico",
    "status": "Status da Ficha",
    "studentId": "UUID do Aluno",
    "workoutId": "UUID da Ficha de Treino",
    "routineId": "UUID da Rotina de Treino",
    "exerciseId": "UUID do Exercício",
}


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
        "API RESTful desenvolvida com **Spec-Driven Development (SDD)**, **SQLAlchemy 2.0 ORM**, "
        "**Autenticação Stateless JWT (`HS256`) + RBAC (`PERSONAL` e `STUDENT`)** e tratamento de erros "
        "padronizado pela **RFC 9457 (Problem Details)**.\n\n"
        "### Passo a Passo Rápido para Testar `GET /api/v1/auth/me`:\n"
        "1. Use o painel **Guia Passo a Passo** logo acima para autenticar com 1 clique como `PERSONAL` ou `STUDENT` (ou execute `POST /api/v1/auth/login` e cole o `accessToken` em **Autorizar JWT**).\n"
        "2. Abra `GET /api/v1/auth/me` (`#/Authentication/get_me_api_v1_auth_me_get`) e clique em **Executar Requisição** para receber `200` com seu perfil.\n"
        "3. Remova o token no botão do Passo 3 e execute novamente para validar o erro `401` no padrão **RFC 9457**."
    ),
    version="1.0.0",
    openapi_tags=OPENAPI_TAGS_METADATA,
    docs_url=None,
    lifespan=lifespan,
)


def custom_openapi() -> dict:
    """Personaliza o esquema OpenAPI 3.1 traduzindo descrições padrões para português e unificando erros na RFC 9457."""
    if app.openapi_schema:
        return app.openapi_schema

    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=OPENAPI_TAGS_METADATA,
    )

    for path_item in openapi_schema.get("paths", {}).values():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue

            for param in operation.get("parameters", []):
                p_name = param.get("name", "")
                if p_name in PARAM_TITLE_TRANSLATIONS and "schema" in param:
                    param["schema"]["title"] = PARAM_TITLE_TRANSLATIONS[p_name]

            responses = operation.get("responses", {})
            for code, resp_obj in responses.items():
                if not isinstance(resp_obj, dict):
                    continue
                if resp_obj.get("description") == "Successful Response":
                    if code == "201":
                        resp_obj["description"] = "Recurso criado com sucesso."
                    elif code == "204":
                        resp_obj["description"] = "Operação concluída com sucesso (sem conteúdo no corpo)."
                    else:
                        resp_obj["description"] = "Operação realizada com sucesso."
                elif code == "422" and resp_obj.get("description") == "Validation Error":
                    resp_obj["description"] = (
                        "Erro de Validação Semântica (Padrão RFC 9457 Problem Details)."
                    )
                    resp_obj["content"] = {
                        "application/problem+json": {
                            "schema": {"$ref": "#/components/schemas/ApiError"}
                        }
                    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi  # type: ignore[method-assign]

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


@app.get("/docs", response_class=HTMLResponse, include_in_schema=False)
def custom_swagger_ui_docs() -> HTMLResponse:
    """Documentação Swagger UI aprimorada em português com guia passo a passo e autenticação JWT em 1 clique."""
    return HTMLResponse(content=SWAGGER_DOCS_HTML)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
@app.get("/login", response_class=HTMLResponse, include_in_schema=False)
def interactive_dashboard() -> HTMLResponse:
    """[Conteúdo Extra] Painel Web interativo com Tela de Autenticação JWT/RBAC e Dashboard."""
    return HTMLResponse(content=DASHBOARD_HTML)


@app.get(
    "/health",
    tags=["Health"],
    summary="Verificar disponibilidade e saúde da GymFlow API",
    response_description="Status operacional da API retornado com sucesso.",
)
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "GymFlow API", "version": "1.0.0"}
