/* ========================================
   Products Management
   ======================================== */

async function renderProducts() {
    try {
        const products = await api('/api/products');
        let html = `
            <div class="toolbar">
                <div class="toolbar-left">
                    <input type="text" class="search-input" id="product-search" placeholder="🔍 搜索商品名称/编码..." oninput="searchProducts()">
                </div>
                <div class="toolbar-right">
                    <button class="btn btn-primary" onclick="showProductForm()">+ 新增商品</button>
                </div>
            </div>
            <div class="card">
                <div class="card-body no-padding">
                    <div class="table-wrap">
                        <table>
                            <thead>
                                <tr><th>编码</th><th>名称</th><th>分类</th><th>单位</th><th>销售价</th><th>采购价</th><th>库存</th><th>最低库存</th><th>操作</th></tr>
                            </thead>
                            <tbody id="product-tbody">`;

        html += renderProductRows(products);

        html += `           </tbody>
                        </table>
                    </div>
                </div>
            </div>`;

        contentArea.innerHTML = html;
    } catch (e) {
        contentArea.innerHTML = `<div class="alert alert-danger">加载失败: ${e.message}</div>`;
    }
}

function renderProductRows(products) {
    if (!products.length) return '<tr><td colspan="9" class="text-center text-muted">暂无数据</td></tr>';
    return products.map(p => {
        const lowClass = p.stock_qty <= p.min_stock ? 'text-danger font-bold' : '';
        return `
        <tr>
            <td>${p.code}</td>
            <td>${p.name}</td>
            <td>${p.category || '-'}</td>
            <td>${p.unit}</td>
            <td>${formatMoney(p.sale_price)}</td>
            <td>${formatMoney(p.purchase_price)}</td>
            <td class="${lowClass}">${p.stock_qty}</td>
            <td>${p.min_stock}</td>
            <td>
                <button class="btn btn-sm btn-secondary" onclick="showProductForm(${p.id})">编辑</button>
                <button class="btn btn-sm btn-warning" onclick="showStockForm(${p.id})">库存</button>
                <button class="btn btn-sm btn-danger" onclick="deleteProduct(${p.id})">删除</button>
            </td>
        </tr>`;
    }).join('');
}

async function searchProducts() {
    const q = document.getElementById('product-search').value;
    const products = await api(`/api/products?search=${encodeURIComponent(q)}`);
    document.getElementById('product-tbody').innerHTML = renderProductRows(products);
}

async function showProductForm(id) {
    let product = null;
    if (id) {
        const products = await api('/api/products');
        product = products.find(p => p.id === id);
    }

    const title = id ? '编辑商品' : '新增商品';
    const body = `
        <div class="form-row">
            <div class="form-group">
                <label>商品编码 <span class="required">*</span></label>
                <input class="form-control" id="prod-code" value="${product ? product.code : ''}" ${product ? '' : 'placeholder="如 P009"'}>
            </div>
            <div class="form-group">
                <label>商品名称 <span class="required">*</span></label>
                <input class="form-control" id="prod-name" value="${product ? product.name : ''}" placeholder="商品名称">
            </div>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label>分类</label>
                <input class="form-control" id="prod-category" value="${product ? product.category || '' : ''}" placeholder="如 工具/电器">
            </div>
            <div class="form-group">
                <label>单位</label>
                <input class="form-control" id="prod-unit" value="${product ? product.unit || '个' : '个'}">
            </div>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label>销售单价 <span class="required">*</span></label>
                <input class="form-control" type="number" step="0.01" id="prod-sale-price" value="${product ? product.sale_price : ''}" placeholder="0.00">
            </div>
            <div class="form-group">
                <label>采购单价 <span class="required">*</span></label>
                <input class="form-control" type="number" step="0.01" id="prod-purchase-price" value="${product ? product.purchase_price : ''}" placeholder="0.00">
            </div>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label>初始库存</label>
                <input class="form-control" type="number" id="prod-stock" value="${product ? product.stock_qty : 0}" ${product ? 'readonly' : ''}>
                ${product ? '<small class="text-muted">编辑模式下不可修改库存，请使用库存调整功能</small>' : ''}
            </div>
            <div class="form-group">
                <label>最低库存预警</label>
                <input class="form-control" type="number" id="prod-min-stock" value="${product ? product.min_stock : 10}">
            </div>
        </div>`;

    openModal(title, body, `
        <button class="btn btn-secondary" onclick="closeModal()">取消</button>
        <button class="btn btn-primary" id="modal-submit">保存</button>
    `, async () => {
        const data = {
            code: document.getElementById('prod-code').value.trim(),
            name: document.getElementById('prod-name').value.trim(),
            category: document.getElementById('prod-category').value.trim(),
            unit: document.getElementById('prod-unit').value.trim(),
            sale_price: parseFloat(document.getElementById('prod-sale-price').value) || 0,
            purchase_price: parseFloat(document.getElementById('prod-purchase-price').value) || 0,
            stock_qty: parseInt(document.getElementById('prod-stock').value) || 0,
            min_stock: parseInt(document.getElementById('prod-min-stock').value) || 10
        };
        if (!data.code || !data.name) { showToast('请填写商品编码和名称', 'error'); return; }

        if (id) {
            await api(`/api/products/${id}`, { method: 'PUT', body: JSON.stringify(data) });
        } else {
            await api('/api/products', { method: 'POST', body: JSON.stringify(data) });
        }
        closeModal();
        showToast(id ? '更新成功' : '创建成功', 'success');
        renderProducts();
    });
}

