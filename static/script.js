let tasks = [];
let currentFilter = {
    search: '',
    priority: 'all',
    status: 'all',
    category: 'all',
    sortBy: 'priority'
};

// ---------------- INITIALIZATION ----------------
async function init() {
    await fetchTasks();
    await loadStats();
    setupEventListeners();
}

function setupEventListeners() {
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            currentFilter.search = e.target.value.toLowerCase();
            filterAndDisplayTasks();
        });
    }
    
    const filterPriority = document.getElementById('filterPriority');
    if (filterPriority) {
        filterPriority.addEventListener('change', (e) => {
            currentFilter.priority = e.target.value;
            filterAndDisplayTasks();
        });
    }
    
    const filterStatus = document.getElementById('filterStatus');
    if (filterStatus) {
        filterStatus.addEventListener('change', (e) => {
            currentFilter.status = e.target.value;
            filterAndDisplayTasks();
        });
    }
    
    const filterCategory = document.getElementById('filterCategory');
    if (filterCategory) {
        filterCategory.addEventListener('change', (e) => {
            currentFilter.category = e.target.value;
            filterAndDisplayTasks();
        });
    }
    
    const sortBy = document.getElementById('sortBy');
    if (sortBy) {
        sortBy.addEventListener('change', (e) => {
            currentFilter.sortBy = e.target.value;
            filterAndDisplayTasks();
        });
    }
}

// ---------------- FETCH TASKS ----------------
async function fetchTasks() {
    try {
        let res = await fetch("/get-tasks", {
            credentials: 'same-origin'
        });
        tasks = await res.json();
        filterAndDisplayTasks();
    } catch (error) {
        console.error("Error fetching tasks:", error);
    }
}

// ---------------- FILTER AND DISPLAY ----------------
function filterAndDisplayTasks() {
    let filtered = tasks.filter(task => {
        if (currentFilter.search && !task.title.toLowerCase().includes(currentFilter.search)) {
            return false;
        }
        if (currentFilter.priority !== 'all' && task.priority !== currentFilter.priority) {
            return false;
        }
        if (currentFilter.status !== 'all' && task.status !== currentFilter.status) {
            return false;
        }
        if (currentFilter.category !== 'all' && task.category !== currentFilter.category) {
            return false;
        }
        return true;
    });
    
    filtered.sort((a, b) => {
        if (currentFilter.sortBy === 'priority') {
            const priorityOrder = { 'High': 1, 'Medium': 2, 'Low': 3 };
            return (priorityOrder[a.priority] || 2) - (priorityOrder[b.priority] || 2);
        } else if (currentFilter.sortBy === 'dueDate') {
            return (a.due_date || '9999-12-31').localeCompare(b.due_date || '9999-12-31');
        }
        return 0;
    });
    
    displayTasks(filtered);
}

// ---------------- ADD TASK ----------------
async function addTask() {
    let title = document.getElementById("taskInput").value;
    let description = document.getElementById("taskDesc").value;
    let priority = document.getElementById("prioritySelect").value;
    let dueDate = document.getElementById("dueDateInput").value;
    let category = document.getElementById("categorySelect").value;

    if(title === ""){
        alert("Please enter task title");
        return;
    }

    try {
        await fetch("/add-task", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                title: title,
                description: description,
                priority: priority,
                due_date: dueDate,
                category: category
            }),
            credentials: 'same-origin'
        });

        document.getElementById("taskInput").value = "";
        document.getElementById("taskDesc").value = "";
        document.getElementById("dueDateInput").value = "";
        closeModal();
        await fetchTasks();
        await loadStats();
        alert("Task added successfully!");
    } catch (error) {
        console.error("Error adding task:", error);
        alert("Error adding task");
    }
}

// ---------------- EDIT TASK ----------------
function editTask(id, title, description, priority, dueDate, category) {
    document.getElementById("editTaskId").value = id;
    document.getElementById("editTitle").value = title;
    document.getElementById("editDesc").value = description || "";
    document.getElementById("editPriority").value = priority;
    document.getElementById("editDueDate").value = dueDate || "";
    document.getElementById("editCategory").value = category;
    document.getElementById("editModal").style.display = "flex";
}

