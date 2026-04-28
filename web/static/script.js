let currentCapturedImage = null;
let currentStudentData = null;
let currentVerificationScore = null;
let hardwarePollTimer = null;
let verificationAwaitsDecision = false;
let registryCapturedImages = [];

document.addEventListener("DOMContentLoaded", () => {
    initializeNavigation();
    initializeCamera();
    initializeClock();
    loadStudents();
    loadAttendance();
    setupEventListeners();
    renderIdleState();
    startHardwarePolling();
});

function initializeNavigation() {
    const navButtons = document.querySelectorAll(".nav-btn");
    const panels = document.querySelectorAll(".panel");

    navButtons.forEach((button) => {
        button.addEventListener("click", () => {
            navButtons.forEach((item) => item.classList.remove("active"));
            panels.forEach((panel) => panel.classList.remove("active"));
            button.classList.add("active");
            document.getElementById(button.dataset.panel).classList.add("active");
        });
    });
}

function setupEventListeners() {
    document.getElementById("tagInput").addEventListener("keypress", handleTagInput);
    document.getElementById("confirmBtn").addEventListener("click", confirmAttendance);
    document.getElementById("retryBtn").addEventListener("click", resetVerification);
    document.getElementById("addStudentForm").addEventListener("submit", handleAddStudent);
    document.getElementById("captureStudentPhotoBtn").addEventListener("click", captureStudentRegistryPhoto);
    document.getElementById("clearStudentPhotosBtn").addEventListener("click", clearStudentRegistryPhotos);
}

function initializeClock() {
    const updateClock = () => {
        const now = new Date();
        document.getElementById("clockTime").textContent = now.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
        });
        document.getElementById("clockDate").textContent = now.toLocaleDateString([], {
            day: "2-digit",
            month: "short",
            year: "numeric",
        });
    };

    updateClock();
    setInterval(updateClock, 1000);
}

function initializeCamera() {
    document.getElementById("cameraContainer").innerHTML = `
        <div class="camera-shell">
            <div class="stage-placeholder">
                <div class="placeholder-icon">📷</div>
                <div class="placeholder-title">Live viewfinder starting</div>
                <div class="placeholder-text">Look at the camera. The green box appears only when a face is detected.</div>
            </div>
            <button class="action-btn capture-btn" id="captureBtn">Capture From Pi Camera</button>
            <div class="camera-status" id="cameraStatus">Camera live</div>
        </div>
    `;

    document.getElementById("captureBtn").addEventListener("click", captureImage);
    startViewfinder();
}

function startViewfinder(label = "") {
    const liveImage = document.getElementById("liveImage");
    const livePlaceholder = document.getElementById("livePlaceholder");
    if (!liveImage || !livePlaceholder) return;

    const params = new URLSearchParams();
    if (label) params.set("label", label);
    params.set("t", Date.now().toString());

    liveImage.src = `/api/viewfinder?${params.toString()}`;
    liveImage.style.display = "block";
    livePlaceholder.style.display = "none";
}

async function warmUpCamera() {
    try {
        await fetch("/api/capture", { method: "POST" });
    } catch (error) {
        console.log("Camera warm-up skipped");
    }
}

function renderIdleState() {
    verificationAwaitsDecision = false;
    setMachineBanner("System idle. Waiting for a student to approach and scan the NFC card.");
    setHeroSystemStatus("Ready");
    setStepState("arrival", "active");
    setStepState("scan", "idle");
    setStepState("capture", "idle");
    setStepState("confirm", "idle");
    document.getElementById("studentQuickView").innerHTML = "No student selected yet.";
    document.getElementById("finalReceipt").innerHTML = `<div class="receipt-state">Waiting for a successful verification.</div>`;
}

function startHardwarePolling() {
    if (hardwarePollTimer) {
        clearInterval(hardwarePollTimer);
    }

    hardwarePollTimer = setInterval(async () => {
        try {
            const response = await fetch("/api/hardware/poll");
            const data = await response.json();
            if (!response.ok) {
                return;
            }

            if (data.tag_id) {
                const tagInput = document.getElementById("tagInput");
                tagInput.value = data.tag_id;
                await processTag(data.tag_id);
                tagInput.value = "";
            }

            if (verificationAwaitsDecision && data.decision === "confirm") {
                await confirmAttendance();
            } else if (verificationAwaitsDecision && data.decision === "retry") {
                resetVerification();
            }
        } catch (error) {
            console.log("Hardware poll unavailable", error);
        }
    }, 500);
}

function setMachineBanner(message) {
    document.getElementById("machineStatusBanner").textContent = message;
}

function setHeroSystemStatus(status) {
    document.getElementById("heroSystemStatus").textContent = status;
}

