// Imlochi sayti: onlayn o'girgich. O'girish serverdagi converter.py orqali
// (/api/convert) — bot bilan bir xil qoidalar.
(() => {
  const src = document.getElementById("src");
  const out = document.getElementById("out");
  const status = document.getElementById("status");
  const count = document.getElementById("src-count");
  const dirLabel = document.getElementById("dir-label");
  const copyBtn = document.getElementById("copy");
  const modes = [...document.querySelectorAll(".mode")];
  const LABELS = Object.fromEntries(modes.map((b) => [b.dataset.dir, b.textContent]));

  let direction = "auto";
  try { direction = localStorage.getItem("imlochi-dir") || "auto"; } catch {}
  if (!LABELS[direction]) direction = "auto";

  let timer = null;
  let seq = 0;

  function setMode(dir) {
    direction = dir;
    modes.forEach((b) => {
      const on = b.dataset.dir === dir;
      b.classList.toggle("active", on);
      b.setAttribute("aria-checked", String(on));
    });
    try { localStorage.setItem("imlochi-dir", dir); } catch {}
    run();
  }

  async function run() {
    const text = src.value;
    count.textContent = text.length.toLocaleString("uz");
    if (!text.trim()) {
      out.textContent = "";
      dirLabel.textContent = "";
      status.textContent = "";
      return;
    }
    const id = ++seq;
    status.className = "status";
    status.textContent = "O‘girilmoqda…";
    try {
      const res = await fetch("/api/convert", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, direction }),
      });
      const data = await res.json();
      if (id !== seq) return; // eskirgan javob
      if (!res.ok) throw new Error(data.error === "too_many_requests"
        ? "Juda ko‘p so‘rov, birozdan so‘ng urinib ko‘ring"
        : "Xatolik yuz berdi");
      out.textContent = data.result;
      dirLabel.textContent = direction === "auto" ? `(${LABELS[data.direction]})` : "";
      status.textContent = "";
    } catch (e) {
      if (id !== seq) return;
      status.className = "status err";
      status.textContent = e.message || "Server bilan aloqa yo‘q";
    }
  }

  async function copy(text, button, done = "Nusxa olindi ✓") {
    if (!text) return;
    const original = button.textContent;
    try {
      await navigator.clipboard.writeText(text);
      button.textContent = done;
    } catch {
      button.textContent = "Nusxalab bo‘lmadi";
    }
    setTimeout(() => { button.textContent = original; }, 1600);
  }

  modes.forEach((b) => b.addEventListener("click", () => setMode(b.dataset.dir)));
  src.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(run, 250); });
  copyBtn.addEventListener("click", () => copy(out.textContent, copyBtn));

  const shareCopy = document.getElementById("share-copy");
  shareCopy.addEventListener("click", () => copy(shareCopy.dataset.link, shareCopy, "Havola nusxalandi ✓"));

  // Foydalanuvchilar soni (faqat umumiy son).
  fetch("/api/stats").then((r) => r.json()).then(({ users }) => {
    if (users >= 10) {
      const el = document.getElementById("users-count");
      el.querySelector("b").textContent = users.toLocaleString("uz");
      el.hidden = false;
    }
  }).catch(() => {});

  setMode(direction);
})();
