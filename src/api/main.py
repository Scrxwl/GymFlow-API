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
@app.get("/login", response_class=HTMLResponse, include_in_schema=False)
def interactive_dashboard() -> HTMLResponse:
    """[Conteúdo Extra] Painel Web interativo com Tela de Autenticação JWT/RBAC e Dashboard."""
    return HTMLResponse(content=DASHBOARD_HTML)


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "GymFlow API", "version": "1.0.0"}
