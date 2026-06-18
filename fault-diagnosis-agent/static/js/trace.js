// trace.js: renders the full RAG pipeline trace visualization.
(function () {
  var queryEl = document.getElementById("query");
  var btn = document.getElementById("btnRun");
  var statusEl = document.getElementById("status");
  var topKEl = document.getElementById("topK");
  var topKValEl = document.getElementById("topKVal");
  var sessionIdEl = document.getElementById("sessionId");
  var container = document.getElementById("traceContainer");
  var quickRow = document.getElementById("quickRow");

  if (quickRow) {
    quickRow.innerHTML =
      '常见查询（点击填入）：' +
      '<span class="quick-link" data-q="压缩机压力过高报警怎么办？">压缩机压力过高</span>' +
      '<span class="quick-link" data-q="分离器液位过高一直不降怎么办？">分离器液位过高</span>' +
      '<span class="quick-link" data-q="气井积液油套压差大怎么办？">气井积液</span>' +
      '<span class="quick-link" data-q="干管压力过高报警如何定位井组？">干管压力过高</span>';
    quickRow.querySelectorAll(".quick-link").forEach(function (el) {
      el.addEventListener("click", function () {
        if (queryEl) queryEl.value = el.getAttribute("data-q");
      });
    });
  }

  if (topKEl && topKValEl) {
    topKEl.addEventListener("input", function () { topKValEl.textContent = topKEl.value; });
  }
  if (btn) btn.addEventListener("click", run);
  if (queryEl) {
    queryEl.addEventListener("keydown", function (e) {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") run();
    });
  }

  async function run() {
    if (!queryEl) return;
    var q = queryEl.value.trim();
    if (!q) { if (statusEl) statusEl.textContent = "请输入故障描述"; return; }
    btn.disabled = true;
    if (statusEl) statusEl.innerHTML = '<span class="spinner"></span>正在诊断…';
    container.innerHTML = "";
    try {
      var data = await window.Diag.API.diagnoseTrace(
        q,
        topKEl ? parseInt(topKEl.value, 10) || 5 : 5,
        (sessionIdEl && sessionIdEl.value) || "web-" + Date.now()
      );
      render(data);
      if (statusEl) {
        var dur = data.trace && data.trace.duration_ms ? " · " + data.trace.duration_ms + " ms" : "";
        statusEl.textContent = "诊断完成" + dur;
      }
    } catch (err) {
      if (statusEl) statusEl.textContent = "请求失败：" + err.message;
    } finally {
      btn.disabled = false;
    }
  }

  function render(data) {
    var trace = data.trace || {};
    var html =
      renderEntityExtraction(trace.entities) +
      renderFaultClassification(trace.fault_classification) +
      renderRetrieval(trace.retrieval) +
      renderReasoning(trace.reasoning) +
      renderSolution(trace.solution) +
      renderFinalAnswer(trace.final_answer);
    container.innerHTML = html;
  }

  function renderEntityExtraction(entities) {
    if (!entities) return "";
    var slots = [
      { label: "设备 (device)", key: "device_match" },
      { label: "指标 (indicator)", key: "indicator_match" },
      { label: "状态 (condition)", key: "condition_match" },
      { label: "阈值 (threshold)", key: "threshold_match" },
    ];
    var itemsHtml = slots.map(function (s) {
      var v = entities[s.key];
      return '<div class="entity-item' + (v ? "" : " empty") + '">' +
        '<span class="label">' + s.label + '</span>' +
        '<span class="value">' + (v || "(未匹配)") + "</span></div>";
    }).join("");
    return '<div class="panel"><h2><span class="step">1</span> 实体提取</h2>' +
      '<div style="font-size:13px;color:var(--muted);margin-bottom:8px;">原始查询：<code style="background:#f3f4f6;padding:2px 6px;border-radius:4px;">' +
      window.Diag.escapeHtml(entities.raw_query || "") + "</code></div>" +
      '<div class="entity-list">' + itemsHtml + "</div></div>";
  }

  function renderFaultClassification(ft) {
    if (!ft) return "";
    var candidates = ft.all_candidates || [];
    var maxScore = Math.max.apply(null, candidates.map(function (c) { return c.keyword_score || 0; }).concat([1]));
    var selected = ft.selected_fault_type;
    var rows = candidates
      .slice()
      .sort(function (a, b) { return (b.keyword_score || 0) - (a.keyword_score || 0); })
      .map(function (c) {
        var score = c.keyword_score || 0;
        var pct = Math.round((score / maxScore) * 100);
        var isSel = c.fault_type === selected;
        var kwTxt = (c.matched_keywords && c.matched_keywords.length)
          ? '<span style="color:var(--muted);font-size:11px;">命中关键词：' +
            c.matched_keywords.map(function (k) {
              return '<code style="background:#eef2ff;padding:1px 6px;border-radius:4px;margin-right:4px;">' + window.Diag.escapeHtml(k) + "</code>";
            }).join("") + "</span>"
          : '<span style="color:var(--muted);font-size:11px;">未命中关键词</span>';
        return '<div class="bar-row' + (isSel ? " selected" : "") + '">' +
          '<div class="bar-label">' + window.Diag.escapeHtml(c.label || c.fault_type) +
          (isSel ? " &#9733;" : "") + "</div>" +
          '<div class="bar-outer"><div class="bar-inner" style="width:' + pct + '%;"></div></div>' +
          '<div class="bar-score">' + score.toFixed(0) + "</div></div>" +
          '<div style="padding:2px 0 6px 190px;">' + kwTxt + "</div>";
      })
      .join("");
    return '<div class="panel"><h2><span class="step">2</span> 故障类型分类</h2>' +
      '<div style="font-size:13px;color:var(--muted);margin-bottom:6px;">最终选中类型：<strong style="color:var(--success);">' +
      window.Diag.escapeHtml(selected || "(未知)") + "</strong>" +
      (ft.heuristic_applied ? '（启发式 fallback 命中）' : '') + "</div>" +
      '<div class="bar-chart">' + rows + "</div></div>";
  }

  function renderRetrieval(ret) {
    if (!ret) return "";
    var tokens = ret.query_tokens || [];
    var allDocs = ret.documents || [];
    var topDocs = ret.top_results || [];
    var topIds = {};
    for (var i = 0; i < topDocs.length; i++) topIds[topDocs[i].doc_id] = true;

    var tokenHtml = tokens.length
      ? '<div class="tokens">' + tokens.map(function (t) { return '<span class="token">' + window.Diag.escapeHtml(t) + "</span>"; }).join("") + "</div>"
      : '<div style="color:var(--muted);font-size:13px;">(无)</div>';

    var tableHtml = '<table class="data-table"><thead><tr>' +
      "<th>文档</th><th>设备</th><th>指标</th><th>BM25</th><th>故障类型</th><th>设备匹配</th><th>指标匹配</th><th>条件匹配</th><th>Overlap</th><th>Final</th></tr></thead><tbody>" +
      allDocs.map(function (d) {
        var cls = topIds[d.doc_id] ? ' class="top-row"' : "";
        return "<tr" + cls + ">" +
          "<td>" + window.Diag.escapeHtml(d.title || d.doc_id) + "</td>" +
          "<td>" + window.Diag.escapeHtml(d.device || "") + "</td>" +
          "<td>" + window.Diag.escapeHtml(d.indicator || "") + "</td>" +
          '<td class="num">' + Number(d.bm25_score || 0).toFixed(2) + "</td>" +
          '<td class="num">' + Number(d.fault_type_match_score || 0).toFixed(1) + "</td>" +
          '<td class="num">' + Number(d.device_match_score || 0).toFixed(1) + "</td>" +
          '<td class="num">' + Number(d.indicator_match_score || 0).toFixed(1) + "</td>" +
          '<td class="num">' + Number(d.condition_match_score || 0).toFixed(1) + "</td>" +
          '<td class="num">' + Number(d.overlap_score || 0).toFixed(1) + "</td>" +
          '<td class="num"><strong>' + Number(d.final_score || 0).toFixed(2) + "</strong></td>" +
          "</tr>";
      }).join("") + "</tbody></table>";

    var stackHtml = topDocs.length
      ? '<h2 style="margin-top:16px;">Top-K 得分构成（堆叠条形图）</h2><div class="bar-chart">' +
        topDocs.map(function (d) {
          var parts = [
            { name: "BM25", val: d.bm25_score || 0, color: "#93c5fd" },
            { name: "FaultType", val: d.fault_type_match_score || 0, color: "#f59e0b" },
            { name: "Device", val: d.device_match_score || 0, color: "#10b981" },
            { name: "Indicator", val: d.indicator_match_score || 0, color: "#6366f1" },
            { name: "Condition", val: d.condition_match_score || 0, color: "#ec4899" },
            { name: "Overlap", val: d.overlap_score || 0, color: "#a855f7" },
          ];
          var segs = parts.map(function (p) {
            return '<div style="flex:' + p.val.toFixed(2) + ';background:' + p.color + ';height:20px;font-size:10px;color:#fff;text-align:center;line-height:20px;" title="' + p.name + ':' + p.val.toFixed(1) + '">' + (p.val > 0 ? p.val.toFixed(0) : "") + "</div>";
          }).join("");
          return '<div><div style="font-size:12px;margin-bottom:4px;">' + window.Diag.escapeHtml(d.title || d.doc_id) + " <small style='color:var(--muted);'>(" + Number(d.final_score || 0).toFixed(2) + ")</small></div>" +
            '<div style="display:flex;height:20px;border-radius:8px;overflow:hidden;gap:2px;">' + segs + "</div></div>";
        }).join("") + "</div>"
      : "";

    return '<div class="panel"><h2><span class="step">3</span> 检索打分</h2>' +
      '<div style="font-size:13px;color:var(--muted);margin-bottom:6px;">Top-K = ' + (ret.top_k || 0) + "</div>" +
      '<div style="font-size:13px;color:var(--muted);">分词结果（共 ' + tokens.length + ' 个 token）：</div>' +
      tokenHtml +
      '<h2 style="margin-top:16px;">全部文档打分明细（绿色高亮 = Top-K）</h2>' +
      tableHtml + stackHtml + "</div>";
  }

  function renderReasoning(r) {
    if (!r) return "";
    var causes = r.root_causes_used || [];
    var causesHtml = causes.length
      ? causes.map(function (c) { return "<li>" + window.Diag.escapeHtml(c) + "</li>"; }).join("")
      : '<li style="color:var(--muted);">(无)</li>';
    return '<div class="panel"><h2><span class="step">4</span> 推理与根因</h2>' +
      '<div class="entity-list">' +
      '<div class="entity-item"><span class="label">主文档标题</span><span class="value">' + window.Diag.escapeHtml(r.selected_primary_doc_title || "(无)") + "</span></div>" +
      '<div class="entity-item"><span class="label">文档 ID</span><span class="value">' + window.Diag.escapeHtml(r.selected_primary_doc_id || "-") + "</span></div>" +
      '<div class="entity-item"><span class="label">LLM 尝试</span><span class="value">' + (r.llm_attempted ? "是" : "否") + "</span></div>" +
      '<div class="entity-item"><span class="label">LLM 结果</span><span class="value">' + (r.llm_used ? "使用" : "未使用/不可用") + "</span></div>" +
      "</div>" +
      '<h2 style="margin-top:16px;">使用的根因片段</h2><ol class="steps">' + causesHtml + "</ol>" +
      '<h2 style="margin-top:16px;">拼接后的根因分析</h2><div class="root-cause">' + window.Diag.escapeHtml(r.assembled_root_cause || "(无)") + "</div>" +
      (r.llm_output_if_any ? '<h2 style="margin-top:16px;">LLM 原始输出</h2><div class="markdown">' + window.Diag.escapeHtml(r.llm_output_if_any) + "</div>" : "") +
      "</div>";
  }

  function renderSolution(s) {
    if (!s) return "";
    var stepsFromKb = s.steps_from_kb || [];
    var stepRows = stepsFromKb.map(function (step) {
      return '<div style="margin-bottom:6px;"><code style="background:#f3f4f6;padding:2px 6px;border-radius:4px;font-size:11px;">' + window.Diag.escapeHtml(step.step_id || "") + '</code> ' +
        window.Diag.escapeHtml(step.text || "") + "</div>";
    }).join("");
    var validated = s.validated_steps || [];
    var validatedHtml = validated.length
      ? validated.map(function (v) { return "<li>" + window.Diag.escapeHtml(v) + "</li>"; }).join("")
      : '<li style="color:var(--muted);">(无)</li>';
    return '<div class="panel"><h2><span class="step">5</span> 方案生成</h2>' +
      '<div style="font-size:13px;color:var(--muted);">主文档：' + window.Diag.escapeHtml(s.primary_doc_title || "-") + "</div>" +
      '<h2 style="margin-top:16px;">原始步骤（带 step_id）</h2>' + stepRows +
      '<h2 style="margin-top:16px;">动词校验后的最终步骤</h2><ol class="steps">' + validatedHtml + "</ol>" +
      '<div style="font-size:13px;margin-top:10px;">动词校验已过滤步骤数：<strong>' + (s.steps_filtered_by_verb_check || 0) + "</strong></div>" +
      '<h2 style="margin-top:16px;">风险提示</h2><div class="risk-warn">' + window.Diag.escapeHtml(s.risk || "(无)") + "</div></div>";
  }

  function renderFinalAnswer(fa) {
    if (!fa) return "";
    return '<div class="panel"><h2><span class="step">6</span> 最终答案</h2>' +
      '<div class="kv">' +
      '<div class="item"><span class="k">参考标题</span><span class="v" style="font-size:12px;">' + window.Diag.escapeHtml(fa.reference_title || "-") + "</span></div>" +
      '<div class="item"><span class="k">参考分数</span><span class="v" style="font-size:13px;">' + Number(fa.reference_score || 0).toFixed(2) + "</span></div>" +
      "</div>" +
      '<h2 style="margin-top:16px;">Markdown 答案</h2><div class="root-cause">' + window.Diag.renderMarkdown(fa.final_markdown || "") + "</div>" +
      "</div>";
  }
})();
