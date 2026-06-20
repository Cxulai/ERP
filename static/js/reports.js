/* ========================================
   Financial Reports
   ======================================== */

let incomeChart = null;
let profitChart = null;

async function renderReports() {
    try {
        const [summary, income] = await Promise.all([
            api('/api/reports?type=summary'),
            api('/api/reports?type=income')
        ]);

        contentArea.innerHTML = `
            <div class="kpi-grid mb-24">
                <div class="kpi-card">
                    <div class="kpi-icon green">💰</div>
                    <div class="kpi-info">
                        <h3>${formatMoney(summary.sales_revenue)}</h3>
                        <p>本月销售收入</p>
                    </div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-icon red">💸</div>
                    <div class="kpi-info">
                        <h3>${formatMoney(summary.purchase_cost)}</h3>
                        <p>本月采购成本</p>
                    </div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-icon blue">📊</div>
                    <div class="kpi-info">
                        <h3 style="color:${summary.profit >= 0 ? 'var(--success)' : 'var(--danger)'}">${formatMoney(summary.profit)}</h3>
                        <p>本月毛利</p>
                    </div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-icon orange">📋</div>
                    <div class="kpi-info">
                        <h3>${summary.sales_count} / ${summary.purchase_count}</h3>
                        <p>本月订单数 (销/采)</p>
                    </div>
                </div>
            </div>

            <div class="kpi-grid mb-24" style="grid-template-columns: repeat(3, 1fr)">
                <div class="kpi-card">
                    <div class="kpi-icon blue">📥</div>
                    <div class="kpi-info">
                        <h3>${formatMoney(summary.receivables)}</h3>
                        <p>应收账款</p>
                    </div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-icon orange">📤</div>
                    <div class="kpi-info">
                        <h3>${formatMoney(summary.payables)}</h3>
                        <p>应付账款</p>
                    </div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-icon purple">💵</div>
                    <div class="kpi-info">
                        <h3>${formatMoney(summary.sales_pending)}</h3>
                        <p>待处理销售额</p>
                    </div>
                </div>
            </div>

            <div class="page-grid">
                <div class="card">
                    <div class="card-header"><h3>📈 销售收入趋势 (月度)</h3></div>
                    <div class="card-body">
                        <div class="chart-container-lg">
                            <canvas id="income-chart"></canvas>
                        </div>
                    </div>
                </div>
                <div class="card">
                    <div class="card-header"><h3>📊 采购支出趋势 (月度)</h3></div>
                    <div class="card-body">
                        <div class="chart-container-lg">
                            <canvas id="profit-chart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Render income chart
        if (incomeChart) incomeChart.destroy();
        const ictx = document.getElementById('income-chart');
        if (ictx && income.sales_monthly.length > 0) {
            incomeChart = new Chart(ictx, {
                type: 'bar',
                data: {
                    labels: income.sales_monthly.map(r => r.month),
                    datasets: [
                        {
                            label: '已完成',
                            data: income.sales_monthly.map(r => r.completed_amount),
                            backgroundColor: '#10b981',
                            borderRadius: 4,
                        },
                        {
                            label: '总计(含进行中)',
                            data: income.sales_monthly.map(r => r.total_amount),
                            backgroundColor: '#93c5fd',
                            borderRadius: 4,
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'bottom' } },
                    scales: { y: { beginAtZero: true, ticks: { callback: v => '¥' + v.toLocaleString() } } }
                }
            });
        }

        // Render purchase chart
        if (profitChart) profitChart.destroy();
        const pctx = document.getElementById('profit-chart');
        if (pctx && income.purchase_monthly.length > 0) {
            profitChart = new Chart(pctx, {
                type: 'bar',
                data: {
                    labels: income.purchase_monthly.map(r => r.month),
                    datasets: [
                        {
                            label: '已完成',
                            data: income.purchase_monthly.map(r => r.completed_amount),
                            backgroundColor: '#f59e0b',
                            borderRadius: 4,
                        },
                        {
                            label: '总计(含进行中)',
                            data: income.purchase_monthly.map(r => r.total_amount),
                            backgroundColor: '#fde68a',
                            borderRadius: 4,
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'bottom' } },
                    scales: { y: { beginAtZero: true, ticks: { callback: v => '¥' + v.toLocaleString() } } }
                }
            });
        }
    } catch (e) {
        contentArea.innerHTML = `<div class="alert alert-danger">加载失败: ${e.message}</div>`;
    }
}
