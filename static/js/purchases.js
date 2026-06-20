/* ========================================
   Purchase Orders
   ======================================== */

const PURCHASE_STATUS_FILTERS = [
    { value: '', label: '全部' },
    { value: 'draft', label: '草稿' },
    { value: 'confirmed', label: '已确认' },
    { value: 'received', label: '已收货' },
    { value: 'completed', label: '已完成' },
    { value: 'cancelled', label: '已取消' }
];

async function renderPurchasesList() {
    try {
        const orders = await api('/api/purchase-orders');
        contentArea.innerHTML = `
            <div class="toolbar">
                <div class="toolbar-left">
                    <input type="text" class="search-input" id="purchase-search" placeholder="🔍 搜索订单号/供应商..." oninput="searchPurchases()">
                    <select class="form-control" id="purchase-status-filter" onchange="searchPurchases()" style="width:130px">
                        ${PURCHASE_STATUS_FILTERS.map(f => `<option value="${f.value}">${f.label}</option>`).join('')}
                    </select>
                </div>
                <div class="toolbar-right">
                    <button class="btn btn-primary" onclick="showPurchaseForm()">+ 新建采购订单</button>
                </div>
            </div>
            <div class="card">
                <div class="card-body no-padding">
                    <div class="table-wrap">
                        <table>
                            <thead><tr><th>订单号</th><th>供应商</th><th>日期</th><th>金额</th><th>已付</th><th>状态</th><th>操作</th></tr></thead>
                            <tbody id="purchase-tbody">${renderPurchaseOrderRows(orders)}</tbody>
                        </table>
                    </div>
                </div>
            </div>`;
    } catch (e) {
        contentArea.innerHTML = `<div class="alert alert-danger">加载失败: ${e.message}</div>`;
    }
}

function renderPurchaseOrderRows(orders) {
    if (!orders.length) return '<tr><td colspan="7" class="text-center text-muted">暂无数据</td></tr>';
    return orders.map(o => `
        <tr>
            <td class="font-bold">${o.order_no}</td>
            <td>${o.supplier_name}</td>
            <td>${formatDate(o.order_date)}</td>
            <td>${formatMoney(o.total_amount)}</td>
            <td>${formatMoney(o.paid_amount)}</td>
            <td>${statusBadge(o.status)}</td>
            <td>
                ${o.status === 'draft' ? `<button class="btn btn-xs btn-success" onclick="changePurchaseStatus(${o.id},'confirm')">确认</button>` : ''}
                ${o.status === 'confirmed' ? `<button class="btn btn-xs btn-warning" onclick="changePurchaseStatus(${o.id},'receive')">收货</button>` : ''}
                ${o.status === 'received' ? `<button class="btn btn-xs btn-primary" onclick="changePurchaseStatus(${o.id},'complete')">完成</button>` : ''}
                ${o.status === 'draft' || o.status === 'confirmed' ? `<button class="btn btn-xs btn-danger" onclick="changePurchaseStatus(${o.id},'cancel')">取消</button>` : ''}
                ${o.status === 'draft' ? `<button class="btn btn-xs btn-secondary" onclick="showPurchaseForm(${o.id})">编辑</button>` : ''}
                ${o.status === 'draft' || o.status === 'cancelled' ? `<button class="btn btn-xs btn-danger" onclick="deletePurchaseOrder(${o.id})">删除</button>` : ''}
            </td>
        </tr>`).join('');
}

async function searchPurchases() {
    const q = document.getElementById('purchase-search').value;
    const status = document.getElementById('purchase-status-filter').value;
    let url = '/api/purchase-orders?';
    if (q) url += `search=${encodeURIComponent(q)}&`;
    if (status) url += `status=${status}&`;
    const orders = await api(url);
    document.getElementById('purchase-tbody').innerHTML = renderPurchaseOrderRows(orders);
}

async function changePurchaseStatus(id, action) {
    const labels = { confirm: '确认', receive: '收货', complete: '完成', cancel: '取消' };
    if (action === 'cancel' && !confirm('确定取消该订单吗？')) return;
    try {
        await api(`/api/purchase-orders/${id}`, {
            method: 'PUT',
            body: JSON.stringify({ action })
        });
        showToast(`${labels[action]}成功`, 'success');
        renderPurchasesList();
    } catch (e) { /* handled */ }
}

