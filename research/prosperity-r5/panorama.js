(() => {
  const views = [...document.querySelectorAll('[data-view]')];
  const tabs = [...document.querySelectorAll('.tabbar a')];
  function update() {
    const section = location.hash.slice(1);
    const choice = views.some(view => view.id === section) ? section :
      (views.find(view => !view.hidden)?.id || 'art');
    for (const view of views) view.hidden = view.id !== choice;
    for (const tab of tabs) {
      if (tab.hash === '#' + choice) tab.setAttribute('aria-current', 'page');
      else tab.removeAttribute('aria-current');
    }
  }
  for (const tab of tabs) tab.addEventListener('click', event => {
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    if (location.hash !== tab.hash) history.pushState(null, '', tab.hash);
    update();
  });
  window.addEventListener('hashchange', update);
  window.addEventListener('popstate', update);
  update();
})();