async function showStockForm(id) {
    const products = await api('/api/products');
    const p = products.find(pr => pr.id === id);
    if (!p) return;

    const body = `
        <div class="alert alert-info">当前库存: <strong>${p.stock_qty}</strong> ${p.unit}</div>
        <div class="form-row">
            <div class="form-group">
                <label>调整类型</label>
                <select class="form-control" id="stock-type">
                    <option value="adjust">手动调整 (+/-)</option>
                    <option value="in">入库 (+)</option>
                    <option value="out">出库 (-)</option>
                </select>
            </div>
            <div class="form-group">
                <label>变动数量（出库填负数）</label>
                <input class="form-control" type="number" id="stock-qty" value="0" placeholder="如 10 或 -5">
            </div>
        </div>
        <div class="form-group">
            <label>备注</label>
            <input class="form-control" id="stock-notes" placeholder="调整原因">
        </div>`;

    openModal(`库存调整 - ${p.name}`, body, `
        <button class="btn btn-secondary" onclick="closeModal()">取消</button>
        <button class="btn btn-primary" id="modal-submit">确认调整</button>
    `, async () => {
        const qty = parseInt(document.getElementById('stock-qty').value) || 0;
        if (qty === 0) { showToast('请输入变动数量', 'error'); return; }
        await api(`/api/products/${id}/stock`, {
            method: 'PUT',
            body: JSON.stringify({
                qty: qty,
                type: document.getElementById('stock-type').value,
                notes: document.getElementById('stock-notes').value
            })
        });
        closeModal();
        showToast('库存调整成功', 'success');
        renderProducts();
    });
}

async function deleteProduct(id) {
    if (!confirm('确定删除该商品吗？')) return;
    try {
        await api(`/api/products/${id}`, { method: 'DELETE' });
        showToast('删除成功', 'success');
        renderProducts();
    } catch (e) { /* api handles toast */ }
}

/* ========================================
   Inventory Logs
   ======================================== */

async function renderInventory() {
    try {
        const logs = await api('/api/inventory-logs');
        let html = `
            <div class="card">
                <div class="card-header"><h3>📋 库存流水记录</h3></div>
                <div class="card-body no-padding">
                    <div class="table-wrap">
                        <table>
                            <thead><tr><th>时间</th><th>商品</th><th>类型</th><th>变动</th><th>变动前</th><th>变动后</th><th>关联单号</th><th>备注</th></tr></thead>
                            <tbody>`;

        const typeLabels = {
            init: '初始库存', in: '入库', out: '出库', adjust: '手动调整',
            sale: '销售出库', purchase: '采购入库', cancel_return: '取消退回'
        };

        if (logs.length > 0) {
            html += logs.map(l => `
                <tr>
                    <td>${l.created_at}</td>
                    <td>${l.product_name} (${l.product_code})</td>
                    <td>${typeLabels[l.change_type] || l.change_type}</td>
                    <td class="${l.qty > 0 ? 'text-success' : 'text-danger'}">${l.qty > 0 ? '+' : ''}${l.qty}</td>
                    <td>${l.before_qty}</td>
                    <td>${l.after_qty}</td>
                    <td>${l.reference || '-'}</td>
                    <td>${l.notes || '-'}</td>
                </tr>`).join('');
        } else {
            html += '<tr><td colspan="8" class="text-center text-muted">暂无库存流水</td></tr>';
        }

        html += `           </tbody>
                        </table>
                    </div>
                </div>
            </div>`;
        contentArea.innerHTML = html;
    } catch (e) {
        contentArea.innerHTML = `<div class="alert alert-danger">加载失败: ${e.message}</div>`;
    }
}
