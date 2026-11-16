// Use-case page behaviour. Every setup state is prerendered; this script only
// toggles hidden, selected, checked, and aria attributes, and writes copy strings
// with textContent. URL values are checked against the ids on the page and are
// never written into the DOM. No storage, no requests.

const BATCH_VALUES = ['yes', 'no'];

function initSetup(): void {
  const form = document.querySelector<HTMLFormElement>('[data-setup-form]');
  if (!form) return;
  const select = form.querySelector<HTMLSelectElement>('select[name="setup"]');
  const radios = Array.from(form.querySelectorAll<HTMLInputElement>('input[name="batch"]'));
  const helper = document.getElementById('setup-helper');
  const notice = document.querySelector<HTMLElement>('[data-invalid-notice]');
  const announcer = document.querySelector<HTMLElement>('[data-announcer]');
  if (!select || radios.length === 0) return;

  const setupIds = (form.dataset.setupIds ?? '').split(' ').filter(Boolean);
  const ampereIds = new Set((form.dataset.ampereIds ?? '').split(' ').filter(Boolean));
  const defaultSetup = form.dataset.defaultSetup ?? setupIds[0];
  const defaultBatch = form.dataset.defaultBatch ?? BATCH_VALUES[0];
  const parts = Array.from(document.querySelectorAll<HTMLElement>('[data-state], [data-for-state]'));

  const show = (setup: string, batch: string): void => {
    const key = `${setup}|${batch}`;
    for (const part of parts) {
      part.hidden = (part.dataset.state ?? part.dataset.forState) !== key;
    }
    for (const option of Array.from(select.options)) option.selected = option.value === setup;
    for (const radio of radios) radio.checked = radio.value === batch;
    if (helper) helper.hidden = !ampereIds.has(setup);
    applyToggles();
  };

  const current = (): [string, string] => {
    const batch = radios.find((radio) => radio.checked)?.value ?? defaultBatch;
    return [select.value, batch];
  };

  const announce = (setup: string, batch: string): void => {
    if (!announcer) return;
    const label = Array.from(select.options).find((option) => option.value === setup)?.text ?? '';
    const batchText = batch === 'yes' ? form.dataset.announceYes ?? '' : form.dataset.announceNo ?? '';
    announcer.textContent = (form.dataset.announce ?? '')
      .replace('{setup}', label)
      .replace('{batch}', batchText);
  };

  const onChange = (): void => {
    const [setup, batch] = current();
    show(setup, batch);
    if (notice) notice.hidden = true;
    announce(setup, batch);
    // Allowlisted ids only; replaceState so the Back button leaves the page in one step.
    const url = new URL(window.location.href);
    url.searchParams.set('setup', setup);
    url.searchParams.set('batch', batch);
    history.replaceState(null, '', url);
  };

  // Read the URL once. Unknown values fall back to the default and show the notice.
  const params = new URLSearchParams(window.location.search);
  const rawSetup = params.get('setup');
  const rawBatch = params.get('batch');
  const setupOk = rawSetup === null || setupIds.includes(rawSetup);
  const batchOk = rawBatch === null || BATCH_VALUES.includes(rawBatch);
  const setup = rawSetup !== null && setupOk ? rawSetup : defaultSetup;
  const batch = rawBatch !== null && batchOk ? rawBatch : defaultBatch;

  form.hidden = false;
  show(setup, batch);
  if (notice) {
    // Name which value was bad; each prerendered text names what the page shows.
    const which = !setupOk && !batchOk ? 'both' : !setupOk ? 'setup' : 'batch';
    for (const text of Array.from(notice.querySelectorAll<HTMLElement>('[data-invalid]'))) {
      text.hidden = text.dataset.invalid !== which;
    }
    notice.hidden = setupOk && batchOk;
  }

  select.addEventListener('change', onChange);
  for (const radio of radios) radio.addEventListener('change', onChange);
}

// Advanced options: one toggle per state; the choice carries across setup changes.
let showAll = false;

function applyToggles(): void {
  for (const toggle of Array.from(document.querySelectorAll<HTMLButtonElement>('.options-toggle'))) {
    toggle.setAttribute('aria-pressed', String(showAll));
    toggle.textContent = (showAll ? toggle.dataset.labelFewer : toggle.dataset.labelAll) ?? '';
    const grid = document.getElementById(toggle.getAttribute('aria-controls') ?? '');
    if (!grid) continue;
    for (const card of Array.from(grid.querySelectorAll<HTMLElement>('.option-card'))) {
      if (card.dataset.defaultHidden === undefined) card.dataset.defaultHidden = String(card.hidden);
      card.hidden = !showAll && card.dataset.defaultHidden === 'true';
    }
  }
}

function initToggles(): void {
  for (const toggle of Array.from(document.querySelectorAll<HTMLButtonElement>('.options-toggle'))) {
    // Shipped hidden: without scripts it would do nothing.
    toggle.hidden = false;
    toggle.addEventListener('click', () => {
      showAll = !showAll;
      applyToggles();
      // The button keeps focus: it is never hidden or replaced.
    });
  }
  applyToggles();
}

// On this page: focus moves to the section heading; the current link follows scrolling.
function initSectionNav(): void {
  const nav = document.querySelector<HTMLElement>('[data-section-nav]');
  if (!nav) return;
  const links = Array.from(nav.querySelectorAll<HTMLAnchorElement>('a[href^="#"]'));
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)');

  const setCurrent = (id: string): void => {
    for (const link of links) {
      if (link.hash === `#${id}`) link.setAttribute('aria-current', 'true');
      else link.removeAttribute('aria-current');
    }
  };

  for (const link of links) {
    link.addEventListener('click', (event) => {
      const section = document.getElementById(link.hash.slice(1));
      const heading = section?.querySelector<HTMLElement>('h1, h2');
      if (!section || !heading) return;
      event.preventDefault();
      section.scrollIntoView({ behavior: reduce.matches ? 'auto' : 'smooth', block: 'start' });
      heading.focus({ preventScroll: true });
      setCurrent(section.id);
    });
  }

  if (!('IntersectionObserver' in window)) return;
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) setCurrent(entry.target.id);
      }
    },
    { rootMargin: '-35% 0px -60% 0px' },
  );
  for (const link of links) {
    const section = document.getElementById(link.hash.slice(1));
    if (section) observer.observe(section);
  }
}

initToggles();
initSetup();
initSectionNav();
