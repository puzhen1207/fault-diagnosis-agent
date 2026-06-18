// kb.js: renders KB overview page (kb.html) & items list page (items.html).
(function () {
  var statsEl = document.getElementById("overview");
  var itemsTable = document.getElementById("kb-items-table");
  var itemsContainer = document.getElementById("itemsContainer");
  var itemsStatusEl = document.getElementById("status");

  var COLORS = ["#2563eb", "#059669", "#d97706", "#dc2626", "#8b5cf6", "#06b6d4", "#ec4899", "#64748b", "#10b981", "#f59e0b", "#3b82f6"];

  function drawPie(canvasId, data) {
    var canvas = document.getElementById(canvasId);
    if (!canvas) return;
    var ctx = canvas.getContext("2d");
    var w = canvas.width, h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    var cx = 120, cy = h / 2, r = 80;
    var total = data.reduce(function (a, b) { return a + b.value; }, 0);
    if (total === 0) {
      ctx.fillStyle = "#d1d5db";
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "#6b7280";
      ctx.font = "12px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("无数据", cx, cy);
      return;
    }
    var start = -Math.PI / 2;
    data.forEach(function (d, i) {
      var angle = (d.value / total) * Math.PI * 2;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, r, start, start + angle);
      ctx.closePath();
      ctx.fillStyle = COLORS[i % COLORS.length];
      ctx.fill();
      start += angle;
    });
    // legend on the right
    ctx.textAlign = "left";
    ctx.font = "12px sans-serif";
    var ly = 30;
    data.forEach(function (d, i) {
      var color = COLORS[i % COLORS.length];
      ctx.fillStyle = color;
      ctx.fillRect(220, ly - 8, 10, 10);
      ctx.fillStyle = "#1f2937";
      var txt = d.label + " (" + d.value + ")";
      ctx.fillText(txt, 236, ly + 2);
      ly += 16;
    });
  }

  function entries(dict) {
    var out = [];
    for (var k in dict) if (Object.prototype.hasOwnProperty.call(dict, k)) out.push({ label: k, value: dict[k] });
    return out;
  }

  if (statsEl) {
    window.Diag.API.kbStats().then(function (stats) {
      statsEl.innerHTML =
        '<div class="item"><span class="k">条目总数</span><span class="v">' + (stats.total_items || 0) + "</span></div>" +
        '<div class="item"><span class="k">总 token 数</span><span class="v">' + (stats.total_tokens || 0) + "</span></div>" +
        '<div class="item"><span class="k">平均步骤数</span><span class="v">' + (stats.avg_steps_per_item ? Number(stats.avg_steps_per_item).toFixed(1) : "0") + "</span></div>" +
        '<div class="item"><span class="k">平均别名数</span><span class="v">' + (stats.avg_aliases_per_item ? Number(stats.avg_aliases_per_item).toFixed(1) : "0") + "</span></div>" +
        '<div class="item"><span class="k">知识库路径</span><span class="v" style="font-size:11px;">' + window.Diag.escapeHtml(stats.kb_path || "-") + "</span></div>";

      drawPie("deviceChart", entries(stats.device_distribution || {}));
      drawPie("faultChart", entries(stats.fault_type_distribution || {}));
      drawPie("indicatorChart", entries(stats.indicator_distribution || {}));
    }).catch(function (err) { if (statsEl) statsEl.textContent = "加载失败：" + err.message; });
  }

  if (itemsTable) {
    var tbody = itemsTable.querySelector("tbody");
    window.Diag.API.kbItems().then(function (items) {
      var html = "";
      for (var i = 0; i < items.length; i++) {
        var it = items[i];
        html += "<tr>" +
          "<td>" + window.Diag.escapeHtml(it.id) + "</td>" +
          "<td>" + window.Diag.escapeHtml(it.title) + "</td>" +
          "<td>" + window.Diag.escapeHtml(it.device || "") + "</td>" +
          "<td>" + window.Diag.escapeHtml(it.indicator || "") + "</td>" +
          '<td class="num">' + (it.steps_count || 0) + "</td>" +
          '<td class="num">' + (it.aliases_count || 0) + "</td>" +
          "</tr>";
      }
      tbody.innerHTML = html;
    });
  }

  if (itemsContainer) {
    window.Diag.API.kbItems().then(function (items) {
      if (itemsStatusEl) itemsStatusEl.textContent = "共 " + items.length + " 条知识条目";
      var html = "";
      for (var i = 0; i < items.length; i++) {
        var it = items[i];
        html += '<div class="kb-card">' +
          '<h3>' + window.Diag.escapeHtml(it.title) + '</h3>' +
          '<div class="meta">ID: ' + window.Diag.escapeHtml(it.id) + " · 设备: " + window.Diag.escapeHtml(it.device || "-") + " · 指标: " + window.Diag.escapeHtml(it.indicator || "-") + "</div>" +
          "<details><summary>查看详情</summary>" +
          '<p><strong>故障类型：</strong>' + window.Diag.escapeHtml(it.fault_type || "") + "</p>" +
          '<p><strong>步骤数：</strong>' + (it.steps_count || 0) + '，<strong>别名数：</strong>' + (it.aliases_count || 0) + "</p>" +
          '<p><strong>searchable_text 预览：</strong><br><span style="font-size:12px;color:var(--muted);">' + window.Diag.escapeHtml(it.searchable_text_preview || "") + "...</span></p>" +
          "</details></div>";
      }
      itemsContainer.innerHTML = html;
    }).catch(function (err) { if (itemsStatusEl) itemsStatusEl.textContent = "加载失败：" + err.message; });
  }
})();
