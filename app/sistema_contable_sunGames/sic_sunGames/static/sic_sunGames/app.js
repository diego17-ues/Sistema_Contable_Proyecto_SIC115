(() => {
  'use strict';

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const money = value => new Intl.NumberFormat('es-SV', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(Number(value) || 0);
  const number = value => new Intl.NumberFormat('es-SV', { maximumFractionDigits: 2 }).format(Number(value) || 0);
  const today = () => new Date().toISOString().slice(0, 10);
  const safe = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
  const screenUrls = JSON.parse($('#screenUrls').textContent);
  const logoUrl = JSON.parse($('#logoUrl').textContent);
  const initialScreen = $('#appShell').dataset.screen || 'dashboard';
  const initialParams = new URLSearchParams(window.location.search);
  const savedUser = JSON.parse($('#currentUser').textContent);
  const modulos = JSON.parse($('#modulos').textContent);
  const serverRendered = $('#appContent').dataset.serverRendered === 'true';
  const serverScreens = ['users', 'audit'];

  const navGroups = [
    { label: 'Inicio', items: [{ id: 'dashboard', title: 'Dashboard', icon: '⌂' }] },
    { label: 'Contabilidad', items: [{ id: 'ledger', title: 'Libro Mayor', icon: '▤' }, { id: 'accounts', title: 'Catálogo de cuentas', icon: '☷' }, { id: 'reports', title: 'Estados financieros', icon: '▥' }] },
    { label: 'Operación', items: [{ id: 'operations', title: 'Ventas y costos', icon: '◫' }] },
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
  const ledgerRows = [
    { id: 1, date: '2026-10-31', code: '5101', account: 'Ingresos por licencias de videojuegos', concept: 'Ventas · corte de octubre', reference: 'V-1048', type: 'Comprobante de Ingreso', correlativo: 'Comprobante de Ingreso-2026-00001', side: 'Abono', amount: 6240 },
    { id: 2, date: '2026-10-31', code: '4104', account: 'Costo de ventas', concept: 'Costo · corte de octubre', reference: 'CST-1031', type: 'Comprobante de Egreso', correlativo: 'Comprobante de Egreso-2026-00001', side: 'Cargo', amount: 2380 },
    { id: 3, date: '2026-10-30', code: '4201', account: 'Sueldos y salarios administrativos', concept: 'Gastos · corte de octubre', reference: 'GAS-1030', type: 'Comprobante de Egreso', correlativo: 'Comprobante de Egreso-2026-00002', side: 'Cargo', amount: 940 },
    { id: 4, date: '2026-10-29', code: '5101', account: 'Ingresos por licencias de videojuegos', concept: 'Venta · Título A', reference: 'V-1046', type: 'Comprobante de Ingreso', correlativo: 'Comprobante de Ingreso-2026-00002', side: 'Abono', amount: 1280 },
    { id: 5, date: '2026-10-27', code: '4104', account: 'Costo de ventas', concept: 'Costo · Título A', reference: 'CST-1027', type: 'Comprobante de Egreso', correlativo: 'Comprobante de Egreso-2026-00003', side: 'Cargo', amount: 520 },
    { id: 6, date: '2026-10-01', code: '1101', account: 'Caja general', concept: 'Saldo de apertura', reference: 'AP-2026', type: 'Diario', correlativo: 'Diario-2026-00001', side: 'Cargo', amount: 3000 },
    { id: 7, date: '2026-10-01', code: '3101', account: 'Capital social', concept: 'Saldo de capital', reference: 'AP-2026', type: 'Diario', correlativo: 'Diario-2026-00002', side: 'Abono', amount: 3000 },
    { id: 8, date: '2026-10-28', code: '5101', account: 'Ingresos por licencias de videojuegos', concept: 'Venta · Título C', reference: 'V-1045', type: 'Comprobante de Ingreso', correlativo: 'Comprobante de Ingreso-2026-00003', side: 'Abono', amount: 615 },
  ];

  const sales = [
    { id: 'V-1048', date: '2026-10-31', title: 'Título A', channel: 'Tienda digital', amount: 1280, status: 'Pendiente' },
    { id: 'V-1047', date: '2026-10-30', title: 'Título B', channel: 'Tienda digital', amount: 940, status: 'Pendiente' },
    { id: 'V-1046', date: '2026-10-29', title: 'Título A', channel: 'Steam', amount: 760, status: 'Registrada', correlativo: 'Comprobante de Ingreso-2026-00002' },
    { id: 'V-1045', date: '2026-10-28', title: 'Título C', channel: 'Tienda digital', amount: 615, status: 'Registrada', correlativo: 'Comprobante de Ingreso-2026-00003' },
    { id: 'V-1044', date: '2026-10-27', title: 'Título B', channel: 'Steam', amount: 480, status: 'Pendiente' },
  ];

  const state = {
    current: initialScreen, report: initialParams.get('report') || 'results', operation: initialParams.get('operation') || 'verify', period: 'month',
    currentUser: savedUser, ledgerMode: initialParams.get('mode') || 'ledger', trialBalanceTo: today(),
    ledgerFilter: { account: '5101', from: '', to: '' }, salesQuery: '', accountQuery: '', accountGroup: '',
    periodStatus: 'ABIERTO', closedRange: null, worksheet: null, provisionalFrom: '2026-10-01', provisionalTo: '2026-10-31',
    steamStatus: 'En espera',
    nextLedgerId: 9,
    salesTotal: 78240,
  };

  function renderNavigation() {
    const visibleGroups = navGroups.map(group => ({ ...group, items: group.items.filter(item => modulos.includes(item.id)) })).filter(group => group.items.length);
    $('#navigation').innerHTML = visibleGroups.map(group => `<div class="nav-label">${group.label}</div>${group.items.map(item => `<button type="button" class="nav-link ${state.current === item.id ? 'active' : ''}" data-view="${item.id}"><span class="nav-icon" aria-hidden="true">${item.icon}</span><span>${item.title}</span></button>`).join('')}`).join('');
  }

  function canView(view) {
    return modulos.includes(view);
  }

  function setScreen(view, params = {}, replace = false) {
    if (serverScreens.includes(view) || serverRendered) { window.location.assign(screenUrls[view]); return; }
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
    return `<div class="page-heading"><div><h1>${title}</h1><p>${subtitle}</p></div><div class="heading-actions">${actions}</div></div>`;
  }

  function page() {
    if (!canView(state.current)) {
      window.location.replace(screenUrls[modulos.includes('dashboard') ? 'dashboard' : modulos[0]] || screenUrls.logout);
      return;
    }
    renderNavigation();
    const titles = { dashboard: 'Dashboard', ledger: 'Libro Mayor', accounts: 'Catálogo de cuentas', reports: 'Estados financieros', operations: 'Ventas y costos', users: 'Usuarios', audit: 'Auditoría' };
    $('#breadcrumb').textContent = titles[state.current] || 'Panel';
    const periodClosed = state.periodStatus === 'CERRADO_PROVISIONAL';
    const periodLabel = periodClosed ? 'Período cerrado provisionalmente' : 'Período abierto';
    $('.sidebar-period span:last-child').textContent = periodLabel;
    $('.sidebar-period .status-dot').classList.toggle('is-closed', periodClosed);
    $('.topbar-period').innerHTML = `<span class="status-dot ${periodClosed ? 'is-closed' : ''}"></span>${periodLabel}`;
    if (serverRendered) return;
    const renderers = { dashboard: dashboardPage, ledger: ledgerPage, accounts: accountsPage, reports: reportsPage, operations: operationsPage };
    $('#appContent').innerHTML = (renderers[state.current] || dashboardPage)();
    if ($('#provisionalFrom') && state.provisionalFrom) $('#provisionalFrom').value = state.provisionalFrom;
    syncScreenUrl();
  }

  function dashboardPage() {
    const periodLabel = state.period === 'year' ? 'Año actual' : state.period === 'quarter' ? 'Últimos 90 días' : 'Últimos 30 días';
    const salesValue = state.salesTotal + (state.period === 'year' ? 34420 : state.period === 'quarter' ? 12860 : 0);
    const lastSale = sales[0];
    return `${heading('Dashboard', 'Resumen de ventas y rendimiento de costos.', `<button class="button button-gold" type="button" data-action="simulate-sale">＋ Nueva venta</button>`)}
      <div class="demo-banner"><div class="dashboard-filter"><label for="dashboardPeriod">Período</label><select id="dashboardPeriod"><option value="month" ${state.period === 'month' ? 'selected' : ''}>Últimos 30 días</option><option value="quarter" ${state.period === 'quarter' ? 'selected' : ''}>Últimos 90 días</option><option value="year" ${state.period === 'year' ? 'selected' : ''}>Año actual</option></select></div></div>
      <div class="kpi-grid">
        <article class="card kpi-card" data-icon="＄"><div class="kpi-label">Ventas registradas</div><div class="kpi-value">${money(salesValue)}</div><div class="kpi-foot"><span class="positive">${periodLabel}</span> · valores del período</div></article>
        <article class="card kpi-card" data-icon="↗"><div class="kpi-label">Resultado bruto</div><div class="kpi-value">${money(28640 + (sales.length - 5) * 85)}</div><div class="kpi-foot">Resultado del período</div></article>
        <article class="card kpi-card" data-icon="◷"><div class="kpi-label">Costo estimado</div><div class="kpi-value">${money(49600)}</div><div class="kpi-foot">Comparativo del período</div></article>
        <article class="card kpi-card" data-icon="▤"><div class="kpi-label">Última venta</div><div class="kpi-value">${money(lastSale.amount)}</div><div class="kpi-foot">${safe(lastSale.date)} · ${safe(lastSale.title)}</div></article>
      </div>
      <div class="dashboard-grid">
        <section class="card"><div class="card-header"><div><h2>Ventas recientes</h2><p>Últimas operaciones</p></div><div class="chart-legend"><span><i class="legend-mark"></i>Ventas</span></div></div>
          <div class="card-body chart-area"><svg class="sales-chart" viewBox="0 0 620 205" role="img" aria-label="Gráfico de ventas"><defs><linearGradient id="salesFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#d8a628" stop-opacity=".23"/><stop offset="1" stop-color="#d8a628" stop-opacity="0"/></linearGradient></defs><line class="chart-grid" x1="42" y1="28" x2="605" y2="28"/><line class="chart-grid" x1="42" y1="77" x2="605" y2="77"/><line class="chart-grid" x1="42" y1="126" x2="605" y2="126"/><line class="chart-grid" x1="42" y1="175" x2="605" y2="175"/><text class="chart-axis" x="4" y="31">$4k</text><text class="chart-axis" x="4" y="80">$3k</text><text class="chart-axis" x="4" y="129">$2k</text><text class="chart-axis" x="4" y="178">$1k</text><path class="chart-area-fill" d="M42 139 L121 112 L200 123 L279 79 L358 91 L437 55 L516 74 L605 34 L605 175 L42 175 Z"/><path class="chart-line" d="M42 139 L121 112 L200 123 L279 79 L358 91 L437 55 L516 74 L605 34"/><circle class="chart-point" cx="42" cy="139" r="4"/><circle class="chart-point" cx="121" cy="112" r="4"/><circle class="chart-point" cx="200" cy="123" r="4"/><circle class="chart-point" cx="279" cy="79" r="4"/><circle class="chart-point" cx="358" cy="91" r="4"/><circle class="chart-point" cx="437" cy="55" r="4"/><circle class="chart-point" cx="516" cy="74" r="4"/><circle class="chart-point" cx="605" cy="34" r="4"/><text class="chart-axis" x="39" y="196">01</text><text class="chart-axis" x="118" y="196">05</text><text class="chart-axis" x="197" y="196">09</text><text class="chart-axis" x="276" y="196">13</text><text class="chart-axis" x="355" y="196">17</text><text class="chart-axis" x="434" y="196">21</text><text class="chart-axis" x="513" y="196">25</text><text class="chart-axis" x="597" y="196">30</text></svg></div></section>
        <section class="card"><div class="card-header"><div><h2>Rendimiento de costeo</h2><p>Presupuesto frente a costo real</p></div></div><div class="card-body"><div class="cost-list"><div><div class="cost-item-head"><span>Título A</span><strong>${money(18400)}</strong></div><div class="progress-track"><div class="progress-fill" style="width:72%"></div></div><div class="cost-meta"><span>Presupuesto ${money(25600)}</span><span>72%</span></div></div><div><div class="cost-item-head"><span>Título B</span><strong>${money(14100)}</strong></div><div class="progress-track"><div class="progress-fill navy-fill" style="width:86%"></div></div><div class="cost-meta"><span>Presupuesto ${money(16400)}</span><span>86%</span></div></div><div><div class="cost-item-head"><span>Título C</span><strong>${money(7100)}</strong></div><div class="progress-track"><div class="progress-fill green-fill" style="width:58%"></div></div><div class="cost-meta"><span>Presupuesto ${money(12200)}</span><span>58%</span></div></div></div></div></section>
      </div>
      <div class="dashboard-bottom"><section class="card"><div class="card-header"><div><h2>Últimas ventas</h2><p>Canal, fecha y estado de registro</p></div><button class="text-button" type="button" data-view="operations" data-operation="verify">Ver ventas →</button></div><div class="table-wrap"><table><thead><tr><th>Fecha</th><th>Producto</th><th>Canal</th><th>Estado</th><th class="num">Monto</th></tr></thead><tbody>${sales.slice(0, 4).map(sale => `<tr><td>${safe(sale.date)}</td><td><strong>${safe(sale.title)}</strong><small>${safe(sale.id)}</small></td><td>${safe(sale.channel)}</td><td><span class="tag ${sale.status === 'Registrada' ? 'tag-open' : 'tag-muted'}">${safe(sale.status)}</span></td><td class="num">${money(sale.amount)}</td></tr>`).join('')}</tbody></table></div></section><section class="card"><div class="card-header"><div><h2>Accesos rápidos</h2><p>Operaciones frecuentes</p></div></div><div class="card-body"><div class="quick-links"><button class="quick-link" type="button" data-view="ledger">Registrar movimiento <span>↗</span></button><button class="quick-link" type="button" data-view="reports">Estado de Resultados <span>↗</span></button><button class="quick-link" type="button" data-view="operations" data-operation="steam">Conexión con Steam <span>↗</span></button><button class="quick-link" type="button" data-view="accounts">Catálogo de cuentas <span>↗</span></button></div></div></section></div>`;
  }

  function accountOptions(selected = '') {
    return accounts.filter(account => account.status === 'Activa').map(account => `<option value="${safe(account.code)}" ${selected === account.code ? 'selected' : ''}>${safe(account.code)} · ${safe(account.name)}</option>`).join('');
  }

  function ledgerPage() {
    if (state.ledgerMode === 'trial-balance') return trialBalancePage();
    const selectedCode = state.ledgerFilter.account || '5101';
    const selectedAccount = accounts.find(account => account.code === selectedCode);
    let balance = 0;
    const accountRows = ledgerRows.filter(row => row.code === selectedCode).sort((a, b) => a.date.localeCompare(b.date) || a.id - b.id).map(row => {
      balance += row.side === 'Cargo' ? row.amount : -row.amount;
      return { ...row, balance, balanceSide: balance > 0 ? 'Deudor' : balance < 0 ? 'Acreedor' : 'Saldado' };
    });
    const filtered = accountRows.filter(row => (!state.ledgerFilter.from || row.date >= state.ledgerFilter.from) && (!state.ledgerFilter.to || row.date <= state.ledgerFilter.to));
    return `${heading('Libro Mayor', 'Consulta y registra movimientos por cuenta.', `<button class="button button-secondary" type="button" data-action="show-trial-balance">Balance de comprobación</button><button class="button button-secondary" type="button" data-action="export" data-source="ledger" data-format="xlsx">↓ Excel</button>`)}
      <div class="filter-bar ledger-filters"><div class="field grow"><label for="ledgerAccountFilter">Cuenta del Libro Mayor</label><select id="ledgerAccountFilter">${accountOptions(selectedCode)}</select></div><div class="field"><label for="ledgerFrom">Desde</label><input id="ledgerFrom" type="date" value="${safe(state.ledgerFilter.from)}"/></div><div class="field"><label for="ledgerTo">Hasta</label><input id="ledgerTo" type="date" value="${safe(state.ledgerFilter.to)}"/></div><button class="button button-secondary" type="button" data-action="filter-ledger">Consultar</button><button class="text-button" type="button" data-action="clear-ledger-filter">Limpiar fechas</button></div>
      <section class="card ledger-entry"><div class="ledger-account-banner"><span class="ledger-account-label">Cuenta contable</span><strong>${selectedAccount ? `${safe(selectedAccount.code)} · ${safe(selectedAccount.name)}` : 'Selecciona una cuenta'}</strong><span>${selectedAccount ? `${safe(selectedAccount.group)} · Naturaleza ${safe(selectedAccount.nature).toLowerCase()}` : ''}</span></div>
        <div class="entry-title"><div><h2>Registrar transacción</h2></div></div>
        <div class="table-wrap ledger-table-wrap"><table class="ledger-table ledger-input-table"><thead><tr><th class="line-col">N.º</th><th>Fecha</th><th>Descripción</th><th>Ref.</th><th>Tipo</th><th class="num">Debe</th><th class="num">Haber</th><th></th></tr></thead><tbody id="movementRows">${movementRowMarkup(1)}</tbody></table></div>
        <div class="entry-actions"><button class="button button-secondary button-small" type="button" data-action="add-ledger-row">＋ Agregar línea</button><div class="entry-actions-right"><button class="button button-primary" type="button" data-action="save-ledger">Guardar en Libro Mayor</button></div></div>
      </section>
      <section class="card ledger-history section-gap"><div class="card-header"><div><h2>Detalle del Libro Mayor</h2><p>${selectedAccount ? safe(selectedAccount.name) : 'Cuenta seleccionada'}</p></div><span class="tag">${filtered.length} transacciones</span></div><div class="table-wrap ledger-table-wrap"><table class="ledger-table" id="ledgerTable"><thead><tr><th class="line-col">N.º</th><th>Correlativo</th><th>Fecha</th><th>Descripción</th><th>Ref.</th><th class="num">Debe</th><th class="num">Haber</th><th class="num">Saldo</th></tr></thead><tbody>${filtered.length ? filtered.map((row, index) => `<tr><td class="line-col">${String(index + 1).padStart(2, '0')}</td><td><strong class="correlative-value">${safe(row.correlativo || '—')}</strong></td><td>${safe(row.date)}</td><td>${safe(row.concept)}</td><td>${safe(row.reference || '—')}</td><td class="num">${row.side === 'Cargo' ? money(row.amount) : '—'}</td><td class="num">${row.side === 'Abono' ? money(row.amount) : '—'}</td><td class="num ledger-balance"><strong>${money(Math.abs(row.balance))}</strong><small>${row.balanceSide}</small></td></tr>`).join('') : `<tr><td colspan="8"><div class="empty-state"><strong>Sin movimientos en esta cuenta</strong></div></td></tr>`}</tbody></table></div><div class="table-footer"><span>${filtered.length} registros</span></div></section>`;
  }

  function movementRowMarkup(lineNumber = 1) {
    return `<tr class="ledger-input-row"><td class="line-col">${String(lineNumber).padStart(2, '0')}</td><td><input class="ledger-line-date" type="date" value="${safe(today())}" aria-label="Fecha"/></td><td><input class="ledger-line-concept" aria-label="Descripción"/></td><td><input class="ledger-line-reference" aria-label="Referencia"/></td><td><select class="ledger-line-type" aria-label="Tipo de transacción"><option value="">Tipo</option>${transactionTypes.map(type => `<option value="${safe(type)}">${safe(type)}</option>`).join('')}</select></td><td><input class="ledger-line-debit money-input" type="number" min="0" step="0.01" aria-label="Debe"/></td><td><input class="ledger-line-credit money-input" type="number" min="0" step="0.01" aria-label="Haber"/></td><td><button class="movement-delete" type="button" data-action="remove-ledger-row" aria-label="Quitar línea">×</button></td></tr>`;
  }

  function trialBalanceRows(asOf) {
    return accounts.filter(account => account.status === 'Activa' || ledgerRows.some(row => row.code === account.code)).map(account => {
      const net = ledgerRows.filter(row => row.code === account.code && row.date <= asOf).reduce((sum, row) => sum + (row.side === 'Cargo' ? row.amount : -row.amount), 0);
      return { ...account, debit: Math.max(net, 0), credit: Math.max(-net, 0) };
    });
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

  function accountsPage() {
    const actions = state.currentUser?.role === 'Administrador' ? `<button class="button button-primary" type="button" data-action="new-account">＋ Nueva cuenta</button>` : '';
    return `${heading('Catálogo de cuentas', 'Consulta las cuentas contables.', actions)}
      <div class="filter-bar"><div class="field grow"><label for="accountQuery">Buscar cuenta</label><input id="accountQuery" value="${safe(state.accountQuery)}" placeholder="Código o denominación"/></div><div class="field"><label for="accountGroup">Tipo de cuenta</label><select id="accountGroup"><option value="">Todos</option>${['Activo', 'Pasivo', 'Patrimonio', 'Desarrollo', 'Egreso', 'Ingreso'].map(group => `<option ${state.accountGroup === group ? 'selected' : ''}>${group}</option>`).join('')}</select></div></div>
      <div id="accountResults">${accountResultsMarkup()}</div>`;
  }

  function accountResultsMarkup() {
    const query = state.accountQuery.toLowerCase();
    const isAdmin = state.currentUser?.role === 'Administrador';
    const filtered = accounts.filter(account => (!query || `${account.code} ${account.name}`.toLowerCase().includes(query)) && (!state.accountGroup || account.group === state.accountGroup));
    return `<section class="card"><div class="card-header"><div><h2>Cuentas contables</h2></div><span class="tag">${filtered.length} cuentas</span></div><div class="table-wrap"><table><thead><tr><th>Código</th><th>Denominación</th><th>Tipo</th><th>Naturaleza</th><th>Estado</th>${isAdmin ? '<th></th>' : ''}</tr></thead><tbody>${filtered.map(account => `<tr><td><strong>${safe(account.code)}</strong></td><td><strong>${safe(account.name)}</strong><small>${safe(account.description)}</small></td><td>${safe(account.group)}</td><td>${safe(account.nature)}</td><td><span class="tag ${account.status === 'Activa' ? 'tag-open' : 'tag-muted'}">${safe(account.status)}</span></td>${isAdmin ? `<td class="num"><button class="text-button" type="button" data-action="edit-account" data-code="${safe(account.code)}">Editar</button><button class="text-button" type="button" data-action="toggle-account" data-code="${safe(account.code)}">${account.status === 'Activa' ? 'Desactivar' : 'Activar'}</button></td>` : ''}</tr>`).join('') || `<tr><td colspan="6"><div class="empty-state">Sin cuentas coincidentes</div></td></tr>`}</tbody></table></div><div class="table-footer"><span>Registros: ${filtered.length}</span></div></section>`;
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
    if (!hasCurrentWorksheet()) return worksheetRequired(tabs);
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
    const pending = sales.filter(sale => sale.status === 'Pendiente' && sale.date >= from && sale.date <= to);
    const periodRows = ledgerRows.filter(row => row.date >= from && row.date <= to);
    const open = state.periodStatus !== 'CERRADO_PROVISIONAL';
    const sameWorksheet = state.worksheet && state.worksheet.from === from && state.worksheet.to === to;
    return `${heading('Cierre provisional', 'Valida las operaciones del período y genera la Hoja de Trabajo.', '')}${tabs}
      <section class="card"><div class="card-header"><div><h2>Período a revisar</h2><p>Selecciona el rango que se utilizará en la hoja.</p></div><span class="tag ${open ? 'tag-open' : 'tag-warn'}">${open ? 'Abierto' : 'Cerrado provisionalmente'}</span></div><div class="card-body"><div class="filter-bar" style="margin:0"><div class="field"><label for="provisionalFrom">Fecha inicial</label><input id="provisionalFrom" type="date" value="${safe(from)}" ${open ? '' : 'disabled'}/></div><div class="field"><label for="provisionalTo">Fecha final</label><input id="provisionalTo" type="date" value="${safe(to)}" ${open ? '' : 'disabled'}/></div><span class="tag tag-muted">Tipo: PROVISIONAL_MENSUAL</span><button class="button button-secondary" type="button" data-action="check-provisional" ${open ? '' : 'disabled'}>Consultar requisitos</button></div></div></section>
      <section class="card section-gap"><div class="card-header"><div><h2>Requisitos previos</h2><p>Las ventas del rango deben estar registradas antes de preparar la hoja.</p></div></div><div class="table-wrap"><table><thead><tr><th>Validación</th><th>Resultado</th><th>Detalle</th></tr></thead><tbody><tr><td><strong>Estado del período</strong></td><td><span class="tag ${open ? 'tag-open' : 'tag-warn'}">${open ? 'Abierto' : 'Cerrado provisionalmente'}</span></td><td>${open ? 'Admite revisión' : 'No admite nuevos movimientos'}</td></tr><tr><td><strong>Ventas pendientes</strong></td><td><span class="tag ${pending.length ? 'tag-warn' : 'tag-open'}">${pending.length ? `${pending.length} pendientes` : 'Completado'}</span></td><td>${pending.length ? 'Deben registrarse en el Libro Mayor antes de generar la hoja.' : 'No hay ventas pendientes en el rango.'}</td></tr><tr><td><strong>Movimientos en Libro Mayor</strong></td><td><span class="tag ${periodRows.length ? 'tag-open' : 'tag-muted'}">${periodRows.length} transacciones</span></td><td>${periodRows.length ? 'Disponibles para incorporar a la hoja.' : 'No hay movimientos en las fechas seleccionadas.'}</td></tr></tbody></table></div>${pending.length ? `<div class="card-body"><button class="button button-secondary" type="button" data-view="operations" data-operation="post">Ir a contabilizar ventas</button></div>` : ''}<div class="table-footer"><span>Las validaciones se consultan al generar la hoja.</span>${sameWorksheet ? '<button class="text-button" type="button" data-report="worksheet">Abrir Hoja de Trabajo →</button>' : ''}</div></section>
      <div class="heading-actions section-gap">${open ? `<button class="button button-primary" type="button" data-action="generate-worksheet" ${pending.length || !periodRows.length ? 'disabled' : ''}>Generar Hoja de Trabajo</button>` : '<button class="button button-secondary" type="button" data-action="reopen-period">Reabrir período</button>'}${sameWorksheet ? '<button class="button button-secondary" type="button" data-report="worksheet">Revisar hoja generada</button>' : ''}</div>`;
  }

  function closingPage(tabs) {
    return `${heading('Cierre contable', 'El cierre provisional se prepara con la Hoja de Trabajo del período.', '')}${tabs}<section class="card"><div class="card-header"><div><h2>Estado del período</h2><p>Flujo de revisión contable</p></div><span class="tag ${state.periodStatus === 'ABIERTO' ? 'tag-open' : 'tag-warn'}">${state.periodStatus === 'ABIERTO' ? 'Abierto' : 'Cerrado provisionalmente'}</span></div><div class="card-body"><div class="notice"><span class="notice-icon">i</span><span>El cierre provisional requiere generar y revisar la Hoja de Trabajo. Los estados financieros del período se habilitan a partir de esa hoja.</span></div><div class="section-gap"><button class="button button-primary" type="button" data-report="provisional">${state.periodStatus === 'ABIERTO' ? 'Preparar cierre provisional' : 'Consultar período cerrado'}</button>${hasCurrentWorksheet() ? '<button class="button button-secondary" type="button" data-report="worksheet">Abrir Hoja de Trabajo</button>' : ''}</div></div></section>`;
  }

  function worksheetPage(tabs) {
    if (!hasCurrentWorksheet()) return `${heading('Hoja de Trabajo', 'Consolida los saldos y prepara los estados del período.', '')}${tabs}<section class="card"><div class="empty-state"><strong>No hay una Hoja de Trabajo generada para este período</strong>Primero valida el rango en Cierre provisional y genera la hoja desde los movimientos del Libro Mayor.<div class="section-gap"><button class="button button-primary" type="button" data-report="provisional">Ir a Cierre provisional</button></div></div></section>`;
    const sheet = state.worksheet;
    const totals = sheet.totals;
    const pair = (debit, credit) => `<td class="num">${debit ? money(debit) : '—'}</td><td class="num">${credit ? money(credit) : '—'}</td>`;
    const tableRows = sheet.rows.map(row => `<tr><td><strong>${safe(row.code || '—')}</strong><small>${safe(row.name)}</small></td>${pair(row.trialDebit,row.trialCredit)}${pair(row.adjustDebit,row.adjustCredit)}${pair(row.adjustedDebit,row.adjustedCredit)}${pair(row.resultsDebit,row.resultsCredit)}${pair(row.equityDebit,row.equityCredit)}${pair(row.balanceDebit,row.balanceCredit)}</tr>`).join('');
    const checks = worksheetChecks(sheet);
    const checkMarkup = checks.map(item => `<div class="balance-check ${item.ok ? 'is-balanced' : 'is-unbalanced'}"><span>${item.ok ? '✓' : '⚠'}</span><div><strong>${item.title}</strong><small>${item.ok ? 'Cuadra' : `Diferencia ${money(item.debit - item.credit)}`}</small></div></div>`).join('');
    const adjustments = ledgerRows.filter(row => row.type === 'Ajuste' && row.date >= sheet.from && row.date <= sheet.to);
    const adjustmentRows = adjustments.map(row => `<tr><td><strong>${safe(row.code)} · ${safe(row.account)}</strong></td><td>${safe(row.correlativo)}</td><td>${safe(row.date)}</td><td>${safe(row.concept)}</td><td class="num">${row.side === 'Cargo' ? money(row.amount) : '—'}</td><td class="num">${row.side === 'Abono' ? money(row.amount) : '—'}</td></tr>`).join('') || '<tr><td colspan="6" class="empty-cell">Sin ajustes para este período</td></tr>';
    const adjustmentForm = state.periodStatus === 'ABIERTO' ? `<section class="card section-gap"><div class="card-header"><div><h2>Registrar transacción de ajuste</h2></div></div><form id="adjustmentForm" class="adjustment-form"><div class="field"><label for="adjustmentAccount">Cuenta</label><select id="adjustmentAccount" name="code" required>${accountOptions()}</select></div><div class="field"><label for="adjustmentDate">Fecha</label><input id="adjustmentDate" name="date" type="date" value="${safe(sheet.to)}" min="${safe(sheet.from)}" max="${safe(sheet.to)}" required/></div><div class="field adjustment-description"><label for="adjustmentConcept">Descripción</label><input id="adjustmentConcept" name="concept" required/></div><div class="field"><label for="adjustmentReference">Referencia</label><input id="adjustmentReference" name="reference"/></div><div class="field"><label for="adjustmentDebit">Debe</label><input id="adjustmentDebit" name="debit" class="money-input" type="number" min="0" step="0.01"/></div><div class="field"><label for="adjustmentCredit">Haber</label><input id="adjustmentCredit" name="credit" class="money-input" type="number" min="0" step="0.01"/></div><button class="button button-primary" type="submit">Guardar ajuste</button></form></section>` : '';
    return `${heading('Hoja de Trabajo', 'Revisa los saldos del Libro Mayor.', `<button class="button button-secondary" type="button" data-action="export" data-source="worksheet" data-format="pdf">↓ PDF</button><button class="button button-secondary" type="button" data-action="export" data-source="worksheet" data-format="xlsx">↓ Excel</button>`)}${tabs}
      <div class="demo-banner"><span><strong>Hoja generada</strong> · ${safe(sheet.from)} a ${safe(sheet.to)} · ${sheet.rows.filter(row => row.code).length} cuentas</span><span class="tag ${state.periodStatus === 'ABIERTO' ? 'tag-open' : 'tag-warn'}">${state.periodStatus === 'ABIERTO' ? 'En revisión' : 'Cierre provisional'}</span></div>
      <div class="balance-checks">${checkMarkup}</div>
      <section class="card worksheet-card"><div class="table-wrap worksheet-wrap"><table class="worksheet-table" id="worksheetMatrix"><thead><tr><th rowspan="2">Cuenta</th><th colspan="2">Balance de comprobación</th><th colspan="2">Ajustes</th><th colspan="2">Balance ajustado</th><th colspan="2">Estado de resultados</th><th colspan="2">Cambios en patrimonio</th><th colspan="2">Balance general</th></tr><tr><th>Debe</th><th>Haber</th><th>Debe</th><th>Haber</th><th>Debe</th><th>Haber</th><th>Debe</th><th>Haber</th><th>Debe</th><th>Haber</th><th>Debe</th><th>Haber</th></tr></thead><tbody>${tableRows}<tr class="worksheet-total"><td><strong>Totales</strong></td>${pair(totals.trialDebit,totals.trialCredit)}${pair(totals.adjustDebit,totals.adjustCredit)}${pair(totals.adjustedDebit,totals.adjustedCredit)}${pair(totals.resultsDebit,totals.resultsCredit)}${pair(totals.equityDebit,totals.equityCredit)}${pair(totals.balanceDebit,totals.balanceCredit)}</tr></tbody></table></div></section>
      <section class="card section-gap"><div class="card-header"><div><h2>Detalle de ajustes</h2></div><span class="tag">${adjustments.length}</span></div><div class="table-wrap"><table class="adjustment-detail-table"><thead><tr><th>Cuenta</th><th>Correlativo</th><th>Fecha</th><th>Descripción</th><th class="num">Debe</th><th class="num">Haber</th></tr></thead><tbody>${adjustmentRows}</tbody></table></div></section>${adjustmentForm}
      <section class="card section-gap"><div class="card-header"><div><h2>Estados financieros</h2></div></div><div class="card-body"><div class="quick-links"><button class="quick-link" type="button" data-report="results">Estado de Resultados <span>↗</span></button><button class="quick-link" type="button" data-report="changes">Estado de Cambios en el Patrimonio <span>↗</span></button><button class="quick-link" type="button" data-report="balance">Estado de situación financiera <span>↗</span></button></div></div></section>
      <div class="entry-actions section-gap">${state.periodStatus === 'ABIERTO' ? `<button class="button button-primary" type="button" data-action="confirm-provisional-close" ${checks.every(item => item.ok) ? '' : 'disabled'}>Confirmar cierre provisional</button>` : '<button class="button button-secondary" type="button" data-action="reopen-period">Reabrir período</button>'}</div>`;
  }

  function worksheetChecks(sheet) {
    const pairs = [['Balance de comprobación', 'trialDebit', 'trialCredit'], ['Ajustes', 'adjustDebit', 'adjustCredit'], ['Balance ajustado', 'adjustedDebit', 'adjustedCredit'], ['Estado de resultados', 'resultsDebit', 'resultsCredit'], ['Balance general', 'balanceDebit', 'balanceCredit']];
    return pairs.map(([title, debitKey, creditKey]) => {
      const debit = Number(sheet.totals[debitKey]) || 0, credit = Number(sheet.totals[creditKey]) || 0;
      return { title, debit, credit, ok: Math.abs(debit - credit) < 0.005 };
    });
  }

  function generateWorksheet() {
    const from = $('#provisionalFrom')?.value || state.provisionalFrom || '2026-10-01';
    const to = $('#provisionalTo')?.value || state.provisionalTo || '2026-10-31';
    state.provisionalFrom = from;
    state.provisionalTo = to;
    if (!from || !to || from > to) { showToast('La fecha inicial debe ser igual o anterior a la fecha final.', 'error'); return; }
    if (state.periodStatus !== 'ABIERTO') { showToast('El período ya está cerrado provisionalmente.', 'warning'); return; }
    const pending = sales.filter(sale => sale.status === 'Pendiente' && sale.date >= from && sale.date <= to);
    if (pending.length) { page(); showToast('Registra las ventas pendientes antes de generar la Hoja de Trabajo.', 'warning'); return; }
    const periodRows = ledgerRows.filter(row => row.date >= from && row.date <= to);
    if (!periodRows.length) { page(); showToast('No hay movimientos en el rango seleccionado.', 'warning'); return; }
    state.worksheet = buildWorksheet(from, to);
    state.report = 'worksheet';
    page();
  }

  function buildWorksheet(from, to) {
    const codes = [...new Set(ledgerRows.filter(row => row.date <= to).map(row => row.code))];
    const rows = codes.map(code => {
      const account = accounts.find(item => item.code === code);
      if (!account) return null;
      const openingRows = ledgerRows.filter(row => row.code === code && row.date < from);
      const periodRows = ledgerRows.filter(row => row.code === code && row.date >= from && row.date <= to);
      const normalRows = periodRows.filter(row => row.type !== 'Ajuste');
      const adjustmentRows = periodRows.filter(row => row.type === 'Ajuste');
      const net = list => list.reduce((sum, row) => sum + (row.side === 'Cargo' ? row.amount : -row.amount), 0);
      const sideTotals = list => ({ debit: list.filter(row => row.side === 'Cargo').reduce((sum,row) => sum + row.amount,0), credit: list.filter(row => row.side === 'Abono').reduce((sum,row) => sum + row.amount,0) });
      const openingNet = net(openingRows);
      const normalTotals = sideTotals(normalRows);
      const adjustTotals = sideTotals(adjustmentRows);
      const trialNet = openingNet + normalTotals.debit - normalTotals.credit;
      const adjustedNet = trialNet + adjustTotals.debit - adjustTotals.credit;
      const periodNet = net(periodRows);
      const trialDebit = Math.max(trialNet,0), trialCredit = Math.max(-trialNet,0);
      const adjustedDebit = Math.max(adjustedNet,0), adjustedCredit = Math.max(-adjustedNet,0);
      const resultsIncluded = account.group === 'Ingreso' || account.group === 'Egreso';
      const equityIncluded = account.group === 'Patrimonio';
      const balanceIncluded = ['Activo','Pasivo','Patrimonio'].includes(account.group);
      return {
        code, name: account.name, group: account.group, nature: account.nature,
        openingNet, periodDebit: sideTotals(periodRows).debit, periodCredit: sideTotals(periodRows).credit, periodNet,
        trialDebit, trialCredit, adjustDebit: adjustTotals.debit, adjustCredit: adjustTotals.credit, adjustedDebit, adjustedCredit,
        resultsDebit: resultsIncluded ? Math.max(periodNet,0) : 0, resultsCredit: resultsIncluded ? Math.max(-periodNet,0) : 0,
        equityDebit: equityIncluded ? adjustedDebit : 0, equityCredit: equityIncluded ? adjustedCredit : 0,
        balanceDebit: balanceIncluded ? adjustedDebit : 0, balanceCredit: balanceIncluded ? adjustedCredit : 0,
      };
    }).filter(Boolean);
    const resultNet = rows.filter(row => row.group === 'Ingreso' || row.group === 'Egreso').reduce((sum,row) => sum + row.periodNet,0);
    if (resultNet !== 0) rows.push({ code: '', name: 'Resultado del período', group: 'Resultado', trialDebit: 0, trialCredit: 0, adjustDebit: 0, adjustCredit: 0, adjustedDebit: 0, adjustedCredit: 0, resultsDebit: Math.max(-resultNet,0), resultsCredit: Math.max(resultNet,0), equityDebit: Math.max(resultNet,0), equityCredit: Math.max(-resultNet,0), balanceDebit: Math.max(resultNet,0), balanceCredit: Math.max(-resultNet,0), periodNet: -resultNet, openingNet: 0, periodDebit: 0, periodCredit: 0 });
    const keys = ['trialDebit','trialCredit','adjustDebit','adjustCredit','adjustedDebit','adjustedCredit','resultsDebit','resultsCredit','equityDebit','equityCredit','balanceDebit','balanceCredit'];
    const totals = Object.fromEntries(keys.map(key => [key, rows.reduce((sum,row) => sum + (row[key] || 0),0)]));
    return { from, to, generatedAt: today(), rows, totals };
  }

  function requestProvisionalClose() {
    // TODO(CU-07.2): las acciones que cambian el estado del período están pendientes de definir.
    showToast('El cierre provisional está pendiente de definición (CU-07).', 'warning');
  }

  function requestPeriodReopen() {
    // TODO(CU-07): la reapertura de un período está pendiente de definir.
    showToast('La reapertura del período está pendiente de definición (CU-07).', 'warning');
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
    const sheet = state.worksheet;
    const incomeRows = sheet.rows.filter(row => row.code && row.group === 'Ingreso').map(row => ({ label: `${row.code} · ${row.name}`, amount: -row.periodNet, kind: 'detail' }));
    const expenseRows = sheet.rows.filter(row => row.code && row.group === 'Egreso').map(row => ({ label: `${row.code} · ${row.name}`, amount: row.periodNet, kind: 'detail' }));
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
    const sheet = state.worksheet;
    const balances = sheet.rows.filter(row => row.code && ['Activo', 'Pasivo', 'Patrimonio'].includes(row.group));
    const result = sheet.rows.find(row => row.name === 'Resultado del período');
    const groupRows = (group, sign) => balances.filter(row => row.group === group).map(row => ({ label: `${row.code} · ${row.name}`, amount: (row.balanceCredit - row.balanceDebit) * sign, kind: 'detail' }));
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
    const rows = sheet.rows.filter(row => row.code && row.group === 'Patrimonio').map(row => {
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
    const period = source === 'trial-balance' ? `Al ${state.trialBalanceTo}` : source === 'worksheet' || source === 'report' ? `${state.worksheet?.from || ''} al ${state.worksheet?.to || ''}` : '';
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
    return `<section class="card"><div class="card-header"><div><h2>Informes relacionados con el cierre anual</h2><p>Ejercicio con Hoja de Trabajo disponible</p></div><span class="tag tag-demo">${safe(state.worksheet.from.slice(0,4))}</span></div><div class="card-body"><div class="quick-links"><button class="quick-link" type="button" data-report="results">Estado de Resultados <span>↗</span></button><button class="quick-link" type="button" data-report="changes">Estado de Cambios en el Patrimonio <span>↗</span></button><button class="quick-link" type="button" data-report="balance">Balance General <span>↗</span></button><button class="quick-link" type="button" data-report="worksheet">Hoja de Trabajo <span>↗</span></button></div></div></section>`;
  }

  const operationTabs = [['verify', 'Verificar ventas'], ['post', 'Contabilizar ventas'], ['reconcile', 'Conciliar ventas'], ['steam', 'Conexión Steam']];
  function operationsPage() {
    const activeTitle = operationTabs.find(([id]) => id === state.operation)?.[1] || operationTabs[0][1];
    const tabs = `<div class="tabs">${operationTabs.map(([id, title]) => `<button class="tab-button ${state.operation === id ? 'active' : ''}" type="button" data-operation="${id}">${title}</button>`).join('')}</div>`;
    const content = state.operation === 'post' ? postSalesPanel() : state.operation === 'reconcile' ? reconcilePanel() : state.operation === 'steam' ? steamPanel() : verifySalesPanel();
    return `${heading('Ventas y costos', 'Consulta y registra ventas.', '')}${tabs}${content}`;
  }

  function verifySalesPanel() {
    const filtered = sales.filter(item => !state.salesQuery || `${item.id} ${item.title} ${item.channel}`.toLowerCase().includes(state.salesQuery.toLowerCase()));
    return `<div class="demo-banner"><span><strong>Resumen del período</strong> · Consulta de ventas.</span></div><div class="filter-bar"><div class="field grow"><label for="salesQuery">Buscar venta</label><input id="salesQuery" value="${safe(state.salesQuery)}" placeholder="Código, título o canal"/></div><div class="field"><label for="salesFrom">Desde</label><input id="salesFrom" type="date" value="2026-10-01"/></div><div class="field"><label for="salesTo">Hasta</label><input id="salesTo" type="date" value="2026-10-31"/></div><button class="button button-secondary" type="button" data-action="filter-sales">Consultar</button></div><section class="card"><div class="card-header"><div><h2>Ventas</h2><p>Listado de ventas identificadas para consulta</p></div><span class="tag">${filtered.length} ventas</span></div><div class="table-wrap"><table><thead><tr><th>Fecha</th><th>Identificador</th><th>Producto</th><th>Canal</th><th>Estado</th><th class="num">Monto</th></tr></thead><tbody>${filtered.map(sale => `<tr><td>${safe(sale.date)}</td><td><strong>${safe(sale.id)}</strong><small>${safe(sale.correlativo || (sale.status === 'Pendiente' ? 'Sin correlativo hasta registrar' : ''))}</small></td><td>${safe(sale.title)}</td><td>${safe(sale.channel)}</td><td><span class="tag ${sale.status === 'Registrada' ? 'tag-open' : 'tag-muted'}">${safe(sale.status)}</span></td><td class="num">${money(sale.amount)}</td></tr>`).join('')}</tbody></table></div></section>`;
  }

  function postSalesPanel() {
    const pending = sales.filter(sale => sale.status === 'Pendiente');
    return `<div class="notice"><span class="notice-icon">i</span><span>Al registrar una venta, el ingreso se aplica directamente a la cuenta correspondiente del Libro Mayor.</span></div><section class="card section-gap"><div class="card-header"><div><h2>Ventas pendientes de registro</h2><p>Selecciona una venta para registrarla directamente en el Libro Mayor.</p></div><span class="tag tag-muted">${pending.length} pendientes</span></div><div class="table-wrap"><table><thead><tr><th>Fecha</th><th>Venta</th><th>Producto</th><th>Canal</th><th class="num">Monto</th><th></th></tr></thead><tbody>${pending.length ? pending.map(sale => `<tr><td>${safe(sale.date)}</td><td><strong>${safe(sale.id)}</strong></td><td>${safe(sale.title)}</td><td>${safe(sale.channel)}</td><td class="num">${money(sale.amount)}</td><td class="num"><button class="button button-primary button-small" type="button" data-action="post-sale" data-sale="${safe(sale.id)}">Registrar</button></td></tr>`).join('') : `<tr><td colspan="6"><div class="empty-state"><strong>No hay ventas pendientes</strong></div></td></tr>`}</tbody></table></div></section>`;
  }

  function reconcilePanel() {
    return `<div class="demo-banner"><span><strong>Conciliación</strong> · Pantalla de consulta para identificar diferencias entre fuentes de venta.</span></div><section class="card"><div class="card-header"><div><h2>Conciliar ventas</h2><p>Selecciona un período y consulta los registros disponibles.</p></div></div><div class="card-body"><div class="filter-bar" style="margin:0"><div class="field"><label for="reconcileFrom">Desde</label><input id="reconcileFrom" type="date" value="2026-10-01"/></div><div class="field"><label for="reconcileTo">Hasta</label><input id="reconcileTo" type="date" value="2026-10-31"/></div><div class="field"><label for="reconcileSource">Origen</label><select id="reconcileSource"><option>Todos</option><option>Tienda digital</option><option>Steam</option></select></div><button class="button button-primary" type="button" data-action="reconcile">Consultar conciliación</button></div></div><div class="empty-state"><strong>Selecciona filtros para mostrar coincidencias</strong>La conciliación compara los registros del período seleccionado.</div></section>`;
  }

  function steamPanel() {
    const statusStyle = state.steamStatus === 'Conectado' ? 'steam-connected' : state.steamStatus === 'Fuera de servicio' ? 'steam-offline' : 'steam-waiting';
    const statusIcon = state.steamStatus === 'Conectado' ? '✓' : state.steamStatus === 'Fuera de servicio' ? '×' : '…';
    return `<section class="card steam-card"><div class="card-header"><div><h2>Estado de Steam API</h2></div><span class="tag tag-demo">Estado de conexión</span></div><div class="card-body"><div class="steam-status-panel ${statusStyle}"><span class="steam-status-icon">${statusIcon}</span><div><strong>${safe(state.steamStatus)}</strong><small>Estado de conexión</small></div></div><div class="filter-bar steam-status-controls"><div class="field"><label for="steamStatusSelect">Estado de conexión</label><select id="steamStatusSelect"><option ${state.steamStatus === 'Conectado' ? 'selected' : ''}>Conectado</option><option ${state.steamStatus === 'En espera' ? 'selected' : ''}>En espera</option><option ${state.steamStatus === 'Fuera de servicio' ? 'selected' : ''}>Fuera de servicio</option></select></div><button class="button button-primary" type="button" data-action="steam-check">Mostrar estado</button></div></div></section>`;
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

  function withAdminAuthorization() {
    // TODO(CU-06): la autorización de administrador para cambios del catálogo no está definida en la especificación.
    showToast('La autorización de administrador está pendiente de definición.', 'warning');
  }

  function onAction(action, target) {
    if (action === 'simulate-sale') {
      const id = `V-${1049 + Math.max(0, sales.length - 5)}`;
      const amount = 320 + Math.round(Math.random() * 480);
      sales.unshift({ id, date: today(), title: 'Título nuevo', channel: 'Tienda digital', amount, status: 'Pendiente' });
      state.salesTotal += amount;
      page(); showToast('Venta agregada.', 'success');
    }
    if (action === 'add-ledger-row') { $('#movementRows').insertAdjacentHTML('beforeend', movementRowMarkup($$('.ledger-input-row', $('#movementRows')).length + 1)); }
    if (action === 'remove-ledger-row') {
      const rows = $$('.ledger-input-row', $('#movementRows'));
      if (rows.length <= 1) { showToast('Debe permanecer al menos una fila.', 'warning'); return; }
      target.closest('.ledger-input-row').remove();
      $$('.ledger-input-row', $('#movementRows')).forEach((row, index) => { $('.line-col', row).textContent = String(index + 1).padStart(2, '0'); });
    }
    if (action === 'save-ledger') saveLedger();
    if (action === 'filter-ledger') {
      state.ledgerFilter = { account: $('#ledgerAccountFilter').value, from: $('#ledgerFrom').value, to: $('#ledgerTo').value };
      page();
    }
    if (action === 'clear-ledger-filter') { state.ledgerFilter = { account: state.ledgerFilter.account || '5101', from: '', to: '' }; page(); }
    if (['new-account', 'edit-account', 'toggle-account'].includes(action)) withAdminAuthorization();
    if (action === 'show-trial-balance') { state.ledgerMode = 'trial-balance'; page(); }
    if (action === 'back-ledger') { state.ledgerMode = 'ledger'; page(); }
    if (action === 'refresh-trial-balance') { state.trialBalanceTo = $('#trialBalanceTo').value || today(); page(); }
    if (action === 'export') exportDocument(target.dataset.source || 'report', target.dataset.format || 'pdf');
    if (action === 'generate-report') showToast('Reporte actualizado con los movimientos del período.', 'success');
    if (action === 'close-period') { state.report = 'provisional'; page(); }
    if (action === 'generate-worksheet') generateWorksheet();
    if (action === 'check-provisional') { state.provisionalFrom = $('#provisionalFrom').value; state.provisionalTo = $('#provisionalTo').value; page(); }
    if (action === 'confirm-provisional-close') requestProvisionalClose();
    if (action === 'reopen-period') requestPeriodReopen();
    if (action === 'go-provisional') { state.report = 'provisional'; page(); }
    if (action === 'filter-sales') { state.salesQuery = $('#salesQuery').value; page(); }
    if (action === 'post-sale') postSale(target.dataset.sale);
    if (action === 'reconcile') showToast('Consulta de conciliación realizada.', 'success');
    if (action === 'steam-check') { state.steamStatus = $('#steamStatusSelect').value; page(); showToast('Estado de conexión actualizado.', 'success'); }
    if (action === 'close-modal') $('#modalRoot').innerHTML = '';
  }

  function saveLedger() {
    const code = $('#ledgerAccountFilter').value;
    const account = accounts.find(item => item.code === code);
    const rows = $$('.ledger-input-row', $('#movementRows')).map(row => ({
      date: $('.ledger-line-date', row).value,
      concept: $('.ledger-line-concept', row).value.trim(),
      reference: $('.ledger-line-reference', row).value.trim(),
      type: $('.ledger-line-type', row).value,
      debit: Number($('.ledger-line-debit', row).value) || 0,
      credit: Number($('.ledger-line-credit', row).value) || 0,
    }));
    if (!code || rows.some(row => !row.date || !row.concept || !row.type || (row.debit <= 0 && row.credit <= 0) || (row.debit > 0 && row.credit > 0))) {
      showToast('Completa fecha, descripción y tipo; registra un monto en Debe o Haber por línea.', 'error'); return;
    }
    if (state.periodStatus === 'CERRADO_PROVISIONAL' && state.closedRange && rows.some(row => row.date >= state.closedRange.from && row.date <= state.closedRange.to)) {
      showToast('El período está cerrado provisionalmente y no admite nuevos movimientos.', 'warning'); return;
    }
    const saved = rows.map(row => {
      const transaction = { id: state.nextLedgerId++, date: row.date, code, account: account?.name || '', concept: row.concept, reference: row.reference, type: row.type, correlativo: nextCorrelative(row.type, row.date), side: row.debit > 0 ? 'Cargo' : 'Abono', amount: row.debit > 0 ? row.debit : row.credit };
      ledgerRows.push(transaction);
      return transaction;
    });
    state.worksheet = null;
    state.ledgerFilter.account = code;
    page(); showToast(`${saved.length} transacción(es) registradas en Libro Mayor.`, 'success');
  }

  function nextCorrelative(type, date) {
    const year = date.slice(0, 4);
    const highest = ledgerRows.reduce((current, row) => {
      if (row.type !== type || !row.date.startsWith(year)) return current;
      const numberPart = Number((row.correlativo || '').match(/-(\d{5})$/)?.[1]) || 0;
      return Math.max(current, numberPart);
    }, 0);
    return `${type}-${year}-${String(highest + 1).padStart(5, '0')}`;
  }

  function postSale(id) {
    const sale = sales.find(item => item.id === id);
    if (!sale || sale.status !== 'Pendiente') return;
    if (state.periodStatus === 'CERRADO_PROVISIONAL' && state.closedRange && sale.date >= state.closedRange.from && sale.date <= state.closedRange.to) {
      showToast('El período de la venta está cerrado provisionalmente.', 'warning'); return;
    }
    sale.status = 'Registrada';
    sale.correlativo = nextCorrelative('Comprobante de Ingreso', sale.date);
    ledgerRows.push({ id: state.nextLedgerId++, date: sale.date, code: '5101', account: 'Ingresos por licencias de videojuegos', concept: `Venta ${sale.id} · ${sale.title}`, reference: sale.id, type: 'Comprobante de Ingreso', correlativo: sale.correlativo, side: 'Abono', amount: sale.amount });
    state.worksheet = null;
    page(); showToast('Venta registrada directamente en Libro Mayor.', 'success');
  }

  function handleForm(event) {
    if (event.target.id === 'adjustmentForm') {
      event.preventDefault();
      const data = Object.fromEntries(new FormData(event.target).entries());
      const debit = Number(data.debit) || 0, credit = Number(data.credit) || 0;
      const sheet = state.worksheet;
      if (state.periodStatus !== 'ABIERTO' || !sheet) { showToast('No se pueden agregar ajustes a un período cerrado.', 'warning'); return; }
      if (!data.code || !data.date || data.date < sheet.from || data.date > sheet.to || !data.concept.trim() || (debit > 0) === (credit > 0)) { showToast('Completa cuenta, fecha y descripción; registra un importe en Debe o Haber.', 'error'); return; }
      const account = accounts.find(item => item.code === data.code);
      if (!account) { showToast('Selecciona una cuenta activa.', 'error'); return; }
      const adjustment = { id: state.nextLedgerId++, date: data.date, code: account.code, account: account.name, concept: data.concept.trim(), reference: data.reference.trim(), type: 'Ajuste', correlativo: nextCorrelative('Ajuste', data.date), side: debit > 0 ? 'Cargo' : 'Abono', amount: debit > 0 ? debit : credit };
      ledgerRows.push(adjustment);
      state.worksheet = buildWorksheet(sheet.from, sheet.to);
      state.report = 'worksheet';
      const balanced = worksheetChecks(state.worksheet).every(item => item.ok);
      page();
      showToast(balanced ? `Ajuste ${adjustment.correlativo} guardado.` : `Ajuste ${adjustment.correlativo} guardado; la hoja aún no cuadra.`, balanced ? 'success' : 'warning');
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
    if (reportButton) { state.report = reportButton.dataset.report; updateScreenQuery('report', state.report); page(); return; }
    if (operationButton) { state.operation = operationButton.dataset.operation; updateScreenQuery('operation', state.operation); page(); return; }
    if (actionButton) onAction(actionButton.dataset.action, actionButton);
  });
  $('#appShell').addEventListener('submit', handleForm);
  $('#appShell').addEventListener('change', event => {
    if (event.target.id === 'dashboardPeriod') { state.period = event.target.value; page(); }
    if (event.target.id === 'ledgerAccountFilter') { state.ledgerFilter.account = event.target.value; page(); }
    if (event.target.id === 'accountGroup') { state.accountGroup = event.target.value; $('#accountResults').innerHTML = accountResultsMarkup(); }
  });
  $('#appShell').addEventListener('input', event => {
    if (event.target.id === 'accountQuery') { state.accountQuery = event.target.value; $('#accountResults').innerHTML = accountResultsMarkup(); }
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
    const screen = Object.keys(screenUrls).find(name => !['login', 'logout'].includes(name) && new URL(screenUrls[name], window.location.origin).pathname === window.location.pathname) || 'dashboard';
    state.current = screen;
    const params = new URLSearchParams(window.location.search);
    state.report = params.get('report') || state.report;
    state.operation = params.get('operation') || state.operation;
    state.ledgerMode = params.get('mode') || state.ledgerMode;
    $('#appShell').dataset.screen = state.current;
    showCurrentUser();
    page();
  }

  window.addEventListener('popstate', showScreenFromUrl);
  showScreenFromUrl();
  JSON.parse($('#serverMessages').textContent).forEach(message => showToast(message.text, message.level === 'success' ? 'success' : message.level === 'warning' ? 'warning' : 'error'));
})();