function setStepState(stepName, state) {
    const element = document.getElementById(`step-${stepName}`);
    if (!element) return;
    element.classList.remove("active", "completed");
    if (state === "active") element.classList.add("active");
    if (state === "completed") element.classList.add("completed");
}

function renderStudentQuickView(student) {
    document.getElementById("studentQuickView").innerHTML = `
        <strong>${escapeHtml(student.name)}</strong><br>
        Student ID: ${escapeHtml(student.student_id)}<br>
        Class ${escapeHtml(student.class_name || "-")} • Section ${escapeHtml(student.section || "-")} • Roll No. ${escapeHtml(student.roll_no || "-")}
    `;
}

function renderVerificationResult(match, data) {
    const resultContainer = document.getElementById("resultContainer");
    const scorePercent = `${(data.score * 100).toFixed(2)}%`;

    if (match) {
        resultContainer.innerHTML = `
            <div class="result-content">
                <div class="result-pill success">Match Detected</div>
                <div class="match-score">${scorePercent}</div>
                <div class="placeholder-title">Student Verified Successfully</div>
                <div class="placeholder-text">The stored record matches the live image. Attendance is ready to be confirmed.</div>
                <div class="detail-grid">
                    <div class="detail-box">
                        <span class="detail-label">Student Name</span>
                        <span class="detail-value">${escapeHtml(data.student.name)}</span>
                    </div>
                    <div class="detail-box">
                        <span class="detail-label">Student ID</span>
                        <span class="detail-value">${escapeHtml(data.student.student_id)}</span>
                    </div>
                    <div class="detail-box">
                        <span class="detail-label">Class</span>
                        <span class="detail-value">${escapeHtml(data.student.class_name || "-")}</span>
                    </div>
                    <div class="detail-box">
                        <span class="detail-label">Section</span>
                        <span class="detail-value">${escapeHtml(data.student.section || "-")}</span>
                    </div>
                    <div class="detail-box">
                        <span class="detail-label">Roll No.</span>
                        <span class="detail-value">${escapeHtml(data.student.roll_no || "-")}</span>
                    </div>
                    <div class="detail-box">
                        <span class="detail-label">Verification Score</span>
                        <span class="detail-value">${scorePercent}</span>
                    </div>
                </div>
            </div>
        `;
    } else {
        resultContainer.innerHTML = `
            <div class="result-content">
                <div class="result-pill error">No Match</div>
                <div class="match-score">${scorePercent}</div>
                <div class="placeholder-title">Verification failed</div>
                <div class="placeholder-text">The live image did not match the stored record. Retry with better positioning or lighting.</div>
            </div>
        `;
    }
}

function renderFinalReceipt(student, score) {
    const scorePercent = `${(score * 100).toFixed(2)}%`;
    document.getElementById("finalReceipt").innerHTML = `
        <div class="receipt-content">
            <div class="receipt-heading">ATTENDANCE MARKED</div>
            <div class="receipt-subtext">
                The student has completed NFC validation and image verification successfully. Attendance has been recorded as present.
            </div>
            <div class="receipt-grid">
                <div class="receipt-item">
                    <span class="receipt-label">Student Name</span>
                    <span class="receipt-value">${escapeHtml(student.name)}</span>
                </div>
                <div class="receipt-item">
                    <span class="receipt-label">Class</span>
                    <span class="receipt-value">${escapeHtml(student.class_name || "-")}</span>
                </div>
                <div class="receipt-item">
                    <span class="receipt-label">Section</span>
                    <span class="receipt-value">${escapeHtml(student.section || "-")}</span>
                </div>
                <div class="receipt-item">
                    <span class="receipt-label">Roll No.</span>
                    <span class="receipt-value">${escapeHtml(student.roll_no || "-")}</span>
                </div>
                <div class="receipt-item">
                    <span class="receipt-label">Student ID</span>
                    <span class="receipt-value">${escapeHtml(student.student_id)}</span>
                </div>
                <div class="receipt-item">
                    <span class="receipt-label">Status</span>
                    <span class="receipt-value">Marked Present</span>
                </div>
                <div class="receipt-item">
                    <span class="receipt-label">Verification</span>
                    <span class="receipt-value">Dual Verified</span>
                </div>
                <div class="receipt-item">
                    <span class="receipt-label">Match Score</span>
                    <span class="receipt-value">${scorePercent}</span>
                </div>
            </div>
        </div>
    `;
}

async function handleTagInput(event) {
    if (event.key !== "Enter") return;

    const tag = event.target.value.trim();
    if (!tag) return;

    await processTag(tag);
    event.target.value = "";
}

