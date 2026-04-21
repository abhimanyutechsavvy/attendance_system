let currentCapturedImage = null;
let currentStudentData = null;
let videoStream = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeCamera();
    loadStudents();
    loadAttendance();
    setupEventListeners();
});

function setupEventListeners() {
    document.getElementById('tagInput').addEventListener('keypress', handleTagInput);
    document.getElementById('captureBtn').addEventListener('click', captureImage);
    document.getElementById('confirmBtn').addEventListener('click', confirmAttendance);
    document.getElementById('retryBtn').addEventListener('click', resetVerification);
    document.getElementById('addStudentForm').addEventListener('submit', handleAddStudent);
}

async function initializeCamera() {
    // Remove browser camera initialization
    // Use Pi camera via API instead
    document.getElementById('cameraContainer').innerHTML = `
        <button class="btn btn-primary btn-sm mt-2" id="captureBtn">
            <i class="bi bi-camera-fill"></i> Capture from Pi Camera
        </button>
        <div id="cameraStatus" class="mt-2 text-muted">Camera ready</div>
    `;
    
    // Pre-warm the camera by making an initial capture and discard
    setTimeout(() => {
        warmUpCamera();
    }, 500);
}

async function warmUpCamera() {
    try {
        // Make a silent capture to initialize camera settings
        const response = await fetch('/api/capture', {
            method: 'POST'
        });
        if (response.ok) {
            console.log('Camera warmed up successfully');
        }
    } catch (error) {
        console.log('Camera warm-up failed, will try again on first capture');
    }
}

function captureImage() {
    // Prevent manual capture if auto-capture is in progress
    if (document.getElementById('captureBtn').disabled) return;
    
    const captureBtn = document.getElementById('captureBtn');
    const statusDiv = document.getElementById('cameraStatus');
    
    captureBtn.disabled = true;
    captureBtn.innerHTML = '<i class="bi bi-camera-fill"></i> Capturing...';
    statusDiv.innerHTML = '<div class="spinner-border spinner-border-sm" role="status"></div> Initializing camera...';
    
    // Camera warm-up delay
    setTimeout(async () => {
        statusDiv.innerHTML = '<div class="spinner-border spinner-border-sm" role="status"></div> Capturing image...';
        
        try {
            const response = await fetch('/api/capture', {
                method: 'POST'
            });
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            currentCapturedImage = data.image;
            
            const liveImage = document.getElementById('liveImage');
            liveImage.src = currentCapturedImage;
            liveImage.style.display = 'block';
            document.getElementById('livePlaceholder').style.display = 'none';
            
            statusDiv.innerHTML = '<span class="text-success">✓ Image captured successfully</span>';
            
            if (currentStudentData) {
                verifyImage();
            }
        } catch (error) {
            console.error('Capture error:', error);
            statusDiv.innerHTML = `<span class="text-danger">✗ Capture failed: ${error.message}</span>`;
        } finally {
            captureBtn.disabled = false;
            captureBtn.innerHTML = '<i class="bi bi-camera-fill"></i> Capture from Pi Camera';
        }
    }, 1500); // 1.5 second warm-up for manual capture
}

async function handleTagInput(e) {
    if (e.key !== 'Enter') return;
    
    const tag = e.target.value.trim();
    if (!tag) return;
    
    try {
        const response = await fetch('/api/students');
        const students = await response.json();
        const student = students.find(s => s.tag_id === tag);
        
        if (!student) {
            showResult('Student not found', 'error');
            e.target.value = '';
            return;
        }
        
        currentStudentData = student;
        showResult(`Student found: ${student.name}. Initializing camera...`, 'success');
        
        // Automatically capture after RFID with camera warm-up delay
        setTimeout(() => {
            autoCaptureForVerification();
        }, 2000); // 2 second delay for camera initialization
        
    } catch (error) {
        showResult('Error: ' + error.message, 'error');
    }
    
    e.target.value = '';
}

async function autoCaptureForVerification() {
    if (!currentStudentData) return;
    
    const captureBtn = document.getElementById('captureBtn');
    const statusDiv = document.getElementById('cameraStatus');
    
    // Disable manual capture during auto-capture
    captureBtn.disabled = true;
    captureBtn.innerHTML = '<i class="bi bi-camera-fill"></i> Auto-capturing...';
    statusDiv.innerHTML = '<div class="spinner-border spinner-border-sm" role="status"></div> Initializing camera...';
    
    // Additional warm-up time
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    statusDiv.innerHTML = '<div class="spinner-border spinner-border-sm" role="status"></div> Capturing image...';
    
    try {
        const response = await fetch('/api/capture', {
            method: 'POST'
        });
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        currentCapturedImage = data.image;
        
        const liveImage = document.getElementById('liveImage');
        liveImage.src = currentCapturedImage;
        liveImage.style.display = 'block';
        document.getElementById('livePlaceholder').style.display = 'none';
        
        statusDiv.innerHTML = '<span class="text-success">✓ Image captured successfully</span>';
        
        // Automatically verify the image
        await verifyImage();
        
    } catch (error) {
        console.error('Auto-capture error:', error);
        statusDiv.innerHTML = `<span class="text-danger">✗ Auto-capture failed: ${error.message}</span>`;
        captureBtn.disabled = false;
        captureBtn.innerHTML = '<i class="bi bi-camera-fill"></i> Capture from Pi Camera';
    }
}

