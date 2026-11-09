(() => {
  const modales = () => document.querySelectorAll('[data-modal]');

  function actualizar(form) {
    const motivo = form.querySelector('textarea').value.trim();
    let listo = motivo !== '';
    if ('formCierre' in form.dataset) {
      const confirmacion = form.querySelector('[name$="confirmacion"]').value;
      listo = listo && form.dataset.cuadra === 'true' && confirmacion === 'CONFIRMAR';
    } else {
      listo = listo && form.querySelector('[type="password"]').value !== '';
    }
    form.querySelector('[data-confirmar]').disabled = !listo;
  }

  document.addEventListener('click', event => {
    const abrir = event.target.closest('[data-abrir-modal]');
    if (abrir) {
      const modal = document.querySelector(`[data-modal="${abrir.dataset.abrirModal}"]`);
      if (modal) { modal.hidden = false; modal.querySelector('input:not([type="hidden"]), textarea')?.focus(); }
      return;
    }
    const cerrar = event.target.closest('[data-cerrar-modal]');
    if (cerrar) { cerrar.closest('[data-modal]').hidden = true; return; }
    if (event.target.matches('[data-modal]')) event.target.hidden = true;
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') modales().forEach(modal => { modal.hidden = true; });
  });
  document.querySelectorAll('[data-form-cierre], [data-form-reapertura]').forEach(form => {
    form.addEventListener('input', () => actualizar(form));
    actualizar(form);
  });
})();
