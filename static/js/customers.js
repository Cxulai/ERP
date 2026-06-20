/* ========================================
   Customers Management
   ======================================== */

async function renderCustomers() {
    try {
        const customers = await api('/api/customers');
        contentArea.innerHTML = `
            <div class="toolbar">
                <div class="toolbar-left">
                    <input type="text" class="search-input" id="customer-search" placeholder="🔍 搜索客户..." oninput="searchCustomers()">
                </div>
                <div class="toolbar-right">
                    <button class="btn btn-primary" onclick="showCustomerForm()">+ 新增客户</button>
                </div>
            </div>
            <div class="card">
                <div class="card-body no-padding">
                    <div class="table-wrap">
                        <table>
                            <thead><tr><th>名称</th><th>联系人</th><th>电话</th><th>邮箱</th><th>地址</th><th>操作</th></tr></thead>
                            <tbody id="customer-tbody">${renderCustomerRows(customers)}</tbody>
                        </table>
                    </div>
                </div>
            </div>`;
    } catch (e) {
        contentArea.innerHTML = `<div class="alert alert-danger">加载失败: ${e.message}</div>`;
    }
}

function renderCustomerRows(customers) {
    if (!customers.length) return '<tr><td colspan="6" class="text-center text-muted">暂无数据</td></tr>';
    return customers.map(c => `
        <tr>
            <td class="font-bold">${c.name}</td>
            <td>${c.contact_person || '-'}</td>
            <td>${c.phone || '-'}</td>
            <td>${c.email || '-'}</td>
            <td class="truncate" style="max-width:200px">${c.address || '-'}</td>
            <td>
                <button class="btn btn-sm btn-secondary" onclick="showCustomerForm(${c.id})">编辑</button>
                <button class="btn btn-sm btn-danger" onclick="deleteCustomer(${c.id})">删除</button>
            </td>
        </tr>`).join('');
}

async function searchCustomers() {
    const q = document.getElementById('customer-search').value;
    const customers = await api(`/api/customers?search=${encodeURIComponent(q)}`);
    document.getElementById('customer-tbody').innerHTML = renderCustomerRows(customers);
}

async function showCustomerForm(id) {
    let c = null;
    if (id) {
        const customers = await api('/api/customers');
        c = customers.find(cu => cu.id === id);
    }
    const title = id ? '编辑客户' : '新增客户';
    const body = `
        <div class="form-group">
            <label>客户名称 <span class="required">*</span></label>
            <input class="form-control" id="cust-name" value="${c ? c.name : ''}" placeholder="公司/个人名称">
        </div>
        <div class="form-row">
            <div class="form-group">
                <label>联系人</label>
                <input class="form-control" id="cust-contact" value="${c ? c.contact_person || '' : ''}" placeholder="联系人姓名">
            </div>
            <div class="form-group">
                <label>电话</label>
                <input class="form-control" id="cust-phone" value="${c ? c.phone || '' : ''}" placeholder="手机/座机">
            </div>
        </div>
        <div class="form-group">
            <label>邮箱</label>
            <input class="form-control" type="email" id="cust-email" value="${c ? c.email || '' : ''}" placeholder="email@example.com">
        </div>
        <div class="form-group">
            <label>地址</label>
            <input class="form-control" id="cust-address" value="${c ? c.address || '' : ''}" placeholder="详细地址">
        </div>`;

    openModal(title, body, `
        <button class="btn btn-secondary" onclick="closeModal()">取消</button>
        <button class="btn btn-primary" id="modal-submit">保存</button>
    `, async () => {
        const data = {
            name: document.getElementById('cust-name').value.trim(),
            contact_person: document.getElementById('cust-contact').value.trim(),
            phone: document.getElementById('cust-phone').value.trim(),
            email: document.getElementById('cust-email').value.trim(),
            address: document.getElementById('cust-address').value.trim()
        };
        if (!data.name) { showToast('请填写客户名称', 'error'); return; }
        if (id) {
            await api(`/api/customers/${id}`, { method: 'PUT', body: JSON.stringify(data) });
        } else {
            await api('/api/customers', { method: 'POST', body: JSON.stringify(data) });
        }
        closeModal();
        showToast(id ? '更新成功' : '创建成功', 'success');
        renderCustomers();
    });
}

async function deleteCustomer(id) {
    if (!confirm('确定删除该客户吗？')) return;
    try {
        await api(`/api/customers/${id}`, { method: 'DELETE' });
        showToast('删除成功', 'success');
        renderCustomers();
    } catch (e) { /* handled */ }
}
