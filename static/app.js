document.addEventListener('DOMContentLoaded', () => {
  const menu = document.querySelector('.menu-button');
  menu?.addEventListener('click', () => {
    const open = document.querySelector('#sidebar').classList.toggle('open');
    menu.setAttribute('aria-expanded', String(open));
  });
  document.querySelectorAll('[data-confirm]').forEach(form => {
    form.addEventListener('submit', event => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });
  document.querySelectorAll('[data-chart]').forEach(element => {
    try {
      const figure = JSON.parse(document.getElementById(element.dataset.chart).textContent);
      Plotly.newPlot(element, figure.data, figure.layout, {
        responsive: true, displayModeBar: false, displaylogo: false,
      });
    } catch (error) {
      element.textContent = 'The chart could not be loaded. Refresh the page to try again.';
    }
  });
  const kind = document.querySelector('#id_kind');
  if (kind) {
    const toggle = () => {
      const cash = ['deposit', 'withdraw'].includes(kind.value);
      ['asset', 'quantity', 'fee'].forEach(name => {
        const input = document.querySelector(`#id_${name}`);
        input.closest('p').hidden = cash;
        if (cash) input.value = name === 'asset' ? '' : name === 'quantity' ? '1' : '0';
      });
    };
    kind.addEventListener('change', toggle);
    toggle();
  }
});
