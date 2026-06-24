"use strict";

const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file-input");
const browseBtn = document.getElementById("browse-btn");
const selectedFile = document.getElementById("selected-file");
const selectedName = document.getElementById("selected-name");
const extractBtn = document.getElementById("extract-btn");
const clearBtn = document.getElementById("clear-btn");
const statusBox = document.getElementById("status");
const resultSection = document.getElementById("result-section");
const resultText = document.getElementById("result-text");
const pageCount = document.getElementById("page-count");
const copyBtn = document.getElementById("copy-btn");
const downloadBtn = document.getElementById("download-btn");
const backendInfo = document.getElementById("backend-info");
const acceptedTypes = document.getElementById("accepted-types");

// Settings elements
const settingsBtn = document.getElementById("settings-btn");
const settingsOverlay = document.getElementById("settings-overlay");
const settingsClose = document.getElementById("settings-close");
const settingsForm = document.getElementById("settings-form");
const settingsStatus = document.getElementById("settings-status");
const testBtn = document.getElementById("test-btn");
const resetBtn = document.getElementById("reset-btn");

const SETTING_FIELDS = ["base_url", "model", "api_key", "pdf_dpi", "timeout", "prompt"];

let currentFile = null;
let downloadName = "extracted.txt";

// --- Load backend info -----------------------------------------------------
function applyConfig(cfg) {
  const s = cfg.settings || {};
  backendInfo.textContent = `GLM-OCR @ ${s.base_url}  •  model: ${s.model}`;
  const exts = cfg.allowed_extensions.map((e) => "." + e).join(", ");
  acceptedTypes.textContent = "Accepted: " + exts;
  fileInput.setAttribute("accept", cfg.allowed_extensions.map((e) => "." + e).join(","));
  SETTING_FIELDS.forEach((key) => {
    const el = document.getElementById("set-" + key);
    if (el && s[key] !== undefined) el.value = s[key];
  });
}

function loadConfig() {
  return fetch("/api/config")
    .then((r) => r.json())
    .then(applyConfig)
    .catch(() => {
      backendInfo.textContent = "";
    });
}
loadConfig();

// --- Settings panel --------------------------------------------------------
function openSettings() {
  settingsStatus.classList.add("hidden");
  settingsOverlay.classList.remove("hidden");
}
function closeSettings() {
  settingsOverlay.classList.add("hidden");
}
function settingsStatusMsg(kind, message) {
  settingsStatus.className = "settings-status " + kind;
  settingsStatus.textContent = message;
  settingsStatus.classList.remove("hidden");
}
function collectSettings() {
  const data = {};
  SETTING_FIELDS.forEach((key) => {
    const el = document.getElementById("set-" + key);
    if (!el) return;
    data[key] = el.type === "number" ? Number(el.value) : el.value;
  });
  return data;
}

settingsBtn.addEventListener("click", openSettings);
settingsClose.addEventListener("click", closeSettings);
settingsOverlay.addEventListener("click", (e) => {
  if (e.target === settingsOverlay) closeSettings();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !settingsOverlay.classList.contains("hidden")) closeSettings();
});

settingsForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  settingsStatusMsg("loading", "Saving…");
  try {
    const resp = await fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(collectSettings()),
    });
    const cfg = await resp.json();
    if (!resp.ok) {
      settingsStatusMsg("error", "❌ " + (cfg.error || "Could not save settings."));
      return;
    }
    applyConfig(cfg);
    settingsStatusMsg("ok", "✓ Settings saved.");
  } catch (err) {
    settingsStatusMsg("error", "❌ " + err.message);
  }
});

testBtn.addEventListener("click", async () => {
  settingsStatusMsg("loading", "Testing connection…");
  try {
    const resp = await fetch("/api/test-connection", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(collectSettings()),
    });
    const data = await resp.json();
    if (!resp.ok || !data.ok) {
      settingsStatusMsg("error", "❌ " + (data.error || "Connection failed."));
      return;
    }
    const models = data.models && data.models.length
      ? " Models: " + data.models.join(", ")
      : "";
    settingsStatusMsg("ok", `✓ Connected to ${data.base_url}.${models}`);
    loadConfig();
  } catch (err) {
    settingsStatusMsg("error", "❌ " + err.message);
  }
});

resetBtn.addEventListener("click", async () => {
  settingsStatusMsg("loading", "Resetting…");
  try {
    const resp = await fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reset: true }),
    });
    const cfg = await resp.json();
    applyConfig(cfg);
    settingsStatusMsg("ok", "✓ Reset to defaults.");
  } catch (err) {
    settingsStatusMsg("error", "❌ " + err.message);
  }
});

// --- File selection --------------------------------------------------------
function setFile(file) {
  currentFile = file;
  selectedName.textContent = `${file.name} (${formatSize(file.size)})`;
  selectedFile.classList.remove("hidden");
  hideStatus();
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

browseBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  fileInput.click();
});
dropzone.addEventListener("click", () => fileInput.click());
dropzone.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    fileInput.click();
  }
});
fileInput.addEventListener("change", () => {
  if (fileInput.files.length) setFile(fileInput.files[0]);
});

["dragenter", "dragover"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  })
);
["dragleave", "drop"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
  })
);
dropzone.addEventListener("drop", (e) => {
  if (e.dataTransfer.files.length) setFile(e.dataTransfer.files[0]);
});

clearBtn.addEventListener("click", () => {
  currentFile = null;
  fileInput.value = "";
  selectedFile.classList.add("hidden");
  resultSection.classList.add("hidden");
  hideStatus();
});

// --- Extract ---------------------------------------------------------------
extractBtn.addEventListener("click", async () => {
  if (!currentFile) return;

  setBusy(true);
  showStatus("loading", "Extracting text… this can take a moment per page.");
  resultSection.classList.add("hidden");

  const formData = new FormData();
  formData.append("file", currentFile);

  try {
    const resp = await fetch("/api/extract", { method: "POST", body: formData });
    const data = await resp.json();

    if (!resp.ok) {
      showStatus("error", "❌ " + (data.error || "Extraction failed."));
      return;
    }

    resultText.value = data.text || "";
    downloadName = data.filename || "extracted.txt";
    pageCount.textContent =
      data.page_count > 1 ? `(${data.page_count} pages)` : "";
    resultSection.classList.remove("hidden");
    hideStatus();
    resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (err) {
    showStatus("error", "❌ Network error: " + err.message);
  } finally {
    setBusy(false);
  }
});

// --- Result actions --------------------------------------------------------
copyBtn.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(resultText.value);
    toast("Copied to clipboard");
  } catch {
    resultText.select();
    document.execCommand("copy");
    toast("Copied to clipboard");
  }
});

downloadBtn.addEventListener("click", async () => {
  // Use a Blob so any edits made in the textarea are included.
  const blob = new Blob([resultText.value], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = downloadName;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
});

// --- Helpers ---------------------------------------------------------------
function setBusy(busy) {
  extractBtn.disabled = busy;
  extractBtn.textContent = busy ? "Working…" : "Extract text";
}

function showStatus(kind, message) {
  statusBox.className = "status " + kind;
  statusBox.innerHTML =
    kind === "loading" ? `<span class="spinner"></span>${message}` : message;
  statusBox.classList.remove("hidden");
}

function hideStatus() {
  statusBox.classList.add("hidden");
}

function toast(message) {
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = message;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 1800);
}
