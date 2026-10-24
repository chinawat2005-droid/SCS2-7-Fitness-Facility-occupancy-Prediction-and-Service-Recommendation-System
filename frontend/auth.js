// สถานะการล็อกอิน + แถบเมนูกลาง ใช้ร่วมกันทุกหน้า
const Session = (() => {
  const KEY = "gym_session";
  const read = () => { try { return JSON.parse(localStorage.getItem(KEY)); } catch { return null; } };
  return {
    get: read,
    set(data) { try { localStorage.setItem(KEY, JSON.stringify(data)); } catch {} },
    clear() { try { localStorage.removeItem(KEY); } catch {} },
    token() { return read()?.access_token || null; },
  };
})();

async function api(path, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  if (opts.body && !headers["Content-Type"]) headers["Content-Type"] = "application/json";
  const tk = Session.token();
  if (tk) headers.Authorization = "Bearer " + tk;
  const r = await fetch(path, { ...opts, headers });
  let data = null;
  try { data = await r.json(); } catch {}
  if (!r.ok) {
    if (r.status === 401 && tk) Session.clear();
    const d = data?.detail;
    const msg = typeof d === "string" ? d : Array.isArray(d) ? "ข้อมูลที่กรอกไม่ถูกต้อง" : "เกิดข้อผิดพลาด (" + r.status + ")";
    throw new Error(msg);
  }
  return data;
}

function renderHeader(active) {
  const links = [["/", "ฟิตเนส", "gyms"], ["/occupancy.html", "ความหนาแน่น", "occupancy"], ["/reviews-page", "รีวิวฟิตเนส", "reviews"], ["/recommend.html", "แนะนำฟิตเนส", "recommend"],
    ["/dashboard-page", "Dashboard ผู้จัดการ", "dashboard"]
  ];
  document.querySelector("header.site nav").innerHTML = links
    .map(([href, label, id]) => `<a href="${href}"${id === active ? ' aria-current="page"' : ""}>${label}</a>`)
    .join("");
  const who = document.querySelector("header.site .who");
  const s = Session.get();
  if (s?.user) {
    who.innerHTML = `<span>สวัสดี ${s.user.username.replace(/[&<>"]/g, "")}</span><button id="logout" type="button">ออกจากระบบ</button>`;
    document.getElementById("logout").onclick = () => { Session.clear(); location.reload(); };
  } else {
    who.innerHTML = `<a href="/login.html" style="color:#fff">เข้าสู่ระบบ</a><a href="/register.html" style="color:#fff">สมัครสมาชิก</a>`;
  }
}

function setupAuthForm(endpoint) {
  const form = document.getElementById("form");
  const err = document.getElementById("err");
  const btn = form.querySelector("button");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    err.textContent = "";
    const body = { username: form.username.value, password: form.password.value };
    if (form.confirm && form.confirm.value !== body.password) {
      err.textContent = "รหัสผ่านสองช่องไม่ตรงกัน";
      return;
    }
    btn.disabled = true;
    try {
      Session.set(await api(endpoint, { method: "POST", body: JSON.stringify(body) }));
      const next = new URLSearchParams(location.search).get("next");
      location.href = next && next.startsWith("/") && !next.startsWith("//") ? next : "/";
    } catch (ex) {
      err.textContent = ex.message;
      btn.disabled = false;
    }
  });
}

// ปุ่ม "← หน้าหลัก" ลอยมุมซ้ายล่าง แสดงทุกหน้ายกเว้นหน้าหลัก
(function () {
  const p = location.pathname;
  if (p === "/" || p === "/index.html") return;
  function addBackButton() {
    if (document.getElementById("back-home")) return;
    const a = document.createElement("a");
    a.id = "back-home";
    a.href = "/";
    a.textContent = "← หน้าหลัก";
    a.style.cssText = "position:fixed;left:16px;bottom:16px;z-index:9999;padding:10px 16px;" +
      "background:#1f2937;color:#fff;text-decoration:none;border-radius:999px;font-size:.95rem;" +
      "box-shadow:0 2px 8px rgba(0,0,0,.3)";
    document.body.appendChild(a);
  }
  if (document.body) addBackButton();
  else document.addEventListener("DOMContentLoaded", addBackButton);
})();
