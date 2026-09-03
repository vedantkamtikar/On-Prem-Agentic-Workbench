/**
 * Sovereign On-Prem Agentic AI Workbench - Frontend Application Logic
 * 3-Screen Streamlined Architecture with Theme Toggle & Real-Time Deliverables History
 */

document.addEventListener("DOMContentLoaded", () => {
    // -------------------------------------------------------------------------
    // 1. Light / Dark Theme Toggle
    // -------------------------------------------------------------------------
    const btnThemeToggle = document.getElementById("btn-theme-toggle");
    const optDark = document.getElementById("opt-dark");
    const optLight = document.getElementById("opt-light");

    function applyTheme(theme) {
        document.documentElement.setAttribute("data-theme", theme);
        localStorage.setItem("workbench_theme", theme);
        if (optDark && optLight) {
            if (theme === "dark") {
                optDark.classList.add("active");
                optLight.classList.remove("active");
            } else {
                optLight.classList.add("active");
                optDark.classList.remove("active");
            }
        }
    }

    const savedTheme = localStorage.getItem("workbench_theme") || "dark";
    applyTheme(savedTheme);

    btnThemeToggle?.addEventListener("click", () => {
        const currentTheme = document.documentElement.getAttribute("data-theme") || "dark";
        const nextTheme = currentTheme === "dark" ? "light" : "dark";
        applyTheme(nextTheme);
    });

    // -------------------------------------------------------------------------
    // 2. Navigation & Screen Switching (3 Tabs)
    // -------------------------------------------------------------------------
    const navTabs = document.querySelectorAll(".nav-tab");
    const screens = document.querySelectorAll(".screen-container");

    navTabs.forEach(tab => {
        tab.addEventListener("click", () => {
            navTabs.forEach(t => t.classList.remove("active"));
            screens.forEach(s => s.classList.remove("active-screen"));

            tab.classList.add("active");
            const screenId = tab.getAttribute("data-screen");
            const targetScreen = document.getElementById(screenId);
            if (targetScreen) {
                targetScreen.classList.add("active-screen");
            }

            // Auto-refresh when entering screens
            if (screenId === "screen-kb") {
                fetchIndexedDocuments();
            } else if (screenId === "screen-trust") {
                fetchHardwareTelemetry();
                fetchNetworkAudit();
            } else if (screenId === "screen-workspace") {
                fetchDeliverablesHistory();
            }
        });
    });

    // -------------------------------------------------------------------------
    // 3. Hardware Telemetry & Header Polling
    // -------------------------------------------------------------------------
    const headerVram = document.getElementById("header-vram-text");
    const headerRouter = document.getElementById("header-router-name");
    const headerWorker = document.getElementById("header-worker-name");
    const gaugeVramText = document.getElementById("gauge-vram-text");
    const gaugeVramBar = document.getElementById("gauge-vram-bar");
    const gaugeRamText = document.getElementById("gauge-ram-text");
    const gaugeRamBar = document.getElementById("gauge-ram-bar");

    async function fetchHardwareTelemetry() {
        try {
            const res = await fetch("/system/hardware");
            if (!res.ok) return;
            const data = await res.json();

            const vramMb = data.vram.allocated_mb;
            const vramTotalMb = data.vram.total_mb;
            const vramPct = data.vram.usage_pct;
            const ramUsedGb = (data.system_ram.used_mb / 1024).toFixed(1);
            const ramTotalGb = (data.system_ram.total_mb / 1024).toFixed(1);
            const ramPct = data.system_ram.usage_pct;

            if (headerVram) {
                headerVram.innerText = `${(vramMb / 1024).toFixed(1)} / ${(vramTotalMb / 1024).toFixed(1)} GB`;
            }
            if (gaugeVramText) {
                gaugeVramText.innerText = `${(vramMb / 1024).toFixed(1)} GB / ${(vramTotalMb / 1024).toFixed(1)} GB (${vramPct}%)`;
            }
            if (gaugeVramBar) {
                gaugeVramBar.style.width = `${Math.min(100, vramPct)}%`;
            }

            if (gaugeRamText) {
                gaugeRamText.innerText = `${ramUsedGb} GB / ${ramTotalGb} GB (${ramPct}%)`;
            }
            if (gaugeRamBar) {
                gaugeRamBar.style.width = `${Math.min(100, ramPct)}%`;
            }
        } catch (e) {
            console.debug("Telemetry fetch note:", e);
        }
    }

    document.getElementById("btn-refresh-hardware")?.addEventListener("click", fetchHardwareTelemetry);

    // Initial Telemetry fetch & periodic poll
    fetchHardwareTelemetry();
    setInterval(fetchHardwareTelemetry, 30000);

    // -------------------------------------------------------------------------
    // 4. Network Socket Audit Monitor
    // -------------------------------------------------------------------------
    const socketTbody = document.getElementById("network-sockets-tbody");
    const auditTag = document.getElementById("audit-compliance-tag");

    async function fetchNetworkAudit() {
        try {
            const res = await fetch("/system/network-audit");
            if (!res.ok) return;
            const data = await res.json();

            if (auditTag) {
                if (data.air_gap_compliant) {
                    auditTag.innerText = "100% Loopback (Air-Gap Certified)";
                    auditTag.style.color = "#34d399";
                } else {
                    auditTag.innerText = `WARNING: ${data.external_calls} Non-Loopback Socket(s)`;
                    auditTag.style.color = "#f87171";
                }
            }

            if (socketTbody && data.active_sockets) {
                socketTbody.innerHTML = "";
                data.active_sockets.forEach(sock => {
                    const row = document.createElement("tr");
                    const pillClass = sock.is_loopback ? "conf-high" : "conf-low";
                    const pillText = sock.is_loopback ? "LOOPBACK" : "WAN EGRESS";
                    row.innerHTML = `
                        <td>${sock.type}</td>
                        <td>${sock.local || "-"}</td>
                        <td>${sock.remote || "-"}</td>
                        <td><span class="conf-pill ${pillClass}">${pillText}</span></td>
                    `;
                    socketTbody.appendChild(row);
                });
            }
        } catch (e) {
            console.debug("Socket audit fetch note:", e);
        }
    }

    document.getElementById("btn-refresh-audit")?.addEventListener("click", fetchNetworkAudit);
    fetchNetworkAudit();

    // -------------------------------------------------------------------------
    // 5. Workspace Presets, Shortcuts & Utilities
    // -------------------------------------------------------------------------
    const taskInput = document.getElementById("task-prompt-input");
    const routerModeSelect = document.getElementById("router-mode-select");
    const btnDispatch = document.getElementById("btn-dispatch-task");
    const traceLog = document.getElementById("trace-log");
    const taskOutput = document.getElementById("task-output-preview");
    const stepCounter = document.getElementById("trace-step-counter");

    // Presets
    document.getElementById("preset-incident")?.addEventListener("click", () => {
        taskInput.value = "Conduct a procedural compliance review for Steam Turbine shutdown under SOP-TURB-12. Retrieve valve CV-101 torque requirements and synthesize a formal Executive Approval Report in .docx format.";
        routerModeSelect.value = "general";
        taskInput.focus();
    });

    document.getElementById("preset-ocr")?.addEventListener("click", () => {
        taskInput.value = "Perform optical inspection on the attached engineering drawing. Extract all equipment tags, verify line connection limits, and report any design discrepancies.";
        routerModeSelect.value = "vision";
        taskInput.focus();
    });

    document.getElementById("preset-code")?.addEventListener("click", () => {
        taskInput.value = "Execute a Python vibration analysis script inside the isolated sandbox to compute RMS vibration severity for Turbine Bearing #1 given sensor amplitudes [4.2, 5.1, 8.9, 11.4, 6.2] mm/s.";
        routerModeSelect.value = "coding";
        taskInput.focus();
    });

    // Keyboard Shortcut: Ctrl+Enter to execute task
    taskInput?.addEventListener("keydown", (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
            e.preventDefault();
            btnDispatch?.click();
        }
    });

    // Clear Trace Button
    document.getElementById("btn-clear-trace")?.addEventListener("click", () => {
        if (traceLog) {
            traceLog.innerHTML = `
                <div class="trace-line">
                    <span class="trace-timer">[00:00.00]</span>
                    <span class="trace-tag tag-router">SYSTEM</span>
                    <span class="trace-msg">Execution trace cleared. Ready for next task.</span>
                </div>
            `;
        }
        if (stepCounter) stepCounter.innerText = "Idle (0 Steps)";
    });

    // Copy Output to Clipboard Button
    document.getElementById("btn-copy-output")?.addEventListener("click", async () => {
        if (!taskOutput || !taskOutput.value) return;
        const btn = document.getElementById("btn-copy-output");
        try {
            await navigator.clipboard.writeText(taskOutput.value);
            const originalText = btn.innerText;
            btn.innerText = "Copied to Clipboard";
            btn.style.color = "#34d399";
            setTimeout(() => {
                btn.innerText = originalText;
                btn.style.color = "";
            }, 2000);
        } catch (e) {
            console.error("Clipboard copy error:", e);
        }
    });

    function appendTraceLine(tagType, tagText, message, timestampSec = 0) {
        if (!traceLog) return;
        const mins = Math.floor(timestampSec / 60).toString().padStart(2, '0');
        const secs = (timestampSec % 60).toFixed(2).padStart(5, '0');
        const timerStr = `[${mins}:${secs}]`;

        const line = document.createElement("div");
        line.className = "trace-line";
        let tagClass = "tag-router";
        if (tagType === "tool") tagClass = "tag-tool";
        if (tagType === "agent") tagClass = "tag-agent";
        if (tagType === "doc") tagClass = "tag-doc";
        if (tagType === "err") tagClass = "tag-err";

        line.innerHTML = `
            <span class="trace-timer">${timerStr}</span>
            <span class="trace-tag ${tagClass}">${tagText}</span>
            <span class="trace-msg">${escapeHtml(message)}</span>
        `;
        traceLog.appendChild(line);
        traceLog.scrollTop = traceLog.scrollHeight;
    }

    function escapeHtml(str) {
        if (!str) return "";
        return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    // -------------------------------------------------------------------------
    // 6. Intelligent Workspace File Attachment & Inline Auto-OCR
    // -------------------------------------------------------------------------
    const workspaceDropzone = document.getElementById("workspace-dropzone");
    const workspaceFileInput = document.getElementById("workspace-file-input");
    const workspaceDropzoneStatus = document.getElementById("workspace-dropzone-status");
    const taskFileSelect = document.getElementById("task-file-select");

    const previewBox = document.getElementById("workspace-preview-box");
    const previewFilename = document.getElementById("workspace-preview-filename");
    const previewImg = document.getElementById("workspace-preview-img");
    const ocrStatusPill = document.getElementById("inline-ocr-status-pill");
    const ocrDrawer = document.getElementById("inline-ocr-drawer");
    const ocrTagCount = document.getElementById("inline-ocr-tag-count");
    const ocrTbody = document.getElementById("inline-ocr-tbody");
    const btnToggleOcr = document.getElementById("btn-toggle-ocr-drawer");
    const btnInsertOcr = document.getElementById("btn-insert-ocr-tags");

    let currentExtractedTags = [];

    // Toggle OCR tags drawer
    btnToggleOcr?.addEventListener("click", () => {
        if (!ocrDrawer) return;
        const isHidden = ocrDrawer.style.display === "none";
        ocrDrawer.style.display = isHidden ? "block" : "none";
        btnToggleOcr.innerText = isHidden
            ? `Hide OCR Tags (${currentExtractedTags.length})`
            : `Inspect OCR Tags (${currentExtractedTags.length})`;
    });

    // Insert verified OCR tags into prompt textarea
    btnInsertOcr?.addEventListener("click", () => {
        if (currentExtractedTags.length === 0) return;
        const tagText = currentExtractedTags.map(t => t.text).join(", ");
        const insertBlock = `\n[VERIFIED EXTRACTED TAGS: ${tagText}]\n`;
        if (taskInput) {
            taskInput.value += insertBlock;
            taskInput.focus();
        }
    });

    if (workspaceDropzone && workspaceFileInput) {
        workspaceDropzone.addEventListener("click", () => workspaceFileInput.click());

        workspaceDropzone.addEventListener("dragover", (e) => {
            e.preventDefault();
            workspaceDropzone.classList.add("dragover");
        });
        workspaceDropzone.addEventListener("dragleave", () => {
            workspaceDropzone.classList.remove("dragover");
        });
        workspaceDropzone.addEventListener("drop", (e) => {
            e.preventDefault();
            workspaceDropzone.classList.remove("dragover");
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                handleFileUpload(e.dataTransfer.files[0]);
            }
        });

        workspaceFileInput.addEventListener("change", (e) => {
            if (e.target.files && e.target.files.length > 0) {
                handleFileUpload(e.target.files[0]);
            }
        });
    }

    async function handleFileUpload(file) {
        if (!file) return;
        workspaceDropzoneStatus.style.display = "block";
        workspaceDropzoneStatus.innerText = `Uploading '${file.name}' to air-gapped storage...`;

        const formData = new FormData();
        formData.append("file", file);

        try {
            const res = await fetch("/upload", {
                method: "POST",
                body: formData
            });
            const data = await res.json();

            if (res.ok && data.status === "success") {
                workspaceDropzoneStatus.innerText = `[OK] File attached: ${data.filename} (${(data.size_bytes / 1024).toFixed(1)} KB)`;
                workspaceDropzoneStatus.style.color = "#34d399";

                // Add to dropdown
                let option = taskFileSelect.querySelector(`option[value="${data.file_path}"]`);
                if (!option) {
                    option = document.createElement("option");
                    option.value = data.file_path;
                    option.innerText = `${data.filename} (Attached)`;
                    taskFileSelect.appendChild(option);
                }
                taskFileSelect.value = data.file_path;

                // Setup Inline Thumbnail Preview
                const ext = data.filename.split('.').pop().toLowerCase();
                const isImage = ["png", "jpg", "jpeg", "bmp", "webp"].includes(ext);
                const isPdf = ext === "pdf";

                if (previewBox) previewBox.style.display = "block";
                if (previewFilename) previewFilename.innerText = `${data.filename} (${(data.size_bytes / 1024).toFixed(1)} KB)`;

                if (isImage && previewImg) {
                    previewImg.src = `/${data.file_path}`;
                    previewImg.style.display = "block";
                } else if (previewImg) {
                    previewImg.style.display = "none";
                }

                // Automatic Background CPU OCR for Drawings / PDFs
                if (isImage || isPdf) {
                    if (ocrStatusPill) {
                        ocrStatusPill.style.display = "inline-block";
                        ocrStatusPill.className = "conf-pill conf-med";
                        ocrStatusPill.innerText = "Running CPU OCR...";
                    }
                    runInlineOCR(data.file_path);
                } else {
                    if (ocrStatusPill) ocrStatusPill.style.display = "none";
                    if (ocrDrawer) ocrDrawer.style.display = "none";
                }
            } else {
                workspaceDropzoneStatus.innerText = `Upload failed: ${data.detail || "Server error"}`;
                workspaceDropzoneStatus.style.color = "#f87171";
            }
        } catch (err) {
            workspaceDropzoneStatus.innerText = `Upload error: ${err.message}`;
            workspaceDropzoneStatus.style.color = "#f87171";
        }
    }

    async function runInlineOCR(filePath) {
        try {
            const startT = performance.now();
            const res = await fetch("/tools/ocr", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ file_path: filePath, target_device: "cpu" })
            });
            const data = await res.json();
            const elapsed = Math.round(performance.now() - startT);

            if (res.ok && data.lines) {
                currentExtractedTags = data.lines;
                if (ocrTagCount) ocrTagCount.innerText = currentExtractedTags.length;

                if (ocrStatusPill) {
                    ocrStatusPill.className = "conf-pill conf-high";
                    ocrStatusPill.innerText = `[OK] ${currentExtractedTags.length} tags (${elapsed}ms)`;
                }

                // Render editable table rows
                if (ocrTbody) {
                    ocrTbody.innerHTML = "";
                    if (currentExtractedTags.length === 0) {
                        ocrTbody.innerHTML = `<tr><td colspan="3" style="text-align:center; color:var(--text-muted); padding:0.5rem;">No tags extracted.</td></tr>`;
                    } else {
                        currentExtractedTags.slice(0, 30).forEach((item, idx) => {
                            const tr = document.createElement("tr");
                            const confClass = item.confidence >= 0.85 ? "conf-high" : (item.confidence >= 0.60 ? "conf-med" : "conf-low");
                            tr.innerHTML = `
                                <td>${idx + 1}</td>
                                <td contenteditable="true" style="color:var(--text-primary); outline:none; padding:2px 4px;">${escapeHtml(item.text)}</td>
                                <td><span class="conf-pill ${confClass}">${item.confidence.toFixed(2)}</span></td>
                            `;
                            ocrTbody.appendChild(tr);
                        });
                    }
                }
            }
        } catch (e) {
            console.debug("Inline OCR note:", e);
            if (ocrStatusPill) {
                ocrStatusPill.className = "conf-pill conf-low";
                ocrStatusPill.innerText = "OCR Prepass Skipped";
            }
        }
    }

    // -------------------------------------------------------------------------
    // 7. Deliverables History & Real-Time Archive Manager
    // -------------------------------------------------------------------------
    const deliverablesHistoryTbody = document.getElementById("deliverables-history-tbody");

    async function fetchDeliverablesHistory() {
        if (!deliverablesHistoryTbody) return;
        try {
            const res = await fetch("/deliverables/list");
            if (!res.ok) return;
            const data = await res.json();
            const files = data.deliverables || [];

            deliverablesHistoryTbody.innerHTML = "";
            if (files.length === 0) {
                deliverablesHistoryTbody.innerHTML = `
                    <tr>
                        <td colspan="3" style="text-align: center; color: var(--text-muted); padding: 1rem 0.5rem;">
                            No files generated in output/ yet.
                        </td>
                    </tr>
                `;
                return;
            }

            files.forEach(file => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td style="max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${file.filename}">
                        <strong style="color: var(--text-primary); font-size: 0.72rem;">${file.filename}</strong><br>
                        <span style="font-size: 0.65rem; color: var(--text-muted);">${file.modified_time || ""}</span>
                    </td>
                    <td><span class="conf-pill conf-high" style="font-size: 0.65rem;">${file.size_kb} KB</span></td>
                    <td style="text-align: right;">
                        <a href="${file.download_url}" download="${file.filename}" class="btn btn-sm" style="padding: 1px 5px; font-size: 0.65rem;">Get</a>
                    </td>
                `;
                deliverablesHistoryTbody.appendChild(tr);
            });
        } catch (e) {
            console.debug("Deliverables history fetch note:", e);
        }
    }

    document.getElementById("btn-refresh-history")?.addEventListener("click", fetchDeliverablesHistory);
    fetchDeliverablesHistory();

    // -------------------------------------------------------------------------
    // 8. Dispatch Agent Task Plan (ReAct Loop Execution)
    // -------------------------------------------------------------------------
    btnDispatch?.addEventListener("click", async () => {
        const prompt = taskInput.value.trim();
        if (!prompt) {
            alert("Please provide an engineering task directive.");
            taskInput.focus();
            return;
        }

        const selectedFile = taskFileSelect.value;
        const routerMode = routerModeSelect.value;

        // Reset UI
        btnDispatch.disabled = true;
        btnDispatch.innerText = "Executing Task Plan...";
        stepCounter.innerText = "Planning...";
        taskOutput.value = "Executing multi-step reasoning & tool operations on-premise...\n";

        const startTime = performance.now();
        appendTraceLine("router", "INIT", `Dispatching directive to Sovereign Orchestrator (Mode: ${routerMode})`, 0);

        try {
            const res = await fetch("/agent/run", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    prompt: selectedFile ? `${prompt}\n\n[ATTACHED WORKSPACE FILE: ${selectedFile}]` : prompt,
                    task_hint: routerMode !== "auto" ? routerMode : null
                })
            });

            const data = await res.json();
            const elapsed = (performance.now() - startTime) / 1000;

            if (res.ok && data.status === "completed") {
                appendTraceLine("agent", "COMPLETE", `Execution finished in ${elapsed.toFixed(2)}s across ${data.iterations} iteration(s).`, elapsed);
                taskOutput.value = data.final_response;
                stepCounter.innerText = `Completed (${data.iterations} Steps)`;

                // Update Header Badges
                if (headerWorker) headerWorker.innerText = data.model_used || "qwen3.5:4b";
                
                // Update Active Deliverable Card
                const dlName = document.getElementById("deliverable-filename");
                const dlFormat = document.getElementById("deliverable-format");
                const dlSize = document.getElementById("deliverable-size");
                const dlTag = document.getElementById("deliverable-status-tag");
                const dlBtn = document.getElementById("btn-download-deliverable");

                if (data.latest_deliverable) {
                    if (dlName) dlName.innerText = data.latest_deliverable.filename;
                    if (dlFormat) dlFormat.innerText = data.latest_deliverable.format || "File";
                    if (dlSize) dlSize.innerText = `${data.latest_deliverable.size_kb} KB`;
                    if (dlTag) dlTag.innerText = "Status: Generated";

                    if (dlBtn) {
                        dlBtn.style.display = "block";
                        dlBtn.href = data.latest_deliverable.download_url;
                        dlBtn.setAttribute("download", data.latest_deliverable.filename);
                        const ext = (data.latest_deliverable.filename.split('.').pop() || 'DOCX').toUpperCase();
                        dlBtn.innerText = `Download .${ext} Deliverable`;
                    }
                } else {
                    if (dlName) dlName.innerText = "Console Output Only";
                    if (dlFormat) dlFormat.innerText = "Text / Data";
                    if (dlSize) dlSize.innerText = "Rendered in Trace";
                    if (dlTag) dlTag.innerText = "Status: Completed";
                    if (dlBtn) dlBtn.style.display = "none";
                }

                // Refresh Historical Deliverables Table
                fetchDeliverablesHistory();
            } else {
                appendTraceLine("err", "ERROR", data.detail || "Agent execution failed", elapsed);
                taskOutput.value = `Execution Error: ${data.detail}`;
                stepCounter.innerText = "Failed";
            }
        } catch (err) {
            const elapsed = (performance.now() - startTime) / 1000;
            appendTraceLine("err", "ERROR", err.message, elapsed);
            taskOutput.value = `Network/Backend Error: ${err.message}`;
            stepCounter.innerText = "Connection Error";
        } finally {
            btnDispatch.disabled = false;
            btnDispatch.innerText = "Execute Task Plan (Ctrl+Enter)";
            fetchNetworkAudit();
            fetchHardwareTelemetry();
        }
    });

    // -------------------------------------------------------------------------
    // 9. Knowledge Base & SOP Library (Screen 2)
    // -------------------------------------------------------------------------
    const kbSearchInput = document.getElementById("kb-search-input");
    const btnKbSearch = document.getElementById("btn-run-kb-search");
    const btnKbReindex = document.getElementById("btn-reindex-kb");
    const kbDocsTbody = document.getElementById("kb-docs-tbody");
    const kbResultsContainer = document.getElementById("kb-results-container");
    const kbResultsMeta = document.getElementById("kb-results-meta");

    async function fetchIndexedDocuments() {
        if (!kbDocsTbody) return;
        try {
            const res = await fetch("/tools/kb/list");
            if (!res.ok) return;
            const data = await res.json();

            kbDocsTbody.innerHTML = "";
            if (!data.documents || data.documents.length === 0) {
                kbDocsTbody.innerHTML = `
                    <tr>
                        <td colspan="2" style="text-align: center; color: var(--text-muted); padding: 1.5rem 0.5rem;">
                            No indexed documents found in <code>data/kb/</code>. Click 'Re-Index' to scan.
                        </td>
                    </tr>
                `;
                return;
            }

            data.documents.forEach(doc => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td><strong>${doc.filename}</strong></td>
                    <td><span class="conf-pill conf-high">${doc.chunks} chunks</span></td>
                `;
                kbDocsTbody.appendChild(tr);
            });
        } catch (e) {
            console.debug("KB doc list note:", e);
        }
    }

    btnKbReindex?.addEventListener("click", async () => {
        btnKbReindex.disabled = true;
        btnKbReindex.innerText = "Re-Indexing...";
        try {
            const res = await fetch("/tools/kb/reindex", { method: "POST" });
            const data = await res.json();
            if (res.ok) {
                alert(`Index synchronized! ${data.documents ? data.documents.length : 0} document(s) (${data.chunks_indexed} chunks) indexed on CPU.`);
                fetchIndexedDocuments();
            } else {
                alert(`Re-indexing failed: ${data.detail}`);
            }
        } catch (e) {
            alert(`Re-indexing error: ${e.message}`);
        } finally {
            btnKbReindex.disabled = false;
            btnKbReindex.innerText = "Re-Index";
        }
    });

    btnKbSearch?.addEventListener("click", async () => {
        const query = kbSearchInput.value.trim();
        if (!query) {
            alert("Please enter a search query.");
            kbSearchInput.focus();
            return;
        }

        btnKbSearch.disabled = true;
        btnKbSearch.innerText = "Searching...";
        kbResultsMeta.innerText = "Computing CPU cosine similarities...";

        try {
            const startT = performance.now();
            const res = await fetch("/tools/kb/search", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query: query, top_k: 4 })
            });
            const data = await res.json();
            const elapsed = Math.round(performance.now() - startT);

            if (res.ok && data.results) {
                kbResultsMeta.innerText = `${data.results.length} excerpt(s) retrieved in ${elapsed}ms`;
                kbResultsContainer.innerHTML = "";

                if (data.results.length === 0) {
                    kbResultsContainer.innerHTML = `
                        <div style="text-align: center; color: var(--text-muted); padding: 3rem 1rem;">
                            <strong>No Matching Procedural Clauses Found</strong>
                            <div style="font-size: 0.75rem; margin-top: 0.35rem;">Try adjusting your search terms or re-indexing data/kb/.</div>
                        </div>
                    `;
                } else {
                    data.results.forEach((item, idx) => {
                        const card = document.createElement("div");
                        card.className = "lineage-card";
                        const scorePill = item.score >= 0.40 ? "conf-high" : (item.score >= 0.25 ? "conf-med" : "conf-low");
                        card.innerHTML = `
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
                                <strong style="font-size: 0.8rem; color: var(--text-primary);">#${idx + 1} ${escapeHtml(item.source)}</strong>
                                <span class="conf-pill ${scorePill}">Score: ${(item.score).toFixed(3)}</span>
                            </div>
                            <div class="lineage-claim" style="font-size: 0.78rem; line-height: 1.5; color: var(--text-secondary);">${escapeHtml(item.text)}</div>
                            <div class="lineage-source" style="margin-top: 0.4rem;">CHUNK ID: ${escapeHtml(item.id || "N/A")} | Device: CPU Vector Match</div>
                        `;
                        kbResultsContainer.appendChild(card);
                    });
                }
            } else {
                kbResultsMeta.innerText = "Search Error";
            }
        } catch (e) {
            kbResultsMeta.innerText = `Search error: ${e.message}`;
        } finally {
            btnKbSearch.disabled = false;
            btnKbSearch.innerText = "Search Index (CPU Vector)";
        }
    });

    // Enter key triggers KB search
    kbSearchInput?.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            btnKbSearch?.click();
        }
    });
});
