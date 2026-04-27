let currentCapturedImage = null;
let currentStudentData = null;
let currentVerificationScore = null;
let hardwarePollTimer = null;
let verificationAwaitsDecision = false;
let sleepTimer = null;
let registryCapturedImages = [];

const ADMIN_PASSWORD = "springdalespusa@abhimanyu";

document.addEventListener("DOMContentLoaded", () => {
    setupKioskEvents();
    setupAdminPortal();
    loadStudents();
    loadAttendance();
    renderSleepState();
    startHardwarePolling();
});

function setupKioskEvents() {
    const tagInput = document.getElementById("tagInput");
    tagInput.addEventListener("keydown", async (event) => {
        if (event.key !== "Enter") return;
        const tag = tagInput.value.trim();
        if (!tag) return;
        tagInput.value = "";
        await processTag(tag);
    });

    document.getElementById("confirmBtn").addEventListener("click", confirmAttendance);
    document.getElementById("retryBtn").addEventListener("click", retryVerification);
    document.getElementById("errorResetBtn").addEventListener("click", renderSleepState);
    document.getElementById("addStudentForm").addEventListener("submit", handleAddStudent);
    document.getElementById("captureStudentPhotoBtn").addEventListener("click", captureStudentRegistryPhoto);
    document.getElementById("clearStudentPhotosBtn").addEventListener("click", clearStudentRegistryPhotos);
}

function showScreen(screenId) {
    document.querySelectorAll(".kiosk-screen").forEach((screen) => {
        screen.classList.toggle("active", screen.id === screenId);
    });
}

function setMachineStatus(text, tone = "ready") {
    document.getElementById("machineStatusText").textContent = text;
    const dot = document.getElementById("machineDot");
    dot.classList.remove("warn", "error");
    if (tone === "warn") dot.classList.add("warn");
    if (tone === "error") dot.classList.add("error");
}

function clearSleepTimer() {
    if (sleepTimer) {
        clearTimeout(sleepTimer);
        sleepTimer = null;
    }
}

function renderSleepState() {
    clearSleepTimer();
    currentCapturedImage = null;
    currentStudentData = null;
    currentVerificationScore = null;
    verificationAwaitsDecision = false;
    document.getElementById("liveImage").removeAttribute("src");
    document.getElementById("confirmImage").removeAttribute("src");
    document.querySelectorAll(".camera-frame").forEach((frame) => frame.classList.remove("has-image"));
    document.getElementById("studentName").textContent = "Reading card";
    document.getElementById("studentQuickView").textContent = "Waiting for RFID data.";
    document.getElementById("resultContainer").textContent = "Waiting for verification result.";
    document.getElementById("finalReceipt").textContent = "Waiting for receipt.";
    setMachineStatus("Sleeping");
    showScreen("sleepScreen");
    document.getElementById("tagInput").focus();
}

async function startHardwarePolling() {
    if (hardwarePollTimer) clearInterval(hardwarePollTimer);

    hardwarePollTimer = setInterval(async () => {
        try {
            const response = await fetch("/api/hardware/poll");
            const data = await response.json();
            if (!response.ok) return;

            if (data.tag_id && !currentStudentData) {
                await processTag(data.tag_id);
            }

            if (verificationAwaitsDecision && data.decision === "confirm") {
                await confirmAttendance();
            } else if (verificationAwaitsDecision && data.decision === "retry") {
                retryVerification();
            }
        } catch (error) {
            console.log("Hardware poll unavailable", error);
        }
    }, 500);
}

async function processTag(tag) {
    clearSleepTimer();
    setMachineStatus("Reading card", "warn");
    showScreen("cameraScreen");
    document.getElementById("cameraModeLabel").textContent = "RFID Detected";
    document.getElementById("cameraStatus").textContent = "Searching record";

    try {
        const response = await fetch("/api/students");
        const students = await response.json();
        if (!response.ok) throw new Error(students.error || "Failed to load students");

        const student = students.find((item) => item.tag_id === tag);
        if (!student) {
            showError("Unknown card", "No student record was found for this RFID tag.");
            return;
        }

        currentStudentData = student;
        renderStudentQuickView(student);
        setMachineStatus("Camera waking", "warn");
        document.getElementById("cameraModeLabel").textContent = "Camera On";
        document.getElementById("cameraStatus").textContent = "Capturing";
        await autoCaptureForVerification();
    } catch (error) {
        showError("RFID error", error.message);
    }
}