async function verifyImage() {
    if (!currentCapturedImage || !currentStudentData) return;
    
    const resultContainer = document.getElementById('resultContainer');
    resultContainer.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div>';
    
    try {
        const response = await fetch('/api/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                tag_id: currentStudentData.tag_id,
                image: currentCapturedImage
            })
        });
        
        const data = await response.json();
        
        if (data.match) {
            const scoreClass = data.score > 0.05 ? 'match-score-high' : 'match-score-low';
            resultContainer.innerHTML = `
                <div class="result-message result-success">
                    <i class="bi bi-check-circle"></i> MATCH DETECTED
                </div>
                <p><strong>Student:</strong> ${data.student.name}</p>
                <p><strong>ID:</strong> ${data.student.student_id}</p>
                <p><strong>Match Score:</strong> <span class="${scoreClass}">${(data.score * 100).toFixed(2)}%</span></p>
            `;
            document.getElementById('confirmBtn').style.display = 'block';
            document.getElementById('retryBtn').style.display = 'block';
        } else {
            resultContainer.innerHTML = `
                <div class="result-message result-error">
                    <i class="bi bi-x-circle"></i> NO MATCH
                </div>
                <p>Match Score: <span class="match-score-low">${(data.score * 100).toFixed(2)}%</span></p>
                <p class="text-muted">Try again with better lighting or different angle</p>
            `;
            document.getElementById('retryBtn').style.display = 'block';
            document.getElementById('confirmBtn').style.display = 'none';
        }
    } catch (error) {
        showResult('Verification error: ' + error.message, 'error');
    }
}

async function confirmAttendance() {
    if (!currentStudentData) return;
    
    try {
        const response = await fetch('/api/confirm-attendance', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tag_id: currentStudentData.tag_id, score: 0.012 })
        });
        
        const data = await response.json();
        showResult('Attendance marked successfully!', 'success');
        resetVerification();
        loadAttendance();
        
        setTimeout(() => {
            document.getElementById('tagInput').focus();
        }, 2000);
    } catch (error) {
        showResult('Error marking attendance: ' + error.message, 'error');
    }
}

function resetVerification() {
    currentCapturedImage = null;
    currentStudentData = null;
    document.getElementById('liveImage').style.display = 'none';
    document.getElementById('livePlaceholder').style.display = 'block';
    document.getElementById('resultContainer').innerHTML = '<p class="text-muted">Waiting for verification...</p>';
    document.getElementById('confirmBtn').style.display = 'none';
    document.getElementById('retryBtn').style.display = 'none';
    document.getElementById('tagInput').value = '';
    document.getElementById('tagInput').focus();
}

function showResult(message, type) {
    const resultContainer = document.getElementById('resultContainer');
    const className = type === 'success' ? 'result-success' : 'result-error';
    resultContainer.innerHTML = `<div class="result-message ${className}">${message}</div>`;
}

async function loadStudents() {
    try {
        const response = await fetch('/api/students');
        const students = await response.json();
        
        let html = '<table class="table table-striped"><thead><tr><th>ID</th><th>Name</th><th>Tag</th><th>Photo</th></tr></thead><tbody>';
        
        for (const student of students) {
            html += `
                <tr>
                    <td>${student.student_id}</td>
                    <td>${student.name}</td>
                    <td><code>${student.tag_id}</code></td>
                    <td><img src="/api/student/${student.student_id}/image" alt="${student.name}" style="width: 50px; height: 50px; border-radius: 4px; object-fit: cover;"></td>
                </tr>
            `;
        }
        
        html += '</tbody></table>';
        document.getElementById('studentsList').innerHTML = html;
    } catch (error) {
        document.getElementById('studentsList').innerHTML = `<div class="alert alert-danger">Error loading students: ${error.message}</div>`;
    }
}

async function handleAddStudent(e) {
    e.preventDefault();
    
    const tagId = document.getElementById('newTagId').value;
    const studentId = document.getElementById('newStudentId').value;
    const name = document.getElementById('newStudentName').value;
    const imageFile = document.getElementById('newStudentImage').files[0];
    
    if (!imageFile) {
        alert('Please select an image');
        return;
    }
    
    const reader = new FileReader();
    reader.onload = async function(event) {
        try {
            const response = await fetch('/api/students', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tag_id: tagId,
                    student_id: studentId,
                    name: name,
                    image: event.target.result
                })
            });
            
            if (response.ok) {
                alert('Student added successfully!');
                document.getElementById('addStudentForm').reset();
                loadStudents();
            } else {
                alert('Error adding student');
            }
        } catch (error) {
            alert('Error: ' + error.message);
        }
    };
    reader.readAsDataURL(imageFile);
}

async function loadAttendance() {
    try {
        const response = await fetch('/api/attendance');
        const logs = await response.json();
        
        let html = '<table class="table table-striped"><thead><tr><th>Student</th><th>Time</th><th>Status</th><th>Notes</th></tr></thead><tbody>';
        
        for (const log of logs) {
            const time = new Date(log.timestamp).toLocaleString();
            const statusBadge = log.status === 'present' ? '<span class="badge bg-success">Present</span>' : '<span class="badge bg-warning">Absent</span>';
            html += `
                <tr>
                    <td><strong>${log.name}</strong><br><small class="text-muted">${log.student_id}</small></td>
                    <td>${time}</td>
                    <td>${statusBadge}</td>
                    <td><small>${log.notes || '-'}</small></td>
                </tr>
            `;
        }
        
        html += '</tbody></table>';
        document.getElementById('attendanceList').innerHTML = html;
    } catch (error) {
        document.getElementById('attendanceList').innerHTML = `<div class="alert alert-danger">Error loading attendance: ${error.message}</div>`;
    }
}

// Refresh attendance log every 10 seconds
setInterval(loadAttendance, 10000);
