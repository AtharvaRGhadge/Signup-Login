/* ---------- Utility helpers ---------- */
function showNotification(message, type = 'success') {
    const existing = document.querySelectorAll('.notification');
    existing.forEach(n => n.remove());

    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    const icon = (type === 'success') ? '✅' : '❌';
    notification.innerHTML = `${icon} ${message}`;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease-in';
        setTimeout(() => {
            if (notification.parentNode) notification.remove();
        }, 300);
    }, 4000);
}

/* ---------- Modal logic ---------- */
const editModal = document.getElementById('editModal');
const editForm = document.getElementById('editForm');
const editComplaintIdInput = document.getElementById('editComplaintId');
const editEmailInput = document.getElementById('editEmail');
const editComplaintInput = document.getElementById('editComplaint');
const editSubmitBtn = document.getElementById('editSubmitBtn');
const editCancelBtn = document.getElementById('editCancelBtn');
const editModalClose = document.getElementById('editModalClose');

function openEditModal(id, email, complaintText) {
    editComplaintIdInput.value = id;
    editEmailInput.value = email || '';
    editComplaintInput.value = complaintText || '';
    editModal.style.display = 'block';
    editModal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    editComplaintInput.focus();
}

function closeEditModal() {
    editModal.style.display = 'none';
    editModal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = 'auto';
}

editCancelBtn.addEventListener('click', closeEditModal);
editModalClose.addEventListener('click', closeEditModal);

// Close modal when clicking outside
window.addEventListener('click', function(event) {
    if (event.target === editModal) closeEditModal();
});

// Close modal with Escape
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') closeEditModal();
});

/* ---------- Delegated event handling for action buttons ---------- */

// Use event delegation on the table container to handle dynamically updated rows
document.addEventListener('click', function (e) {
    const toggleBtn = e.target.closest('.toggle-status');
    if (toggleBtn) {
        handleToggleStatus(toggleBtn);
        return;
    }

    const editBtn = e.target.closest('.edit-btn');
    if (editBtn) {
        const id = editBtn.dataset.id;
        const email = editBtn.dataset.email;
        // dataset properties are HTML-escaped; read value directly
        const complaint = editBtn.dataset.complaint || editBtn.getAttribute('data-complaint') || '';
        openEditModal(id, email, complaint);
        return;
    }

    const delBtn = e.target.closest('.delete-btn');
    if (delBtn) {
        handleDelete(delBtn);
        return;
    }
});

/* ---------- Toggle status (admin only) ---------- */
function handleToggleStatus(button) {
    const complaintId = button.dataset.id;
    const currentlyResolved = (button.dataset.resolved === 'true');
    const newStatus = currentlyResolved ? 'pending' : 'resolved';
    const actionText = currentlyResolved ? 'reopened' : 'resolved';

    const originalHTML = button.innerHTML;
    button.innerHTML = '⏳ Processing...';
    button.disabled = true;

    fetch('/toggle_complaint_status', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ complaint_id: complaintId, status: newStatus })
    })
    .then(resp => resp.json())
    .then(data => {
        if (data.success) {
            // update UI
            updateStatusInTable(complaintId, newStatus);
            showNotification(`Complaint ${actionText} successfully!`, 'success');
        } else {
            showNotification('Error updating status: ' + (data.message || 'Unknown error'), 'error');
            button.innerHTML = originalHTML;
            button.disabled = false;
        }
    })
    .catch(err => {
        console.error(err);
        showNotification('Network error. Please try again.', 'error');
        button.innerHTML = originalHTML;
        button.disabled = false;
    });
}

/* ---------- Delete complaint ---------- */
function handleDelete(button) {
    const complaintId = button.dataset.id;
    if (!confirm('⚠️ Are you sure you want to delete this complaint?\n\nThis action cannot be undone and will permanently remove the complaint from the system.')) {
        return;
    }

    const originalHTML = button.innerHTML;
    button.innerHTML = '⏳ Deleting...';
    button.disabled = true;

    fetch('/delete_complaint', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ complaint_id: complaintId })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            removeTableRow(complaintId);
            showNotification('Complaint deleted successfully!', 'success');
        } else {
            showNotification('Error deleting complaint: ' + (data.message || 'Unknown error'), 'error');
            button.innerHTML = originalHTML;
            button.disabled = false;
        }
    })
    .catch(err => {
        console.error(err);
        showNotification('Network error. Please check your connection and try again.', 'error');
        button.innerHTML = originalHTML;
        button.disabled = false;
    });
}

