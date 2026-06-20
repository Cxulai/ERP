/* ========================================
   Sales Orders
   ======================================== */

const SALES_STATUS_FILTERS = [
    { value: '', label: '全部' },
    { value: 'draft', label: '草稿' },
    { value: 'confirmed', label: '已确认' },
    { value: 'shipped', label: '已发货' },
    { value: 'completed', label: '已完成' },
    { value: 'cancelled', label: '已取消' }
];

async function renderSalesList() {
    try {
        const orders = await api('/api/sales-orders');
        contentArea.innerHTML = `
            <div class="toolbar">
                <div class="toolbar-left">
                    <input type="text" class="search-input" id="sales-search" placeholder="🔍 搜索订单号/客户..." oninput="searchSales()">
                    <select class="form-control" id="sales-status-filter" onchange="searchSales()" style="width:130px">
                        ${SALES_STATUS_FILTERS.map(f => `<option value="${f.value}">${f.label}</option>`).join('')}
                    </select>
                </div>
                <div class="toolbar-right">
                    <button class="btn btn-primary" onclick="showSalesForm()">+ 新建销售订单</button>
                </div>
            </div>
            <div class="card">
                <div class="card-body no-padding">
                    <div class="table-wrap">
                        <table>
                            <thead><tr><th>订单号</th><th>客户</th><th>日期</th><th>金额</th><th>已付</th><th>状态</th><th>操作</th></tr></thead>
                            <tbody id="sales-tbody">${renderSalesOrderRows(orders)}</tbody>
                        </table>
                    </div>
                </div>
            </div>`;
    } catch (e) {
        contentArea.innerHTML = `<div class="alert alert-danger">加载失败: ${e.message}</div>`;
    }
}

function renderSalesOrderRows(orders) {
    if (!orders.length) return '<tr><td colspan="7" class="text-center text-muted">暂无数据</td></tr>';
    return orders.map(o => `
        <tr>
            <td class="font-bold">${o.order_no}</td>
            <td>${o.customer_name}</td>
            <td>${formatDate(o.order_date)}</td>
            <td>${formatMoney(o.total_amount)}</td>
            <td>${formatMoney(o.paid_amount)}</td>
            <td>${statusBadge(o.status)}</td>
            <td>
                ${o.status === 'draft' ? `<button class="btn btn-xs btn-success" onclick="changeSalesStatus(${o.id},'confirm')">确认</button>` : ''}
                ${o.status === 'confirmed' ? `<button class="btn btn-xs btn-warning" onclick="changeSalesStatus(${o.id},'ship')">发货</button>` : ''}
                ${o.status === 'confirmed' || o.status === 'shipped' ? `<button class="btn btn-xs btn-primary" onclick="changeSalesStatus(${o.id},'complete')">完成</button>` : ''}
                ${o.status !== 'completed' && o.status !== 'cancelled' ? `<button class="btn btn-xs btn-danger" onclick="changeSalesStatus(${o.id},'cancel')">取消</button>` : ''}
                ${o.status === 'draft' ? `<button class="btn btn-xs btn-secondary" onclick="showSalesForm(${o.id})">编辑</button>` : ''}
                ${o.status === 'draft' || o.status === 'cancelled' ? `<button class="btn btn-xs btn-danger" onclick="deleteSalesOrder(${o.id})">删除</button>` : ''}
            </td>
        </tr>`).join('');
}

async function searchSales() {
    const q = document.getElementById('sales-search').value;
    const status = document.getElementById('sales-status-filter').value;
    let url = '/api/sales-orders?';
    if (q) url += `search=${encodeURIComponent(q)}&`;
    if (status) url += `status=${status}&`;
    const orders = await api(url);
    document.getElementById('sales-tbody').innerHTML = renderSalesOrderRows(orders);
}

async function changeSalesStatus(id, action) {
    const labels = { confirm: '确认', ship: '发货', complete: '完成', cancel: '取消' };
    if (action === 'cancel' && !confirm('确定取消该订单吗？')) return;
    try {
        await api(`/api/sales-orders/${id}`, {
            method: 'PUT',
            body: JSON.stringify({ action })
        });
        showToast(`${labels[action]}成功`, 'success');
        renderSalesList();
    } catch (e) { /* handled */ }
}

