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
      if (propuesto) costo.value = Number(propuesto).toFixed(2);
      recalcular();
    });
    [horas, costo].forEach((campo) => campo.addEventListener('input', recalcular));
    recalcular();
  }

  document.addEventListener('DOMContentLoaded', () => {
    const modal = document.querySelector('[data-costos-modal]');
    if (modal) atraparFoco(modal);
    document.querySelectorAll('[data-costos-form]').forEach(prepararFormulario);
    document.querySelectorAll('[data-mano-obra]').forEach(prepararManoObra);
  });
}());
