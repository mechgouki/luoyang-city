/* Presentation-only H1. Preserve all research route handlers and data. */
(() => {
  'use strict';
  const intro = document.getElementById('home-introduction');
  if (!intro) return;
  const homeTitle = '北魏洛阳 · 走进一千五百年前的都城';
  function syncHomeView() {
    const routeName = (location.hash || '#home').slice(1).split('?')[0];
    const isHome = routeName === 'home' || routeName === 'home-questions';
    intro.hidden = !isHome;
    document.documentElement.dataset.homeView = isHome ? 'home' : 'detail';
    document.querySelectorAll('[data-home-nav]').forEach(link => {
      const active = link.dataset.homeNav === (isHome ? 'home' : routeName);
      link.classList.toggle('is-current', active);
      if (active) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
    if (isHome) document.title = homeTitle;
  }
  // Existing modules call the current route again when their async data arrives.
  // Also listen separately: an older handler may already be registered by app.js.
  const researchRoute = route;
  route = function () {
    researchRoute();
    syncHomeView();
  };
  window.addEventListener('hashchange', syncHomeView);
  document.addEventListener('click', event => {
    const link = event.target.closest('a[data-home-scroll]');
    if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const target = document.getElementById(link.dataset.homeScroll);
    if (!target) return;
    // This also covers clicking a link whose hash is already active.
    requestAnimationFrame(() => requestAnimationFrame(() => {
      syncHomeView();
      const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      target.scrollIntoView({block: 'start', behavior: reduced ? 'instant' : 'smooth'});
      if (link.id === 'home-start' || link.classList.contains('home-skip')) {
        target.setAttribute('tabindex', '-1');
        target.focus({preventScroll: true});
      }
    }));
  });
  syncHomeView();
  document.documentElement.dataset.homepageReady = 'true';
})();
