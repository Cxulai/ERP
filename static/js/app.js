/* ========================================
   ERP System - App Core (Router, Nav, API, Toast)
   ======================================== */

// -- Navigation --
const pageTitle = document.getElementById('page-title');
const contentArea = document.getElementById('content-area');
const navItems = document.querySelectorAll('.nav-item');

const PAGE_TITLES = {
    dashboard: '仪表盘',
    products: '商品管理',
    inventory: '库存流水',
    customers: '客户管理',
    suppliers: '供应商管理',
    sales: '销售订单',
    purchases: '采购订单',
    reports: '财务报表'
};

function navigateTo(page) {
    navItems.forEach(n => n.classList.remove('active'));
    const nav = document.querySelector(`[data-page="${page}"]`);
    if (nav) nav.classList.add('active');
    pageTitle.textContent = PAGE_TITLES[page] || page;
    window.location.hash = page;
    renderPage(page);
}

function renderPage(page) {
    contentArea.innerHTML = '<div class="empty-state"><div class="empty-icon">⏳</div><p>加载中...</p></div>';
    switch (page) {
        case 'dashboard': renderDashboard(); break;
        case 'products': renderProducts(); break;
        case 'inventory': renderInventory(); break;
        case 'customers': renderCustomers(); break;
        case 'suppliers': renderSuppliers(); break;
        case 'sales': renderSalesList(); break;
        case 'purchases': renderPurchasesList(); break;
        case 'reports': renderReports(); break;
        default: renderDashboard();
    }
}

navItems.forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        navigateTo(item.dataset.page);
    });
});

window.addEventListener('hashchange', () => {
    const page = window.location.hash.replace('#', '') || 'dashboard';
    navigateTo(page);
});

// -- API Helpers --
async function api(url, options = {}) {
    try {
        const res = await fetch(url, {
            headers: { 'Content-Type': 'application/json' },
            ...options
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.error || `HTTP ${res.status}`);
        }
        return await res.json();
    } catch (e) {
        showToast(e.message, 'error');
        throw e;
    }
}

// -- Toast --
let toastTimer;
function showToast(msg, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = msg;
    toast.className = `toast toast-${type} show`;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { toast.classList.remove('show'); }, 3000);
}

// -- Modal --
let modalCallback = null;

function openModal(title, bodyHtml, footerHtml, onSubmit) {
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-body').innerHTML = bodyHtml;
    document.getElementById('modal-footer').innerHTML = footerHtml || `
        <button class="btn btn-secondary" onclick="closeModal()">取消</button>
        <button class="btn btn-primary" id="modal-submit">保存</button>
    `;
    document.getElementById('modal-overlay').classList.add('active');
    modalCallback = onSubmit;
    const submitBtn = document.getElementById('modal-submit');
    if (submitBtn) {
        submitBtn.onclick = async () => {
            if (modalCallback) {
                try { await modalCallback(); } catch (e) { /* handled */ }
            }
        };
    }
}

function closeModal() {
    document.getElementById('modal-overlay').classList.remove('active');
    modalCallback = null;
}

document.getElementById('modal-overlay').addEventListener('click', (e) => {
    if (e.target === document.getElementById('modal-overlay')) closeModal();
});

// -- Formatting --
function formatMoney(val) {
    return '¥' + Number(val || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatDate(d) {
    if (!d) return '-';
    const parts = d.split('-');
    if (parts.length === 3) return `${parts[0]}-${parts[1]}-${parts[2]}`;
    return d;
}

function statusBadge(status) {
    const labels = {
        draft: '草稿', confirmed: '已确认', shipped: '已发货', received: '已收货',
        completed: '已完成', cancelled: '已取消'
    };
    return `<span class="badge badge-${status}">${labels[status] || status}</span>`;
}

// -- Clock --
function updateClock() {
    const now = new Date();
    const str = now.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' });
    document.getElementById('current-time').textContent = str;
}
setInterval(updateClock, 1000);
updateClock();

// -- Init --
(function init() {
    const page = window.location.hash.replace('#', '') || 'dashboard';
    navigateTo(page);
})();