async function deleteSalesOrder(id) {
    if (!confirm('确定删除该订单吗？')) return;
    try {
        await api(`/api/sales-orders/${id}`, { method: 'DELETE' });
        showToast('删除成功', 'success');
        renderSalesList();
    } catch (e) { /* handled */ }
}

async function showSalesForm(id) {
    contentArea.innerHTML = '<div class="empty-state"><div class="empty-icon">⏳</div><p>加载中...</p></div>';

    let order = null, items = [];
    if (id) {
        const data = await api(`/api/sales-orders/${id}`);
        order = data.order;
        items = data.items;
    }

    const [customers, products] = await Promise.all([
        api('/api/customers'),
        api('/api/products')
    ]);

    const isDraft = !order || order.status === 'draft';

    contentArea.innerHTML = `
        <div class="card mb-16">
            <div class="card-header flex-between">
                <h3>${id ? '编辑销售订单 - ' + order.order_no : '新建销售订单'}</h3>
                <button class="btn btn-secondary" onclick="renderSalesList()">← 返回列表</button>
            </div>
            <div class="card-body">
                <div class="form-row">
                    <div class="form-group">
                        <label>客户 <span class="required">*</span></label>
                        <select class="form-control" id="so-customer" ${!isDraft ? 'disabled' : ''}>
                            ${customers.map(c => `<option value="${c.id}" ${order && order.customer_id === c.id ? 'selected' : ''}>${c.name}</option>`).join('')}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>订单日期 <span class="required">*</span></label>
                        <input class="form-control" type="date" id="so-date" value="${order ? order.order_date : new Date().toISOString().slice(0,10)}" ${!isDraft ? 'disabled' : ''}>
                    </div>
                </div>
                <div class="form-group">
                    <label>备注</label>
                    <input class="form-control" id="so-notes" value="${order ? order.notes || '' : ''}" ${!isDraft ? 'readonly' : ''}>
                </div>
            </div>
        </div>

        <div class="card mb-16">
            <div class="card-header flex-between">
                <h3>订单明细</h3>
                ${isDraft ? '<button class="btn btn-sm btn-primary" onclick="addSalesItem()">+ 添加商品</button>' : ''}
            </div>
            <div class="card-body no-padding">
                <div class="table-wrap">
                    <table class="order-items-table">
                        <thead><tr><th>商品</th><th>数量</th><th>单价</th><th>金额</th>${isDraft ? '<th>操作</th>' : ''}</tr></thead>
                        <tbody id="so-items">${renderSalesItems(items, products, isDraft)}</tbody>
                    </table>
                </div>
            </div>
            <div class="card-body">
                <div class="order-summary">合计: <span id="so-total">${formatMoney(order ? order.total_amount : 0)}</span></div>
            </div>
        </div>

        ${isDraft ? `
        <div style="text-align:right">
            <button class="btn btn-secondary" onclick="renderSalesList()">取消</button>
            <button class="btn btn-primary" onclick="saveSalesOrder(${id || 0})" style="margin-left:8px">
                ${id ? '更新订单' : '创建订单'}
            </button>
        </div>` : `
        <div class="alert alert-info">订单已${order.status === 'completed' ? '完成' : order.status === 'cancelled' ? '取消' : '确认'}，无法编辑</div>
        `}
    `;
}

function renderSalesItems(items, products, editable) {
    if (!items.length) return `<tr><td colspan="${editable ? 5 : 4}" class="text-center text-muted">暂无明细，请添加商品</td></tr>`;
    return items.map((item, i) => {
        const amount = (item.price || 0) * (item.qty || 0);
        return `
        <tr>
            <td>
                ${editable ? `<select class="form-control" onchange="updateSalesItemPrice(${i})" id="so-item-product-${i}">
                    ${products.map(p => `<option value="${p.id}" data-price="${p.sale_price}" ${item.product_id === p.id ? 'selected' : ''}>${p.name} (${p.code})</option>`).join('')}
                </select>` : (item.product_name || item.product_id)}
            </td>
            <td>${editable ? `<input type="number" value="${item.qty}" min="1" onchange="calcSalesTotal()" id="so-item-qty-${i}">` : item.qty}</td>
            <td>${editable ? `<input type="number" value="${item.price}" step="0.01" onchange="calcSalesTotal()" id="so-item-price-${i}">` : formatMoney(item.price)}</td>
            <td>${formatMoney(amount)}</td>
            ${editable ? `<td><button class="btn btn-xs btn-danger" onclick="removeSalesItem(${i})">删除</button></td>` : ''}
        </tr>`;
    }).join('');
}

