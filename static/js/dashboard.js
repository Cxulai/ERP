/* ========================================
   Dashboard
   ======================================== */

let salesChart = null;

async function renderDashboard() {
    try {
        const data = await api('/api/dashboard');

        const lowStockHtml = data.low_stock.length > 0
            ? data.low_stock.map(p => `
                <tr>
                    <td>${p.code}</td>
                    <td>${p.name}</td>
                    <td class="text-danger font-bold">${p.stock_qty}</td>
                    <td>${p.min_stock}</td>
                </tr>`).join('')
            : '<tr><td colspan="4" class="text-center text-muted">👍 暂无低库存商品</td></tr>';

        const recentHtml = data.recent_sales.length > 0
            ? data.recent_sales.map(o => `
                <tr>
                    <td><a href="#sales" onclick="navigateTo('sales')" style="color:var(--primary);text-decoration:none;">${o.order_no}</a></td>
                    <td>${o.customer_name}</td>
                    <td>${formatDate(o.order_date)}</td>
                    <td>${formatMoney(o.total_amount)}</td>
                    <td>${statusBadge(o.status)}</td>
                </tr>`).join('')
            : '<tr><td colspan="5" class="text-center text-muted">暂无订单</td></tr>';

        contentArea.innerHTML = `
            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-icon green">💰</div>
                    <div class="kpi-info">
                        <h3>${formatMoney(data.monthly_sales)}</h3>
                        <p>本月销售额 · ${data.pending_sales} 笔待处理</p>
                    </div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-icon orange">🛒</div>
                    <div class="kpi-info">
                        <h3>${formatMoney(data.monthly_purchases)}</h3>
                        <p>本月采购额 · ${data.pending_purchases} 笔待收货</p>
                    </div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-icon blue">📦</div>
                    <div class="kpi-info">
                        <h3>${data.product_count}</h3>
                        <p>商品总数 · ${data.low_stock.length} 个低库存预警</p>
                    </div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-icon purple">👥</div>
                    <div class="kpi-info">
                        <h3>${data.customer_count} / ${data.supplier_count}</h3>
                        <p>客户 / 供应商</p>
                    </div>
                </div>
            </div>

            <div class="page-grid">
                <div class="card">
                    <div class="card-header"><h3>📈 月度销售趋势</h3></div>
                    <div class="card-body">
                        <div class="chart-container-lg">
                            <canvas id="sales-trend-chart"></canvas>
                        </div>
                    </div>
                </div>
                <div class="card">
                    <div class="card-header"><h3>⚠️ 低库存预警</h3></div>
                    <div class="card-body no-padding">
                        <div class="table-wrap">
                            <table>
                                <thead><tr><th>编码</th><th>商品名称</th><th>当前库存</th><th>最低库存</th></tr></thead>
                                <tbody>${lowStockHtml}</tbody>
                            </table>
                        </div>
                    </div>
                </div>
                <div class="card page-grid-full">
                    <div class="card-header"><h3>🕐 最近销售订单</h3></div>
                    <div class="card-body no-padding">
                        <div class="table-wrap">
                            <table>
                                <thead><tr><th>订单号</th><th>客户</th><th>日期</th><th>金额</th><th>状态</th></tr></thead>
                                <tbody>${recentHtml}</tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>`;

        // Render chart
        if (salesChart) salesChart.destroy();
        const ctx = document.getElementById('sales-trend-chart');
        if (ctx && data.sales_trend.length > 0) {
            const reversed = [...data.sales_trend].reverse();
            salesChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: reversed.map(r => r.month),
                    datasets: [{
                        label: '销售额 (元)',
                        data: reversed.map(r => r.amount),
                        backgroundColor: '#4f46e5',
                        borderRadius: 6,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true, ticks: { callback: v => '¥' + v.toLocaleString() } }
                    }
                }
            });
        }
    } catch (e) {
        contentArea.innerHTML = `<div class="alert alert-danger">加载失败: ${e.message}</div>`;
    }
}