function renderStudentQuickView(student) {
    document.getElementById("studentName").textContent = student.name;
    document.getElementById("studentQuickView").innerHTML = `
        <div class="fact-row"><span>Student ID</span><strong>${escapeHtml(student.student_id)}</strong></div>
        <div class="fact-row"><span>Class</span><strong>${escapeHtml(student.class_name || "-")}</strong></div>
        <div class="fact-row"><span>Section</span><strong>${escapeHtml(student.section || "-")}</strong></div>
        <div class="fact-row"><span>Roll No.</span><strong>${escapeHtml(student.roll_no || "-")}</strong></div>
        <div class="fact-row"><span>RFID</span><strong>${escapeHtml(student.tag_id)}</strong></div>
    `;
}

async function autoCaptureForVerification() {
    if (!currentStudentData) return;

    try {
        await new Promise((resolve) => setTimeout(resolve, 650));
        const response = await fetch("/api/capture", { method: "POST" });
        const data = await response.json();

        if (!response.ok || data.error) {
            throw new Error(data.error || "Capture failed");
        }

        applyCapturedImage(data.image);
        document.getElementById("cameraStatus").textContent = "Verifying";
        await verifyImage();
    } catch (error) {
        showError("Camera error", error.message);
    }
}

function applyCapturedImage(imageData) {
    currentCapturedImage = imageData;
    currentVerificationScore = null;
    const liveImage = document.getElementById("liveImage");
    const confirmImage = document.getElementById("confirmImage");
    liveImage.src = imageData;
    confirmImage.src = imageData;
    document.querySelectorAll(".camera-frame").forEach((frame) => frame.classList.add("has-image"));
}

async function verifyImage() {
    if (!currentCapturedImage || !currentStudentData) return;

    try {
        const response = await fetch("/api/verify", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                tag_id: currentStudentData.tag_id,
                image: currentCapturedImage,
            }),
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Verification failed");

        currentVerificationScore = data.score;
        currentStudentData = { ...currentStudentData, ...data.student };

        if (data.match) {
            renderVerificationResult(data);
            verificationAwaitsDecision = true;
            setMachineStatus("Confirm attendance", "warn");
            showScreen("confirmScreen");
        } else {
            verificationAwaitsDecision = true;
            document.getElementById("matchScoreLabel").textContent = `Score ${(data.score * 100).toFixed(2)}%`;
            document.getElementById("resultContainer").innerHTML = `
                <strong>No Match</strong><br>
                The live image did not match the stored record. Retry the verification.
            `;
            setMachineStatus("Retry needed", "error");
            showScreen("confirmScreen");
        }
    } catch (error) {
        showError("Verification error", error.message);
    }
}

function renderVerificationResult(data) {
    const scorePercent = `${(data.score * 100).toFixed(2)}%`;
    const photosChecked = data.photos_checked ? `<br>Photos Checked: ${escapeHtml(data.photos_checked)}` : "";
    document.getElementById("matchScoreLabel").textContent = `Score ${scorePercent}`;
    document.getElementById("resultContainer").innerHTML = `
        <strong>${escapeHtml(data.student.name)}</strong><br>
        Student ID: ${escapeHtml(data.student.student_id)}<br>
        Match Score: ${scorePercent}<br>
        Dual verification completed successfully.${photosChecked}
    `;
}

async function confirmAttendance() {
    if (!currentStudentData) return;

    try {
        const response = await fetch("/api/confirm-attendance", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                tag_id: currentStudentData.tag_id,
                score: currentVerificationScore ?? 0,
            }),
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Failed to confirm attendance");

        verificationAwaitsDecision = false;
        setMachineStatus("Attendance saved");
        renderFinalReceipt(currentStudentData, currentVerificationScore ?? 0);
        showScreen("markedScreen");
        loadAttendance();

        sleepTimer = setTimeout(renderSleepState, 4200);
    } catch (error) {
        showError("Attendance error", error.message);
    }
}

function retryVerification() {
    verificationAwaitsDecision = false;
    if (!currentStudentData) {
        renderSleepState();
        return;
    }
    setMachineStatus("Retrying", "warn");
    showScreen("cameraScreen");
    setTimeout(autoCaptureForVerification, 450);
}

