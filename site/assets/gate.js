// site/assets/gate.js
// Magic-URL gate. Crypto params MUST match scripts/crypto_util.py
// (PBKDF2-HMAC-SHA256, iterations from gate.json, AES-GCM, blob = 12-byte IV || ct).
// One PBKDF2 pass per page load: the derived bits are both hashed into the
// public verifier and imported as the AES-GCM key.
(function () {
  const enc = new TextEncoder();
  const b64ToBytes = (s) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));
  const bytesToB64 = (b) => btoa(String.fromCharCode(...new Uint8Array(b)));

  // A mangled fragment (stray %, truncated escape) must not throw: use it raw.
  function readFragment() {
    const raw = location.hash.slice(1);
    if (!raw) return "";
    try {
      return decodeURIComponent(raw);
    } catch (e) {
      return raw;
    }
  }

  async function deriveBits(passphrase, saltB64, iterations) {
    const material = await crypto.subtle.importKey(
      "raw", enc.encode(passphrase), "PBKDF2", false, ["deriveBits"]);
    return crypto.subtle.deriveBits(
      { name: "PBKDF2", salt: b64ToBytes(saltB64), iterations, hash: "SHA-256" },
      material, 256);
  }

  // Distinguishes "your link is broken" from "the site is broken" without
  // hinting at the key itself.
  function showBadKey() {
    const el = document.getElementById("gate-msg");
    if (!el) return;
    el.classList.add("bad-key");
    el.textContent = "Ссылка не подошла. Откройте, пожалуйста, исходную ссылку " +
      "из семейного чата целиком — возможно, она скопировалась не полностью.";
  }

  window.decryptBlob = async function (cryptoKey, buf) {
    const b = new Uint8Array(buf);
    return crypto.subtle.decrypt({ name: "AES-GCM", iv: b.slice(0, 12) }, cryptoKey, b.slice(12));
  };

  window.gateReady = (async function () {
    const params = await fetch("data/gate.json").then((r) => r.json());
    const candidate = readFragment() || localStorage.getItem("imobilien-key") || "";
    document.body.classList.add("locked");
    if (!candidate) throw new Error("locked");  // bare visit: neutral placeholder
    const bits = await deriveBits(candidate, params.salt, params.iterations);
    if (bytesToB64(await crypto.subtle.digest("SHA-256", bits)) !== params.verifier) {
      showBadKey();  // only a stored key that already verified is kept, so keep it
      throw new Error("bad key");
    }
    localStorage.setItem("imobilien-key", candidate);
    history.replaceState(null, "", location.pathname);  // hide key from shoulder-surfers
    document.body.classList.replace("locked", "unlocked");
    const cryptoKey = await crypto.subtle.importKey(
      "raw", bits, "AES-GCM", false, ["decrypt"]);
    return { passphrase: candidate, cryptoKey };
  })();
  window.gateReady.catch(() => {});  // page stays a neutral placeholder
})();