async function processTag(tag) {
    try {
        setHeroSystemStatus("Active");
        setMachineBanner("Student detected. Searching for NFC record...");
        setStepState("arrival", "completed");
        setStepState("scan", "active");

        const response = await fetch("/api/students");
        const students = await response.json();
        const student = students.find((item) => item.tag_id === tag);

        if (!student) {
            setMachineBanner("Unknown card detected. No student record found.");
            showErrorResult("Student not found");
            event.target.value = "";
            return;
        }

        currentStudentData = student;
        renderStudentQuickView(student);
        startViewfinder(student.name);
        setMachineBanner(`Student identified: ${student.name}. Activating camera verification...`);
        setStepState("scan", "completed");
        setStepState("capture", "active");

        setTimeout(() => {
            autoCaptureForVerification();
        }, 1200);
    } catch (error) {
        showErrorResult(`Error: ${error.message}`);
    }
}

async function captureImage() {
    const captureBtn = document.getElementById("captureBtn");
    const statusDiv = document.getElementById("cameraStatus");
    if (captureBtn.disabled) return;

    captureBtn.disabled = true;
    captureBtn.textContent = "Capturing...";
    statusDiv.textContent = "Initializing camera...";
    setMachineBanner("Camera is preparing to capture the student ID card...");

    setTimeout(async () => {
        statusDiv.textContent = "Capturing image...";

        try {
            const response = await fetch("/api/capture", { method: "POST" });
            const data = await response.json();

            if (!response.ok || data.error) {
                throw new Error(data.error || "Capture failed");
            }

            applyCapturedImage(data.image);
            statusDiv.textContent = "Image captured successfully";
            setMachineBanner("Live image captured. Running image verification...");

            if (currentStudentData) {
                await verifyImage();
            }
        } catch (error) {
            statusDiv.textContent = `Capture failed: ${error.message}`;
            setMachineBanner("Camera capture failed. Please retry.");
        } finally {
            captureBtn.disabled = false;
            captureBtn.textContent = "Capture From Pi Camera";
        }
    }, 1200);
}

async function autoCaptureForVerification() {
    if (!currentStudentData) return;

    const captureBtn = document.getElementById("captureBtn");
    const statusDiv = document.getElementById("cameraStatus");
    captureBtn.disabled = true;
    captureBtn.textContent = "Auto-capturing...";
    statusDiv.textContent = "Preparing automatic capture...";

    try {
        await new Promise((resolve) => setTimeout(resolve, 900));

        const response = await fetch("/api/capture", { method: "POST" });
        const data = await response.json();

        if (!response.ok || data.error) {
            throw new Error(data.error || "Capture failed");
        }

        applyCapturedImage(data.image);
        statusDiv.textContent = "Image captured successfully";
        await verifyImage();
    } catch (error) {
        statusDiv.textContent = `Auto-capture failed: ${error.message}`;
        setMachineBanner("Automatic capture failed. Please capture again manually.");
    } finally {
        captureBtn.disabled = false;
        captureBtn.textContent = "Capture From Pi Camera";
    }
}

function applyCapturedImage(imageData) {
    currentCapturedImage = imageData;
    currentVerificationScore = null;
    const liveImage = document.getElementById("liveImage");
    liveImage.src = currentCapturedImage;
    liveImage.style.display = "block";
    document.getElementById("livePlaceholder").style.display = "none";
}

async function verifyImage() {
    if (!currentCapturedImage || !currentStudentData) return;

    document.getElementById("resultContainer").innerHTML = `
        <div class="result-content">
            <div class="placeholder-icon">🔍</div>
            <div class="placeholder-title">Verification in progress</div>
            <div class="placeholder-text">Comparing live image with all stored photos for this student.</div>
        </div>
    `;

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

        if (!response.ok) {
            throw new Error(data.error || "Verification failed");
        }

        currentVerificationScore = data.score;
        currentStudentData = {
            ...currentStudentData,
            ...data.student,
        };
        if (data.annotated_image) {
            applyCapturedImage(data.annotated_image);
        }

        renderStudentQuickView(currentStudentData);
        renderVerificationResult(data.match, data);

        if (data.match) {
            setMachineBanner("Verification successful. Press the green button to mark attendance.");
            setStepState("capture", "completed");
            setStepState("confirm", "active");
            verificationAwaitsDecision = true;
            document.getElementById("confirmBtn").style.display = "block";
            document.getElementById("retryBtn").style.display = "block";
        } else {
            setMachineBanner("Verification failed. Press the red button to retry.");
            verificationAwaitsDecision = true;
            document.getElementById("confirmBtn").style.display = "none";
            document.getElementById("retryBtn").style.display = "block";
        }
    } catch (error) {
        showErrorResult(`Verification error: ${error.message}`);
    }
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
        if (!response.ok) {
            throw new Error(data.error || "Failed to confirm attendance");
        }

        setMachineBanner("Attendance recorded successfully.");
        setHeroSystemStatus("Marked");
        setStepState("confirm", "completed");
        renderFinalReceipt(currentStudentData, currentVerificationScore ?? 0);
        verificationAwaitsDecision = false;
        document.getElementById("resultContainer").innerHTML = `
            <div class="result-content">
                <div class="result-pill success">Attendance Confirmed</div>
                <div class="match-score">${((currentVerificationScore ?? 0) * 100).toFixed(2)}%</div>
                <div class="placeholder-title">Student marked present</div>
                <div class="placeholder-text">The machine has completed the full attendance flow successfully.</div>
            </div>
        `;
        document.getElementById("confirmBtn").style.display = "none";
        document.getElementById("retryBtn").style.display = "none";
        loadAttendance();

        setTimeout(() => {
            resetVerification();
        }, 5000);
    } catch (error) {
        const message = error.message.includes("already marked")
            ? "Attendance was already marked for this student today."
            : `Error marking attendance: ${error.message}`;
        showErrorResult(message);
    }
}

