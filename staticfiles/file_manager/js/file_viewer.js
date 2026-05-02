/**
 * Клиентский просмотр: PDF.js, docx-preview (бинарный docx), SheetJS (xlsx), Highlight.js (текст/код).
 * Данные конфигурации — элемент #file-viewer-config (JSON из Django json_script).
 */
(function () {
  "use strict";

  const MAX_TEXT_CHARS = 600000;

  const HLJS_ALIASES = {
    py: "python",
    js: "javascript",
    mjs: "javascript",
    ts: "typescript",
    tsx: "typescript",
    jsx: "javascript",
    sh: "bash",
    bash: "bash",
    zsh: "bash",
    yml: "yaml",
    h: "c",
    cc: "cpp",
    hpp: "cpp",
    rs: "rust",
    kt: "kotlin",
    md: "markdown",
    vue: "xml",
    svelte: "xml",
  };

  function showError(mount, msg) {
    mount.innerHTML =
      '<div class="file-viewer-fallback file-viewer-js-error"><i class="bi bi-exclamation-triangle"></i><p>' +
      escapeHtml(msg) +
      "</p></div>";
  }

  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function clearLoading() {
    var el = document.getElementById("file-viewer-loading");
    if (el) el.hidden = true;
  }

  async function fetchBinary(url) {
    var res = await fetch(url, { credentials: "same-origin" });
    if (!res.ok) throw new Error("Не удалось загрузить файл (" + res.status + ")");
    return await res.arrayBuffer();
  }

  async function fetchText(url) {
    var res = await fetch(url, { credentials: "same-origin" });
    if (!res.ok) throw new Error("Не удалось загрузить файл (" + res.status + ")");
    return await res.text();
  }

  async function renderPdf(mount, previewUrl) {
    if (typeof pdfjsLib === "undefined") throw new Error("PDF.js не загружен");
    pdfjsLib.GlobalWorkerOptions.workerSrc =
      "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";

    var loadingTask = pdfjsLib.getDocument({ url: previewUrl, withCredentials: true });
    var pdf = await loadingTask.promise;

    var wrap = document.createElement("div");
    wrap.className = "file-viewer-pdf-pages";

    for (var i = 1; i <= pdf.numPages; i++) {
      var page = await pdf.getPage(i);
      var viewport = page.getViewport({ scale: window.devicePixelRatio > 1 ? 1.6 : 1.35 });
      var canvas = document.createElement("canvas");
      var ctx = canvas.getContext("2d");
      canvas.height = viewport.height;
      canvas.width = viewport.width;
      canvas.style.maxWidth = "100%";
      canvas.style.height = "auto";
      await page.render({ canvasContext: ctx, viewport: viewport }).promise;
      wrap.appendChild(canvas);
    }
    mount.appendChild(wrap);
  }

  async function renderText(mount, previewUrl, ext) {
    var raw = await fetchText(previewUrl);
    if (raw.length > MAX_TEXT_CHARS) {
      raw = raw.slice(0, MAX_TEXT_CHARS);
      var banner = document.createElement("div");
      banner.className = "file-viewer-banner";
      banner.innerHTML =
        '<i class="bi bi-scissors"></i> Показан фрагмент (лимит ' + MAX_TEXT_CHARS.toLocaleString() + " символов).";
      mount.appendChild(banner);
    }

    var pre = document.createElement("pre");
    pre.className = "file-viewer-text";
    var code = document.createElement("code");
    code.className = "hljs";

    if (typeof hljs !== "undefined") {
      var lang = HLJS_ALIASES[ext] || ext;
      try {
        if (hljs.getLanguage && hljs.getLanguage(lang)) {
          code.innerHTML = hljs.highlight(raw, { language: lang }).value;
        } else {
          code.innerHTML = hljs.highlightAuto(raw).value;
        }
      } catch (e) {
        code.innerHTML = hljs.highlightAuto(raw).value;
      }
    } else {
      code.textContent = raw;
    }
    pre.appendChild(code);
    mount.appendChild(pre);
  }

  async function renderDocx(mount, previewUrl) {
    if (typeof window.JSZip === "undefined") throw new Error("JSZip не загружен (нужен для docx-preview).");
    var docxApi = window.docx;
    if (!docxApi || typeof docxApi.renderAsync !== "function") {
      throw new Error("docx-preview не загружен.");
    }
    var buf = await fetchBinary(previewUrl);
    var paper = document.createElement("div");
    paper.className = "file-viewer-paper file-viewer-paper--word";
    var inner = document.createElement("div");
    inner.className = "file-viewer-paper-inner file-viewer-docx-preview-root";
    paper.appendChild(inner);
    mount.appendChild(paper);
    await docxApi.renderAsync(buf, inner, null, {
      className: "docx",
      inWrapper: true,
      ignoreWidth: false,
      breakPages: true,
      useBase64URL: true,
      renderHeaders: true,
      renderFooters: true,
      renderFootnotes: true,
      renderEndnotes: true,
    });
  }

  function sheetToHtmlTable(sheet) {
    if (typeof XLSX === "undefined") throw new Error("SheetJS не загружен");
    var range = XLSX.utils.decode_range(sheet["!ref"] || "A1");
    var html =
      '<table class="table table-sm table-bordered mb-0 file-viewer-sheet-table"><tbody>';
    for (var R = range.s.r; R <= range.e.r; R++) {
      html += "<tr>";
      for (var C = range.s.c; C <= range.e.c; C++) {
        var addr = XLSX.utils.encode_cell({ r: R, c: C });
        var cell = sheet[addr];
        var v = cell ? cell.w != null ? String(cell.w) : cell.v != null ? String(cell.v) : "" : "";
        html += "<td>" + escapeHtml(v) + "</td>";
      }
      html += "</tr>";
    }
    html += "</tbody></table>";
    return html;
  }

  async function renderXlsx(mount, previewUrl) {
    if (typeof XLSX === "undefined") throw new Error("SheetJS не загружен");
    var buf = await fetchBinary(previewUrl);
    var wb = XLSX.read(buf, { type: "array" });
    var tabs = document.createElement("div");
    tabs.className = "file-viewer-xlsx-wrap";

    wb.SheetNames.forEach(function (name, idx) {
      var sheet = wb.Sheets[name];
      var sec = document.createElement("section");
      sec.className = "file-viewer-xlsx-section";
      var h = document.createElement("h6");
      h.className = "file-viewer-xlsx-sheet-title";
      h.textContent = name;
      sec.appendChild(h);
      var scroll = document.createElement("div");
      scroll.className = "table-responsive file-viewer-xlsx-scroll";
      scroll.innerHTML = sheetToHtmlTable(sheet);
      sec.appendChild(scroll);
      tabs.appendChild(sec);
    });

    var paper = document.createElement("div");
    paper.className = "file-viewer-paper file-viewer-paper--spreadsheet";
    var inner = document.createElement("div");
    inner.className = "file-viewer-paper-inner";
    inner.appendChild(tabs);
    paper.appendChild(inner);
    mount.appendChild(paper);
  }

  function run() {
    var cfgEl = document.getElementById("file-viewer-config");
    var mount = document.getElementById("file-viewer-mount");
    if (!cfgEl || !mount) return;

    var cfg;
    try {
      cfg = JSON.parse(cfgEl.textContent);
    } catch (e) {
      showError(mount, "Ошибка конфигурации просмотрщика.");
      clearLoading();
      return;
    }

    var mode = cfg.mode;
    var previewUrl = cfg.previewUrl;
    var ext = (cfg.ext || "").toLowerCase();

    Promise.resolve()
      .then(function () {
        if (mode === "js_pdf") return renderPdf(mount, previewUrl);
        if (mode === "js_text") return renderText(mount, previewUrl, ext);
        if (mode === "js_docx") return renderDocx(mount, previewUrl);
        if (mode === "js_xlsx") return renderXlsx(mount, previewUrl);
        throw new Error("Неизвестный режим: " + mode);
      })
      .catch(function (err) {
        console.error(err);
        showError(mount, err.message || String(err));
      })
      .finally(clearLoading);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }
})();