/* ---------- Edit form submit (modal) ---------- */
editSubmitBtn.addEventListener('click', function () {
    const complaintId = editComplaintIdInput.value;
    const updatedComplaint = editComplaintInput.value.trim();

    if (!updatedComplaint) {
        showNotification('Please enter a complaint description.', 'error');
        editComplaintInput.focus();
        return;
    }
    if (updatedComplaint.length < 10) {
        showNotification('Complaint description must be at least 10 characters long.', 'error');
        editComplaintInput.focus();
        return;
    }

    const originalHTML = editSubmitBtn.innerHTML;
    editSubmitBtn.innerHTML = '⏳ Updating...';
    editSubmitBtn.disabled = true;

    fetch('/update_complaint', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ complaint_id: complaintId, complaint: updatedComplaint })
    })
    .then(resp => {
        if (!resp.ok) throw new Error('Network response was not ok. status: ' + resp.status);
        return resp.json();
    })
    .then(data => {
        if (data.success) {
            updateTableRow(complaintId, updatedComplaint);
            closeEditModal();
            showNotification('Complaint updated successfully!', 'success');
        } else {
            showNotification('Error updating complaint: ' + (data.message || 'Unknown error'), 'error');
        }
    })
    .catch(err => {
        console.error(err);
        showNotification('Network error. Please check your connection and try again.', 'error');
    })
    .finally(() => {
        editSubmitBtn.innerHTML = originalHTML;
        editSubmitBtn.disabled = false;
    });
});

/* ---------- Helpers to update DOM rows ---------- */

function updateStatusInTable(complaintId, newStatus) {
    const row = document.querySelector(`tr[data-id="${complaintId}"]`);
    if (!row) return;
    const statusCell = row.cells[2];
    const actionCell = row.cells[3];

    if (newStatus === 'resolved') {
        statusCell.innerHTML = '<span class="status-badge status-resolved"><span class="resolved-tick">✓</span> Resolved</span>';
        // Update toggle button if present
        const toggleBtn = actionCell.querySelector('.toggle-status');
        if (toggleBtn) {
            toggleBtn.className = 'btn btn-secondary btn-sm toggle-status';
            toggleBtn.dataset.resolved = 'true';
            toggleBtn.title = 'Reopen Issue';
            toggleBtn.innerHTML = '🔄 Reopen';
            toggleBtn.disabled = false;
        }
    } else {
        statusCell.innerHTML = '<span class="status-badge status-pending">Pending</span>';
        const toggleBtn = actionCell.querySelector('.toggle-status');
        if (toggleBtn) {
            toggleBtn.className = 'btn btn-success btn-sm toggle-status';
            toggleBtn.dataset.resolved = 'false';
            toggleBtn.title = 'Mark as Resolved';
            toggleBtn.innerHTML = '✅ Resolve';
            toggleBtn.disabled = false;
        }
    }
}

function updateTableRow(complaintId, newComplaintText) {
    const row = document.querySelector(`tr[data-id="${complaintId}"]`);
    if (!row) return;
    const complaintCell = row.cells[1];
    complaintCell.textContent = newComplaintText;

    // Update the edit button's dataset so future edits use the new text
    const editBtn = row.querySelector('.edit-btn');
    if (editBtn) {
        editBtn.dataset.complaint = newComplaintText;
        // also update the displayed text attribute if needed
        editBtn.setAttribute('data-complaint', newComplaintText);
    }
}

function removeTableRow(complaintId) {
    const row = document.querySelector(`tr[data-id="${complaintId}"]`);
    if (!row) return;

    row.style.transition = 'opacity 0.3s ease-out';
    row.style.opacity = '0';
    setTimeout(() => {
        const tbody = row.parentElement;
        row.remove();

        // If tbody empty, show "No complaints" message row
        if (!tbody || tbody.children.length === 0) {
            const table = document.querySelector('.complaints-table');
            if (table) {
                const tBody = table.querySelector('tbody');
                tBody.innerHTML = `
                    <tr>
                        <td colspan="4" class="no-complaints" style="text-align:center; padding:60px 20px;">
                            <div class="emoji">📋</div>
                            <div>No complaints found.</div>
                        </td>
                    </tr>
                `;
            }
        }
    }, 300);
}

/* ---------- Form validation for other forms on page ---------- */
document.addEventListener('DOMContentLoaded', function () {
    // Add basic required textareas validation for HTML forms that submit normally
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function (e) {
            // If this is the editForm we handle it separately
            if (form.id === 'editForm') {
                e.preventDefault();
                return;
            }
            const textareas = form.querySelectorAll('textarea[required]');
            for (const ta of textareas) {
                if (ta.value.trim() === '') {
                    e.preventDefault();
                    ta.focus();
                    showNotification('Please fill in all required fields.', 'error');
                    break;
                }
            }
        });
    });

    // Auto-resize textareas
    const textareas = document.querySelectorAll('textarea');
    textareas.forEach(textarea => {
        textarea.addEventListener('input', function () {
            this.style.height = 'auto';
            this.style.height = this.scrollHeight + 'px';
        });
        // trigger initially in case browser prefilled
        textarea.style.height = 'auto';
        textarea.style.height = textarea.scrollHeight + 'px';
    });
});