function resetVerification() {
    currentCapturedImage = null;
    currentStudentData = null;
    currentVerificationScore = null;
    startViewfinder();
    document.getElementById("resultContainer").innerHTML = `
        <div class="result-content">
            <div class="placeholder-icon">🛡️</div>
            <div class="placeholder-title">Waiting for verification</div>
            <div class="placeholder-text">Once the student scans the card and the image is captured, the match result will appear here.</div>
        </div>
    `;
    document.getElementById("confirmBtn").style.display = "none";
    document.getElementById("retryBtn").style.display = "none";
    document.getElementById("tagInput").value = "";
    document.getElementById("tagInput").focus();
    renderIdleState();
}

function showErrorResult(message) {
    setHeroSystemStatus("Attention");
    document.getElementById("resultContainer").innerHTML = `
        <div class="result-content">
            <div class="result-pill error">Error</div>
            <div class="placeholder-title">${escapeHtml(message)}</div>
            <div class="placeholder-text">Please retry the attendance process.</div>
        </div>
    `;
}

async function loadStudents() {
    try {
        const response = await fetch("/api/students");
        const students = await response.json();
        if (!response.ok) {
            throw new Error(students.error || "Failed to load students");
        }

        if (students.length === 0) {
            document.getElementById("studentsList").innerHTML = `<p class="helper-text">No students added yet.</p>`;
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
        document.getElementById("studentsList").innerHTML = `<p class="helper-text">Error loading students: ${escapeHtml(error.message)}</p>`;
    }
}

async function handleAddStudent(event) {
    event.preventDefault();

    const tagId = document.getElementById("newTagId").value.trim();
    const studentId = document.getElementById("newStudentId").value.trim();
    const className = document.getElementById("newClassName").value.trim();
    const section = document.getElementById("newSection").value.trim();
    const rollNo = document.getElementById("newRollNo").value.trim();
    const name = document.getElementById("newStudentName").value.trim();
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
                tag_id: tagId,
                student_id: studentId,
                class_name: className,
                section: section,
                roll_no: rollNo,
                name: name,
                images: images,
            }),
        });

        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.error || "Error adding student");
        }

        alert(`Student added successfully with ${images.length} photo(s)`);
        document.getElementById("addStudentForm").reset();
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

        if (!response.ok || data.error) {
            throw new Error(data.error || "Capture failed");
        }

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
        reader.onload = (loadEvent) => resolve(loadEvent.target.result);
        reader.onerror = () => reject(new Error(`Could not read ${file.name}`));
        reader.readAsDataURL(file);
    });
}

async function loadAttendance() {
    try {
        const response = await fetch("/api/attendance");
        const logs = await response.json();
        if (!response.ok) {
            throw new Error(logs.error || "Failed to load attendance");
        }

        document.getElementById("heroAttendanceCount").textContent = `${logs.length} logs`;

        if (logs.length === 0) {
            document.getElementById("attendanceList").innerHTML = `<p class="helper-text">No attendance records yet.</p>`;
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
                    <td><strong>${escapeHtml(log.name)}</strong><br><span class="muted-inline">${escapeHtml(log.student_id)}</span></td>
                    <td>${escapeHtml(time)}</td>
                    <td><span class="badge badge-present">${escapeHtml(log.status)}</span></td>
                    <td>${escapeHtml(log.notes || "-")}</td>
                </tr>
            `;
        }

        html += "</tbody></table>";
        document.getElementById("attendanceList").innerHTML = html;
    } catch (error) {
        document.getElementById("attendanceList").innerHTML = `<p class="helper-text">Error loading attendance: ${escapeHtml(error.message)}</p>`;
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