function renderFinalReceipt(student, score) {
    const scorePercent = `${(score * 100).toFixed(2)}%`;
    document.getElementById("finalReceipt").innerHTML = `
        <div class="receipt-item"><span class="receipt-label">Student</span><strong class="receipt-value">${escapeHtml(student.name)}</strong></div>
        <div class="receipt-item"><span class="receipt-label">Student ID</span><strong class="receipt-value">${escapeHtml(student.student_id)}</strong></div>
        <div class="receipt-item"><span class="receipt-label">Class</span><strong class="receipt-value">${escapeHtml(student.class_name || "-")}</strong></div>
        <div class="receipt-item"><span class="receipt-label">Status</span><strong class="receipt-value">Present</strong></div>
        <div class="receipt-item"><span class="receipt-label">Verification</span><strong class="receipt-value">Dual Verified</strong></div>
        <div class="receipt-item"><span class="receipt-label">Score</span><strong class="receipt-value">${scorePercent}</strong></div>
    `;
}

function showError(title, message) {
    verificationAwaitsDecision = false;
    setMachineStatus("Attention needed", "error");
    document.getElementById("errorTitle").textContent = title;
    document.getElementById("errorMessage").textContent = message || "Please retry the attendance process.";
    showScreen("errorScreen");
}

function setupAdminPortal() {
    const hotspot = document.getElementById("adminHotspot");
    const drawer = document.getElementById("adminDrawer");
    const closeButton = document.getElementById("closeAdminBtn");
    const passwordInput = document.getElementById("adminPassword");
    const loginButton = document.getElementById("adminLoginBtn");
    const adminMessage = document.getElementById("adminMessage");
    const adminContent = document.getElementById("adminContent");
    let dragStart = null;

    hotspot.addEventListener("pointerdown", (event) => {
        dragStart = { x: event.clientX, y: event.clientY };
        hotspot.setPointerCapture(event.pointerId);
    });

    hotspot.addEventListener("pointermove", (event) => {
        if (!dragStart) return;
        const movedLeft = dragStart.x - event.clientX;
        const movedDown = event.clientY - dragStart.y;
        if (movedLeft > 80 && movedDown > 20) {
            drawer.classList.add("open");
            passwordInput.focus();
            dragStart = null;
        }
    });

    hotspot.addEventListener("pointerup", () => {
        dragStart = null;
    });

    closeButton.addEventListener("click", () => {
        drawer.classList.remove("open");
    });

    function unlockAdmin() {
        if (passwordInput.value === ADMIN_PASSWORD) {
            adminContent.classList.add("unlocked");
            adminMessage.textContent = "Admin portal unlocked.";
            passwordInput.value = "";
            loadStudents();
            loadAttendance();
        } else {
            adminMessage.textContent = "Incorrect password.";
        }
    }

    loginButton.addEventListener("click", unlockAdmin);
    passwordInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") unlockAdmin();
    });

    document.querySelectorAll(".admin-tab").forEach((button) => {
        button.addEventListener("click", () => {
            document.querySelectorAll(".admin-tab").forEach((item) => item.classList.remove("active"));
            document.querySelectorAll(".admin-panel").forEach((panel) => panel.classList.remove("active"));
            button.classList.add("active");
            document.getElementById(button.dataset.adminPanel).classList.add("active");
        });
    });
}

async function loadStudents() {
    try {
        const response = await fetch("/api/students");
        const students = await response.json();
        if (!response.ok) throw new Error(students.error || "Failed to load students");

        if (students.length === 0) {
            document.getElementById("studentsList").innerHTML = `<p class="empty-state">No students added yet.</p>`;
            return;
        }

        let html = `
            <table>
                <thead>
                    <tr>
                        <th>Photo</th>
                        <th>Name</th>
                        <th>Student ID</th>
                        <th>Class</th>
                        <th>Section</th>
                        <th>Roll No.</th>
                        <th>Tag</th>
                    </tr>
                </thead>
                <tbody>
        `;

        for (const student of students) {
            html += `
                <tr>
                    <td><img class="table-photo" src="/api/student/${encodeURIComponent(student.student_id)}/image" alt="${escapeHtml(student.name)}"></td>
                    <td>${escapeHtml(student.name)}</td>
                    <td>${escapeHtml(student.student_id)}</td>
                    <td>${escapeHtml(student.class_name || "-")}</td>
                    <td>${escapeHtml(student.section || "-")}</td>
                    <td>${escapeHtml(student.roll_no || "-")}</td>
                    <td><code>${escapeHtml(student.tag_id)}</code></td>
                </tr>
            `;
        }

        html += "</tbody></table>";
        document.getElementById("studentsList").innerHTML = html;
    } catch (error) {
        document.getElementById("studentsList").innerHTML = `<p class="empty-state">Error loading students: ${escapeHtml(error.message)}</p>`;
    }
}

