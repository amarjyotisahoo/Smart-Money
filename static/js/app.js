/**
 * SmartMoney - Core Client Application JavaScript
 * Handles Theme Toggling, Modals, Toasts, Responsive Sidebar, and Form Actions
 */

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initSidebar();
  initLucide();
  initAutoDismissAlerts();
});

/* ==========================================================================
   Theme Management (Light / Dark)
   ========================================================================== */

function initTheme() {
  const savedTheme = localStorage.getItem('smartmoney_theme') || 
    (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  
  applyTheme(savedTheme);

  const toggleBtns = document.querySelectorAll('.theme-toggle-btn');
  toggleBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme') || 'light';
      const nextTheme = current === 'dark' ? 'light' : 'dark';
      applyTheme(nextTheme);
      localStorage.setItem('smartmoney_theme', nextTheme);
      
      // Notify charts if available
      if (window.updateChartsTheme) {
        window.updateChartsTheme(nextTheme);
      }
    });
  });
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  const themeIcons = document.querySelectorAll('.theme-toggle-btn i, .theme-toggle-btn svg');
  themeIcons.forEach(icon => {
    if (theme === 'dark') {
      icon.setAttribute('data-lucide', 'sun');
    } else {
      icon.setAttribute('data-lucide', 'moon');
    }
  });
  if (window.lucide) {
    lucide.createIcons();
  }
}

/* ==========================================================================
   Responsive Sidebar & Navigation
   ========================================================================== */

function initSidebar() {
  const sidebar = document.getElementById('appSidebar');
  const toggleBtn = document.getElementById('mobileMenuToggle');
  const closeBtn = document.getElementById('sidebarCloseBtn');

  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      sidebar.classList.toggle('open');
    });
  }

  if (closeBtn && sidebar) {
    closeBtn.addEventListener('click', () => {
      sidebar.classList.remove('open');
    });
  }

  // Close on outside click on mobile
  document.addEventListener('click', (e) => {
    if (sidebar && sidebar.classList.contains('open') && !sidebar.contains(e.target) && e.target !== toggleBtn) {
      sidebar.classList.remove('open');
    }
  });
}

function initLucide() {
  if (window.lucide) {
    lucide.createIcons();
  }
}

/* ==========================================================================
   Modal Dialog Utilities
   ========================================================================== */

function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('show');
    document.body.style.overflow = 'hidden';
    initLucide();
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('show');
    document.body.style.overflow = '';
  }
}

// Global modal backdrop close listener
document.addEventListener('click', (e) => {
  if (e.target.classList.contains('modal-backdrop')) {
    e.target.classList.remove('show');
    document.body.style.overflow = '';
  }
});

/* ==========================================================================
   Toast Notification System
   ========================================================================== */

function showToast(message, type = 'info') {
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;

  const iconName = type === 'success' ? 'check-circle' :
                   type === 'danger' ? 'alert-triangle' :
                   type === 'warning' ? 'alert-circle' : 'info';

  toast.innerHTML = `
    <i data-lucide="${iconName}" style="width: 18px; height: 18px;"></i>
    <span>${message}</span>
  `;

  container.appendChild(toast);
  initLucide();

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

function initAutoDismissAlerts() {
  const flashes = document.querySelectorAll('.alert-auto-dismiss');
  flashes.forEach(flash => {
    setTimeout(() => {
      flash.style.opacity = '0';
      setTimeout(() => flash.remove(), 400);
    }, 4500);
  });
}

/* ==========================================================================
   AJAX Form & Request Helpers
   ========================================================================== */

async function postFormJson(url, formData) {
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
  
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'X-CSRFToken': csrfToken
    },
    body: formData
  });

  return await response.json();
}

async function apiPost(url, data = {}) {
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
  const formData = new FormData();
  
  for (const key in data) {
    formData.append(key, data[key]);
  }

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'X-CSRFToken': csrfToken
    },
    body: formData
  });

  return await response.json();
}