async function updateTask() {
    let id = document.getElementById("editTaskId").value;
    let title = document.getElementById("editTitle").value;
    let description = document.getElementById("editDesc").value;
    let priority = document.getElementById("editPriority").value;
    let dueDate = document.getElementById("editDueDate").value;
    let category = document.getElementById("editCategory").value;

    try {
        await fetch(`/edit-task/${id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                title: title,
                description: description,
                priority: priority,
                due_date: dueDate,
                category: category
            }),
            credentials: 'same-origin'
        });

        closeEditModal();
        await fetchTasks();
        await loadStats();
        alert("Task updated successfully!");
    } catch (error) {
        console.error("Error updating task:", error);
        alert("Error updating task");
    }
}

// ---------------- DELETE TASK ----------------
async function deleteTask(id) {
    if(confirm("Are you sure you want to delete this task?")) {
        try {
            await fetch(`/delete-task/${id}`, {
                method: "DELETE",
                credentials: 'same-origin'
            });
            await fetchTasks();
            await loadStats();
            alert("Task deleted!");
        } catch (error) {
            console.error("Error deleting task:", error);
            alert("Error deleting task");
        }
    }
}

// ---------------- TOGGLE STATUS ----------------
async function toggleStatus(id, currentStatus) {
    let newStatus = currentStatus === "Completed" ? "To Do" : "Completed";
    
    try {
        await fetch(`/update-task/${id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: newStatus }),
            credentials: 'same-origin'
        });
        
        await fetchTasks();
        await loadStats();
        alert(`Task marked as ${newStatus}!`);
    } catch (error) {
        console.error("Error toggling status:", error);
        alert("Error updating status");
    }
}

// ---------------- DISPLAY TASKS ----------------
function displayTasks(filteredTasks) {
    let tbody = document.getElementById("tasksBody");
    if (!tbody) return;
    
    tbody.innerHTML = "";
    
    let completed = 0;
    let progress = 0;
    
    filteredTasks.forEach(task => {
        if(task.status === "Completed") {
            completed++;
        } else {
            progress++;
        }
        
        let priorityDisplay = {
            'High': '🔴 High',
            'Medium': '🟡 Medium',
            'Low': '🟢 Low'
        }[task.priority] || '🟡 Medium';
        
        let dueDateClass = '';
        let dueDateDisplay = task.due_date || 'No due date';
        if(task.due_date && task.status !== 'Completed') {
            let today = new Date().toISOString().split('T')[0];
            if(task.due_date < today) dueDateClass = 'overdue';
            else if(task.due_date === today) dueDateClass = 'due-today';
        }
        
        let categoryEmoji = {
            'Work': '💼',
            'Personal': '🏠',
            'Shopping': '🛒',
            'Health': '💪',
            'Education': '📚'
        }[task.category] || '📁';
        
        tbody.innerHTML += `
        <tr class="${task.status === 'Completed' ? 'completed-row' : ''}">
            <td>
                <div class="task-title"><strong>${escapeHtml(task.title)}</strong></div>
                ${task.description ? `<div class="task-desc"><small>${escapeHtml(task.description)}</small></div>` : ''}
            </td>
            <td><span class="priority-badge ${task.priority ? task.priority.toLowerCase() : 'medium'}">${priorityDisplay}</span></td>
            <td><span class="due-date ${dueDateClass}">📅 ${escapeHtml(dueDateDisplay)}</span></td>
            <td><span class="category-badge">${categoryEmoji} ${escapeHtml(task.category || 'Personal')}</span></td>
            <td>
                <span class="status ${task.status === 'Completed' ? 'completed' : 'todo'}">
                    ${task.status === 'Completed' ? '✓ Completed' : '○ To Do'}
                </span>
            </td>
            <td class="actions">
                <button class="toggle" onclick="toggleStatus(${task.id}, '${task.status}')" title="Toggle Status">🔄</button>
                <button class="edit" onclick="editTask(${task.id}, '${escapeHtml(task.title)}', '${escapeHtml(task.description || '')}', '${task.priority}', '${task.due_date || ''}', '${task.category}')" title="Edit Task">✏️</button>
                <button class="delete" onclick="deleteTask(${task.id})" title="Delete Task">🗑️</button>
            </td>
        </tr>
        `;
    });
    
    document.getElementById("total").innerText = tasks.length;
    document.getElementById("completed").innerText = completed;
    document.getElementById("progress").innerText = progress;
}