async function handleAddStudent(event) {
    event.preventDefault();

    const imageFiles = Array.from(document.getElementById("newStudentImage").files);
    if (imageFiles.length === 0 && registryCapturedImages.length === 0) {
        alert("Please upload or capture at least one image");
        return;
    }

    try {
        const uploadedImages = await Promise.all(imageFiles.map(readFileAsDataUrl));
        const images = [...registryCapturedImages, ...uploadedImages];
        const response = await fetch("/api/students", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                tag_id: document.getElementById("newTagId").value.trim(),
                student_id: document.getElementById("newStudentId").value.trim(),
                class_name: document.getElementById("newClassName").value.trim(),
                section: document.getElementById("newSection").value.trim(),
                roll_no: document.getElementById("newRollNo").value.trim(),
                name: document.getElementById("newStudentName").value.trim(),
                images,
            }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Error adding student");
        event.target.reset();
        clearStudentRegistryPhotos();
        loadStudents();
    } catch (error) {
        alert(error.message);
    }
}

async function captureStudentRegistryPhoto() {
    const captureBtn = document.getElementById("captureStudentPhotoBtn");
    const status = document.getElementById("studentPhotoStatus");
    if (captureBtn.disabled) return;

    captureBtn.disabled = true;
    captureBtn.textContent = "Capturing...";
    status.textContent = "Capturing photo from Pi camera...";

    try {
        const response = await fetch("/api/capture", { method: "POST" });
        const data = await response.json();
        if (!response.ok || data.error) throw new Error(data.error || "Capture failed");
        registryCapturedImages.push(data.image);
        renderStudentPhotoPreview();
    } catch (error) {
        status.textContent = `Capture failed: ${error.message}`;
    } finally {
        captureBtn.disabled = false;
        captureBtn.textContent = "Click Photo For Registry";
    }
}

function clearStudentRegistryPhotos() {
    registryCapturedImages = [];
    renderStudentPhotoPreview();
}

function renderStudentPhotoPreview() {
    const status = document.getElementById("studentPhotoStatus");
    const preview = document.getElementById("studentPhotoPreview");
    status.textContent = registryCapturedImages.length === 0
        ? "No camera photos captured yet."
        : `${registryCapturedImages.length} camera photo(s) ready to save.`;
    preview.innerHTML = registryCapturedImages
        .map((image, index) => `<img src="${image}" alt="Captured student photo ${index + 1}">`)
        .join("");
}

function readFileAsDataUrl(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (event) => resolve(event.target.result);
        reader.onerror = () => reject(new Error(`Could not read ${file.name}`));
        reader.readAsDataURL(file);
    });
}

async function loadAttendance() {
    try {
        const response = await fetch("/api/attendance");
        const logs = await response.json();
        if (!response.ok) throw new Error(logs.error || "Failed to load attendance");

        if (logs.length === 0) {
            document.getElementById("attendanceList").innerHTML = `<p class="empty-state">No attendance records yet.</p>`;
            return;
        }

        let html = `
            <table>
                <thead>
                    <tr>
                        <th>Student</th>
                        <th>Time</th>
                        <th>Status</th>
                        <th>Notes</th>
                    </tr>
                </thead>
                <tbody>
        `;

        for (const log of logs) {
            const time = new Date(log.timestamp).toLocaleString();
            html += `
                <tr>
                    <td><strong>${escapeHtml(log.name)}</strong><br><span>${escapeHtml(log.student_id)}</span></td>
                    <td>${escapeHtml(time)}</td>
                    <td><span class="badge">${escapeHtml(log.status)}</span></td>
                    <td>${escapeHtml(log.notes || "-")}</td>
                </tr>
            `;
        }

        html += "</tbody></table>";
        document.getElementById("attendanceList").innerHTML = html;
    } catch (error) {
        document.getElementById("attendanceList").innerHTML = `<p class="empty-state">Error loading attendance: ${escapeHtml(error.message)}</p>`;
    }
}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

setInterval(loadAttendance, 10000);
