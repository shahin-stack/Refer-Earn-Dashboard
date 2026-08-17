document.addEventListener('DOMContentLoaded', async function () {
    const dateFrom  = document.getElementById('dateFrom');
    const dateTo    = document.getElementById('dateTo');
    const exportBtn = document.getElementById('exportBtn');

    // Store latest data for Excel export
    let currentStats = null;

    // Initial load
    updateDashboard();

    const mainApplyFilter = document.getElementById('mainApplyFilter');
    if (mainApplyFilter) {
        mainApplyFilter.addEventListener('click', updateDashboard);
    }

    async function updateDashboard() {
        const start = dateFrom.value;
        const end   = dateTo.value;

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
            setCard(1, master.total_customer_count.toLocaleString('en-IN'));

            // Card 2 – Total Bonus Points Given (Indian format)
            setCard(2, fmtPts(master.total_bonus_point_given));

            // Card 3 – Total Purchase Count
            setCard(3, stats.purchase_count.toLocaleString('en-IN'));

            // Card 4 – Total Redeemed Count
            setCard(4, stats.redeemed_count.toLocaleString('en-IN'));

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
            await fetchNewCustomerMetrics(start, end);
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

    async function fetchNewCustomerMetrics(start, end) {
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
            
            document.getElementById('nc-cardTotalCustomers').textContent = toIndian(master.total_customer_count);
            document.getElementById('nc-cardBonusPoints').textContent = toIndian(master.total_bonus_point_given);
            document.getElementById('nc-cardPurchaseCount').textContent = toIndian(stats.purchase_count);
            document.getElementById('nc-cardRedeemedCount').textContent = toIndian(stats.redeemed_count);
            document.getElementById('nc-cardPointRedeemed').textContent = toIndian(stats.point_redeemed_value);
            document.getElementById('nc-cardRedeemedPurchase').textContent = fmtRupee(stats.redeemed_purchase_value);
            
            const discountPct = stats.loyalty_discount_pct;
            document.getElementById('nc-cardDiscountPct').textContent = fmtPct(discountPct);
            document.getElementById('nc-discountProgressBar').style.width = Math.min(discountPct * 10, 100) + '%';
            
            document.getElementById('nc-cardAvgPurchase').textContent = fmtRupee(stats.avg_purchase_value);
            document.getElementById('nc-cardAvgRedemption').textContent = toIndian(stats.avg_loyalty_redemption);
            
            document.querySelectorAll('.nc-card').forEach((card, i) => {
                card.style.opacity = '0';
                card.style.transform = 'translateY(15px)';
                setTimeout(() => {
                    card.style.transition = 'all 0.4s ease';
                    card.style.opacity = '1';
                    card.style.transform = 'translateY(0)';
                }, 30 * i);
            });
            
        } catch(e) {
            console.error('Failed to fetch new customer metrics:', e);
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
            [`Refer & Earn Report (${dateFrom.value} to ${dateTo.value})`, ''],
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
        XLSX.writeFile(wb, `Refer_Earn_Report_${dateFrom.value}_to_${dateTo.value}.xlsx`);
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
        });
    });

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

    async function loadCustomerClassification() {
        const start = dateFrom.value;
        const end   = dateTo.value;
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
            const totalEl = document.getElementById('ccTotalParticipants');
            if (totalEl) totalEl.textContent = data.total_participants.toLocaleString('en-IN');

            const baseSizeEl = document.getElementById('ccBaseSize');
            if (baseSizeEl) {
                const buyers = (data.total_buyers || 0).toLocaleString('en-IN');
                baseSizeEl.textContent = `${buyers} purchased in selected range`;
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

    // ─── Reload classification every time its tab is clicked ───────────────────────
    document.querySelectorAll('.tab-link').forEach(link => {
        link.addEventListener('click', () => {
            if (link.getAttribute('data-target') === 'customerClassificationSection') {
                loadCustomerClassification();
            }
        });
    });

    // Also load immediately on page load so data is ready
    loadCustomerClassification();

    // Re-run classification when main Apply filter button is clicked
    if (mainApplyFilter) {
        mainApplyFilter.addEventListener('click', loadCustomerClassification);
    }
});