async function deletePurchaseOrder(id) {
    if (!confirm('确定删除该订单吗？')) return;
    try {
        await api(`/api/purchase-orders/${id}`, { method: 'DELETE' });
        showToast('删除成功', 'success');
        renderPurchasesList();
    } catch (e) { /* handled */ }
}

async function showPurchaseForm(id) {
    contentArea.innerHTML = '<div class="empty-state"><div class="empty-icon">⏳</div><p>加载中...</p></div>';

    let order = null, items = [];
    if (id) {
        const data = await api(`/api/purchase-orders/${id}`);
        order = data.order;
        items = data.items;
    }

    const [suppliers, products] = await Promise.all([
        api('/api/suppliers'),
        api('/api/products')
    ]);

    const isDraft = !order || order.status === 'draft';

    contentArea.innerHTML = `
        <div class="card mb-16">
            <div class="card-header flex-between">
                <h3>${id ? '编辑采购订单 - ' + order.order_no : '新建采购订单'}</h3>
                <button class="btn btn-secondary" onclick="renderPurchasesList()">← 返回列表</button>
            </div>
            <div class="card-body">
                <div class="form-row">
                    <div class="form-group">
                        <label>供应商 <span class="required">*</span></label>
                        <select class="form-control" id="po-supplier" ${!isDraft ? 'disabled' : ''}>
                            ${suppliers.map(s => `<option value="${s.id}" ${order && order.supplier_id === s.id ? 'selected' : ''}>${s.name}</option>`).join('')}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>订单日期 <span class="required">*</span></label>
                        <input class="form-control" type="date" id="po-date" value="${order ? order.order_date : new Date().toISOString().slice(0,10)}" ${!isDraft ? 'disabled' : ''}>
                    </div>
                </div>
                <div class="form-group">
                    <label>备注</label>
                    <input class="form-control" id="po-notes" value="${order ? order.notes || '' : ''}" ${!isDraft ? 'readonly' : ''}>
                </div>
            </div>
        </div>

        <div class="card mb-16">
            <div class="card-header flex-between">
                <h3>采购明细</h3>
                ${isDraft ? '<button class="btn btn-sm btn-primary" onclick="addPurchaseItem()">+ 添加商品</button>' : ''}
            </div>
            <div class="card-body no-padding">
                <div class="table-wrap">
                    <table class="order-items-table">
                        <thead><tr><th>商品</th><th>数量</th><th>单价</th><th>金额</th>${isDraft ? '<th>操作</th>' : ''}</tr></thead>
                        <tbody id="po-items">${renderPurchaseItems(items, products, isDraft)}</tbody>
                    </table>
                </div>
            </div>
            <div class="card-body">
                <div class="order-summary">合计: <span id="po-total">${formatMoney(order ? order.total_amount : 0)}</span></div>
            </div>
        </div>

        ${isDraft ? `
        <div style="text-align:right">
            <button class="btn btn-secondary" onclick="renderPurchasesList()">取消</button>
            <button class="btn btn-primary" onclick="savePurchaseOrder(${id || 0})" style="margin-left:8px">
                ${id ? '更新订单' : '创建订单'}
            </button>
        </div>` : `
        <div class="alert alert-info">订单已${order.status === 'completed' ? '完成' : order.status === 'cancelled' ? '取消' : order.status === 'received' ? '收货' : '确认'}，无法编辑</div>
        `}
    `;
}

function renderPurchaseItems(items, products, editable) {
    if (!items.length) return `<tr><td colspan="${editable ? 5 : 4}" class="text-center text-muted">暂无明细，请添加商品</td></tr>`;
    return items.map((item, i) => {
        const amount = (item.price || 0) * (item.qty || 0);
        return `
        <tr>
            <td>
                ${editable ? `<select class="form-control" onchange="updatePOItemPrice(${i})" id="po-item-product-${i}">
                    ${products.map(p => `<option value="${p.id}" data-price="${p.purchase_price}" ${item.product_id === p.id ? 'selected' : ''}>${p.name} (${p.code})</option>`).join('')}
                </select>` : (item.product_name || item.product_id)}
            </td>
            <td>${editable ? `<input type="number" value="${item.qty}" min="1" onchange="calcPOTotal()" id="po-item-qty-${i}">` : item.qty}</td>
            <td>${editable ? `<input type="number" value="${item.price}" step="0.01" onchange="calcPOTotal()" id="po-item-price-${i}">` : formatMoney(item.price)}</td>
            <td>${formatMoney(amount)}</td>
            ${editable ? `<td><button class="btn btn-xs btn-danger" onclick="removePurchaseItem(${i})">删除</button></td>` : ''}
        </tr>`;
    }).join('');
}

