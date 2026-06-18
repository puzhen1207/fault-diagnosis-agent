// common.js: Common utility functions for all pages.
(function (global) {
  var API = {
    diagnoseTrace: function (query, topK, sessionId) {
      return fetch("/diagnose/trace", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query, top_k: topK || 5, session_id: sessionId || "default" }),
      }).then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      });
    },
    kbStats: function () {
      return fetch("/kb/stats").then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      });
    },
    kbItems: function () {
      return fetch("/kb/items").then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      });
    },
    kbItem: function (id) {
      return fetch("/kb/items/" + encodeURIComponent(id)).then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      });
    },
  };

  function escapeHtml(s) {
    if (s == null) s = "";
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function renderMarkdown(text) {
    return "<p>" + escapeHtml(text || "")
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\n\n/g, "</p><p>")
      .replace(/\n/g, "<br>") + "</p>";
  }

  global.Diag = { API: API, escapeHtml: escapeHtml, renderMarkdown: renderMarkdown };
})(window);
