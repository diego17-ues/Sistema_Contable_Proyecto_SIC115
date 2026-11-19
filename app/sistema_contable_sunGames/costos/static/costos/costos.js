// Modales del módulo de costos: Escape cierra, foco atrapado, validación
// en línea y botón de guardar deshabilitado mientras se envía.
(function () {
  'use strict';
  const FOCUSABLE = 'a[href], button:not([disabled]), input:not([type="hidden"]):not([disabled]), select:not([disabled]), textarea:not([disabled])';

  function cerrar(modal) {
    const enlace = modal.querySelector('.modal-close');
    if (enlace) window.location.href = enlace.href;
  }

  function atraparFoco(modal) {
    const dialogo = modal.querySelector('[role="dialog"]');
    const elementos = () => Array.from(dialogo.querySelectorAll(FOCUSABLE));
    const conError = dialogo.querySelector('.form-error');
    const primero = (conError && conError.closest('.field') && conError.closest('.field').querySelector('input, select, textarea'))
      || dialogo.querySelector('input:not([type="hidden"]), select, textarea') || elementos()[0];
    if (primero) primero.focus();
    document.addEventListener('keydown', (evento) => {
      if (evento.key === 'Escape') { evento.preventDefault(); cerrar(modal); return; }
      if (evento.key !== 'Tab') return;
      const lista = elementos();
      if (!lista.length) return;
      const inicio = lista[0];
      const fin = lista[lista.length - 1];
      if (evento.shiftKey && document.activeElement === inicio) { evento.preventDefault(); fin.focus(); }
      else if (!evento.shiftKey && document.activeElement === fin) { evento.preventDefault(); inicio.focus(); }
      else if (!dialogo.contains(document.activeElement)) { evento.preventDefault(); inicio.focus(); }
    });
  }

  function mensaje(campo) {
    if (campo.validity.valueMissing) return 'Este campo es obligatorio.';
    if (campo.validity.rangeUnderflow) return 'Debe ser mayor que cero.';
    if (campo.validity.badInput || campo.validity.stepMismatch) return 'Ingresa un número válido.';
    return campo.validationMessage;
  }

  function validar(campo) {
    const contenedor = campo.closest('.field');
    if (!contenedor) return true;
    let error = contenedor.querySelector('.form-error[data-js]');
    const texto = campo.checkValidity() ? '' : mensaje(campo);
    if (!error && texto) {
      error = document.createElement('span');
      error.className = 'form-error';
      error.dataset.js = '1';
      contenedor.appendChild(error);
    }
    if (error) error.textContent = texto;
    campo.setAttribute('aria-invalid', texto ? 'true' : 'false');
    return !texto;
  }

  function prepararFormulario(form) {
    const campos = Array.from(form.querySelectorAll('input:not([type="hidden"]), select, textarea'));
    campos.forEach((campo) => campo.addEventListener('blur', () => validar(campo)));
    form.addEventListener('submit', (evento) => {
      const validos = campos.map(validar).every(Boolean);
      if (!validos) { evento.preventDefault(); return; }
      if (form.dataset.enviando) { evento.preventDefault(); return; }
      form.dataset.enviando = '1';
      form.querySelectorAll('button[type="submit"]').forEach((boton) => {
        boton.disabled = true;
        boton.textContent = 'Guardando…';
      });
    });
  }

  function prepararManoObra(form) {
    const fuente = form.querySelector('[data-costos-tarifas]');
    const tarifas = fuente ? JSON.parse(fuente.textContent) : {};
    const proceso = form.querySelector('[name="proceso"]');
    const horas = form.querySelector('[name="horas"]');
    const costo = form.querySelector('[name="costo_hora"]');
    const salida = form.querySelector('[data-importe-mo]');
    const usd = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });
    function recalcular() {
      const h = Number(horas.value);
      const c = Number(costo.value);
      salida.textContent = h > 0 && c > 0 ? usd.format(Math.round(h * c * 100) / 100) : '—';
    }
    proceso.addEventListener('change', () => {
      const propuesto = tarifas[proceso.value];
      if (propuesto) costo.value = propuesto;
      recalcular();
    });
    [horas, costo].forEach((campo) => campo.addEventListener('input', recalcular));
    recalcular();
  }

  function crearNodoSvg(nombre, atributos, texto) {
    const nodo = document.createElementNS('http://www.w3.org/2000/svg', nombre);
    Object.entries(atributos || {}).forEach(([clave, valor]) => {
      nodo.setAttribute(clave, valor);
    });
    if (texto !== undefined) nodo.textContent = texto;
    return nodo;
  }

  function renderizarRendimiento() {
    const grafico = document.querySelector('[data-rendimiento-chart]');
    const fuente = document.getElementById('graficoRendimiento');
    const vacio = document.querySelector('[data-rendimiento-vacio]');
    if (!grafico || !fuente) return;

    const filas = JSON.parse(fuente.textContent).map((fila) => ({
      ...fila,
      estimado: Number(fila.estimado),
      real: Number(fila.real),
    })).filter((fila) => Number.isFinite(fila.estimado)
      && Number.isFinite(fila.real));

    if (!filas.length) {
      grafico.hidden = true;
      if (vacio) vacio.hidden = false;
      return;
    }

    grafico.hidden = false;
    if (vacio) vacio.hidden = true;
    grafico.replaceChildren();

    const ancho = 1100;
    const margenIzquierdo = 245;
    const margenDerecho = 115;
    const inicioY = 56;
    const altoFila = 66;
    const altoBarra = 13;
    const anchoGrafico = ancho - margenIzquierdo - margenDerecho;
    const maximoDato = Math.max(
      1,
      ...filas.flatMap((fila) => [fila.estimado, fila.real]),
    );
    const magnitud = 10 ** Math.floor(Math.log10(maximoDato));
    const fraccion = maximoDato / magnitud;
    const maximoEscala = (fraccion <= 1 ? 1
      : fraccion <= 2 ? 2
        : fraccion <= 5 ? 5 : 10) * magnitud;
    const alto = inicioY + filas.length * altoFila + 24;
    const dinero = new Intl.NumberFormat('es-SV', {
      style: 'currency', currency: 'USD', maximumFractionDigits: 2,
    });
    const dineroEje = new Intl.NumberFormat('es-SV', {
      style: 'currency', currency: 'USD', maximumFractionDigits: 0,
    });

    grafico.setAttribute('viewBox', `0 0 ${ancho} ${alto}`);
    grafico.setAttribute('width', String(ancho));
    grafico.setAttribute('height', String(alto));
    grafico.setAttribute('preserveAspectRatio', 'xMinYMin meet');

    grafico.append(
      crearNodoSvg('rect', {
        x: margenIzquierdo, y: 15, width: 12, height: 12, rx: 3,
        fill: 'var(--navy)',
      }),
      crearNodoSvg('text', {
        x: margenIzquierdo + 18, y: 25, fill: 'var(--ink)',
        'font-size': 12,
      }, 'Estimación'),
      crearNodoSvg('rect', {
        x: margenIzquierdo + 120, y: 15, width: 12, height: 12, rx: 3,
        fill: 'var(--gold)',
      }),
      crearNodoSvg('text', {
        x: margenIzquierdo + 138, y: 25, fill: 'var(--ink)',
        'font-size': 12,
      }, 'Costo real vigente'),
    );

    for (let marca = 0; marca <= 4; marca += 1) {
      const valor = maximoEscala * marca / 4;
      const x = margenIzquierdo + anchoGrafico * marca / 4;
      grafico.append(
        crearNodoSvg('line', {
          x1: x, y1: inicioY - 8, x2: x,
          y2: inicioY + filas.length * altoFila,
          stroke: 'var(--line)', 'stroke-width': 1,
        }),
        crearNodoSvg('text', {
          x, y: inicioY - 15, fill: 'var(--muted)',
          'font-size': 10, 'text-anchor': 'middle',
        }, dineroEje.format(valor)),
      );
    }

    filas.forEach((fila, indice) => {
      const y = inicioY + indice * altoFila;
      const anchoEstimado = anchoGrafico * fila.estimado / maximoEscala;
      const anchoReal = anchoGrafico * fila.real / maximoEscala;
      const nombre = fila.juego.length > 27
        ? `${fila.juego.slice(0, 26)}…` : fila.juego;
      const rotuloOrden = crearNodoSvg('text', {
        x: 8, y: y + 18, fill: 'var(--navy)',
        'font-size': 11, 'font-weight': 700,
      }, fila.orden);
      const rotuloJuego = crearNodoSvg('text', {
        x: 8, y: y + 35, fill: 'var(--muted)', 'font-size': 10,
      }, nombre);
      rotuloJuego.appendChild(crearNodoSvg('title', {}, fila.juego));
      grafico.append(rotuloOrden, rotuloJuego);

      [
        { y: y + 4, valor: fila.estimado, ancho: anchoEstimado,
          color: 'var(--navy)', nombre: 'Estimación' },
        { y: y + 27, valor: fila.real, ancho: anchoReal,
          color: 'var(--gold)', nombre: 'Costo real vigente' },
      ].forEach((barra) => {
        const rectangulo = crearNodoSvg('rect', {
          x: margenIzquierdo, y: barra.y, width: barra.ancho,
          height: altoBarra, rx: 4, fill: barra.color,
        });
        rectangulo.appendChild(crearNodoSvg(
          'title', {},
          `${barra.nombre} · ${fila.estimacion}: ${dinero.format(barra.valor)}`,
        ));
        const xTexto = Math.min(
          ancho - 4, margenIzquierdo + barra.ancho + 7,
        );
        const importe = crearNodoSvg('text', {
          x: xTexto, y: barra.y + 11, fill: 'var(--ink)',
          'font-size': 10,
        }, dinero.format(barra.valor));
        grafico.append(rectangulo, importe);
      });
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    const modal = document.querySelector('[data-costos-modal]');
    if (modal) atraparFoco(modal);
    document.querySelectorAll('[data-costos-form]').forEach(prepararFormulario);
    document.querySelectorAll('[data-mano-obra]').forEach(prepararManoObra);
    document.querySelectorAll('[data-imprimir]').forEach((boton) => boton.addEventListener('click', () => window.print()));
    renderizarRendimiento();
  });
}());