// ---------------- LOAD STATISTICS ----------------
async function loadStats() {
    try {
        let res = await fetch("/get-stats", { credentials: 'same-origin' });
        let stats = await res.json();
        
        document.getElementById("dueToday").innerText = stats.due_today || 0;
        document.getElementById("completionRate").innerText = `${stats.completion_rate || 0}%`;
        document.getElementById("progressFill").style.width = `${stats.completion_rate || 0}%`;
    } catch (error) {
        console.error("Error loading stats:", error);
    }
}

// ---------------- EXPORT FUNCTIONS ----------------
function exportTodayTasks() {
    window.location.href = "/export-today-tasks";
    closeExportModal();
}

function exportAllTasks() {
    window.location.href = "/export-all-tasks";
    closeExportModal();
}

// ---------------- MODAL FUNCTIONS ----------------
function openModal() {
    document.getElementById("taskModal").style.display = "flex";
}

function closeModal() {
    document.getElementById("taskModal").style.display = "none";
}

function closeEditModal() {
    document.getElementById("editModal").style.display = "none";
}

function showExportModal() {
    document.getElementById("exportModal").style.display = "flex";
}

function closeExportModal() {
    document.getElementById("exportModal").style.display = "none";
}

async function showStats() {
    try {
        let res = await fetch("/get-stats", { credentials: 'same-origin' });
        let stats = await res.json();
        
        document.getElementById("statsContent").innerHTML = `
            <div class="stats-grid">
                <div class="stat-item">
                    <div style="font-size: 48px;">📊</div>
                    <h3>${stats.total}</h3>
                    <p>Total Tasks</p>
                </div>
                <div class="stat-item">
                    <div style="font-size: 48px;">✅</div>
                    <h3>${stats.completed}</h3>
                    <p>Completed</p>
                </div>
                <div class="stat-item">
                    <div style="font-size: 48px;">📈</div>
                    <h3>${stats.completion_rate}%</h3>
                    <p>Completion Rate</p>
                </div>
                <div class="stat-item">
                    <div style="font-size: 48px;">📅</div>
                    <h3>${stats.due_today}</h3>
                    <p>Due Today</p>
                </div>
            </div>
            <div class="priority-stats">
                <h3>Priority Breakdown</h3>
                <div>🔴 High: ${stats.priority_stats?.High || 0}</div>
                <div>🟡 Medium: ${stats.priority_stats?.Medium || 0}</div>
                <div>🟢 Low: ${stats.priority_stats?.Low || 0}</div>
            </div>
        `;
        document.getElementById("statsModal").style.display = "flex";
    } catch (error) {
        console.error("Error showing stats:", error);
    }
}

function closeStatsModal() {
    document.getElementById("statsModal").style.display = "none";
}

async function showActivity() {
    try {
        let res = await fetch("/get-activity", { credentials: 'same-origin' });
        let activities = await res.json();
        
        document.getElementById("activityContent").innerHTML = `
            <div class="activity-list">
                ${activities.map(activity => `
                    <div class="activity-item">
                        <div class="activity-icon">📝</div>
                        <div class="activity-details">
                            <div class="activity-action"><strong>${activity.action.replace('_', ' ').toUpperCase()}</strong></div>
                            <div class="activity-info">${escapeHtml(activity.details || '')}</div>
                            <div class="activity-time"><small>${new Date(activity.timestamp).toLocaleString()}</small></div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
        document.getElementById("activityModal").style.display = "flex";
    } catch (error) {
        console.error("Error showing activity:", error);
    }
}

function closeActivityModal() {
    document.getElementById("activityModal").style.display = "none";
}

// ---------------- HELPER FUNCTIONS ----------------
function escapeHtml(text) {
    if (!text) return '';
    let div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ---------------- INITIALIZE ----------------
document.addEventListener('DOMContentLoaded', () => {
    init();
});