function updateSalesItemPrice(i) {
    const sel = document.getElementById(`so-item-product-${i}`);
    const price = sel.options[sel.selectedIndex].dataset.price;
    document.getElementById(`so-item-price-${i}`).value = price;
    calcSalesTotal();
}

let salesItemCount = 0;

function addSalesItem() {
    const tbody = document.getElementById('so-items');
    salesItemCount = tbody.querySelectorAll('tr').length;
    const idx = salesItemCount;
    const row = document.createElement('tr');
    row.innerHTML = `
        <td><select class="form-control" id="so-item-product-${idx}" onchange="updateSalesItemPrice(${idx})"></select></td>
        <td><input type="number" value="1" min="1" onchange="calcSalesTotal()" id="so-item-qty-${idx}"></td>
        <td><input type="number" value="0" step="0.01" onchange="calcSalesTotal()" id="so-item-price-${idx}"></td>
        <td id="so-item-amount-${idx}">¥0.00</td>
        <td><button class="btn btn-xs btn-danger" onclick="this.closest('tr').remove();calcSalesTotal();">删除</button></td>`;
    tbody.appendChild(row);
    // Populate product select
    api('/api/products').then(products => {
        const sel = document.getElementById(`so-item-product-${idx}`);
        if (sel) {
            sel.innerHTML = products.map(p => `<option value="${p.id}" data-price="${p.sale_price}">${p.name} (${p.code})</option>`).join('');
            updateSalesItemPrice(idx);
        }
    });
}

function removeSalesItem(i) {
    const tr = document.querySelector(`#so-items tr:nth-child(${i + 1})`);
    if (tr) tr.remove();
    calcSalesTotal();
}

function calcSalesTotal() {
    const tbody = document.getElementById('so-items');
    if (!tbody) return;
    let total = 0;
    const rows = tbody.querySelectorAll('tr');
    rows.forEach((row, i) => {
        const qtyInput = row.querySelector(`[id^="so-item-qty-"]`);
        const priceInput = row.querySelector(`[id^="so-item-price-"]`);
        if (qtyInput && priceInput) {
            const qty = parseInt(qtyInput.value) || 0;
            const price = parseFloat(priceInput.value) || 0;
            total += qty * price;
        }
    });
    const totalEl = document.getElementById('so-total');
    if (totalEl) totalEl.textContent = formatMoney(total);
}

async function saveSalesOrder(id) {
    const customer_id = parseInt(document.getElementById('so-customer').value);
    const order_date = document.getElementById('so-date').value;
    const notes = document.getElementById('so-notes').value;

    if (!customer_id || !order_date) { showToast('请填写客户和日期', 'error'); return; }

    const items = [];
    const tbody = document.getElementById('so-items');
    const rows = tbody.querySelectorAll('tr');
    rows.forEach((row, i) => {
        const productSel = row.querySelector(`[id^="so-item-product-"]`);
        const qtyInput = row.querySelector(`[id^="so-item-qty-"]`);
        const priceInput = row.querySelector(`[id^="so-item-price-"]`);
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
            await api(`/api/sales-orders/${id}`, {
                method: 'PUT',
                body: JSON.stringify({ action: 'update', customer_id, order_date, notes, items })
            });
        } else {
            await api('/api/sales-orders', {
                method: 'POST',
                body: JSON.stringify({ customer_id, order_date, notes, items })
            });
        }
        showToast(id ? '更新成功' : '创建成功', 'success');
        renderSalesList();
    } catch (e) { /* handled */ }
}
