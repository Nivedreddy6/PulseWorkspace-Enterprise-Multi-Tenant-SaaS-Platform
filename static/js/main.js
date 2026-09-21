// PulseWorkspace UI Interactivity

document.addEventListener('DOMContentLoaded', () => {
  // Workspace dropdown toggle
  const wsBtn = document.getElementById('workspaceSelectBtn');
  const wsMenu = document.getElementById('workspaceDropdownMenu');

  if (wsBtn && wsMenu) {
    wsBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      wsMenu.classList.toggle('show');
    });

    document.addEventListener('click', () => {
      wsMenu.classList.remove('show');
    });
  }

  // Modal handlers
  document.querySelectorAll('[data-open-modal]').forEach(trigger => {
    trigger.addEventListener('click', (e) => {
      e.preventDefault();
      const targetId = trigger.getAttribute('data-open-modal');
      const modal = document.getElementById(targetId);
      if (modal) modal.classList.add('show');
    });
  });

  document.querySelectorAll('[data-close-modal]').forEach(trigger => {
    trigger.addEventListener('click', () => {
      const modal = trigger.closest('.modal-overlay');
      if (modal) modal.classList.remove('show');
    });
  });

  // Close modal when clicking outside modal content
  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        overlay.classList.remove('show');
      }
    });
  });

  // Kanban Drag and Drop
  const taskCards = document.querySelectorAll('.task-card');
  const columns = document.querySelectorAll('.kanban-column');

  let draggedCard = null;

  taskCards.forEach(card => {
    card.setAttribute('draggable', 'true');

    card.addEventListener('dragstart', (e) => {
      draggedCard = card;
      card.style.opacity = '0.5';
      e.dataTransfer.setData('text/plain', card.getAttribute('data-task-id'));
    });

    card.addEventListener('dragend', () => {
      if (draggedCard) {
        draggedCard.style.opacity = '1';
      }
      draggedCard = null;
    });
  });

  columns.forEach(col => {
    col.addEventListener('dragover', (e) => {
      e.preventDefault();
      col.style.borderColor = 'var(--accent-primary)';
    });

    col.addEventListener('dragleave', () => {
      col.style.borderColor = 'var(--border-subtle)';
    });

    col.addEventListener('drop', (e) => {
      e.preventDefault();
      col.style.borderColor = 'var(--border-subtle)';
      const targetStatus = col.getAttribute('data-column-status');
      const taskId = e.dataTransfer.getData('text/plain');

      if (taskId && draggedCard && targetStatus) {
        const wrapper = col.querySelector('.kanban-cards-wrapper');
        wrapper.appendChild(draggedCard);

        // Send AJAX update to backend
        const csrfToken = getCookie('csrftoken');
        const formData = new FormData();
        formData.append('status', targetStatus);

        fetch(`/kanban/update-status/${taskId}/`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrfToken,
          },
          body: formData,
        })
        .then(res => res.json())
        .then(data => {
          if (!data.success) {
            console.error('Failed to update status:', data.error);
          }
        })
        .catch(err => console.error('Status sync error:', err));
      }
    });
  });
});

// Helper to retrieve CSRF token
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}
