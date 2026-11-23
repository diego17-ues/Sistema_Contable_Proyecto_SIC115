(() => {
  'use strict';

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const money = value => new Intl.NumberFormat('es-SV', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(Number(value) || 0);
  const number = value => new Intl.NumberFormat('es-SV', { maximumFractionDigits: 2 }).format(Number(value) || 0);
  const today = () => new Date().toISOString().slice(0, 10);
  const safe = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
  const screenUrls = JSON.parse($('#screenUrls').textContent);
  const csrfToken = () => $('#logoutForm [name=csrfmiddlewaretoken]')?.value || '';
  async function api(url, options = {}) {
    const response = await fetch(url, { credentials: 'same-origin', ...options, headers: { Accept: 'application/json', 'X-CSRFToken': csrfToken(), ...(options.headers || {}) } });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || 'No se pudo completar la operación.');
    return data;
  }
  const logoUrl = JSON.parse($('#logoUrl').textContent);
  const initialScreen = $('#appShell').dataset.screen || 'dashboard';
  const initialParams = new URLSearchParams(window.location.search);
  const savedUser = JSON.parse($('#currentUser').textContent);
  const modulos = JSON.parse($('#modulos').textContent);
  const initialPeriodStatus = JSON.parse($('#periodStatus').textContent);
  const serverRendered = $('#appContent').dataset.serverRendered === 'true';
  const serverScreens = ['users', 'audit', 'accounts', 'ledger', 'estimacion', 'costos', 'rendimiento'];

  const navGroups = [
    { label: 'Inicio', items: [{ id: 'dashboard', title: 'Dashboard', icon: '⌂' }] },
    { label: 'Contabilidad', items: [{ id: 'ledger', title: 'Libro Mayor', icon: '▤' }, { id: 'accounts', title: 'Catálogo de cuentas', icon: '☷' }, { id: 'reports', title: 'Estados financieros', icon: '▥' }] },
    { label: 'Operación', items: [{ id: 'operations', title: 'Ventas', icon: '◫' }] },
    { label: 'Costos', items: [{ id: 'costos', title: 'Costeo Videojuego', icon: '◈' }, { id: 'estimacion', title: 'Estimación', icon: '◇' }, { id: 'rendimiento', title: 'Rendimiento de videojuegos', icon: '↗' }] },
    { label: 'Administración', items: [{ id: 'users', title: 'Usuarios', icon: '♙' }, { id: 'audit', title: 'Auditoría', icon: '◷' }] },
  ];

  const accounts = [
    { code: '1101', name: 'Caja general', group: 'Activo', nature: 'Deudora', status: 'Activa', description: 'Efectivo disponible en caja.' },
    { code: '1104', name: 'Cuentas por cobrar a plataformas', group: 'Activo', nature: 'Deudora', status: 'Activa', description: 'Importes pendientes de liquidación por plataformas.' },
    { code: '1204', name: 'Videojuegos en desarrollo', group: 'Activo', nature: 'Deudora', status: 'Activa', description: 'Costos acumulados de videojuegos en desarrollo.' },
    { code: '1205', name: 'Videojuegos terminados', group: 'Activo', nature: 'Deudora', status: 'Activa', description: 'Costo de videojuegos terminados.' },
    { code: '2103', name: 'IVA débito fiscal', group: 'Pasivo', nature: 'Acreedora', status: 'Activa', description: 'IVA generado por ventas.' },
    { code: '3101', name: 'Capital social', group: 'Patrimonio', nature: 'Acreedora', status: 'Activa', description: 'Aportes de capital.' },
    { code: '3102', name: 'Reserva legal', group: 'Patrimonio', nature: 'Acreedora', status: 'Activa', description: 'Reserva legal registrada.' },
    { code: '3103', name: 'Utilidades acumuladas', group: 'Patrimonio', nature: 'Acreedora', status: 'Activa', description: 'Resultados acumulados de ejercicios anteriores.' },
    { code: '3104', name: 'Pérdidas y ganancias', group: 'Patrimonio', nature: 'Acreedora', status: 'Activa', description: 'Cuenta de resultado del ejercicio.' },
    { code: '4101', name: 'Mano de obra directa de desarrollo', group: 'Desarrollo', nature: 'Deudora', status: 'Activa', description: 'Sueldos del equipo que trabaja directamente en un juego.' },
    { code: '4102', name: 'Servicios directos de desarrollo', group: 'Desarrollo', nature: 'Deudora', status: 'Activa', description: 'Servicios contratados para un videojuego específico.' },
    { code: '4103', name: 'Costos indirectos de desarrollo', group: 'Desarrollo', nature: 'Deudora', status: 'Activa', description: 'Costos comunes asignados a órdenes de trabajo.' },
    { code: '4104', name: 'Costo de ventas', group: 'Egreso', nature: 'Deudora', status: 'Activa', description: 'Costo de los videojuegos vendidos.' },
    { code: '4201', name: 'Sueldos y salarios administrativos', group: 'Egreso', nature: 'Deudora', status: 'Activa', description: 'Sueldos del personal administrativo.' },
    { code: '4207', name: 'Depreciación de mobiliario y equipo', group: 'Egreso', nature: 'Deudora', status: 'Activa', description: 'Depreciación del período.' },
    { code: '4301', name: 'Publicidad y marketing', group: 'Egreso', nature: 'Deudora', status: 'Activa', description: 'Campañas y material promocional.' },
    { code: '4401', name: 'Intereses', group: 'Egreso', nature: 'Deudora', status: 'Activa', description: 'Intereses de préstamos.' },
    { code: '4501', name: 'Otros gastos', group: 'Egreso', nature: 'Deudora', status: 'Activa', description: 'Gastos que no corresponden a otra cuenta específica.' },
    { code: '4502', name: 'Gastos por servicios profesionales', group: 'Egreso', nature: 'Deudora', status: 'Activa', description: 'Servicios profesionales recibidos en el período.' },
    { code: '4503', name: 'Impuesto sobre la renta', group: 'Egreso', nature: 'Deudora', status: 'Activa', description: 'Impuesto del ejercicio determinado.' },
    { code: '5101', name: 'Ingresos por licencias de videojuegos', group: 'Ingreso', nature: 'Acreedora', status: 'Activa', description: 'Ventas de licencias de videojuegos.' },
    { code: '5102', name: 'Ingresos por contenido adicional (DLC)', group: 'Ingreso', nature: 'Acreedora', status: 'Activa', description: 'Ventas de contenido adicional.' },
    { code: '5103', name: 'Descuentos y devoluciones sobre ventas', group: 'Ingreso', nature: 'Deudora', status: 'Activa', description: 'Cuenta que reduce las ventas netas.' },
    { code: '5104', name: 'Ingresos financieros', group: 'Ingreso', nature: 'Acreedora', status: 'Activa', description: 'Intereses ganados.' },
    { code: '5105', name: 'Otros ingresos', group: 'Ingreso', nature: 'Acreedora', status: 'Activa', description: 'Ingresos que no corresponden a otra cuenta específica.' },
  ];

  const transactionTypes = ['Diario', 'Comprobante de Ingreso', 'Comprobante de Egreso', 'Ajuste'];
  // Los movimientos y las ventas vienen del servidor (Libro Mayor y Steam simulado).
  const ledgerRows = [];

  let sales = [];

  const state = {
    current: initialScreen, report: initialParams.get('report') || (initialScreen === 'closed' ? 'worksheet' : 'results'), operation: initialParams.get('operation') || 'verify', period: 'month',
    currentUser: savedUser, ledgerMode: initialParams.get('mode') || 'ledger', trialBalanceTo: today(),
    ledgerFilter: { account: '5101', from: '', to: '' }, salesQuery: '', salesFrom: '', salesTo: '', salesLoaded: false, salesLoading: false, salesError: null, canPostSales: false, provisional: null, cuentas: [],
    periodStatus: initialPeriodStatus || 'ABIERTO',
    indicatorPeriodStatus: initialPeriodStatus || 'ABIERTO',
    closedRange: null, worksheet: null, provisionalFrom: '2026-10-01', provisionalTo: '2026-10-31',
    provisionalRequestId: 0,
    steamStatus: 'En espera', steamContact: null, steamError: null,
    reconciliationPreview: null, reconciliationResult: null,
    dashboardCostos: null, dashboardCostosLoading: false,
    dashboardCostosError: null,
    closedPeriod: null, closedPeriodLoaded: false, closedPeriodLoading: false,
    closedPeriodError: null, closedStatements: null,
    nextLedgerId: 9,
  };

  const SESSION_IDLE_LIMIT = 10 * 60 * 1000;
  const SESSION_HEARTBEAT_INTERVAL = 4 * 60 * 1000;
  let lastSessionActivity = Date.now();
  let lastSessionHeartbeat = Date.now();
  let sessionHeartbeatPending = false;

  function registerSessionActivity() {
    lastSessionActivity = Date.now();
  }

  async function checkSessionActivity() {
    if (!state.currentUser || sessionHeartbeatPending) return;
    const now = Date.now();
    if (now - lastSessionActivity >= SESSION_IDLE_LIMIT) {
      const form = $('#logoutForm');
      if (form?.requestSubmit) form.requestSubmit();
      else window.location.replace(screenUrls.login);
      return;
    }
    if (now - lastSessionHeartbeat < SESSION_HEARTBEAT_INTERVAL) return;

    sessionHeartbeatPending = true;
    lastSessionHeartbeat = now;
    try {
      const response = await fetch(screenUrls.api_session_activity, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          Accept: 'application/json',
          'X-CSRFToken': csrfToken(),
        },
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || data.active !== true) {
        window.location.replace(screenUrls.login);
      }
    } catch (error) {
      window.location.replace(screenUrls.login);
    } finally {
      sessionHeartbeatPending = false;
    }
  }

  ['click', 'keydown', 'input', 'pointerdown', 'pointermove', 'scroll', 'touchstart', 'wheel']
    .forEach(eventName => window.addEventListener(
      eventName, registerSessionActivity, { passive: true }
    ));
  window.addEventListener('focus', checkSessionActivity);
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) checkSessionActivity();
  });
  window.setInterval(checkSessionActivity, 30 * 1000);

  function renderNavigation() {
    const visibleGroups = navGroups.map(group => ({ ...group, items: group.items.filter(item => modulos.includes(item.id)) })).filter(group => group.items.length);
    $('#navigation').innerHTML = visibleGroups.map(group => `<div class="nav-label">${group.label}</div>${group.items.map(item => `<button type="button" class="nav-link ${state.current === item.id ? 'active' : ''}" data-view="${item.id}"><span class="nav-icon" aria-hidden="true">${item.icon}</span><span>${item.title}</span></button>`).join('')}`).join('');
  }

  function canView(view) {
    return view === 'closed' || modulos.includes(view);
  }

  function canReopenPeriod() {
    return state.currentUser?.role === 'Administrador';
  }

  function canReadCostDashboard() {
    return ['Administrador', 'Contador General', 'Contador de Costos']
      .includes(state.currentUser?.role);
  }

  function setScreen(view, params = {}, replace = false) {
    if (serverScreens.includes(view) || serverRendered) { window.location.assign(screenUrls[view]); return; }
    if (view === 'closed') state.report = 'worksheet';
    if (view === 'reports'
        && state.indicatorPeriodStatus === 'CERRADO_PROVISIONAL') {
      state.report = 'results';
    }
    const target = new URL(screenUrls[view], window.location.origin);
    Object.entries(params).forEach(([key, value]) => {
      if (value) target.searchParams.set(key, value);
    });
    const method = replace ? 'replaceState' : 'pushState';
    window.history[method]({ screen: view }, '', `${target.pathname}${target.search}`);
    state.current = view;
    $('#appShell').dataset.screen = view;
    page();
  }

  function updateScreenQuery(key, value) {
    const target = new URL(window.location.href);
    if (value) target.searchParams.set(key, value);
    else target.searchParams.delete(key);
    window.history.replaceState({ screen: state.current }, '', `${target.pathname}${target.search}`);
  }

  function syncScreenUrl() {
    const target = new URL(screenUrls[state.current], window.location.origin);
    target.searchParams.delete('report');
    target.searchParams.delete('operation');
    target.searchParams.delete('mode');
    if (state.current === 'reports') target.searchParams.set('report', state.report);
    if (state.current === 'operations') target.searchParams.set('operation', state.operation);
    if (state.current === 'ledger' && state.ledgerMode === 'trial-balance') target.searchParams.set('mode', state.ledgerMode);
    window.history.replaceState({ screen: state.current }, '', `${target.pathname}${target.search}`);
  }

  function heading(title, subtitle, actions = '') {
    const description = subtitle ? `<p>${subtitle}</p>` : '';
    return `<div class="page-heading"><div><h1>${title}</h1>${description}</div><div class="heading-actions">${actions}</div></div>`;
  }

  function page() {
    if (!canView(state.current)) {
      window.location.replace(screenUrls[modulos.includes('dashboard') ? 'dashboard' : modulos[0]] || screenUrls.logout);
      return;
    }
    renderNavigation();
    const titles = { dashboard: 'Dashboard', ledger: 'Libro Mayor', accounts: 'Catálogo de cuentas', reports: 'Estados financieros', operations: 'Ventas', users: 'Usuarios', audit: 'Auditoría', estimacion: 'Estimación', costos: 'Costeo Videojuego', rendimiento: 'Rendimiento de videojuegos', closed: 'Período cerrado' };
    $('#breadcrumb').textContent = titles[state.current] || 'Panel';
    const periodClosed = state.indicatorPeriodStatus === 'CERRADO_PROVISIONAL';
    const periodLabel = periodClosed ? 'Período cerrado provisionalmente' : 'Período abierto';
    const sidebarPeriod = $('.sidebar-period');
    if (sidebarPeriod) {
      sidebarPeriod.querySelector('span:last-child').textContent = periodLabel;
      sidebarPeriod.querySelector('.status-dot').classList.toggle('is-closed', periodClosed);
    }
    const topbarPeriod = $('.topbar-period');
    if (topbarPeriod) {
      topbarPeriod.innerHTML = `<span class="status-dot ${periodClosed ? 'is-closed' : ''}"></span>${periodClosed ? `${periodLabel} · Ver documentos` : periodLabel}`;
    }
    if (serverRendered) return;
    if (['dashboard', 'reports', 'closed'].includes(state.current)
        && !state.closedPeriodLoaded && !state.closedPeriodLoading) {
      loadClosedPeriod();
    }
    if (state.current === 'dashboard' && canReadCostDashboard()
        && !state.dashboardCostos
        && !state.dashboardCostosLoading && !state.dashboardCostosError) {
      state.dashboardCostosLoading = true;
      loadDashboardCostos();
    }
    if (state.current === 'dashboard' && state.currentUser?.role !== 'Contador de Costos'
        && (state.salesQuery || state.salesFrom || state.salesTo)) {
      state.salesQuery = '';
      state.salesFrom = '';
      state.salesTo = '';
      state.salesLoaded = false;
      sales = [];
    }
    if (['dashboard', 'operations'].includes(state.current)
        && state.currentUser?.role !== 'Contador de Costos'
        && !state.salesLoaded && !state.salesLoading) loadSales();
    const renderers = { dashboard: dashboardPage, reports: reportsPage, operations: operationsPage, closed: closedPeriodPage };
    $('#appContent').innerHTML = (renderers[state.current] || dashboardPage)();
    if ($('#provisionalFrom') && state.provisionalFrom) $('#provisionalFrom').value = state.provisionalFrom;
    syncScreenUrl();
  }

  async function loadDashboardCostos() {
    try {
      state.dashboardCostos = await api(screenUrls.api_cost_dashboard);
      state.dashboardCostosError = null;
    } catch (error) {
      state.dashboardCostosError = error.message;
    } finally {
      state.dashboardCostosLoading = false;
      if (state.current === 'dashboard') page();
    }
  }

  async function loadClosedPeriod(force = false) {
    if (state.closedPeriodLoading || (state.closedPeriodLoaded && !force)) return;
    state.closedPeriodLoading = true;
    state.closedPeriodError = null;
    try {
      const data = await api(screenUrls.api_cierre_activo);
      state.closedPeriod = data.cerrado ? data : null;
      state.closedStatements = data.cerrado ? data.estados : null;
      state.indicatorPeriodStatus = data.estado || 'ABIERTO';
      state.periodStatus = state.indicatorPeriodStatus;
      if (data.cerrado) {
        state.provisionalFrom = data.periodo.desde;
        state.provisionalTo = data.periodo.hasta;
        state.worksheet = normalizeWorksheet(data);
        if (state.current === 'reports'
            && ['provisional', 'closing'].includes(state.report)) {
          state.report = 'results';
        }
      } else {
        state.closedStatements = null;
      }
    } catch (error) {
      state.closedPeriodError = error.message;
    } finally {
      state.closedPeriodLoading = false;
      state.closedPeriodLoaded = true;
      if (['dashboard', 'reports', 'closed'].includes(state.current)) page();
    }
  }

  function dashboardClosedPeriod() {
    if (state.indicatorPeriodStatus !== 'CERRADO_PROVISIONAL') return '';
    const detalle = state.closedPeriod
      ? `${safe(state.closedPeriod.periodo.nombre)} · ${safe(state.closedPeriod.periodo.desde)} al ${safe(state.closedPeriod.periodo.hasta)}`
      : state.closedPeriodLoading ? 'Consultando el período…' : 'Cierre provisional activo';
    return `<section class="card section-gap"><div class="card-header"><div><h2>Período cerrado provisionalmente</h2><p>${detalle}</p></div><span class="tag tag-warn">Cerrado</span></div><div class="card-body"><button class="button button-secondary" type="button" data-view="closed">Ver Hoja de Trabajo y estados financieros</button>${state.closedPeriodError ? `<p class="form-error">${safe(state.closedPeriodError)}</p>` : ''}</div></section>`;
  }

  function closedPeriodPage() {
    if (state.closedPeriodLoading) {
      return `${heading('Período cerrado provisionalmente')}<section class="card"><div class="empty-state"><strong>Cargando documentos emitidos…</strong></div></section>`;
    }
    if (state.closedPeriodError) {
      return `${heading('Período cerrado provisionalmente')}<section class="card"><div class="empty-state"><strong>No se pudo cargar el cierre.</strong>${safe(state.closedPeriodError)}<div class="section-gap"><button class="button button-secondary" type="button" data-action="reload-closed-period">Reintentar</button></div></div></section>`;
    }
    if (!state.closedPeriod) {
      return `${heading('Período cerrado')}<section class="card"><div class="empty-state"><strong>No hay un cierre provisional activo.</strong></div></section>`;
    }
    const tabs = `<div class="tabs">${reportTabs.filter(([id]) => ['worksheet', 'results', 'balance', 'changes'].includes(id)).map(([id, title]) => `<button class="tab-button ${state.report === id ? 'active' : ''}" type="button" data-report="${id}">${title}</button>`).join('')}</div>`;
    const period = state.closedPeriod.periodo;
    const status = `<div class="demo-banner"><span><strong>${safe(period.nombre)}</strong> · ${safe(period.desde)} al ${safe(period.hasta)}</span><span class="tag tag-warn">Cerrado provisionalmente</span></div>`;
    const content = state.report === 'results'
      ? `${heading('Estado de Resultados')}${tabs}${incomeStatement()}`
      : state.report === 'balance'
        ? `${heading('Estado de Situación Financiera')}${tabs}${balanceStatement()}`
        : state.report === 'changes'
          ? `${heading('Estado de Cambios en el Patrimonio')}${tabs}${changesStatement()}`
          : worksheetPage(tabs);
    return `${status}${content}`;
  }

  function costDashboardPerformance() {
    const data = state.dashboardCostos;
    if (state.dashboardCostosLoading) {
      return '<div class="empty-state"><strong>Cargando rendimiento de órdenes…</strong></div>';
    }
    if (state.dashboardCostosError) {
      return `<div class="empty-state"><strong>No se pudo cargar el rendimiento.</strong><br>${safe(state.dashboardCostosError)}<br><button class="text-button" type="button" data-action="reload-cost-dashboard">Reintentar</button></div>`;
    }
    const ultima = data?.ultimaOrden;
    if (!ultima) {
      return '<div class="empty-state"><strong>Aún no hay órdenes finalizadas.</strong></div>';
    }
    const estado = ultima.viable === null
      ? (ultima.estimacion ? 'Pendiente de costos' : 'Sin estimación vinculada')
      : ultima.viable
        ? 'Dentro del presupuesto'
        : 'Sobre el presupuesto';
    const estadoTag = ultima.viable === null ? 'tag-muted' : ultima.viable ? 'tag-open' : 'tag-warn';
    const variacion = ultima.variacion === null ? '—'
      : Number(ultima.variacion) > 0
        ? `+${money(ultima.variacion)}` : money(ultima.variacion);
    const porcentaje = ultima.porcentaje === null ? '—'
      : `${Number(ultima.porcentaje) > 0 ? '+' : ''}${number(ultima.porcentaje)}%`;
    return `<div class="card-body"><p><strong>OT-${safe(ultima.id)} · ${safe(ultima.juego)}</strong></p><dl class="close-summary"><div><dt>Estimación vinculada</dt><dd>${safe(ultima.estimacion || 'Sin vínculo')}</dd></div><div><dt>Presupuesto estimado</dt><dd>${ultima.totalEstimado === null ? '—' : money(ultima.totalEstimado)}</dd></div><div><dt>Costo real</dt><dd>${ultima.totalReal === null ? '—' : money(ultima.totalReal)}</dd></div><div><dt>Variación (real − estimado)</dt><dd>${variacion}</dd></div><div><dt>Variación porcentual</dt><dd>${porcentaje}</dd></div></dl><p><span class="tag ${estadoTag}">${safe(estado)}</span></p></div>`;
  }

  function dashboardOrdenesFinalizadas() {
    if (!canReadCostDashboard()) return '';
    if (state.dashboardCostosLoading) return '';
    if (state.dashboardCostosError) return '';
    const filas = state.dashboardCostos?.ordenesFinalizadasRecientes || [];
    const contenido = filas.length ? filas.map(orden => {
      const rendimiento = orden.viable === true ? 'Dentro del presupuesto'
        : orden.viable === false ? 'Sobre el presupuesto'
          : orden.estimacion ? 'Pendiente de comparar' : 'Sin estimación';
      return `<tr><td><strong>OT-${safe(orden.id)}</strong><small>${safe(orden.juego)}</small></td><td class="num">${orden.totalEstimado === null ? '—' : money(orden.totalEstimado)}</td><td class="num">${orden.totalReal === null ? '—' : money(orden.totalReal)}</td><td class="num">${orden.variacion === null ? '—' : money(orden.variacion)}</td><td>${safe(rendimiento)}</td></tr>`;
    }).join('') : '<tr><td colspan="5"><div class="empty-state"><strong>No hay órdenes finalizadas para resumir.</strong></div></td></tr>';
    return `<section class="card section-gap"><div class="card-header"><div><h2>Órdenes finalizadas</h2></div></div><div class="table-wrap"><table><thead><tr><th>Orden y juego</th><th class="num">Estimación</th><th class="num">Costo real</th><th class="num">Variación</th><th>Rendimiento</th></tr></thead><tbody>${contenido}</tbody></table></div></section>`;
  }

  function dashboardCostosPage() {
    const data = state.dashboardCostos;
    return `${heading('DashBoard')}
      <div class="kpi-grid">
        <article class="card kpi-card" data-icon="◷"><div class="kpi-label">Pendientes de finalizar</div><div class="kpi-value">${data ? number(data.ordenesPendientes) : '—'}</div></article>
        <article class="card kpi-card" data-icon="✓"><div class="kpi-label">Órdenes finalizadas</div><div class="kpi-value">${data ? number(data.ordenesFinalizadas) : '—'}</div></article>
      </div>
      ${dashboardUltimaOrdenRegistrada()}
      <section class="card section-gap"><div class="card-header"><div><h2>Rendimiento de la última orden finalizada</h2></div></div>${costDashboardPerformance()}</section>
      ${dashboardOrdenesFinalizadas()}
      `;
  }

  function dashboardUltimaOrdenRegistrada() {
    const orden = state.dashboardCostos?.ultimaOrdenRegistrada;
    if (state.dashboardCostosLoading) {
      return '<section class="card section-gap"><div class="card-body"><div class="empty-state"><strong>Cargando última orden registrada…</strong></div></div></section>';
    }
    if (state.dashboardCostosError) {
      return `<section class="card section-gap"><div class="card-body">${costDashboardPerformance()}</div></section>`;
    }
    if (!orden) {
      return '<section class="card section-gap"><div class="card-header"><div><h2>Última orden registrada</h2></div></div><div class="card-body"><div class="empty-state"><strong>Aún no hay órdenes registradas.</strong></div></div></section>';
    }
    const fecha = new Date(`${orden.fechaInicio}T12:00:00`).toLocaleDateString('es-SV');
    return `<section class="card section-gap"><div class="card-header"><div><h2>Última orden registrada</h2></div><span class="tag ${orden.estado === 'Cerrada' ? 'tag-open' : 'tag-muted'}">${safe(orden.estado)}</span></div><div class="card-body"><dl class="close-summary"><div><dt>Orden y juego</dt><dd>OT-${safe(orden.id)} · ${safe(orden.juego)}</dd></div><div><dt>Fecha de inicio</dt><dd>${safe(fecha)}</dd></div><div><dt>Costo real vigente</dt><dd>${orden.totalReal === null ? '—' : money(orden.totalReal)}</dd></div><div><dt>Estimación vinculada</dt><dd>${safe(orden.estimacion || 'Sin vínculo')}</dd></div></dl></div></section>`;
  }

  function dashboardCostosSummary() {
    if (!canReadCostDashboard()) return '';
    const data = state.dashboardCostos;
    return `<section class="card"><div class="card-header"><div><h2>Costeo de órdenes finalizadas</h2></div>${data ? `<span class="tag">${number(data.ordenesFinalizadas)} finalizadas</span>` : ''}</div>${costDashboardPerformance()}</section>`;
  }

  function dashboardSalesWindow() {
    const hasta = today();
    const end = new Date(`${hasta}T00:00:00Z`);
    let desde;
    if (state.period === 'year') {
      desde = `${hasta.slice(0, 4)}-01-01`;
    } else {
      end.setUTCDate(end.getUTCDate() - (state.period === 'quarter' ? 89 : 29));
      desde = end.toISOString().slice(0, 10);
    }
    return { desde, hasta };
  }

  function dashboardSalesInPeriod() {
    const { desde, hasta } = dashboardSalesWindow();
    return sales.filter(sale => sale.date >= desde && sale.date <= hasta);
  }

  function dashboardSalesChart() {
    if (!state.salesLoaded || state.salesLoading) return '<div class="empty-state"><strong>Cargando ventas registradas…</strong></div>';
    if (state.salesError) return `<div class="empty-state"><strong>No se pudieron cargar las ventas.</strong>${safe(state.salesError)}</div>`;
    const { desde, hasta } = dashboardSalesWindow();
    const days = Math.max(1, Math.round((Date.parse(`${hasta}T00:00:00Z`) - Date.parse(`${desde}T00:00:00Z`)) / 86400000) + 1);
    const count = 8;
    const values = Array(count).fill(0);
    const filtered = dashboardSalesInPeriod().filter(sale => sale.status === 'Registrada');
    filtered.forEach(sale => {
      const offset = Math.max(0, Math.floor((Date.parse(`${sale.date}T00:00:00Z`) - Date.parse(`${desde}T00:00:00Z`)) / 86400000));
      const bucket = Math.min(count - 1, Math.floor(offset / days * count));
      values[bucket] += sale.amount;
    });
    if (!filtered.length) return '<div class="empty-state"><strong>No hay ventas registradas en este período.</strong></div>';
    const max = Math.max(...values, 1);
    const points = values.map((value, index) => ({
      x: 42 + (563 * index / (count - 1)),
      y: 170 - (value / max * 135),
      value,
    }));
    const line = points.map((point, index) => `${index ? 'L' : 'M'}${point.x.toFixed(1)} ${point.y.toFixed(1)}`).join(' ');
    const fill = `${line} L605 175 L42 175 Z`;
    const ticks = [1, 2, 3, 4].map(index => {
      const y = 28 + (147 * (index - 1) / 3);
      const label = money(max * (4 - index) / 3);
      return `<line class="chart-grid" x1="42" y1="${y}" x2="605" y2="${y}"/><text class="chart-axis" x="2" y="${y + 3}">${safe(label)}</text>`;
    }).join('');
    const labels = points.map((point, index) => {
      const date = new Date(Date.parse(`${desde}T00:00:00Z`) + Math.floor(days * index / count) * 86400000);
      return `<text class="chart-axis" x="${point.x - 14}" y="196">${date.toISOString().slice(5, 10)}</text>`;
    }).join('');
    const markers = points.map(point => `<circle class="chart-point" cx="${point.x.toFixed(1)}" cy="${point.y.toFixed(1)}" r="4"/>`).join('');
    return `<div class="card-body chart-area"><svg class="sales-chart" viewBox="0 0 620 205" role="img" aria-label="Ventas registradas agrupadas por fecha"><defs><linearGradient id="salesFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#d8a628" stop-opacity=".23"/><stop offset="1" stop-color="#d8a628" stop-opacity="0"/></linearGradient></defs>${ticks}<path class="chart-area-fill" d="${fill}"/><path class="chart-line" d="${line}"/>${markers}${labels}</svg></div>`;
  }

  function dashboardPage() {
    if (state.currentUser?.role === 'Contador de Costos') return dashboardCostosPage();
    const delPeriodo = dashboardSalesInPeriod();
    const registradas = delPeriodo.filter(sale => sale.status === 'Registrada');
    const ventasPeriodo = registradas.reduce((total, sale) => total + sale.amount, 0);
    const pendientes = delPeriodo.filter(sale => sale.status !== 'Registrada').length;
    const ultimaVenta = [...sales].sort((a, b) => b.time.localeCompare(a.time))[0];
    const periodLabel = state.period === 'year' ? 'Año actual' : state.period === 'quarter' ? 'Últimos 90 días' : 'Últimos 30 días';
    const latestSales = [...sales].sort((a, b) => b.time.localeCompare(a.time)).slice(0, 4);
    const latestSalesRows = latestSales.map(sale => `<tr><td>${safe(sale.date)}</td><td><strong>${safe(sale.title)}</strong><small>${safe(sale.id)}</small></td><td>${safe(sale.channel)}</td><td><span class="tag ${sale.status === 'Registrada' ? 'tag-open' : 'tag-muted'}">${safe(sale.status)}</span></td><td class="num">${money(sale.amount)}</td></tr>`).join('')
      || `<tr><td colspan="5" class="empty-cell">${state.salesError ? 'No se pudieron cargar las ventas.' : state.salesLoaded ? 'No hay ventas recibidas.' : 'Cargando ventas…'}</td></tr>`;
    return `${heading('Dashboard', 'Resumen de ventas y rendimiento de órdenes finalizadas.')}
      <div class="demo-banner"><div class="dashboard-filter"><label for="dashboardPeriod">Período</label><select id="dashboardPeriod"><option value="month" ${state.period === 'month' ? 'selected' : ''}>Últimos 30 días</option><option value="quarter" ${state.period === 'quarter' ? 'selected' : ''}>Últimos 90 días</option><option value="year" ${state.period === 'year' ? 'selected' : ''}>Año actual</option></select></div></div>
      <div class="kpi-grid">
        <article class="card kpi-card" data-icon="＄"><div class="kpi-label">Ventas registradas</div><div class="kpi-value">${state.salesLoaded && !state.salesError ? money(ventasPeriodo) : '—'}</div><div class="kpi-foot"><span class="positive">${periodLabel}</span></div></article>
        <article class="card kpi-card" data-icon="◷"><div class="kpi-label">Ventas pendientes</div><div class="kpi-value">${state.salesLoaded && !state.salesError ? number(pendientes) : '—'}</div><div class="kpi-foot">Eventos recibidos sin contabilizar</div></article>
        ${canReadCostDashboard() ? `<article class="card kpi-card" data-icon="✓"><div class="kpi-label">Órdenes finalizadas</div><div class="kpi-value">${state.dashboardCostos ? number(state.dashboardCostos.ordenesFinalizadas) : '—'}</div><div class="kpi-foot">Con rendimiento basado en costos reales</div></article>` : ''}
        <article class="card kpi-card" data-icon="▤"><div class="kpi-label">Última venta recibida</div><div class="kpi-value">${state.salesLoaded && !state.salesError && ultimaVenta ? money(ultimaVenta.amount) : '—'}</div><div class="kpi-foot">${state.salesError ? 'No se pudieron cargar las ventas' : ultimaVenta ? `${safe(ultimaVenta.date)} · ${safe(ultimaVenta.title)}` : state.salesLoaded ? 'Sin ventas recibidas' : 'Consultando ventas…'}</div></article>
      </div>
      ${dashboardClosedPeriod()}
      <div class="dashboard-grid">
        <section class="card"><div class="card-header"><div><h2>Ventas registradas</h2><p>Totales por fecha · ${periodLabel}</p></div><div class="chart-legend"><span><i class="legend-mark"></i>Ventas</span></div></div>${dashboardSalesChart()}</section>
        ${dashboardCostosSummary()}
      </div>
      ${dashboardOrdenesFinalizadas()}
      <div class="dashboard-bottom"><section class="card"><div class="card-header"><div><h2>Últimas ventas</h2><p>Canal, fecha y estado de registro</p></div><button class="text-button" type="button" data-view="operations" data-operation="verify">Ver ventas →</button></div><div class="table-wrap"><table><thead><tr><th>Fecha</th><th>Producto</th><th>Canal</th><th>Estado</th><th class="num">Monto</th></tr></thead><tbody>${latestSalesRows}</tbody></table></div></section><section class="card"><div class="card-header"><div><h2>Accesos rápidos</h2></div></div><div class="card-body"><div class="quick-links"><button class="quick-link" type="button" data-view="ledger">Registrar movimiento <span>↗</span></button><button class="quick-link" type="button" data-view="reports">Estados financieros <span>↗</span></button><button class="quick-link" type="button" data-view="operations" data-operation="steam">Conexión con Steam <span>↗</span></button><button class="quick-link" type="button" data-view="accounts">Catálogo de cuentas <span>↗</span></button></div></div></section></div>`;
  }

  function accountOptions(selected = '') {
    return state.cuentas.filter(account => account.status === 'Activa').map(account => `<option value="${safe(account.code)}" ${selected === account.code ? 'selected' : ''}>${safe(account.code)} · ${safe(account.name)}</option>`).join('');
  }

  function trialBalanceRows(asOf) {
    return accounts.filter(account => account.status === 'Activa' || ledgerRows.some(row => row.code === account.code)).map(account => {
      const net = ledgerRows.filter(row => row.code === account.code && row.date <= asOf).reduce((sum, row) => sum + (row.side === 'Cargo' ? row.amount : -row.amount), 0);
      return { ...account, debit: Math.max(net, 0), credit: Math.max(-net, 0) };
    }).filter(row => Math.abs(row.debit - row.credit) > 0.005);
  }

  function trialBalancePage() {
    const rows = trialBalanceRows(state.trialBalanceTo);
    const totalDebit = rows.reduce((sum, row) => sum + row.debit, 0);
    const totalCredit = rows.reduce((sum, row) => sum + row.credit, 0);
    const balanced = Math.abs(totalDebit - totalCredit) < 0.005;
    return `${heading('Balance de Comprobación', `Al ${safe(state.trialBalanceTo)} · expresado en USD`, `<button class="button button-secondary" type="button" data-action="export" data-source="trial-balance" data-format="pdf">↓ PDF</button><button class="button button-secondary" type="button" data-action="export" data-source="trial-balance" data-format="xlsx">↓ Excel</button>`)}
      <div class="filter-bar"><div class="field"><label for="trialBalanceTo">Fecha de corte</label><input id="trialBalanceTo" type="date" value="${safe(state.trialBalanceTo)}"/></div><button class="button button-secondary" type="button" data-action="refresh-trial-balance">Generar</button><button class="text-button" type="button" data-action="back-ledger">Volver al Libro Mayor</button></div>
      <section class="card statement-card"><div class="statement-heading"><img src="${safe(logoUrl)}" alt="SunGames"/><strong>SunGames S.A. de C.V.</strong><h2>Balance de Comprobación</h2><p>Al ${safe(state.trialBalanceTo)}</p><span>Expresado en USD</span></div><div class="table-wrap"><table class="statement-table" id="trialBalanceTable"><thead><tr><th>Cuenta y detalle</th><th class="num">Debe</th><th class="num">Haber</th></tr></thead><tbody>${rows.map(row => `<tr><td><strong>${safe(row.code)} · ${safe(row.name)}</strong></td><td class="num">${row.debit ? money(row.debit) : '—'}</td><td class="num">${row.credit ? money(row.credit) : '—'}</td></tr>`).join('')}<tr class="statement-total"><td><strong>Totales</strong></td><td class="num"><strong>${money(totalDebit)}</strong></td><td class="num"><strong>${money(totalCredit)}</strong></td></tr></tbody></table></div><div class="statement-status ${balanced ? 'is-balanced' : 'is-unbalanced'}"><span>${balanced ? '✓' : '⚠'}</span><strong>${balanced ? 'Balanceado' : `Diferencia ${money(totalDebit - totalCredit)}`}</strong></div></section>`;
  }

  const reportTabs = [
    ['results', 'Estado de Resultados'], ['balance', 'Estado de situación financiera'], ['changes', 'Cambios en patrimonio'],
    ['provisional', 'Cierre provisional'], ['worksheet', 'Hoja de trabajo'], ['closing', 'Cierre contable'], ['annual', 'Informe anual'],
  ];

  function reportsPage() {
    const tabs = `<div class="tabs">${reportTabs.map(([id, title]) => `<button class="tab-button ${state.report === id ? 'active' : ''}" type="button" data-report="${id}">${title}</button>`).join('')}</div>`;
    if (state.report === 'provisional') return provisionalPage(tabs);
    if (state.report === 'worksheet') return worksheetPage(tabs);
    if (state.report === 'closing') return closingPage(tabs);
    if (state.indicatorPeriodStatus === 'CERRADO_PROVISIONAL'
        && !state.closedPeriod) {
      const status = state.closedPeriodLoading
        ? '<strong>Cargando estados del período cerrado…</strong>'
        : state.closedPeriodError
          ? `<strong>No se pudieron cargar los estados del cierre.</strong><p>${safe(state.closedPeriodError)}</p><button class="button button-secondary" type="button" data-action="reload-closed-period">Reintentar</button>`
          : '<strong>Consultando el período cerrado…</strong>';
      return `${heading('Estados financieros')}${tabs}<section class="card"><div class="empty-state">${status}</div></section>`;
    }
    if (!hasCurrentWorksheet() && !state.closedPeriod) return worksheetRequired(tabs);
    if (state.report === 'results') return `${heading('Estado de Resultados', '', `<button class="button button-secondary" type="button" data-action="export" data-source="report" data-format="pdf">↓ PDF</button><button class="button button-secondary" type="button" data-action="export" data-source="report" data-format="xlsx">↓ Excel</button>`)}${tabs}${incomeStatement()}`;
    if (state.report === 'balance') return `${heading('Estado de Situación Financiera', '', `<button class="button button-secondary" type="button" data-action="export" data-source="report" data-format="pdf">↓ PDF</button><button class="button button-secondary" type="button" data-action="export" data-source="report" data-format="xlsx">↓ Excel</button>`)}${tabs}${balanceStatement()}`;
    if (state.report === 'changes') return `${heading('Estado de Cambios en el Patrimonio', '', `<button class="button button-secondary" type="button" data-action="export" data-source="report" data-format="pdf">↓ PDF</button><button class="button button-secondary" type="button" data-action="export" data-source="report" data-format="xlsx">↓ Excel</button>`)}${tabs}${changesStatement()}`;
    if (state.report === 'annual') return `${heading('Cierre anual', 'Consulta los informes del ejercicio a partir de la Hoja de Trabajo.', '')}${tabs}${annualReport()}`;
    return worksheetRequired(tabs);
  }

  function hasCurrentWorksheet() {
    return Boolean(state.worksheet && state.worksheet.from === state.provisionalFrom && state.worksheet.to === state.provisionalTo);
  }

  function worksheetRequired(tabs) {
    return `${heading('Estados financieros', 'Los informes del cierre se preparan desde la Hoja de Trabajo del período.', '')}${tabs}<section class="card"><div class="empty-state"><strong>Genera primero la Hoja de Trabajo</strong>Selecciona el período en Cierre provisional, revisa los movimientos del Libro Mayor y genera la hoja para habilitar los estados financieros.<div class="section-gap"><button class="button button-primary" type="button" data-report="provisional">Ir a Cierre provisional</button></div></div></section>`;
  }

  function provisionalPage(tabs) {
    const from = state.provisionalFrom || '2026-10-01';
    const to = state.provisionalTo || '2026-10-31';
    const info = provisionalInfo(from, to);
    const loading = state.provisionalLoading && !info;
    const pending = { length: info ? info.ventasPendientes : 0 };
    const periodRows = { length: info ? info.movimientos : 0 };
    const open = state.indicatorPeriodStatus !== 'CERRADO_PROVISIONAL'
      && (!info || info.estado !== 'CERRADO_PROVISIONAL');
    const estadoTexto = loading ? 'Consultando…' : open ? 'Abierto' : 'Cerrado provisionalmente';
    const estadoDetalle = loading ? 'Consultando el estado del período.' : open ? 'Admite revisión' : 'No admite nuevos movimientos';
    const pendientesTexto = loading ? 'Consultando…' : pending.length ? `${pending.length} pendientes` : 'Completado';
    const pendientesDetalle = loading ? 'Consultando las ventas del rango.' : pending.length ? 'Deben registrarse en el Libro Mayor antes de generar la hoja.' : 'No hay ventas pendientes en el rango.';
    const movimientosTexto = loading ? 'Consultando…' : `${periodRows.length} transacciones`;
    const movimientosDetalle = loading ? 'Consultando los movimientos del rango.' : periodRows.length ? 'Disponibles para incorporar a la hoja.' : 'No hay movimientos en las fechas seleccionadas.';
    const errorMarkup = info?.error ? `<div class="notice section-gap"><span class="notice-icon">!</span><span>${safe(info.error)}</span></div>` : '';
    const sameWorksheet = state.worksheet && state.worksheet.from === from && state.worksheet.to === to;
    const periodAction = open
      ? `<button class="button button-primary" type="button" data-action="generate-worksheet" ${state.provisionalLoading || pending.length || !periodRows.length ? 'disabled' : ''}>Generar Hoja de Trabajo</button>`
      : canReopenPeriod()
        ? '<button class="button button-secondary" type="button" data-action="reopen-period">Reabrir período</button>'
        : '';
    return `${heading('Cierre provisional', 'Valida las operaciones del período y genera la Hoja de Trabajo.', '')}${tabs}
      <section class="card"><div class="card-header"><div><h2>Período a revisar</h2><p>Selecciona el rango que se utilizará en la hoja.</p></div><span class="tag ${loading ? 'tag-muted' : open ? 'tag-open' : 'tag-warn'}">${estadoTexto}</span></div><div class="card-body"><div class="filter-bar" style="margin:0"><div class="field"><label for="provisionalFrom">Fecha inicial</label><input id="provisionalFrom" type="date" value="${safe(from)}" ${state.provisionalLoading ? 'disabled' : ''}/></div><div class="field"><label for="provisionalTo">Fecha final</label><input id="provisionalTo" type="date" value="${safe(to)}" ${state.provisionalLoading ? 'disabled' : ''}/></div><button class="button button-secondary" type="button" data-action="check-provisional" ${state.provisionalLoading ? 'disabled' : ''}>${state.provisionalLoading ? 'Consultando…' : 'Consultar requisitos'}</button></div>${errorMarkup}</div></section>
      <section class="card section-gap"><div class="card-header"><div><h2>Requisitos previos</h2><p>Las ventas del rango deben estar registradas antes de preparar la hoja.</p></div></div><div class="table-wrap"><table><thead><tr><th>Validación</th><th>Resultado</th><th>Detalle</th></tr></thead><tbody><tr><td><strong>Estado del período</strong></td><td><span class="tag ${loading ? 'tag-muted' : open ? 'tag-open' : 'tag-warn'}">${estadoTexto}</span></td><td>${estadoDetalle}</td></tr><tr><td><strong>Ventas pendientes</strong></td><td><span class="tag ${loading ? 'tag-muted' : pending.length ? 'tag-warn' : 'tag-open'}">${pendientesTexto}</span></td><td>${pendientesDetalle}</td></tr><tr><td><strong>Movimientos en Libro Mayor</strong></td><td><span class="tag ${loading ? 'tag-muted' : periodRows.length ? 'tag-open' : 'tag-muted'}">${movimientosTexto}</span></td><td>${movimientosDetalle}</td></tr></tbody></table></div>${pending.length ? `<div class="card-body"><button class="button button-secondary" type="button" data-view="operations" data-operation="post">Ir a contabilizar ventas</button></div>` : ''}<div class="table-footer"><span>Se volverán a validar al generar la hoja.</span>${sameWorksheet ? '<button class="text-button" type="button" data-report="worksheet">Abrir Hoja de Trabajo →</button>' : ''}</div></section>
      <div class="heading-actions section-gap">${periodAction}${sameWorksheet ? '<button class="button button-secondary" type="button" data-report="worksheet">Revisar hoja generada</button>' : ''}</div>`;
  }

  function closingPage(tabs) {
    if (state.indicatorPeriodStatus === 'CERRADO_PROVISIONAL') {
      const adminAction = canReopenPeriod()
        ? `<a class="button button-secondary" href="${safe(screenUrls.closing)}">Administrar período</a>` : '';
      return `${heading('Cierre contable', '', '')}${tabs}<section class="card"><div class="card-header"><div><h2>Período cerrado provisionalmente</h2></div><span class="tag tag-warn">Cerrado</span></div><div class="card-body"><p>La Hoja de Trabajo y los estados financieros del cierre están disponibles para consulta.</p><div class="section-gap"><button class="button button-primary" type="button" data-view="closed">Ver Hoja de Trabajo y estados financieros</button>${adminAction}</div></div></section>`;
    }
    const label = canReopenPeriod() ? 'Cerrar o reabrir períodos' : 'Cerrar períodos';
    return `${heading('Cierre contable', 'El cierre provisional se prepara con la Hoja de Trabajo del período.', '')}${tabs}<section class="card"><div class="card-header"><div><h2>Estado del período</h2><p>Flujo de revisión contable</p></div><span class="tag ${state.periodStatus === 'ABIERTO' ? 'tag-open' : 'tag-warn'}">${state.periodStatus === 'ABIERTO' ? 'Abierto' : 'Cerrado provisionalmente'}</span></div><div class="card-body"><div class="notice"><span class="notice-icon">i</span><span>El cierre provisional requiere generar y revisar la Hoja de Trabajo. Los estados financieros del período se habilitan a partir de esa hoja.</span></div><div class="section-gap"><a class="button button-primary" href="${safe(screenUrls.closing)}">${label}</a><button class="button button-secondary" type="button" data-report="provisional">${state.periodStatus === 'ABIERTO' ? 'Preparar cierre provisional' : 'Consultar período cerrado'}</button>${hasCurrentWorksheet() ? '<button class="button button-secondary" type="button" data-report="worksheet">Abrir Hoja de Trabajo</button>' : ''}</div></div></section>`;
  }

  function worksheetPage(tabs) {
    if (!hasCurrentWorksheet()) return `${heading('Hoja de Trabajo', 'Consolida los saldos y prepara los estados del período.', '')}${tabs}<section class="card"><div class="empty-state"><strong>No hay una Hoja de Trabajo generada para este período</strong>Primero valida el rango en Cierre provisional y genera la hoja desde los movimientos del Libro Mayor.<div class="section-gap"><button class="button button-primary" type="button" data-report="provisional">Ir a Cierre provisional</button></div></div></section>`;
    const sheet = state.worksheet;
    const totals = sheet.totals;
    const pair = (debit, credit) => `<td class="num">${debit ? money(debit) : '—'}</td><td class="num">${credit ? money(credit) : '—'}</td>`;
    const tableRows = sheet.rows.map(row => `<tr><td><strong>${safe(row.code || '—')}</strong><small>${safe(row.name)}</small></td>${pair(row.trialDebit,row.trialCredit)}${pair(row.adjustDebit,row.adjustCredit)}${pair(row.adjustedDebit,row.adjustedCredit)}${pair(row.resultsDebit,row.resultsCredit)}${pair(row.equityDebit,row.equityCredit)}${pair(row.balanceDebit,row.balanceCredit)}</tr>`).join('');
    const checks = worksheetChecks(sheet);
    const checkMarkup = checks.map(item => `<div class="balance-check ${item.ok ? 'is-balanced' : 'is-unbalanced'}"><span>${item.ok ? '✓' : '⚠'}</span><div><strong>${item.title}</strong><small>${item.ok ? 'Cuadra' : `Diferencia ${money(item.debit - item.credit)}`}</small></div></div>`).join('');
    const adjustments = sheet.adjustments || [];
    const adjustmentRows = adjustments.map(row => `<tr><td><strong>${safe(row.code)} · ${safe(row.account)}</strong></td><td>${safe(row.correlativo)}</td><td>${safe(row.date)}</td><td>${safe(row.concept)}</td><td class="num">${row.side === 'Cargo' ? money(row.amount) : '—'}</td><td class="num">${row.side === 'Abono' ? money(row.amount) : '—'}</td></tr>`).join('') || '<tr><td colspan="6" class="empty-cell">Sin ajustes para este período</td></tr>';
    const adjustmentForm = state.periodStatus === 'ABIERTO' ? `<section class="card section-gap"><div class="card-header"><div><h2>Registrar transacción de ajuste</h2></div></div><form id="adjustmentForm" class="adjustment-form"><div class="field"><label for="adjustmentAccount">Cuenta</label><select id="adjustmentAccount" name="code" required>${accountOptions()}</select></div><div class="field"><label for="adjustmentDate">Fecha</label><input id="adjustmentDate" name="date" type="date" value="${safe(sheet.to)}" min="${safe(sheet.from)}" max="${safe(sheet.to)}" required/></div><div class="field adjustment-description"><label for="adjustmentConcept">Descripción</label><input id="adjustmentConcept" name="concept" required/></div><div class="field"><label for="adjustmentReference">Referencia</label><input id="adjustmentReference" name="reference"/></div><div class="field"><label for="adjustmentDebit">Debe</label><input id="adjustmentDebit" name="debit" class="money-input" type="number" min="0" step="0.01"/></div><div class="field"><label for="adjustmentCredit">Haber</label><input id="adjustmentCredit" name="credit" class="money-input" type="number" min="0" step="0.01"/></div><button class="button button-primary" type="submit">Guardar ajuste</button></form></section>` : '';
    const periodAction = state.periodStatus === 'ABIERTO'
      ? `<button class="button button-primary" type="button" data-action="confirm-provisional-close" ${checks.every(item => item.ok) ? '' : 'disabled'}>Confirmar cierre provisional</button>`
      : canReopenPeriod()
        ? '<button class="button button-secondary" type="button" data-action="reopen-period">Reabrir período</button>'
        : '';
    return `${heading('Hoja de Trabajo', 'Revisa los saldos del Libro Mayor.', `<button class="button button-secondary" type="button" data-action="export" data-source="worksheet" data-format="pdf">↓ PDF</button><button class="button button-secondary" type="button" data-action="export" data-source="worksheet" data-format="xlsx">↓ Excel</button>`)}${tabs}
      <div class="demo-banner"><span><strong>Hoja generada</strong> · ${safe(sheet.from)} a ${safe(sheet.to)} · ${sheet.rows.filter(row => row.code).length} cuentas</span><span class="tag ${state.periodStatus === 'ABIERTO' ? 'tag-open' : 'tag-warn'}">${state.periodStatus === 'ABIERTO' ? 'En revisión' : 'Cierre provisional'}</span></div>
      <div class="balance-checks">${checkMarkup}</div>
      <section class="card worksheet-card"><div class="table-wrap worksheet-wrap"><table class="worksheet-table" id="worksheetMatrix"><thead><tr><th rowspan="2">Cuenta</th><th colspan="2">Balance de comprobación</th><th colspan="2">Ajustes</th><th colspan="2">Balance ajustado</th><th colspan="2">Estado de resultados</th><th colspan="2">Cambios en patrimonio</th><th colspan="2">Balance general</th></tr><tr><th>Debe</th><th>Haber</th><th>Debe</th><th>Haber</th><th>Debe</th><th>Haber</th><th>Debe</th><th>Haber</th><th>Debe</th><th>Haber</th><th>Debe</th><th>Haber</th></tr></thead><tbody>${tableRows}<tr class="worksheet-total"><td><strong>Totales</strong></td>${pair(totals.trialDebit,totals.trialCredit)}${pair(totals.adjustDebit,totals.adjustCredit)}${pair(totals.adjustedDebit,totals.adjustedCredit)}${pair(totals.resultsDebit,totals.resultsCredit)}${pair(totals.equityDebit,totals.equityCredit)}${pair(totals.balanceDebit,totals.balanceCredit)}</tr></tbody></table></div></section>
      <section class="card section-gap"><div class="card-header"><div><h2>Detalle de ajustes</h2></div><span class="tag">${adjustments.length}</span></div><div class="table-wrap"><table class="adjustment-detail-table"><thead><tr><th>Cuenta</th><th>Correlativo</th><th>Fecha</th><th>Descripción</th><th class="num">Debe</th><th class="num">Haber</th></tr></thead><tbody>${adjustmentRows}</tbody></table></div></section>${adjustmentForm}
      <section class="card section-gap"><div class="card-header"><div><h2>Estados financieros</h2></div></div><div class="card-body"><div class="quick-links"><button class="quick-link" type="button" data-report="results">Estado de Resultados <span>↗</span></button><button class="quick-link" type="button" data-report="changes">Estado de Cambios en el Patrimonio <span>↗</span></button><button class="quick-link" type="button" data-report="balance">Estado de situación financiera <span>↗</span></button></div></div></section>
      <div class="entry-actions section-gap">${periodAction}</div>`;
  }

  function worksheetChecks(sheet) {
    const pairs = [['Balance de comprobación', 'trialDebit', 'trialCredit'], ['Ajustes', 'adjustDebit', 'adjustCredit'], ['Balance ajustado', 'adjustedDebit', 'adjustedCredit'], ['Estado de resultados', 'resultsDebit', 'resultsCredit'], ['Balance general', 'balanceDebit', 'balanceCredit']];
    return pairs.map(([title, debitKey, creditKey]) => {
      const debit = Number(sheet.totals[debitKey]) || 0, credit = Number(sheet.totals[creditKey]) || 0;
      return { title, debit, credit, ok: Math.abs(debit - credit) < 0.005 };
    });
  }

  function provisionalInfo(from, to) {
    const info = state.provisional;
    if (info && info.from === from && info.to === to) return info;
    if (!state.provisionalLoading) loadProvisional(from, to);
    return null;
  }

  async function loadProvisional(from, to) {
    const requestId = state.provisionalRequestId + 1;
    state.provisionalRequestId = requestId;
    state.provisionalLoading = true;
    try {
      const data = await api(`${screenUrls.api_hoja}?${new URLSearchParams({ desde: from, hasta: to })}`);
      if (requestId !== state.provisionalRequestId) return null;
      state.provisional = { ...data, from, to };
      state.periodStatus = state.indicatorPeriodStatus === 'CERRADO_PROVISIONAL'
        ? 'CERRADO_PROVISIONAL' : data.estado;
      state.cuentas = data.cuentas;
      if (state.worksheet && state.worksheet.from === from && state.worksheet.to === to) state.worksheet = normalizeWorksheet(data);
    } catch (error) {
      if (requestId !== state.provisionalRequestId) return null;
      state.provisional = { from, to, ventasPendientes: 0, movimientos: 0, error: error.message };
      showToast(error.message, 'error');
    } finally {
      if (requestId === state.provisionalRequestId) {
        state.provisionalLoading = false;
      }
    }
    if (requestId !== state.provisionalRequestId) return null;
    if (state.current === 'reports') page();
    return state.provisional;
  }

  async function consultProvisionalRequirements() {
    const from = $('#provisionalFrom')?.value || '';
    const to = $('#provisionalTo')?.value || '';
    if (!from || !to || from > to) {
      showToast('La fecha inicial debe ser igual o anterior a la final.', 'error');
      return;
    }
    state.provisionalFrom = from;
    state.provisionalTo = to;
    state.provisional = null;
    const request = loadProvisional(from, to);
    page();
    await request;
  }

  function normalizeWorksheet(data) {
    const sheet = data.worksheet;
    const toNumber = row => Object.fromEntries(Object.entries(row).map(([key, value]) => [key, typeof value === 'string' && /^-?\d+(\.\d+)?$/.test(value) && key !== 'code' ? Number(value) : value]));
    return { ...sheet, rows: sheet.rows.map(toNumber), totals: toNumber(sheet.totals), adjustments: sheet.adjustments.map(toNumber), periodo: data.periodo };
  }

  async function generateWorksheet() {
    const from = $('#provisionalFrom')?.value || state.provisionalFrom;
    const to = $('#provisionalTo')?.value || state.provisionalTo;
    state.provisionalFrom = from;
    state.provisionalTo = to;
    if (!from || !to || from > to) { showToast('La fecha inicial debe ser igual o anterior a la fecha final.', 'error'); return; }
    const info = await loadProvisional(from, to);
    if (!info || info.error) return;
    if (state.periodStatus !== 'ABIERTO') { showToast('El período ya está cerrado provisionalmente.', 'warning'); return; }
    if (info.ventasPendientes) { showToast('Registra las ventas pendientes antes de generar la Hoja de Trabajo.', 'warning'); return; }
    if (!info.movimientos) { showToast('No hay movimientos en el rango seleccionado.', 'warning'); return; }
    state.worksheet = normalizeWorksheet(info);
    state.report = 'worksheet';
    page();
  }

  function requestProvisionalClose() {
    const info = state.provisional;
    const sheet = state.worksheet;
    if (!info || !sheet) return;
    const name = info.periodo.nombre;
    const summary = `<div class="field full"><strong>${safe(name)}</strong><small class="help">${safe(sheet.from)} a ${safe(sheet.to)} · ${info.transacciones} partidas · ${info.movimientos} movimientos · Balanza: ${info.balanzaCuadra ? 'cuadra' : `no cuadra (diferencia ${money(info.diferencia)})`} · Ventas pendientes: ${info.ventasPendientes}</small></div><div class="field full"><div class="notice"><span class="notice-icon">!</span><span>El período quedará cerrado y dejará de aceptar transacciones hasta que un administrador lo reabra.</span></div></div>`;
    const fields = `${summary}<div class="field full"><label for="closeConfirm">Escribe CONFIRMAR exactamente *</label><input id="closeConfirm" name="confirmacion" autocomplete="off"/></div><div class="field full"><label for="closeReason">Motivo *</label><textarea id="closeReason" name="motivo" rows="3"></textarea></div>`;
    openModal('Cerrar período', 'Cierre provisional desde la Hoja de Trabajo', fields, 'Cerrar período', data => {
      const body = new FormData();
      Object.entries({ desde: sheet.from, hasta: sheet.to, confirmacion: data.confirmacion, motivo: data.motivo }).forEach(([key, value]) => body.append(key, value));
      api(screenUrls.api_cierre_provisional, { method: 'POST', body }).then(result => {
        $('#modalRoot').innerHTML = '';
        state.indicatorPeriodStatus = 'CERRADO_PROVISIONAL';
        showToast(result.mensaje, 'success');
        loadClosedPeriod(true).then(async () => {
          await loadProvisional(sheet.from, sheet.to);
          state.report = 'worksheet';
          page();
        });
      }).catch(error => showToast(error.message, 'error'));
      return false;
    });
    const submit = $('#genericModalForm [type="submit"]');
    const update = () => { submit.disabled = !(info.balanzaCuadra && !info.ventasPendientes && $('#closeConfirm').value === 'CONFIRMAR' && $('#closeReason').value.trim()); };
    $('#genericModalForm').addEventListener('input', update);
    update();
  }

  function requestAnnualClose() {
    if (!state.worksheet) return;
    const year = state.worksheet.from.slice(0, 4);
    const desde = `${year}-01-01`;
    const hasta = `${year}-12-31`;
    const fields = `<div class="field full"><strong>Ejercicio ${safe(year)}</strong><small class="help">${desde} a ${hasta} · El servidor validará la balanza, el estado del período y las ventas pendientes.</small></div><div class="field full"><label for="annualConfirm">Escribe CONFIRMAR exactamente *</label><input id="annualConfirm" name="confirmacion" autocomplete="off"/></div><div class="field full"><label for="annualReason">Motivo *</label><textarea id="annualReason" name="motivo" rows="3"></textarea></div>`;
    openModal('Cierre anual', 'El servidor validará el ejercicio antes de cerrarlo.', fields, 'Confirmar cierre anual', data => {
      const body = new FormData();
      Object.entries({ desde, hasta, tipo_cierre: 'anual', confirmacion: data.confirmacion, motivo: data.motivo }).forEach(([key, value]) => body.append(key, value));
      api(screenUrls.api_cierre_provisional, { method: 'POST', body }).then(async result => {
        $('#modalRoot').innerHTML = '';
        state.indicatorPeriodStatus = 'CERRADO_PROVISIONAL';
        showToast(result.mensaje, 'success');
        await loadClosedPeriod(true);
        await loadProvisional(desde, hasta);
        state.report = 'annual';
        page();
      }).catch(error => showToast(error.message, 'error'));
      return false;
    });
    const submit = $('#genericModalForm [type="submit"]');
    const update = () => { submit.disabled = !($('#annualConfirm').value === 'CONFIRMAR' && $('#annualReason').value.trim()); };
    $('#genericModalForm').addEventListener('input', update);
    update();
  }

  async function previewReconciliation() {
    const desde = $('#reconcileFrom').value;
    const hasta = $('#reconcileTo').value;
    state.reconcileFrom = desde;
    state.reconcileTo = hasta;
    state.reconciliationResult = null;
    try {
      const params = new URLSearchParams({ desde, hasta });
      state.reconciliationPreview = await api(`${screenUrls.api_conciliar_ventas}?${params}`);
    } catch (error) {
      state.reconciliationPreview = null;
      showToast(error.message, 'error');
    }
    if (state.current === 'operations') page();
  }

  async function confirmReconciliation() {
    if (!state.reconciliationPreview) return;
    const body = new FormData();
    body.append('desde', state.reconcileFrom);
    body.append('hasta', state.reconcileTo);
    try {
      state.reconciliationResult = await api(screenUrls.api_conciliar_ventas, { method: 'POST', body });
      state.reconciliationPreview = null;
      const errores = state.reconciliationResult.errores || [];
      const mensaje = errores.length
        ? `${state.reconciliationResult.conciliadas} conciliadas; ${errores.length} no se contabilizaron. Revisa el detalle.`
        : 'Conciliación procesada y auditada.';
      showToast(mensaje, errores.length ? 'warning' : 'success');
      await loadSales();
    } catch (error) {
      showToast(error.message, 'error');
    }
    if (state.current === 'operations') page();
  }

  function requestPeriodReopen() {
    if (!canReopenPeriod()) {
      showToast('Solo un administrador puede reabrir un período.', 'error');
      return;
    }
    window.location.assign(screenUrls.closing);
  }

  function statementHeading(title, period) {
    return `<div class="statement-heading"><img src="${safe(logoUrl)}" alt="SunGames"/><strong>SunGames S.A. de C.V.</strong><h2>${title}</h2><p>${period}</p><span>Expresado en USD</span></div>`;
  }

  function statementRowsMarkup(rows) {
    return rows.map(row => {
      if (row.kind === 'section') return `<tr class="statement-section"><td colspan="3">${safe(row.label)}</td></tr>`;
      if (row.kind === 'total' || row.kind === 'final') return `<tr class="statement-total ${row.kind === 'final' ? 'statement-final' : ''}"><td><strong>${safe(row.label)}</strong></td><td class="num">—</td><td class="num"><strong>${money(row.amount)}</strong></td></tr>`;
      return `<tr><td>${safe(row.label)}</td><td class="num">${money(row.amount)}</td><td class="num">—</td></tr>`;
    }).join('');
  }

  function incomeStatement() {
    const emitido = state.closedStatements?.resultados;
    if (emitido) return emittedStatement(emitido, 'Estado de Resultados');
    const sheet = state.worksheet;
    const incomeRows = sheet.rows.filter(row => row.code && row.group === 'Ingreso').map(row => ({ label: `${row.code} · ${row.name}`, amount: -row.periodNet, kind: 'detail' })).filter(row => Math.abs(row.amount) > 0.005);
    const expenseRows = sheet.rows.filter(row => row.code && row.group === 'Egreso').map(row => ({ label: `${row.code} · ${row.name}`, amount: row.periodNet, kind: 'detail' })).filter(row => Math.abs(row.amount) > 0.005);
    const incomeTotal = incomeRows.reduce((sum, row) => sum + row.amount, 0);
    const expenseTotal = expenseRows.reduce((sum, row) => sum + row.amount, 0);
    const finalResult = incomeTotal - expenseTotal;
    const rows = [
      { kind: 'section', label: 'INGRESOS' }, ...incomeRows, { kind: 'total', label: 'Total ingresos', amount: incomeTotal },
      { kind: 'section', label: 'EGRESOS' }, ...expenseRows, { kind: 'total', label: 'Total egresos', amount: expenseTotal },
      { kind: 'final', label: 'Resultado del período', amount: finalResult },
    ];
    return `<section class="card statement-card">${statementHeading('Estado de Resultados', `${safe(sheet.from)} al ${safe(sheet.to)}`)}<div class="table-wrap"><table class="statement-table"><thead><tr><th rowspan="2">Detalle</th><th colspan="2" class="sum-heading">Sumas</th></tr><tr><th class="num">Parcial</th><th class="num">Total</th></tr></thead><tbody>${statementRowsMarkup(rows)}</tbody></table></div></section>`;
  }

  function balanceStatement() {
    const emitido = state.closedStatements?.balance;
    if (emitido) return emittedStatement(emitido, 'Estado de Situación Financiera');
    const sheet = state.worksheet;
    const balances = sheet.rows.filter(row => row.code && ['Activo', 'Pasivo', 'Patrimonio'].includes(row.group));
    const result = sheet.rows.find(row => row.name === 'Resultado del período');
    const groupRows = (group, sign) => balances.filter(row => row.group === group).map(row => ({ label: `${row.code} · ${row.name}`, amount: (row.balanceCredit - row.balanceDebit) * sign, kind: 'detail' })).filter(row => Math.abs(row.amount) > 0.005);
    const assets = groupRows('Activo', -1);
    const liabilities = groupRows('Pasivo', 1);
    const equity = groupRows('Patrimonio', 1);
    const unclassified = sheet.rows.filter(row => row.code && row.group === 'Desarrollo' && Math.abs(row.balanceDebit - row.balanceCredit) > 0.005).map(row => ({ label: `${row.code} · ${row.name}`, amount: row.balanceDebit - row.balanceCredit, kind: 'detail' }));
    const resultAmount = result ? result.balanceCredit - result.balanceDebit : 0;
    const totalAssets = assets.reduce((sum, row) => sum + row.amount, 0);
    const totalLiabilities = liabilities.reduce((sum, row) => sum + row.amount, 0);
    const totalEquity = equity.reduce((sum, row) => sum + row.amount, 0) + resultAmount;
    const rows = [
      { kind: 'section', label: 'ACTIVO' }, ...assets, { kind: 'total', label: 'Total activo', amount: totalAssets },
      { kind: 'section', label: 'PASIVO' }, ...liabilities, { kind: 'total', label: 'Total pasivo', amount: totalLiabilities },
      { kind: 'section', label: 'PATRIMONIO' }, ...equity, { label: 'Resultado del período', amount: resultAmount, kind: 'detail' },
      { kind: 'total', label: 'Total pasivo y patrimonio', amount: totalLiabilities + totalEquity },
    ];
    if (unclassified.length) rows.push({ kind: 'section', label: 'DESARROLLO · SIN CLASIFICACIÓN EN EL CATÁLOGO' }, ...unclassified);
    return `<section class="card statement-card">${statementHeading('Estado de Situación Financiera', `Al ${safe(sheet.to)}`)}<div class="table-wrap"><table class="statement-table"><thead><tr><th rowspan="2">Detalle</th><th colspan="2" class="sum-heading">Sumas</th></tr><tr><th class="num">Parcial</th><th class="num">Total</th></tr></thead><tbody>${statementRowsMarkup(rows)}</tbody></table></div></section>`;
  }

  function changesStatement() {
    const sheet = state.worksheet;
    const rows = sheet.rows.filter(row => row.code && row.group === 'Patrimonio' && [row.openingNet, row.periodCredit, row.periodDebit, row.balanceCredit - row.balanceDebit].some(v => Math.abs(v || 0) > 0.005)).map(row => {
      const opening = -(row.openingNet || 0);
      const increases = row.periodCredit;
      const decreases = row.periodDebit;
      const final = row.balanceCredit - row.balanceDebit;
      return `<tr><td>${safe(row.code)} · ${safe(row.name)}</td><td class="num">${money(opening)}</td><td class="num">${money(increases)}</td><td class="num">${money(decreases)}</td><td class="num"><strong>${money(final)}</strong></td></tr>`;
    });
    const result = sheet.rows.find(row => row.name === 'Resultado del período');
    if (result) rows.push(`<tr><td>Resultado del período</td><td class="num">—</td><td class="num">${money(Math.max(result.balanceCredit - result.balanceDebit, 0))}</td><td class="num">${money(Math.max(result.balanceDebit - result.balanceCredit, 0))}</td><td class="num"><strong>${money(result.balanceCredit - result.balanceDebit)}</strong></td></tr>`);
    return `<section class="card statement-card">${statementHeading('Estado de Cambios en el Patrimonio', `${safe(sheet.from)} al ${safe(sheet.to)}`)}<div class="table-wrap"><table class="statement-table"><thead><tr><th>Detalle</th><th class="num">Saldo inicial</th><th class="num">Aumentos</th><th class="num">Disminuciones</th><th class="num">Saldo final</th></tr></thead><tbody>${rows.join('') || '<tr><td colspan="5" class="empty-cell">Sin movimientos patrimoniales</td></tr>'}</tbody></table></div></section>`;
  }

  function emittedStatement(emitido, fallbackTitle) {
    const rows = (emitido.filas || []).map(row => {
      if (row.clase === 'seccion' || row.clase === 'grupo') {
        return { kind: 'section', label: row.texto };
      }
      if (row.clase === 'resultado') {
        return { kind: 'final', label: row.texto, amount: Number(row.importe) || 0 };
      }
      if (['subtotal', 'total'].includes(row.clase)) {
        return { kind: 'total', label: row.texto, amount: Number(row.importe) || 0 };
      }
      return { label: `${row.codigo ? `${row.codigo} · ` : ''}${row.texto}`, amount: Number(row.importe) || 0, kind: 'detail' };
    });
    return `<section class="card statement-card">${statementHeading(emitido.titulo || fallbackTitle, emitido.cubre || '')}<div class="table-wrap"><table class="statement-table"><thead><tr><th rowspan="2">Detalle</th><th colspan="2" class="sum-heading">Sumas</th></tr><tr><th class="num">Parcial</th><th class="num">Total</th></tr></thead><tbody>${statementRowsMarkup(rows)}</tbody></table></div></section>`;
  }

  const logoSvgBase64 = 'PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxMjAwIDQwMCIgcm9sZT0iaW1nIiBhcmlhLWxhYmVsbGVkYnk9InRpdGxlIGRlc2MiPgogIDx0aXRsZSBpZD0idGl0bGUiPlN1bkdhbWVzIGxvZ288L3RpdGxlPgogIDxkZXNjIGlkPSJkZXNjIj5BIHN0eWxpemVkIHN1biBiZWhpbmQgYSBnYW1lIGNvbnRyb2xsZXIgZm9sbG93ZWQgYnkgdGhlIFN1bkdhbWVzIHdvcmRtYXJrLjwvZGVzYz4KICA8ZGVmcz4KICAgIDxsaW5lYXJHcmFkaWVudCBpZD0ic3VuIiB4MT0iMCIgeTE9IjAiIHgyPSIxIiB5Mj0iMSI+CiAgICAgIDxzdG9wIG9mZnNldD0iMCIgc3RvcC1jb2xvcj0iI0ZGRDE2NiIvPgogICAgICA8c3RvcCBvZmZzZXQ9IjEiIHN0b3AtY29sb3I9IiNGRjhBM0QiLz4KICAgIDwvbGluZWFyR3JhZGllbnQ+CiAgPC9kZWZzPgogIDxnIHRyYW5zZm9ybT0idHJhbnNsYXRlKDQ1IDM1KSI+CiAgICA8Y2lyY2xlIGN4PSIxNjAiIGN5PSIxNTAiIHI9IjEwNiIgZmlsbD0idXJsKCNzdW4pIi8+CiAgICA8ZyBmaWxsPSJub25lIiBzdHJva2U9IiNGNEI2M0EiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLXdpZHRoPSIxNiI+CiAgICAgIDxwYXRoIGQ9Ik0xNjAgMjB2LTEyIi8+CiAgICAgIDxwYXRoIGQ9Ik0xNjAgMjkydi0xMiIvPgogICAgICA8cGF0aCBkPSJNMzAgMTUwSDE4Ii8+CiAgICAgIDxwYXRoIGQ9Ik0zMDIgMTUwaC0xMiIvPgogICAgICA8cGF0aCBkPSJtNjcgNTctOS05Ii8+CiAgICAgIDxwYXRoIGQ9Im0yNTMgMjQzLTktOSIvPgogICAgICA8cGF0aCBkPSJtNjcgMjQzLTkgOSIvPgogICAgICA8cGF0aCBkPSJtMjUzIDU3IDktOSIvPgogICAgPC9nPgogICAgPHBhdGggZD0iTTc3IDE1M2M5LTM3IDM5LTYwIDc4LTYwaDEwYzM5IDAgNjkgMjMgNzggNjBsMjEgNzZjNSAxOC05IDM2LTI4IDM2LTEwIDAtMTktNS0yNS0xNGwtMjktNDFoLTQ0bC0yOSA0MWMtNiA5LTE1IDE0LTI1IDE0LTE5IDAtMzMtMTgtMjgtMzZsMjEtNzZaIiBmaWxsPSIjMEIxRjMzIi8+CiAgICA8cGF0aCBkPSJNMTE5IDE1MHY0OE05NSAxNzRoNDgiIHN0cm9rZT0iI0Y4RjlGQSIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2Utd2lkdGg9IjEzIi8+CiAgICA8Y2lyY2xlIGN4PSIyMDUiIGN5PSIxNjUiIHI9IjEwIiBmaWxsPSIjRjRCNjNBIi8+CiAgICA8Y2lyY2xlIGN4PSIyMzQiIGN5PSIxOTMiIHI9IjEwIiBmaWxsPSIjRkY2QjM1Ii8+CiAgPC9nPgogIDx0ZXh0IHg9IjM3MCIgeT0iMjA1IiBmaWxsPSIjMEIxRjMzIiBmb250LWZhbWlseT0iQXJpYWwsIEhlbHZldGljYSwgc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMTIiIGZvbnQtd2VpZ2h0PSI4MDAiIGxldHRlci1zcGFjaW5nPSItNCI+U3VuR2FtZXM8L3RleHQ+CiAgPHRleHQgeD0iMzc4IiB5PSIyNzAiIGZpbGw9IiNGRjZCMzUiIGZvbnQtZmFtaWx5PSJBcmlhbCwgSGVsdmV0aWNhLCBzYW5zLXNlcmlmIiBmb250LXNpemU9IjI3IiBmb250LXdlaWdodD0iNzAwIiBsZXR0ZXItc3BhY2luZz0iOCI+SU5URVJBQ1RJVkUgV09STERTPC90ZXh0Pgo8L3N2Zz4K';

  function exportTableRows(table) {
    return [...table.querySelectorAll('tr')].map(row => [...row.querySelectorAll('th,td')].map(cell => {
      const value = cell.innerText.trim();
      if (/^\$\s*[-\d,]+(?:\.\d{1,2})?$/.test(value)) return Number(value.replace(/[^\d.-]/g, '')) || 0;
      return value;
    }));
  }

  function reportTitle(source) {
    if (source === 'trial-balance') return 'Balance de Comprobación';
    if (source === 'worksheet') return 'Hoja de Trabajo';
    if (source === 'ledger') return 'Libro Mayor';
    if (state.current === 'audit') return 'Auditoría';
    return state.report === 'balance' ? 'Estado de Situación Financiera' : state.report === 'changes' ? 'Estado de Cambios en el Patrimonio' : 'Estado de Resultados';
  }

  function exportDocument(source, format) {
    const selectors = { 'trial-balance': '#trialBalanceTable', worksheet: '#worksheetMatrix', ledger: '#ledgerTable', report: '.statement-card .statement-table' };
    const selector = state.current === 'audit' ? '.card table' : selectors[source] || selectors.report;
    const table = $(selector);
    if (!table) { showToast('No hay una tabla disponible para exportar.', 'error'); return; }
    const title = reportTitle(source);
    const period = source === 'trial-balance' ? table.dataset.periodo || `Al ${state.trialBalanceTo}` : source === 'worksheet' || source === 'report' ? `${state.worksheet?.from || ''} al ${state.worksheet?.to || ''}` : '';
    const rows = exportTableRows(table);
    const adjustmentTable = source === 'worksheet' ? $('.adjustment-detail-table') : null;
    if (adjustmentTable) rows.push([], ['Detalle de ajustes'], ...exportTableRows(adjustmentTable));
    const labeledRows = [
      ['', '', '', '', 'SunGames S.A. de C.V.'], ['', '', '', '', title], ['', '', '', '', period], ['', '', '', '', 'Expresado en USD'], [], ...rows,
    ];
    if (format.toLowerCase() === 'xlsx' || format.toLowerCase() === 'excel') {
      downloadXlsx(labeledRows, title, table.tHead?.rows.length || 1).catch(() => showToast('No se pudo preparar el archivo Excel.', 'error'));
      return;
    }
    const logo = `data:image/svg+xml;base64,${logoSvgBase64}`;
    const printWindow = window.open('', '_blank', 'width=1000,height=800');
    if (!printWindow) { showToast('El navegador bloqueó la ventana de impresión.', 'error'); return; }
    const statementCard = table.closest('.statement-card');
    const printableTables = `${table.outerHTML}${adjustmentTable ? `<h2>Detalle de ajustes</h2>${adjustmentTable.outerHTML}` : ''}`;
    const reportHtml = statementCard ? statementCard.outerHTML.replace(`src="${safe(logoUrl)}"`, `src="${logo}"`) : `<header class="print-header"><img src="${logo}" alt="SunGames"><div><strong>SunGames S.A. de C.V.</strong><h1>${safe(title)}</h1><p>${safe(period)}</p><p>Expresado en USD</p></div></header><section class="card statement-card"><div class="table-wrap">${printableTables}</div></section>`;
    printWindow.addEventListener('load', () => printWindow.print(), { once: true });
    printWindow.document.write(`<!doctype html><html lang="es"><head><meta charset="utf-8"><title>${safe(title)}</title><link rel="stylesheet" href="${new URL('styles.css', location.href).href}"><style>body{background:#fff;padding:24px}.print-header{display:flex;align-items:center;gap:20px;margin:0 auto 22px;max-width:900px}.print-header img{width:180px}.print-header div{text-align:center;flex:1}.print-header h1{font-size:17px;margin:5px 0;color:#102b45}.print-header p{margin:3px}.statement-card{max-width:900px;margin:auto;box-shadow:none;border:0}.card-header{display:none}.statement-table{width:100%}@page{size:landscape;margin:15mm}@media print{body{padding:0}}</style></head><body>${reportHtml}</body></html>`);
    printWindow.document.close();
  }

  function logoPngBytes() {
    return new Promise((resolve, reject) => {
      const logo = new Image();
      logo.onload = () => {
        try {
          const canvas = document.createElement('canvas');
          canvas.width = 1200; canvas.height = 400;
          canvas.getContext('2d').drawImage(logo, 0, 0, canvas.width, canvas.height);
          canvas.toBlob(blob => blob ? blob.arrayBuffer().then(buffer => resolve(new Uint8Array(buffer))) : reject(new Error('PNG export failed')), 'image/png');
        } catch (error) { reject(error); }
      };
      logo.onerror = reject;
      logo.src = `data:image/svg+xml;base64,${logoSvgBase64}`;
    });
  }

  async function downloadXlsx(rows, title, headerRows) {
    const logoBytes = await logoPngBytes();
    const xmlEscape = value => String(value ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    const colName = index => { let name = ''; for (let n = index + 1; n; n = Math.floor((n - 1) / 26)) name = String.fromCharCode(65 + (n - 1) % 26) + name; return name; };
    const tableStart = 5;
    const cellXml = (value, ref, style) => typeof value === 'number' && Number.isFinite(value) ? `<c r="${ref}" s="${style === 4 ? 7 : 6}"><v>${value}</v></c>` : `<c r="${ref}"${style ? ` s="${style}"` : ''} t="inlineStr"><is><t xml:space="preserve">${xmlEscape(value)}</t></is></c>`;
    const sheetRows = rows.map((row, rowIndex) => {
      const rowText = String(row[0] || '').toLowerCase();
      const isHeader = rowIndex >= tableStart && rowIndex < tableStart + headerRows;
      const isAdjustmentHeader = row.map(value => String(value).toLowerCase()).includes('correlativo') && row.map(value => String(value).toLowerCase()).includes('haber');
      const style = rowIndex === 1 || rowIndex === 2 ? 5 : isHeader || isAdjustmentHeader ? 1 : rowIndex >= tableStart + headerRows && row.length === 1 ? 2 : rowText.startsWith('total') || rowText.startsWith('totales') || rowText.startsWith('resultado del período') ? 3 : rowIndex >= tableStart + headerRows && rowIndex % 2 === 1 ? 4 : 0;
      return `<row r="${rowIndex + 1}">${row.map((value, colIndex) => cellXml(value, `${colName(colIndex)}${rowIndex + 1}`, style)).join('')}</row>`;
    }).join('');
    const sheet = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheetData>${sheetRows}</sheetData><drawing r:id="rId1"/></worksheet>`;
    const files = [
      ['[Content_Types].xml', `<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/><Override PartName="/xl/drawings/drawing1.xml" ContentType="application/vnd.openxmlformats-officedocument.drawing+xml"/></Types>`],
      ['_rels/.rels', `<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>`],
      ['xl/workbook.xml', `<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="${xmlEscape(title.slice(0,31))}" sheetId="1" r:id="rId1"/></sheets></workbook>`],
      ['xl/_rels/workbook.xml.rels', `<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>`],
      ['xl/worksheets/sheet1.xml', sheet],
      ['xl/worksheets/_rels/sheet1.xml.rels', `<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/drawing" Target="../drawings/drawing1.xml"/></Relationships>`],
      ['xl/styles.xml', `<?xml version="1.0" encoding="UTF-8"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><numFmts count="1"><numFmt numFmtId="164" formatCode="&quot;$&quot;#,##0.00;[Red](&quot;$&quot;#,##0.00)"/></numFmts><fonts count="3"><font><sz val="11"/><name val="Calibri"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="10"/><name val="Calibri"/></font><font><b/><color rgb="FF102B45"/><sz val="11"/><name val="Calibri"/></font></fonts><fills count="5"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF102B45"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFE5F0DD"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFF0F7EA"/><bgColor indexed="64"/></patternFill></fill></fills><borders count="2"><border><left/><right/><top/><bottom/><diagonal/></border><border><left style="thin"><color rgb="FF8BD0CE"/></left><right style="thin"><color rgb="FF8BD0CE"/></right><top style="thin"><color rgb="FF8BD0CE"/></top><bottom style="thin"><color rgb="FFA6D9D2"/></bottom><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="8"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf><xf numFmtId="0" fontId="2" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/><xf numFmtId="0" fontId="2" fillId="4" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/><xf numFmtId="0" fontId="0" fillId="4" borderId="1" xfId="0" applyFill="1" applyBorder="1"/><xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"/><xf numFmtId="164" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyBorder="1"/><xf numFmtId="164" fontId="0" fillId="4" borderId="1" xfId="0" applyNumberFormat="1" applyFill="1" applyBorder="1"/></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>`],
      ['xl/drawings/drawing1.xml', `<?xml version="1.0" encoding="UTF-8"?><xdr:wsDr xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><xdr:oneCellAnchor><xdr:from><xdr:col>0</xdr:col><xdr:colOff>0</xdr:colOff><xdr:row>0</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:from><xdr:ext cx="1500000" cy="500000"/><xdr:pic><xdr:nvPicPr><xdr:cNvPr id="1" name="SunGames"/><xdr:cNvPicPr><a:picLocks noChangeAspect="1"/></xdr:cNvPicPr></xdr:nvPicPr><xdr:blipFill><a:blip r:embed="rId1"/><a:stretch><a:fillRect/></a:stretch></xdr:blipFill><xdr:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="1500000" cy="500000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></xdr:spPr></xdr:pic><xdr:clientData/></xdr:oneCellAnchor></xdr:wsDr>`],
      ['xl/drawings/_rels/drawing1.xml.rels', `<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/image1.png"/></Relationships>`],
      ['xl/media/image1.png', logoBytes],
    ];
    const crcTable = Array.from({ length: 256 }, (_, n) => { let value = n; for (let k = 0; k < 8; k++) value = value & 1 ? 0xedb88320 ^ (value >>> 1) : value >>> 1; return value >>> 0; });
    const crc32 = bytes => { let crc = 0xffffffff; for (const byte of bytes) crc = crcTable[(crc ^ byte) & 0xff] ^ (crc >>> 8); return (crc ^ 0xffffffff) >>> 0; };
    const encoder = new TextEncoder();
    const localParts = [], centralParts = [];
    let offset = 0;
    files.forEach(([path, content]) => {
      const nameBytes = encoder.encode(path), data = content instanceof Uint8Array ? content : encoder.encode(content), crc = crc32(data);
      const local = new Uint8Array(30 + nameBytes.length); const lv = new DataView(local.buffer);
      lv.setUint32(0, 0x04034b50, true); lv.setUint16(4, 20, true); lv.setUint16(6, 0, true); lv.setUint16(8, 0, true); lv.setUint16(10, 0, true); lv.setUint16(12, 0x21, true); lv.setUint32(14, crc, true); lv.setUint32(18, data.length, true); lv.setUint32(22, data.length, true); lv.setUint16(26, nameBytes.length, true); lv.setUint16(28, 0, true); local.set(nameBytes, 30);
      localParts.push(local, data);
      const central = new Uint8Array(46 + nameBytes.length); const cv = new DataView(central.buffer);
      cv.setUint32(0, 0x02014b50, true); cv.setUint16(4, 20, true); cv.setUint16(6, 20, true); cv.setUint16(8, 0, true); cv.setUint16(10, 0, true); cv.setUint16(12, 0, true); cv.setUint16(14, 0x21, true); cv.setUint32(16, crc, true); cv.setUint32(20, data.length, true); cv.setUint32(24, data.length, true); cv.setUint16(28, nameBytes.length, true); cv.setUint16(30, 0, true); cv.setUint16(32, 0, true); cv.setUint32(42, offset, true); central.set(nameBytes, 46);
      centralParts.push(central); offset += local.length + data.length;
    });
    const centralSize = centralParts.reduce((sum, part) => sum + part.length, 0), end = new Uint8Array(22), ev = new DataView(end.buffer);
    ev.setUint32(0, 0x06054b50, true); ev.setUint16(8, files.length, true); ev.setUint16(10, files.length, true); ev.setUint32(12, centralSize, true); ev.setUint32(16, offset, true);
    const blob = new Blob([...localParts, ...centralParts, end], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = `${title.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-zA-Z0-9]+/g, '_')}.xlsx`; document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(link.href), 1000);
    showToast('Archivo Excel descargado.', 'success');
  }

  function annualReport() {
    const year = state.worksheet.from.slice(0, 4);
    const closeAction = ['Administrador', 'Contador General']
      .includes(state.currentUser.role) && state.periodStatus === 'ABIERTO'
      ? `<div class="heading-actions section-gap"><button class="button button-primary" type="button" data-action="confirm-annual-close">Solicitar cierre anual</button></div>`
      : '';
    return `<section class="card"><div class="card-header"><div><h2>Informes relacionados con el cierre anual</h2><p>Ejercicio con Hoja de Trabajo disponible</p></div><span class="tag tag-demo">${safe(year)}</span></div><div class="card-body"><div class="quick-links"><button class="quick-link" type="button" data-report="results">Estado de Resultados <span>↗</span></button><button class="quick-link" type="button" data-report="changes">Estado de Cambios en el Patrimonio <span>↗</span></button><button class="quick-link" type="button" data-report="balance">Balance General <span>↗</span></button><button class="quick-link" type="button" data-report="worksheet">Hoja de Trabajo <span>↗</span></button></div>${closeAction}</div></section>`;
  }

  const operationTabs = [['verify', 'Verificar ventas'], ['post', 'Contabilizar ventas'], ['reconcile', 'Conciliar ventas'], ['steam', 'Conexión Steam']];
  function operationsPage() {
    const activeTitle = operationTabs.find(([id]) => id === state.operation)?.[1] || operationTabs[0][1];
    const tabs = `<div class="tabs">${operationTabs.map(([id, title]) => `<button class="tab-button ${state.operation === id ? 'active' : ''}" type="button" data-operation="${id}">${title}</button>`).join('')}</div>`;
    const content = state.operation === 'post' ? postSalesPanel() : state.operation === 'reconcile' ? reconcilePanel() : state.operation === 'steam' ? steamPanel() : verifySalesPanel();
    return `${heading('Ventas', 'Consulta y registra ventas.', '')}${tabs}${content}`;
  }

  function verifySalesPanel() {
    const filtered = sales.filter(item => !state.salesQuery || `${item.id} ${item.title} ${item.channel}`.toLowerCase().includes(state.salesQuery.toLowerCase()));
    return `<div class="demo-banner"><span><strong>Resumen del período</strong> · Consulta de ventas.</span></div><div class="filter-bar"><div class="field grow"><label for="salesQuery">Buscar venta</label><input id="salesQuery" value="${safe(state.salesQuery)}" placeholder="Código, título o canal"/></div><div class="field"><label for="salesFrom">Desde</label><input id="salesFrom" type="date" value="${safe(state.salesFrom)}"/></div><div class="field"><label for="salesTo">Hasta</label><input id="salesTo" type="date" value="${safe(state.salesTo)}"/></div><button class="button button-secondary" type="button" data-action="filter-sales">Consultar</button></div><section class="card"><div class="card-header"><div><h2>Ventas</h2><p>Listado de ventas identificadas para consulta</p></div><span class="tag">${filtered.length} ventas</span></div><div class="table-wrap"><table><thead><tr><th>Fecha</th><th>Identificador</th><th>Producto</th><th>Canal</th><th>Origen</th><th>Estado</th><th class="num">Monto</th></tr></thead><tbody>${filtered.map(sale => `<tr><td>${safe(sale.date)}</td><td><strong>${safe(sale.id)}</strong><small>${safe(sale.correlativo || (sale.status === 'Pendiente' ? 'Sin correlativo hasta registrar' : ''))}</small></td><td>${safe(sale.title)}</td><td>${safe(sale.channel)}</td><td>${safe(sale.origin)}</td><td><span class="tag ${sale.status === 'Registrada' ? 'tag-open' : 'tag-muted'}">${safe(sale.status)}</span></td><td class="num">${money(sale.amount)}</td></tr>`).join('')}</tbody></table></div></section>`;
  }

  function postSalesPanel() {
    const pending = sales.filter(sale => sale.status === 'Pendiente');
    return `<div class="notice"><span class="notice-icon">i</span><span>Al registrar una venta, el ingreso se aplica directamente a la cuenta correspondiente del Libro Mayor.</span></div><section class="card section-gap"><div class="card-header"><div><h2>Ventas pendientes de registro</h2><p>Selecciona una venta para registrarla directamente en el Libro Mayor.</p></div><span class="tag tag-muted">${pending.length} pendientes</span></div><div class="table-wrap"><table><thead><tr><th>Fecha</th><th>Venta</th><th>Producto</th><th>Canal</th><th class="num">Monto</th><th></th></tr></thead><tbody>${pending.length ? pending.map(sale => `<tr><td>${safe(sale.date)}</td><td><strong>${safe(sale.id)}</strong></td><td>${safe(sale.title)}</td><td>${safe(sale.channel)}</td><td class="num">${money(sale.amount)}</td><td class="num">${state.canPostSales ? `<button class="button button-primary button-small" type="button" data-action="post-sale" data-sale="${safe(sale.id)}">Registrar</button>` : '—'}</td></tr>`).join('') : `<tr><td colspan="6"><div class="empty-state"><strong>No hay ventas pendientes</strong></div></td></tr>`}</tbody></table></div></section>`;
  }

  // TODO(CU-08.3): cotejar liquidaciones y depósitos bancarios requiere
  // definir el formato de liquidación de Steam.
  function reconcilePanel() {
    const preview = state.reconciliationPreview;
    const result = state.reconciliationResult;
    const impactTable = (resumen, titulo) => `<section class="card section-gap"><div class="card-header"><div><h2>${titulo}</h2><p>${resumen.conciliadas ?? resumen.eventos} eventos · Total conciliado ${money(resumen.total)}</p></div></div><div class="table-wrap"><table><thead><tr><th>Cuenta afectada</th><th class="num">Debe</th><th class="num">Haber</th></tr></thead><tbody>${(resumen.cuentasAfectadas || []).map(cuenta => `<tr><td><strong>${safe(cuenta.codigo)}</strong><small>${safe(cuenta.denominacion)}</small></td><td class="num">${money(cuenta.debe)}</td><td class="num">${money(cuenta.haber)}</td></tr>`).join('') || '<tr><td colspan="3"><div class="empty-state"><strong>No hay movimientos para este período.</strong></div></td></tr>'}</tbody><tfoot><tr><th>Total de movimientos</th><th class="num">${money((resumen.cuentasAfectadas || []).reduce((sum, cuenta) => sum + Number(cuenta.debe), 0))}</th><th class="num">${money((resumen.cuentasAfectadas || []).reduce((sum, cuenta) => sum + Number(cuenta.haber), 0))}</th></tr></tfoot></table></div></section>`;
    const previewMarkup = preview ? `<div class="notice section-gap"><span class="notice-icon">i</span><span>${preview.eventos} eventos Steam · Vista previa de su afectación en el Libro Mayor.</span></div>${impactTable(preview, 'Cuentas que afectaría') }<div class="heading-actions section-gap"><button class="button button-primary" type="button" data-action="confirm-reconciliation">Confirmar y contabilizar</button></div>` : '';
    const errors = result?.errores?.length ? `<ul class="form-errors">${result.errores.map(error => `<li>${safe(error.id)}: ${safe(error.mensaje)}</li>`).join('')}</ul>` : '<p class="help">Sin errores.</p>';
    const resultMarkup = result ? `${impactTable(result, 'Resultado de la conciliación')}<section class="card section-gap"><div class="card-body">${errors}</div></section>` : '';
    return `<div class="demo-banner"><span><strong>Resumen de eventos Steam</strong> · Esta pantalla muestra el efecto contable de las ventas del período. El formato de liquidación bancaria de Steam sigue pendiente de definición.</span></div><section class="card"><div class="card-header"><div><h2>Conciliar ventas</h2><p>Calcula importes por período antes de confirmar el registro en el Libro Mayor.</p></div></div><div class="card-body"><div class="filter-bar" style="margin:0"><div class="field"><label for="reconcileFrom">Desde</label><input id="reconcileFrom" type="date" value="${safe(state.reconcileFrom || '2026-10-01')}"/></div><div class="field"><label for="reconcileTo">Hasta</label><input id="reconcileTo" type="date" value="${safe(state.reconcileTo || '2026-10-31')}"/></div><button class="button button-secondary" type="button" data-action="preview-reconciliation">Calcular período</button></div>${previewMarkup}${resultMarkup}</div></section>`;
  }

  function steamPanel() {
    const statusStyle = state.steamStatus === 'Conectado' ? 'steam-connected' : state.steamStatus === 'Error' ? 'steam-error' : state.steamStatus === 'Fuera de servicio' ? 'steam-offline' : 'steam-waiting';
    const statusIcon = state.steamStatus === 'Conectado' ? '✓' : state.steamStatus === 'Error' ? '!' : state.steamStatus === 'Fuera de servicio' ? '×' : '…';
    const contacto = state.steamContact ? new Date(state.steamContact).toLocaleString('es-SV') : 'Sin latidos registrados';
    const error = state.steamError ? new Date(state.steamError).toLocaleString('es-SV') : 'Sin errores recientes';
    return `<section class="card steam-card"><div class="card-header"><div><h2>Simulador de ventas</h2><p>Genera una venta para un título con orden finalizada.</p></div><button class="button button-primary" type="button" data-action="run-simulator-cycle">Ejecutar ciclo</button></div><div class="card-body"><div class="steam-status-panel ${statusStyle}"><span class="steam-status-icon">${statusIcon}</span><div><strong>${safe(state.steamStatus)}</strong><small>Estado de conexión</small></div></div><p class="steam-note">Último latido: ${safe(contacto)} · Último error autenticado: ${safe(error)}</p></div></section>`;
  }

  function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const icon = document.createElement('span');
    icon.className = 'toast-icon';
    icon.setAttribute('aria-hidden', 'true');
    icon.textContent = type === 'error' ? '×' : type === 'warning' ? '⚠' : '✓';
    const text = document.createElement('span');
    text.textContent = message;
    toast.append(icon, text);
    $('#toastRoot').append(toast);
    setTimeout(() => toast.remove(), 3000);
  }

  function openModal(title, description, fields, submitLabel, onSubmit) {
    $('#modalRoot').innerHTML = `<div class="modal-backdrop" data-action="backdrop-close"><section class="modal" role="dialog" aria-modal="true" aria-label="${safe(title)}"><div class="modal-header"><div><h2>${safe(title)}</h2><p>${safe(description)}</p></div><button class="modal-close" type="button" data-action="close-modal" aria-label="Cerrar">×</button></div><form id="genericModalForm" class="modal-form"><div class="modal-fields">${fields}</div><div class="modal-actions"><button class="button button-secondary" type="button" data-action="close-modal">Cancelar</button><button class="button button-primary" type="submit">${safe(submitLabel)}</button></div></form></section></div>`;
    $('#genericModalForm').onsubmit = event => { event.preventDefault(); const data = Object.fromEntries(new FormData(event.currentTarget).entries()); if (onSubmit(data) !== false) $('#modalRoot').innerHTML = ''; };
    $('.modal-backdrop').addEventListener('click', event => { if (event.target === $('.modal-backdrop')) $('#modalRoot').innerHTML = ''; });
  }

  function onAction(action, target) {
    if (action === 'show-trial-balance') { state.ledgerMode = 'trial-balance'; page(); }
    if (action === 'back-ledger') { state.ledgerMode = 'ledger'; page(); }
    if (action === 'refresh-trial-balance') { state.trialBalanceTo = $('#trialBalanceTo').value || today(); page(); }
    if (action === 'export') { if (!exportNiif(target.dataset.source, target.dataset.format)) exportDocument(target.dataset.source || 'report', target.dataset.format || 'pdf'); }
    if (action === 'generate-report') showToast('Reporte actualizado con los movimientos del período.', 'success');
    if (action === 'close-period') { state.report = 'provisional'; page(); }
    if (action === 'generate-worksheet') generateWorksheet();
    if (action === 'check-provisional') consultProvisionalRequirements();
    if (action === 'confirm-provisional-close') requestProvisionalClose();
    if (action === 'reopen-period') requestPeriodReopen();
    if (action === 'go-provisional') { state.report = 'provisional'; page(); }
    if (action === 'filter-sales') { state.salesQuery = $('#salesQuery').value; state.salesFrom = $('#salesFrom').value; state.salesTo = $('#salesTo').value; loadSales(); }
    if (action === 'run-simulator-cycle') runSimulatorCycle(target);
    if (action === 'post-sale') postSale(target.dataset.sale);
    if (action === 'reload-cost-dashboard') {
      state.dashboardCostosError = null;
      page();
    }
    if (action === 'reload-closed-period') {
      state.closedPeriodLoaded = false;
      loadClosedPeriod(true);
    }
    if (action === 'preview-reconciliation') previewReconciliation();
    if (action === 'confirm-reconciliation') confirmReconciliation();
    if (action === 'confirm-annual-close') requestAnnualClose();
    if (action === 'close-modal') $('#modalRoot').innerHTML = '';
  }

  function exportNiif(source, format) {
    const tipos = { results: 'estado-resultados', balance: 'balance-general' };
    if (source !== 'report' || format !== 'pdf' || !tipos[state.report] || !state.worksheet) return false;
    window.location.assign(`${screenUrls.pdf_estados.replace('TIPO', tipos[state.report])}?${new URLSearchParams({ desde: state.worksheet.from, hasta: state.worksheet.to })}`);
    return true;
  }

  async function loadSales() {
    state.salesLoading = true;
    state.salesError = null;
    try {
      const params = new URLSearchParams({ q: state.salesQuery, desde: state.salesFrom, hasta: state.salesTo });
      const data = await api(`${screenUrls.api_ventas}?${params}`);
      sales = data.ventas.map(sale => ({ ...sale, amount: Number(sale.amount) }));
      state.steamStatus = data.conexion.estado;
      state.steamContact = data.conexion.ultimoContacto;
      state.steamError = data.conexion.ultimoError;
      state.canPostSales = data.puedeContabilizar;
    } catch (error) {
      state.salesError = error.message;
      showToast(error.message, 'error');
    } finally {
      state.salesLoading = false;
      state.salesLoaded = true;
    }
    if (['dashboard', 'operations'].includes(state.current)) page();
  }

  async function postSale(id) {
    try {
      const result = await api(`${screenUrls.api_ventas}${encodeURIComponent(id)}/contabilizar/`, { method: 'POST' });
      state.worksheet = null;
      state.provisional = null;
      showToast(result.mensaje, 'success');
    } catch (error) {
      showToast(error.message, 'error');
    }
    loadSales();
  }

  async function runSimulatorCycle(button) {
    button.disabled = true;
    button.textContent = 'Ejecutando…';
    try {
      const resultado = await api(screenUrls.api_simulator_cycle, {
        method: 'POST',
      });
      const mensaje = resultado.estado === 'enviada'
        ? `Venta simulada enviada: ${resultado.titulo}.`
        : resultado.detalle || 'No se generó una venta.';
      const tipoAviso = resultado.estado === 'error'
        ? 'error' : resultado.estado === 'omitido' ? 'warning' : 'success';
      showToast(mensaje, tipoAviso);
      await loadSales();
    } catch (error) {
      showToast(error.message, 'error');
      button.disabled = false;
      button.textContent = 'Ejecutar ciclo';
    }
  }

  function handleForm(event) {
    if (event.target.id === 'adjustmentForm') {
      event.preventDefault();
      const sheet = state.worksheet;
      if (state.periodStatus !== 'ABIERTO' || !sheet) { showToast('No se pueden agregar ajustes a un período cerrado.', 'warning'); return; }
      api(screenUrls.api_ajuste, { method: 'POST', body: new FormData(event.target) }).then(async result => {
        await loadProvisional(sheet.from, sheet.to);
        state.report = 'worksheet';
        const balanced = worksheetChecks(state.worksheet).every(item => item.ok);
        page();
        showToast(balanced ? result.mensaje : `${result.mensaje} La hoja aún no cuadra.`, balanced ? 'success' : 'warning');
      }).catch(error => showToast(error.message, 'error'));
      return;
    }
  }

  $('#logoutButton').addEventListener('click', () => {
    state.currentUser = null;
  });

  $('#appShell').addEventListener('click', event => {
    const viewButton = event.target.closest('[data-view]');
    const reportButton = event.target.closest('[data-report]');
    const operationButton = event.target.closest('[data-operation]');
    const actionButton = event.target.closest('[data-action]');
    if (viewButton) {
      if (!canView(viewButton.dataset.view)) { showToast('Esta pantalla está disponible para el administrador.', 'error'); return; }
      const nextView = viewButton.dataset.view;
      const params = {};
      if (nextView === 'ledger') state.ledgerMode = 'ledger';
      if (viewButton.dataset.operation) {
        state.operation = viewButton.dataset.operation;
        params.operation = state.operation;
      }
      setScreen(nextView, params);
      $('#sidebar').classList.remove('is-open'); return;
    }
    if (reportButton) {
      const nextReport = reportButton.dataset.report;
      state.report = (state.closedPeriod
          || state.indicatorPeriodStatus === 'CERRADO_PROVISIONAL')
        && ['provisional', 'closing'].includes(nextReport)
        ? 'worksheet' : nextReport;
      updateScreenQuery('report', state.report);
      page();
      return;
    }
    if (operationButton) { state.operation = operationButton.dataset.operation; updateScreenQuery('operation', state.operation); page(); return; }
    if (actionButton) onAction(actionButton.dataset.action, actionButton);
  });
  $('#appShell').addEventListener('submit', handleForm);
  $('#appShell').addEventListener('change', event => {
    if (event.target.id === 'dashboardPeriod') { state.period = event.target.value; page(); }
  });
  $('#modalRoot').addEventListener('click', event => {
    const action = event.target.closest('[data-action]')?.dataset.action;
    if (action === 'close-modal') $('#modalRoot').innerHTML = '';
  });
  $('#menuToggle').addEventListener('click', () => $('#sidebar').classList.toggle('is-open'));

  function showCurrentUser() {
    if (!state.currentUser) return;
    const user = state.currentUser;
    $('#activeUser').textContent = user.role === 'Contador General' ? `Bienvenida, ${user.name}` : `Te damos la bienvenida, ${user.name}`;
    $('.avatar').textContent = user.name.split(/\s+/).slice(0, 2).map(word => word[0]).join('').toUpperCase();
  }

  function showScreenFromUrl() {
    if (!state.currentUser) {
      window.location.replace(screenUrls.login);
      return;
    }
    const screen = serverRendered ? initialScreen : Object.keys(screenUrls).find(name => !['login', 'logout'].includes(name) && new URL(screenUrls[name], window.location.origin).pathname === window.location.pathname) || 'dashboard';
    state.current = screen;
    const params = new URLSearchParams(window.location.search);
    state.report = params.get('report') || state.report;
    state.operation = params.get('operation') || state.operation;
    state.ledgerMode = params.get('mode') || state.ledgerMode;
    $('#appShell').dataset.screen = state.current;
    showCurrentUser();
    page();
  }

  function wireAccountForm() {
    const form = $('#modalRoot [data-cuenta-form]');
    if (!form) return;
    const rubro = $('[name="rubro"]', form);
    const subtipo = $('[name="subtipo"]', form);
    if (!rubro || !subtipo) return;
    const preview = $('#codigoPropuesto', form);
    const filterSubtypes = () => {
      $$('option', subtipo).forEach(option => { option.hidden = Boolean(option.value) && !option.value.startsWith(rubro.value); });
      if (subtipo.value && !subtipo.value.startsWith(rubro.value)) subtipo.value = '';
    };
    const updatePreview = async () => {
      if (!preview) return;
      preview.value = '';
      if (!rubro.value || !subtipo.value) return;
      const url = new URL(preview.dataset.url, window.location.origin);
      url.searchParams.set('rubro', rubro.value);
      url.searchParams.set('subtipo', subtipo.value);
      const response = await fetch(url, { credentials: 'same-origin', headers: { Accept: 'application/json' } });
      const data = await response.json().catch(() => ({}));
      preview.value = data.codigo || '';
      preview.placeholder = data.error || 'Elige tipo y subtipo';
    };
    rubro.addEventListener('change', () => { filterSubtypes(); updatePreview(); });
    subtipo.addEventListener('change', updatePreview);
    filterSubtypes();
    updatePreview();
  }

  wireAccountForm();

  function wireLedgerForm() {
    const account = $('[data-ledger-account]');
    if (account) account.addEventListener('change', () => account.form.submit());
    const form = $('[data-ledger-form]');
    if (!form) return;
    const rows = () => $$('.ledger-input-row', $('#movementRows'));
    const total = $('#id_mov-TOTAL_FORMS');
    const renumber = () => {
      rows().forEach((row, index) => {
        $('.line-col', row).textContent = String(index + 1).padStart(2, '0');
        $$('[name^="mov-"]', row).forEach(input => {
          input.name = input.name.replace(/^mov-\d+-/, `mov-${index}-`);
          input.id = input.id.replace(/^id_mov-\d+-/, `id_mov-${index}-`);
        });
      });
      total.value = rows().length;
    };
    $('[data-ledger-add]', form).addEventListener('click', () => {
      const index = rows().length;
      $('#movementRows').insertAdjacentHTML('beforeend', $('#movementRowTemplate').innerHTML.replace(/__prefix__/g, index).replace(/__numero__/g, String(index + 1).padStart(2, '0')));
      total.value = index + 1;
    });
    $('#movementRows').addEventListener('click', event => {
      if (!event.target.closest('[data-ledger-remove]')) return;
      if (rows().length <= 1) { showToast('Debe permanecer al menos una fila.', 'warning'); return; }
      event.target.closest('.ledger-input-row').remove();
      renumber();
    });
    form.addEventListener('submit', event => {
      if (!window.confirm(`¿Guardar ${rows().length} movimiento(s) en el Libro Mayor?`)) event.preventDefault();
    });
  }

  wireLedgerForm();
  window.addEventListener('popstate', showScreenFromUrl);
  showScreenFromUrl();
  JSON.parse($('#serverMessages').textContent).forEach(message => showToast(message.text, message.level === 'success' ? 'success' : message.level === 'warning' ? 'warning' : 'error'));
})();
