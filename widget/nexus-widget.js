/**
 * Nexus AI embeddable chat widget.
 *
 * Framework-agnostic, self-contained. Host pages embed it with:
 *   <script src="https://YOUR_HOST/nexus-widget.js"
 *           data-api-base="https://YOUR_API"
 *           data-api-key="nxs_..."></script>
 *
 * It mounts a floating chat bubble + panel in a Shadow DOM so the host page's
 * CSS cannot collide with the widget (and vice versa). All requests use the
 * public API key, which the backend resolves to exactly one organization --
 * tenant isolation holds for anonymous end-users.
 */
(function () {
  "use strict";

  var script = document.currentScript;
  var API_BASE = script.getAttribute("data-api-base") || "http://localhost:8000";
  var API_KEY = script.getAttribute("data-api-key") || "";

  var host = document.createElement("div");
  host.style.cssText = "position:fixed;bottom:20px;right:20px;z-index:2147483647";
  var root = host.attachShadow({ mode: "open" });
  document.body.appendChild(host);

  root.innerHTML =
    '<style>' +
    ":host{all:initial}" +
    "*{box-sizing:border-box;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif}" +
    ".bubble{width:56px;height:56px;border-radius:50%;background:#5b8cff;color:#fff;border:none;" +
    "font-size:24px;cursor:pointer;box-shadow:0 6px 20px rgba(0,0,0,.25)}" +
    ".panel{display:none;flex-direction:column;width:360px;height:520px;background:#141a2a;" +
    "color:#e6ebf5;border:1px solid #243049;border-radius:14px;overflow:hidden;" +
    "box-shadow:0 12px 40px rgba(0,0,0,.4)}" +
    ".panel.open{display:flex}" +
    ".head{padding:14px 16px;background:#1b2235;font-weight:600;border-bottom:1px solid #243049}" +
    ".log{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:10px}" +
    ".q{align-self:flex-end;background:#5b8cff;color:#fff;padding:8px 12px;border-radius:12px;max-width:85%}" +
    ".a{align-self:flex-start;background:#1b2235;padding:8px 12px;border-radius:12px;max-width:90%;line-height:1.45;font-size:14px}" +
    ".src{font-size:11px;color:#8b97b0;margin-top:4px}" +
    ".row{display:flex;gap:8px;padding:12px;border-top:1px solid #243049}" +
    ".row input{flex:1;background:#0b0f1a;border:1px solid #243049;border-radius:8px;padding:8px;color:#e6ebf5}" +
    ".row button{background:#5b8cff;color:#fff;border:none;border-radius:8px;padding:8px 12px;cursor:pointer}" +
    ".empty{color:#8b97b0;font-size:13px;text-align:center;margin-top:20px}" +
    "</style>" +
    '<button class="bubble" aria-label="Open chat">💬</button>' +
    '<div class="panel" role="dialog" aria-label="Nexus AI chat">' +
    '<div class="head">Ask our knowledge base</div>' +
    '<div class="log"><div class="empty">Ask a question to get started.</div></div>' +
    '<div class="row"><input type="text" placeholder="Type a question..." />' +
    "<button>Send</button></div>" +
    "</div>";

  var bubble = root.querySelector(".bubble");
  var panel = root.querySelector(".panel");
  var log = root.querySelector(".log");
  var input = root.querySelector("input");
  var send = root.querySelector(".row button");

  bubble.addEventListener("click", function () {
    panel.classList.toggle("open");
    if (panel.classList.contains("open")) input.focus();
  });

  function escapeHtml(s) {
    var d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function addTurn(question, answer, citations) {
    var empty = log.querySelector(".empty");
    if (empty) empty.remove();
    var q = document.createElement("div");
    q.className = "q";
    q.textContent = question;
    log.appendChild(q);
    var a = document.createElement("div");
    a.className = "a";
    var html = escapeHtml(answer);
    if (citations && citations.length) {
      var srcs = citations
        .map(function (c) {
          return "[" + c.marker + "] " + escapeHtml(c.filename) + (c.page_number ? " p." + c.page_number : "");
        })
        .join("  ");
      html += '<div class="src">' + srcs + "</div>";
    }
    a.innerHTML = html;
    log.appendChild(a);
    log.scrollTop = log.scrollHeight;
  }

  async function ask() {
    var q = input.value.trim();
    if (!q) return;
    input.value = "";
    input.disabled = send.disabled = true;
    try {
      var res = await fetch(API_BASE + "/widget/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
        body: JSON.stringify({ question: q }),
      });
      var data = await res.json();
      if (!res.ok) {
        addTurn(q, data.detail || "Something went wrong.", []);
      } else {
        addTurn(q, data.answer, data.citations || []);
      }
    } catch (e) {
      addTurn(q, "Could not reach the server.", []);
    } finally {
      input.disabled = send.disabled = false;
      input.focus();
    }
  }

  send.addEventListener("click", ask);
  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter") ask();
  });
})();
