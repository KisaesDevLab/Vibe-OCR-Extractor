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

let currentFile = null;
let downloadName = "extracted.txt";

// --- Load backend info -----------------------------------------------------
fetch("/api/config")
  .then((r) => r.json())
  .then((cfg) => {
    backendInfo.textContent = `GLM-OCR @ ${cfg.base_url}  •  model: ${cfg.model}`;
    const exts = cfg.allowed_extensions.map((e) => "." + e).join(", ");
    acceptedTypes.textContent = "Accepted: " + exts;
    fileInput.setAttribute(
      "accept",
      cfg.allowed_extensions.map((e) => "." + e).join(",")
    );
  })
  .catch(() => {
    backendInfo.textContent = "";
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
