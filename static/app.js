document.addEventListener('DOMContentLoaded', () => {
  const menu = document.querySelector('.menu-button');
  const sidebar = document.querySelector('#sidebar');
  menu?.addEventListener('click', () => {
    const open = sidebar.classList.toggle('open');
    menu.setAttribute('aria-expanded', String(open));
    if (open) sidebar.querySelector('a').focus();
  });
  sidebar?.addEventListener('keydown', event => {
    if (event.key !== 'Escape' || !sidebar.classList.contains('open')) return;
    sidebar.classList.remove('open');
    menu.setAttribute('aria-expanded', 'false');
    menu.focus();
  });
  const workspace = document.querySelector('.workspace-switch select');
  if (workspace?.form && typeof workspace.form.requestSubmit === 'function') {
    const form = workspace.form;
    workspace.addEventListener('change', () => form.requestSubmit());
    form.querySelector('button[type="submit"]').hidden = true;
  }
  document.querySelectorAll('[data-confirm]').forEach(form => {
    form.addEventListener('submit', event => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });
  const renderChart = element => {
    try {
      const figure = JSON.parse(document.getElementById(element.dataset.chart).textContent);
      Plotly.newPlot(element, figure.data, figure.layout, {
        responsive: true, displayModeBar: false, displaylogo: false,
        locale: document.documentElement.lang,
      });
    } catch (error) {
      element.textContent = document.body.dataset.chartError;
    }
  };
  document.querySelectorAll('[data-chart]').forEach(element => {
    const details = element.closest('details');
    if (!details || details.open) {
      renderChart(element);
      return;
    }
    const renderOnOpen = () => {
      if (!details.open) return;
      details.removeEventListener('toggle', renderOnOpen);
      renderChart(element);
    };
    details.addEventListener('toggle', renderOnOpen);
  });
  const openDashboardSection = hash => {
    const section = document.getElementById(hash.slice(1));
    if (section?.matches('details.dashboard-detail')) section.open = true;
  };
  document.querySelectorAll('.bridge-dashboard a[href^="#"]').forEach(link => {
    link.addEventListener('click', () => openDashboardSection(link.hash));
  });
  openDashboardSection(window.location.hash);
  const kind = document.querySelector('#id_kind');
  if (kind) {
    const asset = document.querySelector('#id_asset');
    const amount = document.querySelector('#id_amount_tl');
    const originalOptions = Array.from(asset.options);
    const options = JSON.parse(document.querySelector('#asset-options').textContent);
    const byId = new Map(options.map(option => [String(option.id), option]));
    const search = document.querySelector('#asset-search');
    const quantityLabel = document.querySelector('label[for="id_quantity"]');
    const priceLabel = document.querySelector('label[for="id_price"]');
    const missingPrices = document.querySelector('#missing-trade-prices');
    const updateQuantityLabel = () => {
      const metal = byId.get(asset.value)?.kind === 'metal';
      const cash = ['deposit', 'withdraw'].includes(kind.value);
      quantityLabel.textContent = metal ? document.body.dataset.gramsLabel : document.body.dataset.unitsLabel;
      amount.closest('p').hidden = cash || metal;
      amount.disabled = cash || metal;
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
      search.querySelector('[role="status"]').textContent = matches.length === 1 ? document.body.dataset.noAssets : '';
    });
    asset.addEventListener('change', updateQuantityLabel);
    const toggle = () => {
      const cash = ['deposit', 'withdraw'].includes(kind.value);
      priceLabel.textContent = cash ? document.body.dataset.cashLabel : document.body.dataset.priceLabel;
      if (missingPrices) missingPrices.hidden = !['buy', 'sell'].includes(kind.value);
      ['asset', 'quantity', 'fee'].forEach(name => {
        const input = document.querySelector(`#id_${name}`);
        input.closest('p').hidden = cash;
        if (cash) input.value = name === 'asset' ? '' : name === 'quantity' ? '1' : '0';
      });
      search.hidden = cash;
      updateQuantityLabel();
    };
    kind.addEventListener('change', toggle);
    toggle();
  }
});
