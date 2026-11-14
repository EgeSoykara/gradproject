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
    const asset = document.querySelector('#id_asset');
    const quantity = document.querySelector('#id_quantity');
    const originalOptions = Array.from(asset.options);
    const options = JSON.parse(document.querySelector('#asset-options').textContent);
    const byId = new Map(options.map(option => [String(option.id), option]));
    const search = document.querySelector('#asset-search');
    const quantityLabel = document.querySelector('label[for="id_quantity"]');
    const updateQuantityLabel = () => {
      quantityLabel.textContent = byId.get(asset.value)?.kind === 'metal' ? 'Grams:' : 'Units:';
    };
    search.hidden = false;
    search.querySelector('input').addEventListener('input', event => {
      const term = event.target.value.trim().toLocaleLowerCase('tr');
      const selected = asset.value;
      const matches = originalOptions.filter(option =>
        !option.value || option.value === selected ||
        option.textContent.toLocaleLowerCase('tr').includes(term) ||
        option.textContent.toLowerCase().includes(term)
      );
      asset.replaceChildren(...matches);
      asset.value = selected;
      search.querySelector('[role="status"]').textContent = matches.length === 1 ? 'No matching assets.' : '';
    });
    asset.addEventListener('change', updateQuantityLabel);
    const toggle = () => {
      const cash = ['deposit', 'withdraw'].includes(kind.value);
      ['asset', 'quantity', 'fee'].forEach(name => {
        const input = document.querySelector(`#id_${name}`);
        input.closest('p').hidden = cash;
        if (cash) input.value = name === 'asset' ? '' : name === 'quantity' ? '1' : '0';
      });
      search.hidden = cash;
      quantity.required = !cash;
      updateQuantityLabel();
    };
    kind.addEventListener('change', toggle);
    toggle();
  }
});
