// site/assets/version.js
// Self-heals a stale cached page: compares the build id baked into this
// script against site/data/version.json (fetched with no-store) and forces
// one reload if they differ. Guarded by sessionStorage so a page that
// already reloaded for a given (stale) build never reloads again, even if
// the browser keeps re-serving the same cached HTML.
const BUILD = "202607271520";
window.BUILD = BUILD;  // exposed read/write for manual verification only

(function () {
  function check() {
    const build = window.BUILD;
    const key = "imobilien-build-checked-" + build;
    if (sessionStorage.getItem(key)) return;
    fetch("data/version.json", { cache: "no-store" })
      .then((r) => r.json())
      .then((v) => {
        if (v && v.build && v.build !== build) {
          sessionStorage.setItem(key, "1");
          location.reload();
        }
      })
      .catch(() => {});  // offline or unreachable: never block the page
  }
  window.__checkVersion = check;  // exposed for manual re-trigger during verification
  check();
})();
