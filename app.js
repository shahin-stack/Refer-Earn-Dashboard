document.addEventListener('DOMContentLoaded', async function () {
    const exportBtn = document.getElementById('exportBtn');

    // Store latest data for Excel export
    let currentStats = null;

    // Initial load
    updateDashboard();

    // ── Overview section filter ───────────────────────────────────────────────
    document.getElementById('overviewApplyFilter')?.addEventListener('click', () => {
        const s = document.getElementById('overviewFrom').value;
        const e = document.getElementById('overviewTo').value;
        updateDashboard(s, e);
    });
    document.getElementById('overviewClearFilter')?.addEventListener('click', () => {
        document.getElementById('overviewFrom').value = '';
        document.getElementById('overviewTo').value   = '';
        updateDashboard('', '');
    });

    async function updateDashboard(start = '', end = '') {

        document.body.style.cursor = 'wait';

        // Show loading state on all core metric cards
        document.querySelectorAll('.metric-card .card-value').forEach(el => {
            el.textContent = '…';
            el.style.opacity = '0.4';
        });
        const progressFill = document.getElementById('discountProgressBar');
        if (progressFill) progressFill.style.width = '0%';

        try {
            const response = await fetch(`/api/dashboard?start=${start}&end=${end}`);
            const data     = await response.json();

            if (!data || data.error) {
                console.error('API error:', data ? data.error : 'no data');
                document.querySelectorAll('.metric-card .card-value').forEach(el => {
                    el.textContent = 'Error';
                    el.style.opacity = '1';
                    el.style.color = '#ef4444';
                });
                return;
            }

            const master = data.master_stats;
            const stats  = data.range_stats;

            // Save for Excel export
            currentStats = { master, stats };

            // ─── Helper formatters ────────────────────────────────────────
            // Indian comma format: 1,42,64,614
            function toIndian(num) {
                num = Math.round(num);
                const s   = String(num);
                const len = s.length;
                if (len <= 3) return s;
                // last 3 digits, then groups of 2
                let result = s.slice(-3);
                let rest   = s.slice(0, len - 3);
                while (rest.length > 2) {
                    result = rest.slice(-2) + ',' + result;
                    rest   = rest.slice(0, rest.length - 2);
                }
                if (rest.length) result = rest + ',' + result;
                return result;
            }

            function fmtPts(val) {
                return toIndian(val);
            }

            function fmtRupee(val) {
                return '₹' + toIndian(val);
            }

            function fmtPct(val) {
                // Show as whole number if close to integer, else 2 dp
                const rounded = Math.round(val);
                return Math.abs(val - rounded) < 0.005 ? rounded + '%' : val.toFixed(2) + '%';
            }

            // ─── Update cards ─────────────────────────────────────────────
            // Card 1 – Total Customer Count
            const el1 = document.getElementById('cardTotalCustomers');
            if (el1) el1.textContent = master.total_customer_count.toLocaleString('en-IN');

            // Card 2 – Total Bonus Points Given (Indian format)
            const el2 = document.getElementById('cardBonusPoints');
            if (el2) el2.textContent = fmtPts(master.total_bonus_point_given);

            // Card 3 – Total Purchase Count
            const el3 = document.getElementById('cardPurchaseCount');
            if (el3) el3.textContent = stats.purchase_count.toLocaleString('en-IN');

            // Card 4 – Total Redeemed Count
            const el4 = document.getElementById('cardRedeemedCount');
            if (el4) el4.textContent = stats.redeemed_count.toLocaleString('en-IN');

            // Card 5 – Total Point Redeemed Value (Indian format)
            const el5 = document.getElementById('cardPointRedeemed');
            if (el5) el5.textContent = fmtPts(stats.point_redeemed_value);

            // Card 6 – Redeemed Purchase Value (Indian Rs format)
            const el6 = document.getElementById('cardRedeemedPurchase');
            if (el6) el6.textContent = fmtRupee(stats.redeemed_purchase_value);

            // Card 7 – Loyalty Discount %
            const discountPct = stats.loyalty_discount_pct;
            const el7 = document.getElementById('cardDiscountPct');
            if (el7) el7.textContent = fmtPct(discountPct);
            const progressFill = document.getElementById('discountProgressBar');
            if (progressFill) progressFill.style.width = Math.min(discountPct * 10, 100) + '%';

            // Card 8 – Avg Purchase Value
            const el8 = document.getElementById('cardAvgPurchase');
            if (el8) el8.textContent = fmtRupee(stats.avg_purchase_value);

            // Card 9 – Avg Point Redemption
            const el9 = document.getElementById('cardAvgRedemption');
            if (el9) el9.textContent = Math.round(stats.avg_loyalty_redemption).toLocaleString('en-IN');

            animateCards();
            // Restore card opacity after loading
            document.querySelectorAll('.metric-card .card-value').forEach(el => {
                el.style.opacity = '1';
            });
            await fetchCustomerTrend(start, end);
        } catch (err) {
            console.error('Failed to fetch dashboard metrics:', err);
            document.querySelectorAll('.metric-card .card-value').forEach(el => {
                el.textContent = 'Error';
                el.style.opacity = '1';
                el.style.color = '#ef4444';
            });
        } finally {
            document.body.style.cursor = 'default';
        }
    }

    // Set nth metric card value
    function setCard(n, value) {
        const el = document.querySelector(`.metric-card:nth-child(${n}) .card-value`);
        if (el) el.textContent = value;
    }

    function animateCards() {
        document.querySelectorAll('.metric-card').forEach((card, i) => {
            card.style.opacity   = '0';
            card.style.transform = 'translateY(15px)';
            setTimeout(() => {
                card.style.transition = 'all 0.4s ease';
                card.style.opacity    = '1';
                card.style.transform  = 'translateY(0)';
            }, 30 * i);
        });
    }

    async function fetchNewCustomerMetrics(start = '', end = '') {
        try {
            const response = await fetch(`/api/new-customer-metrics?start=${start}&end=${end}`);
            const data = await response.json();
            
            if (!data || data.error) return;
            
            const master = data.master_stats;
            const stats  = data.range_stats;

            function toIndian(num) {
                num = Math.round(num);
                const s = String(num);
                if (s.length <= 3) return s;
                let res = s.slice(-3);
                let rest = s.slice(0, s.length - 3);
                while (rest.length > 2) {
                    res = rest.slice(-2) + ',' + res;
                    rest = rest.slice(0, rest.length - 2);
                }
                if (rest.length) res = rest + ',' + res;
                return res;
            }
            
            const fmtRupee = (v) => '₹' + toIndian(v);
            const fmtPct = (v) => Math.abs(v - Math.round(v)) < 0.005 ? Math.round(v) + '%' : v.toFixed(2) + '%';
            
            // Use master.total_customer_count – this is the true new customer count from API
            const ncTotal = document.getElementById('nc-cardTotalCustomers');
            if (ncTotal) ncTotal.textContent = toIndian(master.total_customer_count);
            
            const ncBonus = document.getElementById('nc-cardBonusPoints');
            if (ncBonus) ncBonus.textContent = toIndian(master.total_bonus_point_given);
            
            const ncPurchase = document.getElementById('nc-cardPurchaseCount');
            if (ncPurchase) ncPurchase.textContent = toIndian(stats.purchase_count);
            
            const ncRedeemed = document.getElementById('nc-cardRedeemedCount');
            if (ncRedeemed) ncRedeemed.textContent = toIndian(stats.redeemed_count);
            
            const ncPointRed = document.getElementById('nc-cardPointRedeemed');
            if (ncPointRed) ncPointRed.textContent = toIndian(stats.point_redeemed_value);
            
            const ncRedPurch = document.getElementById('nc-cardRedeemedPurchase');
            if (ncRedPurch) ncRedPurch.textContent = fmtRupee(stats.redeemed_purchase_value);
            
            const discountPct = stats.loyalty_discount_pct;
            const ncDisc = document.getElementById('nc-cardDiscountPct');
            if (ncDisc) ncDisc.textContent = fmtPct(discountPct);
            const ncBar = document.getElementById('nc-discountProgressBar');
            if (ncBar) ncBar.style.width = Math.min(discountPct * 10, 100) + '%';
            
            const ncAvgP = document.getElementById('nc-cardAvgPurchase');
            if (ncAvgP) ncAvgP.textContent = fmtRupee(stats.avg_purchase_value);
            
            const ncAvgR = document.getElementById('nc-cardAvgRedemption');
            if (ncAvgR) ncAvgR.textContent = toIndian(stats.avg_loyalty_redemption);
            
            document.querySelectorAll('.nc-card').forEach((card, i) => {
                card.style.opacity = '0';
                card.style.transform = 'translateY(15px)';
                setTimeout(() => {
                    card.style.transition = 'all 0.4s ease';
                    card.style.opacity = '1';
                    card.style.transform = 'translateY(0)';
                }, 30 * i);
            });

            // Render New Customer trend chart
            if (data.trend && document.getElementById('newTrendChart')) {
                if (window._newTrendChartInst) window._newTrendChartInst.destroy();
                window._newTrendChartInst = new Chart(
                    document.getElementById('newTrendChart'),
                    {
                        type: 'bar',
                        data: {
                            labels: data.trend.labels.map(l => {
                                const d = new Date(l);
                                return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
                            }),
                            datasets: [{
                                label: 'New Customers',
                                data: data.trend.data,
                                backgroundColor: 'rgba(16,185,129,0.7)',
                                borderColor: '#059669',
                                borderWidth: 1,
                                borderRadius: 4
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: { legend: { display: false } },
                            scales: {
                                x: { grid: { display: false }, ticks: { maxTicksLimit: 20, font: { size: 10 } } },
                                y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.05)' } }
                            }
                        }
                    }
                );
            }
            
        } catch(e) {
            console.error('Failed to fetch new customer metrics:', e);
        }
    }

    async function fetchRepeatCustomerMetrics(start = '', end = '') {
        try {
            const response = await fetch(`/api/repeat-customer-metrics?start=${start}&end=${end}`);
            const data = await response.json();
            
            if (!data || data.error) return;
            
            const master = data.master_stats;
            const stats  = data.range_stats;

            function toIndian(num) {
                num = Math.round(num);
                const s = String(num);
                if (s.length <= 3) return s;
                let res = s.slice(-3);
                let rest = s.slice(0, s.length - 3);
                while (rest.length > 2) {
                    res = rest.slice(-2) + ',' + res;
                    rest = rest.slice(0, rest.length - 2);
                }
                if (rest.length) res = rest + ',' + res;
                return res;
            }
            
            const fmtRupee = (v) => '₹' + toIndian(v);
            const fmtPct = (v) => Math.abs(v - Math.round(v)) < 0.005 ? Math.round(v) + '%' : v.toFixed(2) + '%';
            
            const rcTotal = document.getElementById('rc-cardTotalCustomers');
            if (rcTotal) rcTotal.textContent = toIndian(master.total_customer_count);
            
            const rcBonus = document.getElementById('rc-cardBonusPoints');
            if (rcBonus) rcBonus.textContent = toIndian(master.total_bonus_point_given);
            
            const rcPurchase = document.getElementById('rc-cardPurchaseCount');
            if (rcPurchase) rcPurchase.textContent = toIndian(stats.purchase_count);
            
            const rcRedeemed = document.getElementById('rc-cardRedeemedCount');
            if (rcRedeemed) rcRedeemed.textContent = toIndian(stats.redeemed_count);
            
            const rcPointRed = document.getElementById('rc-cardPointRedeemed');
            if (rcPointRed) rcPointRed.textContent = toIndian(stats.point_redeemed_value);
            
            const rcRedPurch = document.getElementById('rc-cardRedeemedPurchase');
            if (rcRedPurch) rcRedPurch.textContent = fmtRupee(stats.redeemed_purchase_value);
            
            const discountPct = stats.loyalty_discount_pct;
            const rcDisc = document.getElementById('rc-cardDiscountPct');
            if (rcDisc) rcDisc.textContent = fmtPct(discountPct);
            const rcBar = document.getElementById('rc-discountProgressBar');
            if (rcBar) rcBar.style.width = Math.min(discountPct * 10, 100) + '%';
            
            const rcAvgP = document.getElementById('rc-cardAvgPurchase');
            if (rcAvgP) rcAvgP.textContent = fmtRupee(stats.avg_purchase_value);
            
            const rcAvgR = document.getElementById('rc-cardAvgRedemption');
            if (rcAvgR) rcAvgR.textContent = toIndian(stats.avg_loyalty_redemption);
            
            document.querySelectorAll('.rc-card').forEach((card, i) => {
                card.style.opacity = '0';
                card.style.transform = 'translateY(15px)';
                setTimeout(() => {
                    card.style.transition = 'all 0.4s ease';
                    card.style.opacity = '1';
                    card.style.transform = 'translateY(0)';
                }, 30 * i);
            });

            // Render Repeat Customer trend chart
            if (data.trend && document.getElementById('repeatTrendChart')) {
                if (window._repeatTrendChartInst) window._repeatTrendChartInst.destroy();
                window._repeatTrendChartInst = new Chart(
                    document.getElementById('repeatTrendChart'),
                    {
                        type: 'bar',
                        data: {
                            labels: data.trend.labels.map(l => {
                                const d = new Date(l);
                                return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
                            }),
                            datasets: [{
                                label: 'Repeat Customers',
                                data: data.trend.data,
                                backgroundColor: 'rgba(37,99,235,0.7)',
                                borderColor: '#2563eb',
                                borderWidth: 1,
                                borderRadius: 4
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: { legend: { display: false } },
                            scales: {
                                x: { grid: { display: false }, ticks: { maxTicksLimit: 20, font: { size: 10 } } },
                                y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.05)' } }
                            }
                        }
                    }
                );
            }
            
        } catch(e) {
            console.error('Failed to fetch repeat customer metrics:', e);
        }
    }
    // ─── Customer Trend Chart ──────────────────────────────────────────────
    let customerTrendChartInstance = null;

    async function fetchCustomerTrend(start, end) {
        try {
            const response = await fetch(`/api/daily-customer-trend?start=${start}&end=${end}`);
            const data = await response.json();
            if (!data || data.error) return;

            renderCustomerTrendChart(data.labels, data.data);
        } catch (err) {
            console.error('Failed to fetch customer trend:', err);
        }
    }

    function renderCustomerTrendChart(labels, dataPoints) {
        const ctx = document.getElementById('customerTrendChart');
        if (!ctx) return;

        if (customerTrendChartInstance) {
            customerTrendChartInstance.destroy();
        }

        const gradient = ctx.getContext('2d').createLinearGradient(0, 0, 0, 300);
        gradient.addColorStop(0, 'rgba(84, 104, 255, 0.4)'); // blue semi-transparent
        gradient.addColorStop(1, 'rgba(84, 104, 255, 0.0)');

        customerTrendChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Daily New Customers',
                    data: dataPoints,
                    borderColor: '#5468FF',
                    backgroundColor: gradient,
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true,
                    pointBackgroundColor: '#fff',
                    pointBorderColor: '#5468FF',
                    pointBorderWidth: 2,
                    pointRadius: 3,
                    pointHoverRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(15, 23, 42, 0.9)',
                        titleColor: '#fff',
                        bodyColor: '#cbd5e1',
                        borderColor: 'rgba(255,255,255,0.1)',
                        borderWidth: 1,
                        padding: 12
                    }
                },
                scales: {
                    x: {
                        grid: { display: false, drawBorder: false },
                        ticks: { color: '#64748b' }
                    },
                    y: {
                        grid: {
                            color: 'rgba(255,255,255,0.05)',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#64748b',
                            precision: 0
                        },
                        beginAtZero: true
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                }
            }
        });
    }

    // ─── Excel Export ─────────────────────────────────────────────────────
    exportBtn.addEventListener('click', () => {
        if (!currentStats) return;
        const ovFrom = document.getElementById('overviewFrom')?.value || '';
        const ovTo   = document.getElementById('overviewTo')?.value   || '';

        const { master, stats } = currentStats;

        function toIndian(num) {
            num = Math.round(num);
            const s   = String(num);
            const len = s.length;
            if (len <= 3) return s;
            let result = s.slice(-3);
            let rest   = s.slice(0, len - 3);
            while (rest.length > 2) {
                result = rest.slice(-2) + ',' + result;
                rest   = rest.slice(0, rest.length - 2);
            }
            if (rest.length) result = rest + ',' + result;
            return result;
        }

        const discountPct = stats.loyalty_discount_pct;
        const pctStr      = Math.abs(discountPct - Math.round(discountPct)) < 0.005
            ? Math.round(discountPct) + '%'
            : discountPct.toFixed(2) + '%';

        const worksheetData = [
            [`Refer & Earn Report (${ovFrom} to ${ovTo})`, ''],
            ['Total Customer Count',           master.total_customer_count],
            ['Total Bonus Point Given',         Math.round(master.total_bonus_point_given)],
            ['Total Purchase Count',            stats.purchase_count],
            ['Total Redeemed Count',            stats.redeemed_count],
            ['Total Point Redeemed Value',      Math.round(stats.point_redeemed_value)],
            ['Total Redeemed Purchase Value',   Math.round(stats.redeemed_purchase_value)],
            ['Loyalty Point Discount %',        pctStr],
            ['Average Purchase Value',          Math.round(stats.avg_purchase_value)],
            ['Average Loyalty Point Redemption',Math.round(stats.avg_loyalty_redemption)]
        ];

        const ws = XLSX.utils.aoa_to_sheet(worksheetData);
        ws['!cols'] = [{ wch: 38 }, { wch: 20 }];

        // ─── Apply Colorful Design Motif ─────────────────────────────────
        const themeBlue = '1F497D';
        const themeBg = 'DCE6F1';   

        const borderAll = {
            top: { style: 'thin', color: { auto: 1 } },
            bottom: { style: 'thin', color: { auto: 1 } },
            left: { style: 'thin', color: { auto: 1 } },
            right: { style: 'thin', color: { auto: 1 } }
        };

        const centered = { horizontal: 'center', vertical: 'center' };
        const leftAlign = { horizontal: 'left', vertical: 'center' };
        const rightAlign = { horizontal: 'right', vertical: 'center' };

        const titleStyle = { 
            font: { bold: true, sz: 14, color: { rgb: themeBlue } }, 
            fill: { fgColor: { rgb: themeBg } }, 
            alignment: centered, border: borderAll
        };
        const labelStyle = { 
            font: { bold: true, sz: 12, color: { rgb: themeBlue } }, 
            fill: { fgColor: { rgb: 'F5F7FA' } },
            alignment: leftAlign, border: borderAll
        };
        const valStyle = { 
            font: { sz: 12, color: { rgb: themeBlue } }, 
            alignment: rightAlign, border: borderAll
        };

        const range = XLSX.utils.decode_range(ws['!ref']);
        for(let R = range.s.r; R <= range.e.r; ++R) {
            for(let C = range.s.c; C <= range.e.c; ++C) {
                const cellRef = XLSX.utils.encode_cell({c:C, r:R});
                if(!ws[cellRef]) ws[cellRef] = { v: '', t: 's' };

                if(R === 0) {
                    ws[cellRef].s = titleStyle;
                } else {
                    if (C === 0) ws[cellRef].s = labelStyle; // Metric Name
                    else ws[cellRef].s = valStyle; // Value
                }
            }
        }

        ws['!merges'] = [{ s: { r: 0, c: 0 }, e: { r: 0, c: 1 } }];
        // ─────────────────────────────────────────────────────────────────

        const wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, 'Refer-Earn-Report');
        XLSX.writeFile(wb, `Refer_Earn_Report_${ovFrom || 'all'}_to_${ovTo || 'all'}.xlsx`);
    });

    // ─── Birth Month Report ───────────────────────────────────────────────
    let birthMonthData = null;

    async function loadBirthMonthReport() {
        try {
            const res = await fetch('/api/birth-month-report');
            birthMonthData = await res.json();
            const tbody = document.getElementById('birthMonthTableBody');
            if (tbody) {
                tbody.innerHTML = birthMonthData.map(row => `<tr><td>${row.month}</td><td>${row.count}</td></tr>`).join('');
            }
        } catch (err) { console.error('Birth month load error:', err); }
    }

    document.getElementById('birthMonthExportBtn')?.addEventListener('click', () => {
        if (!birthMonthData) return;
        const ws = XLSX.utils.json_to_sheet(birthMonthData);
        const wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, 'BirthMonths');
        XLSX.writeFile(wb, 'Birth_Month_Report.xlsx');
    });

    // ─── Age-wise Report ──────────────────────────────────────────────────
    let ageBarChartInstance = null;
    let ageReportData       = null;   // cached for Excel export

    async function loadAgeReport(start = '', end = '') {
        try {
            const res  = await fetch(`/api/age-report?start=${start}&end=${end}`);
            const data = await res.json();

            if (data.error) {
                console.error('Age report error:', data.error);
                return;
            }

            // Cache for export
            ageReportData = data;

            // Show reference date
            const refDateEl = document.getElementById('ageRefDate');
            if (refDateEl) refDateEl.textContent = `As of ${data.reference_date}`;

            // Populate table
            const tbody = document.getElementById('ageTableBody');
            tbody.innerHTML = '';
            data.bands.forEach((row, i) => {
                const tr = document.createElement('tr');
                tr.style.opacity   = '0';
                tr.style.transform = 'translateX(-12px)';
                tr.innerHTML = `
                    <td>${row.age_group}</td>
                    <td>${row.count.toLocaleString('en-IN')}</td>
                `;
                tbody.appendChild(tr);

                // Staggered fade-in
                setTimeout(() => {
                    tr.style.transition = 'all 0.35s ease';
                    tr.style.opacity    = '1';
                    tr.style.transform  = 'translateX(0)';
                }, 60 * i);
            });

            // Total row
            const totalEl = document.getElementById('ageTotalCount');
            if (totalEl) totalEl.textContent = data.total.toLocaleString('en-IN');

            // Bar Chart
            const labels = data.bands.map(b => b.age_group);
            const counts = data.bands.map(b => b.count);
            const maxVal = Math.max(...counts);

            const ctx = document.getElementById('ageBarChart').getContext('2d');

            if (ageBarChartInstance) ageBarChartInstance.destroy();

            ageBarChartInstance = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels,
                    datasets: [{
                        label: 'Users',
                        data: counts,
                        backgroundColor: counts.map(v => {
                            const ratio = v / maxVal;
                            const r = Math.round(59  + (16  - 59)  * (1 - ratio));
                            const g = Math.round(130 + (185 - 130) * (1 - ratio));
                            const b = Math.round(246 + (129 - 246) * (1 - ratio));
                            return `rgba(${r},${g},${b},0.75)`;
                        }),
                        borderColor: counts.map(v => {
                            const ratio = v / maxVal;
                            const r = Math.round(59  + (16  - 59)  * (1 - ratio));
                            const g = Math.round(130 + (185 - 130) * (1 - ratio));
                            const b = Math.round(246 + (129 - 246) * (1 - ratio));
                            return `rgba(${r},${g},${b},1)`;
                        }),
                        borderWidth: 1.5,
                        borderRadius: 8,
                        borderSkipped: false
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: { duration: 900, easing: 'easeOutQuart' },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: 'rgba(15,23,42,0.95)',
                            titleColor: '#f8fafc',
                            bodyColor: '#94a3b8',
                            borderColor: 'rgba(255,255,255,0.1)',
                            borderWidth: 1,
                            padding: 12,
                            callbacks: {
                                label: ctx => ` ${ctx.parsed.y.toLocaleString('en-IN')} users`
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: { color: 'rgba(255,255,255,0.04)' },
                            ticks: { color: '#94a3b8', font: { size: 12 } }
                        },
                        y: {
                            grid: { color: 'rgba(255,255,255,0.04)' },
                            ticks: {
                                color: '#94a3b8',
                                font: { size: 12 },
                                callback: v => v.toLocaleString('en-IN')
                            },
                            beginAtZero: true
                        }
                    }
                }
            });

        } catch (err) {
            console.error('Failed to load age report:', err);
        }
    }

    // Load age report on page load
    loadAgeReport();

    // ─── Age Date Filter Buttons ───────────────────────────────────────────
    document.getElementById('ageApplyFilter')?.addEventListener('click', () => {
        const s = document.getElementById('ageFrom').value;
        const e = document.getElementById('ageTo').value;
        loadAgeReport(s, e);
    });

    document.getElementById('ageClearFilter')?.addEventListener('click', () => {
        document.getElementById('ageFrom').value = '';
        document.getElementById('ageTo').value = '';
        loadAgeReport();
    });

    // ─── Age Report Excel Export ───────────────────────────────────────────
    document.getElementById('ageExportBtn').addEventListener('click', () => {
        if (!ageReportData) return;

        const today   = ageReportData.reference_date.replace(/-/g, '_');
        const rows    = ageReportData.bands;
        const total   = ageReportData.total;

        // Build sheet data
        const sheetData = [
            ['Refer & Earn Age-wise report', ''],
            ['Age Group', 'Count'],
            ...rows.map(r => [r.age_group, r.count]),
            ['Total', total]
        ];

        const ws = XLSX.utils.aoa_to_sheet(sheetData);

        // Column widths
        ws['!cols'] = [{ wch: 25 }, { wch: 15 }];

        // Colors
        const themeBlue = '1F497D'; // Dark blue text
        const themeBg = 'DCE6F1';   // Light blue fill

        // Base styles
        const borderAll = {
            top: { style: 'thin', color: { auto: 1 } },
            bottom: { style: 'thin', color: { auto: 1 } },
            left: { style: 'thin', color: { auto: 1 } },
            right: { style: 'thin', color: { auto: 1 } }
        };
        const centered = { horizontal: 'center', vertical: 'center' };

        const titleStyle = { 
            font: { bold: true, sz: 14, color: { rgb: themeBlue } }, 
            fill: { fgColor: { rgb: themeBg } }, 
            alignment: centered,
            border: borderAll
        };
        const headerStyle = { 
            font: { bold: true, sz: 12, color: { rgb: themeBlue } }, 
            fill: { fgColor: { rgb: themeBg } }, 
            alignment: centered,
            border: borderAll
        };
        const dataStyle = { 
            font: { sz: 11, color: { auto: 1 } }, 
            alignment: centered,
            border: borderAll
        };
        const totalStyle = { 
            font: { bold: true, sz: 12, color: { rgb: themeBlue } }, 
            fill: { fgColor: { rgb: themeBg } }, 
            alignment: centered,
            border: borderAll
        };

        // Apply styles to all cells
        const range = XLSX.utils.decode_range(ws['!ref']);
        for(let R = range.s.r; R <= range.e.r; ++R) {
            for(let C = range.s.c; C <= range.e.c; ++C) {
                const cellRef = XLSX.utils.encode_cell({c:C, r:R});
                if(!ws[cellRef]) ws[cellRef] = { v: '', t: 's' };

                if(R === 0) {
                    ws[cellRef].s = titleStyle;
                } else if(R === 1) {
                    ws[cellRef].s = headerStyle;
                } else if(R === range.e.r) {
                    ws[cellRef].s = totalStyle;
                } else {
                    ws[cellRef].s = dataStyle;
                }
            }
        }

        // Merge title across A1:B1
        ws['!merges'] = [{ s: { r: 0, c: 0 }, e: { r: 0, c: 1 } }];

        const wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, 'Age-wise Report');
        XLSX.writeFile(wb, `Age_Report_${today}.xlsx`);
    });

    // ─── District-wise Report ───────────────────────────────────────────────
    let districtReportData = null;

    async function loadDistrictReport(start = '', end = '') {
        try {
            const res  = await fetch(`/api/district-report?start=${start}&end=${end}`);
            const data = await res.json();

            if (data.error) {
                console.error('District report error:', data.error);
                return;
            }

            districtReportData = data;

            const tbody = document.getElementById('districtTableBody');
            tbody.innerHTML = '';
            
            data.districts.forEach((row, i) => {
                const tr = document.createElement('tr');
                tr.style.opacity   = '0';
                tr.style.transform = 'translateY(10px)';
                tr.innerHTML = `
                    <td>${row.rank}</td>
                    <td>${row.district}</td>
                    <td>${row.count.toLocaleString('en-IN')}</td>
                `;
                tbody.appendChild(tr);

                // Staggered fade-in
                setTimeout(() => {
                    tr.style.transition = 'all 0.35s ease';
                    tr.style.opacity    = '1';
                    tr.style.transform  = 'translateY(0)';
                }, 40 * i);
            });

            // Total row
            const totalEl = document.getElementById('districtTotalCount');
            if (totalEl) totalEl.textContent = data.total.toLocaleString('en-IN');

        } catch (err) {
            console.error('Failed to load district report:', err);
        }
    }

    // ─── District Date Filter Buttons ─────────────────────────────────────
    document.getElementById('districtApplyFilter')?.addEventListener('click', () => {
        const s = document.getElementById('districtFrom').value;
        const e = document.getElementById('districtTo').value;
        loadDistrictReport(s, e);
    });

    document.getElementById('districtClearFilter')?.addEventListener('click', () => {
        document.getElementById('districtFrom').value = '';
        document.getElementById('districtTo').value = '';
        loadDistrictReport();
    });

    // ─── District Excel Export ──────────────────────────────────────────────
    document.getElementById('districtExportBtn').addEventListener('click', () => {
        if (!districtReportData) return;

        const dateString = new Date().toISOString().split('T')[0];
        const rows = districtReportData.districts;
        const total = districtReportData.total;

        // Build sheet data
        const sheetData = [
            ['Refer & Earn Top 20 Districts', '', ''],
            ['Rank', 'District', 'Count'],
            ...rows.map(r => [r.rank, r.district, r.count]),
            ['', 'Total', total]
        ];

        const ws = XLSX.utils.aoa_to_sheet(sheetData);

        // Column widths
        ws['!cols'] = [{ wch: 10 }, { wch: 25 }, { wch: 15 }];

        // Colors
        const themeBlue = '1F497D'; // Dark blue text
        const themeBg = 'DCE6F1';   // Light blue fill

        // Base styles
        const borderAll = {
            top: { style: 'thin', color: { auto: 1 } },
            bottom: { style: 'thin', color: { auto: 1 } },
            left: { style: 'thin', color: { auto: 1 } },
            right: { style: 'thin', color: { auto: 1 } }
        };
        const centered = { horizontal: 'center', vertical: 'center' };

        const titleStyle = { 
            font: { bold: true, sz: 14, color: { rgb: themeBlue } }, 
            fill: { fgColor: { rgb: themeBg } }, 
            alignment: centered,
            border: borderAll
        };
        const headerStyle = { 
            font: { bold: true, sz: 12, color: { rgb: themeBlue } }, 
            fill: { fgColor: { rgb: themeBg } }, 
            alignment: centered,
            border: borderAll
        };
        const dataStyle = { 
            font: { sz: 11, color: { auto: 1 } }, 
            alignment: centered,
            border: borderAll
        };
        const totalStyle = { 
            font: { bold: true, sz: 12, color: { rgb: themeBlue } }, 
            fill: { fgColor: { rgb: themeBg } }, 
            alignment: centered,
            border: borderAll
        };

        // Apply styles
        const range = XLSX.utils.decode_range(ws['!ref']);
        for(let R = range.s.r; R <= range.e.r; ++R) {
            for(let C = range.s.c; C <= range.e.c; ++C) {
                const cellRef = XLSX.utils.encode_cell({c:C, r:R});
                if(!ws[cellRef]) ws[cellRef] = { v: '', t: 's' };

                if(R === 0) {
                    ws[cellRef].s = titleStyle;
                } else if(R === 1) {
                    ws[cellRef].s = headerStyle;
                } else if(R === range.e.r) {
                    // Total row
                    if (C === 0) ws[cellRef].s = dataStyle; // empty rank cell
                    else ws[cellRef].s = totalStyle;
                } else {
                    ws[cellRef].s = dataStyle;
                }
            }
        }

        // Merge title across A1:C1
        ws['!merges'] = [{ s: { r: 0, c: 0 }, e: { r: 0, c: 2 } }];

        const wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, 'District Report');
        XLSX.writeFile(wb, `District_Report_${dateString}.xlsx`);
    });
    // ─── Birth Month Report ────────────────────────────────────────────────
    async function loadBirthMonthReport() {
        try {
            const res  = await fetch('/api/birth-month-summary');
            const data = await res.json();

            if (data.error) {
                console.error('Birth month report error:', data.error);
                return;
            }

            const tbody = document.getElementById('birthMonthTableBody');
            tbody.innerHTML = '';
            
            data.months.forEach((row, i) => {
                const tr = document.createElement('tr');
                tr.style.opacity   = '0';
                tr.style.transform = 'translateY(10px)';
                
                tr.innerHTML = `
                    <td>${row.month}</td>
                    <td style="text-align:right">${row.count.toLocaleString('en-IN')}</td>
                    <td style="text-align:right">
                        <button class="btn-mini-export" data-month-id="${row.month_id}" data-month-name="${row.month}">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                                <polyline points="7 10 12 15 17 10"/>
                                <line x1="12" y1="15" x2="12" y2="3"/>
                            </svg>
                            Download
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);

                const btn = tr.querySelector('.btn-mini-export');
                btn.addEventListener('click', () => exportBirthMonthDetails(btn, row.month_id, row.month));

                setTimeout(() => {
                    tr.style.transition = 'all 0.35s ease';
                    tr.style.opacity    = '1';
                    tr.style.transform  = 'translateY(0)';
                }, 40 * i);
            });

            const totalEl = document.getElementById('birthMonthTotalCount');
            if (totalEl) totalEl.textContent = data.total.toLocaleString('en-IN');

        } catch (err) {
            console.error('Failed to load birth month report:', err);
        }
    }

    async function exportBirthMonthDetails(btnNode, monthId, monthName) {
        try {
            const originalText = btnNode.innerHTML;
            btnNode.innerHTML = 'Downloading...';
            btnNode.disabled = true;

            const res = await fetch(`/api/birth-month-export?month=${monthId}`);
            const payload = await res.json();
            
            if (payload.error) throw new Error(payload.error);

            const rows = payload.data;
            const sheetData = [
                [`Refer & Earn Birth Month: ${monthName}`, '', ''],
                ['Name', 'Phone', 'Date of Birth'],
                ...rows.map(r => [r.name, r.phone, r.dob])
            ];

            const ws = XLSX.utils.aoa_to_sheet(sheetData);
            ws['!cols'] = [{ wch: 30 }, { wch: 15 }, { wch: 15 }];

            const themeBlue = '1F497D';
            const themeBg = 'DCE6F1';   

            const borderAll = {
                top: { style: 'thin', color: { auto: 1 } },
                bottom: { style: 'thin', color: { auto: 1 } },
                left: { style: 'thin', color: { auto: 1 } },
                right: { style: 'thin', color: { auto: 1 } }
            };
            const centered = { horizontal: 'center', vertical: 'center' };

            const titleStyle = { 
                font: { bold: true, sz: 14, color: { rgb: themeBlue } }, 
                fill: { fgColor: { rgb: themeBg } }, 
                alignment: centered, border: borderAll
            };
            const headerStyle = { 
                font: { bold: true, sz: 12, color: { rgb: themeBlue } }, 
                fill: { fgColor: { rgb: themeBg } }, 
                alignment: centered, border: borderAll
            };
            const dataStyle = { 
                font: { sz: 11, color: { auto: 1 } }, 
                alignment: centered, border: borderAll
            };

            const range = XLSX.utils.decode_range(ws['!ref']);
            for(let R = range.s.r; R <= range.e.r; ++R) {
                for(let C = range.s.c; C <= range.e.c; ++C) {
                    const cellRef = XLSX.utils.encode_cell({c:C, r:R});
                    if(!ws[cellRef]) ws[cellRef] = { v: '', t: 's' };

                    if(R === 0) ws[cellRef].s = titleStyle;
                    else if(R === 1) ws[cellRef].s = headerStyle;
                    else ws[cellRef].s = dataStyle;
                }
            }

            ws['!merges'] = [{ s: { r: 0, c: 0 }, e: { r: 0, c: 2 } }];

            const wb = XLSX.utils.book_new();
            XLSX.utils.book_append_sheet(wb, ws, monthName);
            
            const dateString = new Date().toISOString().split('T')[0];
            XLSX.writeFile(wb, `Birthdays_${monthName}_${dateString}.xlsx`);

            btnNode.innerHTML = originalText;
            btnNode.disabled = false;

        } catch (err) {
            console.error('Failed to export:', err);
            btnNode.innerHTML = 'Error!';
            setTimeout(() => { btnNode.innerHTML = 'Download'; btnNode.disabled = false; }, 2000);
        }
    }

    // ─── SPA Tab Navigation ─────────────────────────────────────────────────
    document.querySelectorAll('.tab-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            
            // 1. Update active styling on sidebar links
            document.querySelectorAll('.tab-link').forEach(l => l.classList.remove('active'));
            link.classList.add('active');
            
            // 2. Hide all tab sections, then show the targeted one
            document.querySelectorAll('.tab-section').forEach(sec => sec.classList.remove('active-tab'));
            
            const targetId = link.getAttribute('data-target');
            if (targetId) {
                const targetEl = document.getElementById(targetId);
                if (targetEl) targetEl.classList.add('active-tab');
            }

            // 3. If Overview is clicked, always default to Core Performance tab
            if (targetId === 'overviewSection') {
                document.querySelectorAll('.overview-tab-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.overview-panel').forEach(p => p.classList.remove('active-overview-panel'));
                const coreBtn   = document.getElementById('coreMetricsTab');
                const corePanel = document.getElementById('coreMetricsPanel');
                if (coreBtn)   coreBtn.classList.add('active');
                if (corePanel) corePanel.classList.add('active-overview-panel');
            }

            // 4. If User Insights is clicked, always default to Age-wise Distribution tab
            if (targetId === 'userInsightsSection') {
                document.querySelectorAll('.overview-tab-btn[data-insights-target]').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('#userInsightsSection .overview-panel').forEach(p => p.classList.remove('active-overview-panel'));
                const ageBtn   = document.getElementById('ageInsightsTab');
                const agePanel = document.getElementById('ageInsightsPanel');
                if (ageBtn)   ageBtn.classList.add('active');
                if (agePanel) agePanel.classList.add('active-overview-panel');
            }
        });
    });

    // Ensure default panels are visible on initial page load
    (function initDefaultTabs() {
        // Core Performance (Overview)
        document.querySelectorAll('.overview-panel').forEach(p => p.classList.remove('active-overview-panel'));
        document.querySelectorAll('.overview-tab-btn').forEach(b => b.classList.remove('active'));
        const coreBtn   = document.getElementById('coreMetricsTab');
        const corePanel = document.getElementById('coreMetricsPanel');
        if (coreBtn)   coreBtn.classList.add('active');
        if (corePanel) corePanel.classList.add('active-overview-panel');

        // Age-wise Distribution (User Insights)
        const ageBtn   = document.getElementById('ageInsightsTab');
        const agePanel = document.getElementById('ageInsightsPanel');
        if (ageBtn)   ageBtn.classList.add('active');
        if (agePanel) agePanel.classList.add('active-overview-panel');
    })();


    // ─── Anniversary Month Report ──────────────────────────────────────────
    async function loadAnniversaryMonthReport() {
        try {
            const res  = await fetch('/api/anniversary-month-summary');
            const data = await res.json();

            if (data.error) {
                console.error('Anniversary month report error:', data.error);
                return;
            }

            const tbody = document.getElementById('anniversaryMonthTableBody');
            tbody.innerHTML = '';
            
            data.months.forEach((row, i) => {
                const tr = document.createElement('tr');
                tr.style.opacity   = '0';
                tr.style.transform = 'translateY(10px)';
                
                tr.innerHTML = `
                    <td>${row.month}</td>
                    <td style="text-align:right">${row.count.toLocaleString('en-IN')}</td>
                    <td style="text-align:right">
                        <button class="btn-mini-export" data-month-id="${row.month_id}" data-month-name="${row.month}">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                                <polyline points="7 10 12 15 17 10"/>
                                <line x1="12" y1="15" x2="12" y2="3"/>
                            </svg>
                            Download
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);

                const btn = tr.querySelector('.btn-mini-export');
                btn.addEventListener('click', () => exportAnniversaryMonthDetails(btn, row.month_id, row.month));

                setTimeout(() => {
                    tr.style.transition = 'all 0.35s ease';
                    tr.style.opacity    = '1';
                    tr.style.transform  = 'translateY(0)';
                }, 40 * i);
            });

            const totalEl = document.getElementById('anniversaryMonthTotalCount');
            if (totalEl) totalEl.textContent = data.total.toLocaleString('en-IN');

        } catch (err) {
            console.error('Failed to load anniversary month report:', err);
        }
    }

    async function exportAnniversaryMonthDetails(btnNode, monthId, monthName) {
        try {
            const originalText = btnNode.innerHTML;
            btnNode.innerHTML = 'Downloading...';
            btnNode.disabled = true;

            const res = await fetch(`/api/anniversary-month-export?month=${monthId}`);
            const payload = await res.json();
            
            if (payload.error) throw new Error(payload.error);

            const rows = payload.data;
            const sheetData = [
                [`Refer & Earn Anniversary Month: ${monthName}`, '', ''],
                ['Name', 'Phone', 'Wedding Anniversary Date'],
                ...rows.map(r => [r.name, r.phone, r.anniversary])
            ];

            const ws = XLSX.utils.aoa_to_sheet(sheetData);
            ws['!cols'] = [{ wch: 30 }, { wch: 15 }, { wch: 25 }];

            const themeBlue = '1F497D';
            const themeBg = 'DCE6F1';   

            const borderAll = {
                top: { style: 'thin', color: { auto: 1 } },
                bottom: { style: 'thin', color: { auto: 1 } },
                left: { style: 'thin', color: { auto: 1 } },
                right: { style: 'thin', color: { auto: 1 } }
            };
            const centered = { horizontal: 'center', vertical: 'center' };

            const titleStyle = { 
                font: { bold: true, sz: 14, color: { rgb: themeBlue } }, 
                fill: { fgColor: { rgb: themeBg } }, 
                alignment: centered, border: borderAll
            };
            const headerStyle = { 
                font: { bold: true, sz: 12, color: { rgb: themeBlue } }, 
                fill: { fgColor: { rgb: themeBg } }, 
                alignment: centered, border: borderAll
            };
            const dataStyle = { 
                font: { sz: 11, color: { auto: 1 } }, 
                alignment: centered, border: borderAll
            };

            const range = XLSX.utils.decode_range(ws['!ref']);
            for(let R = range.s.r; R <= range.e.r; ++R) {
                for(let C = range.s.c; C <= range.e.c; ++C) {
                    const cellRef = XLSX.utils.encode_cell({c:C, r:R});
                    if(!ws[cellRef]) ws[cellRef] = { v: '', t: 's' };

                    if(R === 0) ws[cellRef].s = titleStyle;
                    else if(R === 1) ws[cellRef].s = headerStyle;
                    else ws[cellRef].s = dataStyle;
                }
            }

            ws['!merges'] = [{ s: { r: 0, c: 0 }, e: { r: 0, c: 2 } }];

            const wb = XLSX.utils.book_new();
            XLSX.utils.book_append_sheet(wb, ws, monthName);
            
            const dateString = new Date().toISOString().split('T')[0];
            XLSX.writeFile(wb, `Anniversaries_${monthName}_${dateString}.xlsx`);

            btnNode.innerHTML = originalText;
            btnNode.disabled = false;

        } catch (err) {
            console.error('Failed to export:', err);
            btnNode.innerHTML = 'Error!';
            setTimeout(() => { btnNode.innerHTML = 'Download'; btnNode.disabled = false; }, 2000);
        }
    }

    // Load reports on page load
    loadAgeReport();
    loadDistrictReport();
    loadBirthMonthReport();
    loadAnniversaryMonthReport();

    // ─── Customer Classification Report ─────────────────────────────────────
    let classificationDoughnutInstance = null;
    let classificationData = null;

    async function loadCustomerClassification(start = '', end = '') {
        const params = (start && end) ? `?start=${start}&end=${end}` : '';

        try {
            const res  = await fetch(`/api/customer-classification${params}`);
            const data = await res.json();

            if (data.error) {
                console.error('Classification error:', data.error);
                return;
            }

            classificationData = data;

            // ── Dynamic subtitle ─────────────────────────────────────────────
            function fmtCutoff(dateStr) {
                const months = ['January','February','March','April','May','June',
                                'July','August','September','October','November','December'];
                const [y, m, d] = dateStr.split('-');
                return `${months[parseInt(m,10)-1]} ${parseInt(d,10)}, ${y}`;
            }
            const cutoffEl = document.getElementById('ccCutoffDisplay');
            if (cutoffEl && data.cutoff_date) {
                const endFmt   = fmtCutoff(data.date_range.end);
                const startFmt = fmtCutoff(data.cutoff_date);
                cutoffEl.textContent = `${startFmt} – ${endFmt}`;
            }

            // ── KPI Cards ────────────────────────────────────────────────────
            const baseSizeEl = document.getElementById('ccBaseSize');
            if (baseSizeEl) {
                baseSizeEl.textContent = (data.total_buyers || 0).toLocaleString('en-IN');
            }

            const repeatEl = document.getElementById('ccRepeatCount');
            if (repeatEl) repeatEl.textContent = data.repeat_count.toLocaleString('en-IN');

            const repeatPctEl = document.getElementById('ccRepeatPct');
            if (repeatPctEl) repeatPctEl.textContent = data.repeat_pct + '%';

            const repeatSubEl = document.getElementById('ccRepeatSub');
            if (repeatSubEl && data.cutoff_date) {
                repeatSubEl.textContent = `Purchased before ${fmtCutoff(data.cutoff_date)}`;
            }

            const newEl = document.getElementById('ccNewCount');
            if (newEl) newEl.textContent = data.new_count.toLocaleString('en-IN');

            const newPctEl = document.getElementById('ccNewPct');
            if (newPctEl) newPctEl.textContent = data.new_pct + '%';

            const newSubEl = document.getElementById('ccNewSub');
            if (newSubEl && data.cutoff_date) {
                newSubEl.textContent = `First purchase on/after ${fmtCutoff(data.cutoff_date)}`;
            }

            // ── Summary Table (2 rows) ────────────────────────────────────────
            const tbody = document.getElementById('classificationTableBody');
            if (tbody) {
                const rows = [
                    { type: '🔄 Repeat Customers', count: data.repeat_count, pct: data.repeat_pct, cls: 'repeat' },
                    { type: '✨ New Customers',     count: data.new_count,    pct: data.new_pct,    cls: 'new'    }
                ];

                tbody.innerHTML = '';
                rows.forEach((row, i) => {
                    const tr = document.createElement('tr');
                    tr.style.opacity   = '0';
                    tr.style.transform = 'translateY(10px)';
                    const pctColor = row.cls === 'repeat' ? '#f59e0b' : '#10b981';
                    tr.innerHTML = `
                        <td>${row.type}</td>
                        <td style="text-align:right;font-weight:700">${row.count.toLocaleString('en-IN')}</td>
                        <td style="text-align:right">
                            <span style="color:${pctColor};font-weight:600">${row.pct}%</span>
                        </td>
                    `;
                    tbody.appendChild(tr);
                    setTimeout(() => {
                        tr.style.transition = 'all 0.35s ease';
                        tr.style.opacity    = '1';
                        tr.style.transform  = 'translateY(0)';
                    }, 80 * i);
                });

                const tableTotal = document.getElementById('ccTableTotal');
                if (tableTotal) tableTotal.textContent = (data.total_buyers || 0).toLocaleString('en-IN');
            }

            // ── Doughnut Chart (2 segments: Repeat + New) ─────────────────────
            const ctx = document.getElementById('classificationDoughnut');
            if (ctx) {
                if (classificationDoughnutInstance) classificationDoughnutInstance.destroy();

                classificationDoughnutInstance = new Chart(ctx.getContext('2d'), {
                    type: 'doughnut',
                    data: {
                        labels: ['Repeat Customers', 'New Customers'],
                        datasets: [{
                            data:            [data.repeat_count, data.new_count],
                            backgroundColor: ['rgba(245,158,11,0.85)', 'rgba(16,185,129,0.85)'],
                            borderColor:     ['#f59e0b', '#10b981'],
                            borderWidth:     2,
                            hoverOffset:     10
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        cutout: '68%',
                        animation: { duration: 900, easing: 'easeOutQuart' },
                        plugins: {
                            legend: { display: false },
                            tooltip: {
                                backgroundColor: 'rgba(15,23,42,0.95)',
                                titleColor: '#f8fafc',
                                bodyColor:  '#94a3b8',
                                borderColor: 'rgba(255,255,255,0.1)',
                                borderWidth: 1,
                                padding: 12,
                                callbacks: {
                                    label: ctx => {
                                        const val   = ctx.parsed;
                                        const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                                        const pct   = ((val / total) * 100).toFixed(2);
                                        return ` ${val.toLocaleString('en-IN')} (${pct}%)`;
                                    }
                                }
                            }
                        }
                    }
                });
            }

        } catch (err) {
            console.error('Failed to load customer classification:', err);
        }
    }

    // ─── Classification Excel Export ───────────────────────────────────────────────────
    document.getElementById('classificationExportBtn')?.addEventListener('click', () => {
        if (!classificationData) return;

        const d = classificationData;
        const dateStr = new Date().toISOString().split('T')[0];

        const rangeNote = d.date_range
            ? `Date range: ${d.date_range.start} to ${d.date_range.end}`
            : '';

        const sheetData = [
            ['Refer & Earn – Customer Classification Report', '', ''],
            ['Customer Type', 'Count', 'Share %'],
            ['Repeat Customers', d.repeat_count, d.repeat_pct + '%'],
            ['New Customers',    d.new_count,    d.new_pct    + '%'],
            ['Total Buyers (in range)', d.total_buyers || (d.repeat_count + d.new_count), '100%'],
            [],
            [`Note: Repeat = had a purchase before ${d.cutoff_date}. New = first-ever purchase is on/after ${d.cutoff_date}. Classification is dynamic based on selected filter date.`, '', ''],
            [rangeNote, '', ''],
            ['Total R&E Participants (programme base)', d.total_participants, '']
        ];

        const ws = XLSX.utils.aoa_to_sheet(sheetData);
        ws['!cols'] = [{ wch: 50 }, { wch: 18 }, { wch: 12 }];

        const themeBlue = '1F497D';
        const themeBg   = 'DCE6F1';
        const borderAll = {
            top:    { style: 'thin', color: { auto: 1 } },
            bottom: { style: 'thin', color: { auto: 1 } },
            left:   { style: 'thin', color: { auto: 1 } },
            right:  { style: 'thin', color: { auto: 1 } }
        };
        const centered   = { horizontal: 'center', vertical: 'center' };
        const titleStyle = { font: { bold: true, sz: 14, color: { rgb: themeBlue } }, fill: { fgColor: { rgb: themeBg } }, alignment: centered, border: borderAll };
        const headerStyle= { font: { bold: true, sz: 12, color: { rgb: themeBlue } }, fill: { fgColor: { rgb: themeBg } }, alignment: centered, border: borderAll };
        const dataStyle  = { font: { sz: 11, color: { auto: 1 } }, alignment: centered, border: borderAll };
        const totalStyle = { font: { bold: true, sz: 12, color: { rgb: themeBlue } }, fill: { fgColor: { rgb: 'E2EFDA' } }, alignment: centered, border: borderAll };

        const range = XLSX.utils.decode_range(ws['!ref']);
        for (let R = range.s.r; R <= range.e.r; ++R) {
            for (let C = range.s.c; C <= range.e.c; ++C) {
                const ref = XLSX.utils.encode_cell({ c: C, r: R });
                if (!ws[ref]) ws[ref] = { v: '', t: 's' };
                if (R === 0)  ws[ref].s = titleStyle;
                else if (R === 1) ws[ref].s = headerStyle;
                else if (R === 4) ws[ref].s = totalStyle;
                else ws[ref].s = dataStyle;
            }
        }
        ws['!merges'] = [{ s: { r: 0, c: 0 }, e: { r: 0, c: 2 } }];

        const wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, 'Customer Classification');
        XLSX.writeFile(wb, `Customer_Classification_${dateStr}.xlsx`);
    });

    // ─── Classification section filter ───────────────────────────────────────
    document.getElementById('ccApplyFilter')?.addEventListener('click', () => {
        const s = document.getElementById('ccFrom').value;
        const e = document.getElementById('ccTo').value;
        loadCustomerClassification(s, e);
    });
    document.getElementById('ccClearFilter')?.addEventListener('click', () => {
        document.getElementById('ccFrom').value = '';
        document.getElementById('ccTo').value   = '';
        loadCustomerClassification('', '');
    });

    // ─── Repeat Customer Metrics date filter ─────────────────────────────────
    document.getElementById('rcApplyFilter')?.addEventListener('click', () => {
        const s = document.getElementById('rcFrom').value;
        const e = document.getElementById('rcTo').value;
        if (!s || !e) { alert('Please select both From and To dates.'); return; }
        fetchRepeatCustomerMetrics(s, e);
    });
    document.getElementById('rcClearFilter')?.addEventListener('click', () => {
        document.getElementById('rcFrom').value = '';
        document.getElementById('rcTo').value   = '';
        fetchRepeatCustomerMetrics('', '');
    });

    // ─── New Customer Metrics date filter ────────────────────────────────────
    document.getElementById('ncApplyFilter')?.addEventListener('click', () => {
        const s = document.getElementById('ncFrom').value;
        const e = document.getElementById('ncTo').value;
        if (!s || !e) { alert('Please select both From and To dates.'); return; }
        fetchNewCustomerMetrics(s, e);
    });
    document.getElementById('ncClearFilter')?.addEventListener('click', () => {
        document.getElementById('ncFrom').value = '';
        document.getElementById('ncTo').value   = '';
        fetchNewCustomerMetrics('', '');
    });

    // ─── Overview Sub-Tab Switching ───────────────────────────────────────────
    let repeatLoaded = false;
    let newCustLoaded = false;
    document.querySelectorAll('.overview-tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            // Update active button
            document.querySelectorAll('.overview-tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Hide all panels, show target
            document.querySelectorAll('.overview-panel').forEach(p => p.classList.remove('active-overview-panel'));
            const targetId = btn.getAttribute('data-overview-target');
            const targetPanel = document.getElementById(targetId);
            if (targetPanel) targetPanel.classList.add('active-overview-panel');

            // Lazy-load repeat/new metrics on first switch
            if (targetId === 'repeatMetricsPanel' && !repeatLoaded) {
                repeatLoaded = true;
                fetchRepeatCustomerMetrics();
            }
            if (targetId === 'newMetricsPanel' && !newCustLoaded) {
                newCustLoaded = true;
                fetchNewCustomerMetrics();
            }
        });
    });

    // ─── User Insights Sub-Tab Switching (Age · Birth Month · Anniversary) ──
    document.querySelectorAll('[data-insights-target]').forEach(btn => {
        btn.addEventListener('click', () => {
            // Update active button
            document.querySelectorAll('[data-insights-target]').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Hide all insights panels, show the target
            const allPanels = ['ageInsightsPanel', 'birthInsightsPanel', 'anniversaryInsightsPanel'];
            allPanels.forEach(id => {
                const el = document.getElementById(id);
                if (el) el.classList.remove('active-overview-panel');
            });
            const targetId = btn.getAttribute('data-insights-target');
            const targetPanel = document.getElementById(targetId);
            if (targetPanel) targetPanel.classList.add('active-overview-panel');
        });
    });

    // ─── Reload classification when its tab is clicked ───────────────────────
    document.querySelectorAll('.tab-link').forEach(link => {
        link.addEventListener('click', () => {
            if (link.getAttribute('data-target') === 'customerClassificationSection') {
                const s = document.getElementById('ccFrom')?.value || '';
                const e = document.getElementById('ccTo')?.value   || '';
                loadCustomerClassification(s, e);
            }
            // Lazy-load cohort analysis on first visit
            if (link.getAttribute('data-target') === 'cohortAnalysisSection' && !window._cohortLoaded) {
                window._cohortLoaded = true;
                fetchCohortAnalysis();
            }
        });
    });

    // Load all sections independently on page load
    loadCustomerClassification();

    // ─── Cohort Analysis ──────────────────────────────────────────────────────
    let _cohortData = null;   // cache API response
    let _cohortView = 'repeat_count';  // current view mode

    function toIndianNum(n) {
        n = Math.round(n);
        const s = String(n);
        if (s.length <= 3) return s;
        let res = s.slice(-3);
        let rest = s.slice(0, s.length - 3);
        while (rest.length > 2) { res = rest.slice(-2) + ',' + res; rest = rest.slice(0, rest.length - 2); }
        if (rest.length) res = rest + ',' + res;
        return res;
    }

    // Format a rupee value as crores with 2 decimal places (e.g. 7058042 => "0.71Cr")
    function toCr(n) {
        const cr = n / 1e7;
        return cr.toFixed(2) + 'Cr';
    }

    function cohortHeatColor(pct, maxPct, view) {
        // Returns rgba string based on how high value is relative to max in column
        const ratio = maxPct > 0 ? Math.min(pct / maxPct, 1) : 0;
        if (view === 'retention') {
            // Blue heatmap
            const alpha = 0.07 + ratio * 0.80;
            const textDark = ratio > 0.55;
            return { bg: `rgba(37,99,235,${alpha.toFixed(2)})`, text: textDark ? '#fff' : '#1e293b' };
        } else if (view === 'repeat_count') {
            // Teal heatmap
            const alpha = 0.07 + ratio * 0.80;
            const textDark = ratio > 0.55;
            return { bg: `rgba(8,145,178,${alpha.toFixed(2)})`, text: textDark ? '#fff' : '#1e293b' };
        } else if (view === 'revenue' || view === 'avg_purchase') {
            // Emerald heatmap
            const alpha = 0.07 + ratio * 0.80;
            const textDark = ratio > 0.55;
            return { bg: `rgba(5,150,105,${alpha.toFixed(2)})`, text: textDark ? '#fff' : '#1e293b' };
        } else {
            // Purple heatmap for bonus
            const alpha = 0.07 + ratio * 0.80;
            const textDark = ratio > 0.55;
            return { bg: `rgba(124,58,237,${alpha.toFixed(2)})`, text: textDark ? '#fff' : '#1e293b' };
        }
    }

    function getCellValue(cell, view) {
        if (!cell) return null;
        if (view === 'retention')    return { display: cell.retention_pct.toFixed(1) + '%', raw: cell.retention_pct };
        if (view === 'repeat_count') return { display: toIndianNum(cell.active), raw: cell.active };
        if (view === 'revenue')      return { display: '₹' + toCr(cell.revenue), raw: cell.revenue };
        if (view === 'avg_purchase') return { display: '₹' + toCr(cell.avg_purchase), raw: cell.avg_purchase };
        if (view === 'bonus')        return { display: toIndianNum(cell.bonus_redeemed), raw: cell.bonus_redeemed };
        return null;
    }

    function buildCohortTable(data, view) {
        const { cohorts, max_offset } = data;
        if (!cohorts || cohorts.length === 0) {
            document.getElementById('cohortTableContainer').innerHTML =
                '<div style="padding:3rem;text-align:center;color:var(--text-muted);">No cohort data available.</div>';
            return;
        }

        // Compute column max values for heatmap scaling (skip offset 0)
        const colMaxRaw = Array(max_offset + 1).fill(0);
        cohorts.forEach(c => {
            c.cells.forEach((cell, idx) => {
                if (!cell || idx === 0) return;
                const v = getCellValue(cell, view);
                if (v && v.raw > colMaxRaw[idx]) colMaxRaw[idx] = v.raw;
            });
        });

        // Build header
        let html = '<table class="cohort-matrix"><thead><tr>';
        html += '<th>Cohort Month</th><th style="text-align:right">New Customers</th>';
        for (let i = 0; i <= max_offset; i++) {
            html += `<th>Month ${i}</th>`;
        }
        html += '</tr></thead><tbody>';

        // Build rows
        cohorts.forEach(c => {
            html += `<tr><td>${c.cohort_label}</td><td style="text-align:right">${toIndianNum(c.cohort_size)}</td>`;
            c.cells.forEach((cell, idx) => {
                if (!cell) {
                    html += '<td class="cohort-cell-empty">—</td>';
                    return;
                }
                if (idx === 0) {
                    // Month 0: always anchor
                    const v = getCellValue(cell, view);
                    const display = view === 'retention' ? '100%' : (v ? v.display : '—');
                    html += `<td class="cohort-cell-m0">${display}</td>`;
                    return;
                }
                const v = getCellValue(cell, view);
                if (!v) { html += '<td class="cohort-cell-empty">—</td>'; return; }
                const { bg, text } = cohortHeatColor(v.raw, colMaxRaw[idx], view);
                const tooltip = `Active: ${toIndianNum(cell.active)}\\nRetention: ${cell.retention_pct.toFixed(1)}%\\nRevenue: ₹${toCr(cell.revenue)}\\nAvg Purchase: ₹${toCr(cell.avg_purchase)}\\nBonus: ${toIndianNum(cell.bonus_redeemed)}`;
                html += `<td class="cohort-cell-data" style="background:${bg};color:${text};" data-tooltip="${tooltip}">${v.display}</td>`;
            });
            html += '</tr>';
        });

        html += '</tbody></table>';
        document.getElementById('cohortTableContainer').innerHTML = html;
    }

    function updateCohortSummary(data) {
        const { cohorts } = data;
        if (!cohorts || !cohorts.length) return;

        const totalCohorts = cohorts.length;
        const totalCustomers = cohorts.reduce((s, c) => s + c.cohort_size, 0);

        // Avg Month-1 retention across cohorts that have Month-1 data
        const m1retentions = cohorts
            .filter(c => c.cells[1])
            .map(c => c.cells[1].retention_pct);
        const avgM1 = m1retentions.length
            ? (m1retentions.reduce((a, b) => a + b, 0) / m1retentions.length).toFixed(1) + '%'
            : '—';

        // Best cohort by Month-1 retention
        let bestLabel = '—', bestPct = 0;
        cohorts.forEach(c => {
            if (c.cells[1] && c.cells[1].retention_pct > bestPct) {
                bestPct = c.cells[1].retention_pct;
                bestLabel = c.cohort_label;
            }
        });

        document.getElementById('cohortTotalCohorts').textContent   = totalCohorts;
        document.getElementById('cohortTotalCustomers').textContent  = toIndianNum(totalCustomers);
        document.getElementById('cohortAvgM1Retention').textContent  = avgM1;
        document.getElementById('cohortBestCohort').textContent      = bestLabel;
    }

    async function fetchCohortAnalysis() {
        const container = document.getElementById('cohortTableContainer');
        if (!container) return;
        container.innerHTML = '<div style="padding:3rem;text-align:center;color:var(--text-muted);">⏳ Loading cohort data… This may take a few seconds.</div>';

        try {
            const resp = await fetch('/api/cohort-analysis');
            const data = await resp.json();
            if (data.error) throw new Error(data.error);

            _cohortData = data;
            buildCohortTable(data, _cohortView);
            updateCohortSummary(data);

        } catch(e) {
            container.innerHTML = `<div style="padding:3rem;text-align:center;color:var(--accent-red);">⚠️ Failed to load cohort data: ${e.message}</div>`;
            console.error('Cohort analysis error:', e);
        }
    }

    // View-mode toggle buttons
    document.querySelectorAll('.cohort-view-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.cohort-view-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            _cohortView = btn.getAttribute('data-view');
            if (_cohortData) buildCohortTable(_cohortData, _cohortView);
        });
    });

});