function updatePOItemPrice(i) {
    const sel = document.getElementById(`po-item-product-${i}`);
    const price = sel.options[sel.selectedIndex].dataset.price;
    document.getElementById(`po-item-price-${i}`).value = price;
    calcPOTotal();
}

function addPurchaseItem() {
    const tbody = document.getElementById('po-items');
    const existingRows = tbody.querySelectorAll('tr').length;
    const idx = existingRows;
    const row = document.createElement('tr');
    row.innerHTML = `
        <td><select class="form-control" id="po-item-product-${idx}" onchange="updatePOItemPrice(${idx})"></select></td>
        <td><input type="number" value="1" min="1" onchange="calcPOTotal()" id="po-item-qty-${idx}"></td>
        <td><input type="number" value="0" step="0.01" onchange="calcPOTotal()" id="po-item-price-${idx}"></td>
        <td id="po-item-amount-${idx}">¥0.00</td>
        <td><button class="btn btn-xs btn-danger" onclick="this.closest('tr').remove();calcPOTotal();">删除</button></td>`;
    tbody.appendChild(row);
    api('/api/products').then(products => {
        const sel = document.getElementById(`po-item-product-${idx}`);
        if (sel) {
            sel.innerHTML = products.map(p => `<option value="${p.id}" data-price="${p.purchase_price}">${p.name} (${p.code})</option>`).join('');
            updatePOItemPrice(idx);
        }
    });
}

function removePurchaseItem(i) {
    const tr = document.querySelector(`#po-items tr:nth-child(${i + 1})`);
    if (tr) tr.remove();
    calcPOTotal();
}

function calcPOTotal() {
    const tbody = document.getElementById('po-items');
    if (!tbody) return;
    let total = 0;
    const rows = tbody.querySelectorAll('tr');
    rows.forEach((row) => {
        const qtyInput = row.querySelector(`[id^="po-item-qty-"]`);
        const priceInput = row.querySelector(`[id^="po-item-price-"]`);
        if (qtyInput && priceInput) {
            const qty = parseInt(qtyInput.value) || 0;
            const price = parseFloat(priceInput.value) || 0;
            total += qty * price;
        }
    });
    const totalEl = document.getElementById('po-total');
    if (totalEl) totalEl.textContent = formatMoney(total);
}

async function savePurchaseOrder(id) {
    const supplier_id = parseInt(document.getElementById('po-supplier').value);
    const order_date = document.getElementById('po-date').value;
    const notes = document.getElementById('po-notes').value;

    if (!supplier_id || !order_date) { showToast('请填写供应商和日期', 'error'); return; }

    const items = [];
    const tbody = document.getElementById('po-items');
    const rows = tbody.querySelectorAll('tr');
    rows.forEach((row) => {
        const productSel = row.querySelector(`[id^="po-item-product-"]`);
        const qtyInput = row.querySelector(`[id^="po-item-qty-"]`);
        const priceInput = row.querySelector(`[id^="po-item-price-"]`);
        if (productSel && qtyInput && priceInput) {
            const product_id = parseInt(productSel.value);
            const qty = parseInt(qtyInput.value) || 0;
            const price = parseFloat(priceInput.value) || 0;
            if (product_id && qty > 0) items.push({ product_id, qty, price });
        }
    });

    if (!items.length) { showToast('请添加至少一个商品', 'error'); return; }

    try {
        if (id) {
            await api(`/api/purchase-orders/${id}`, {
                method: 'PUT',
                body: JSON.stringify({ action: 'update', supplier_id, order_date, notes, items })
            });
        } else {
            await api('/api/purchase-orders', {
                method: 'POST',
                body: JSON.stringify({ supplier_id, order_date, notes, items })
            });
        }
        showToast(id ? '更新成功' : '创建成功', 'success');
        renderPurchasesList();
    } catch (e) { /* handled */ }
}
