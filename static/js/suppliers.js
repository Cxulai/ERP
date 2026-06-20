/* ========================================
   Suppliers Management
   ======================================== */

async function renderSuppliers() {
    try {
        const suppliers = await api('/api/suppliers');
        contentArea.innerHTML = `
            <div class="toolbar">
                <div class="toolbar-left">
                    <input type="text" class="search-input" id="supplier-search" placeholder="🔍 搜索供应商..." oninput="searchSuppliers()">
                </div>
                <div class="toolbar-right">
                    <button class="btn btn-primary" onclick="showSupplierForm()">+ 新增供应商</button>
                </div>
            </div>
            <div class="card">
                <div class="card-body no-padding">
                    <div class="table-wrap">
                        <table>
                            <thead><tr><th>名称</th><th>联系人</th><th>电话</th><th>邮箱</th><th>地址</th><th>操作</th></tr></thead>
                            <tbody id="supplier-tbody">${renderSupplierRows(suppliers)}</tbody>
                        </table>
                    </div>
                </div>
            </div>`;
    } catch (e) {
        contentArea.innerHTML = `<div class="alert alert-danger">加载失败: ${e.message}</div>`;
    }
}

function renderSupplierRows(suppliers) {
    if (!suppliers.length) return '<tr><td colspan="6" class="text-center text-muted">暂无数据</td></tr>';
    return suppliers.map(s => `
        <tr>
            <td class="font-bold">${s.name}</td>
            <td>${s.contact_person || '-'}</td>
            <td>${s.phone || '-'}</td>
            <td>${s.email || '-'}</td>
            <td class="truncate" style="max-width:200px">${s.address || '-'}</td>
            <td>
                <button class="btn btn-sm btn-secondary" onclick="showSupplierForm(${s.id})">编辑</button>
                <button class="btn btn-sm btn-danger" onclick="deleteSupplier(${s.id})">删除</button>
            </td>
        </tr>`).join('');
}

async function searchSuppliers() {
    const q = document.getElementById('supplier-search').value;
    const suppliers = await api(`/api/suppliers?search=${encodeURIComponent(q)}`);
    document.getElementById('supplier-tbody').innerHTML = renderSupplierRows(suppliers);
}

async function showSupplierForm(id) {
    let s = null;
    if (id) {
        const suppliers = await api('/api/suppliers');
        s = suppliers.find(su => su.id === id);
    }
    const title = id ? '编辑供应商' : '新增供应商';
    const body = `
        <div class="form-group">
            <label>供应商名称 <span class="required">*</span></label>
            <input class="form-control" id="supp-name" value="${s ? s.name : ''}" placeholder="供应商名称">
        </div>
        <div class="form-row">
            <div class="form-group">
                <label>联系人</label>
                <input class="form-control" id="supp-contact" value="${s ? s.contact_person || '' : ''}" placeholder="联系人">
            </div>
            <div class="form-group">
                <label>电话</label>
                <input class="form-control" id="supp-phone" value="${s ? s.phone || '' : ''}" placeholder="联系电话">
            </div>
        </div>
        <div class="form-group">
            <label>邮箱</label>
            <input class="form-control" type="email" id="supp-email" value="${s ? s.email || '' : ''}" placeholder="email@example.com">
        </div>
        <div class="form-group">
            <label>地址</label>
            <input class="form-control" id="supp-address" value="${s ? s.address || '' : ''}" placeholder="详细地址">
        </div>`;

    openModal(title, body, `
        <button class="btn btn-secondary" onclick="closeModal()">取消</button>
        <button class="btn btn-primary" id="modal-submit">保存</button>
    `, async () => {
        const data = {
            name: document.getElementById('supp-name').value.trim(),
            contact_person: document.getElementById('supp-contact').value.trim(),
            phone: document.getElementById('supp-phone').value.trim(),
            email: document.getElementById('supp-email').value.trim(),
            address: document.getElementById('supp-address').value.trim()
        };
        if (!data.name) { showToast('请填写供应商名称', 'error'); return; }
        if (id) {
            await api(`/api/suppliers/${id}`, { method: 'PUT', body: JSON.stringify(data) });
        } else {
            await api('/api/suppliers', { method: 'POST', body: JSON.stringify(data) });
        }
        closeModal();
        showToast(id ? '更新成功' : '创建成功', 'success');
        renderSuppliers();
    });
}

async function deleteSupplier(id) {
    if (!confirm('确定删除该供应商吗？')) return;
    try {
        await api(`/api/suppliers/${id}`, { method: 'DELETE' });
        showToast('删除成功', 'success');
        renderSuppliers();
    } catch (e) { /* handled */ }
}
