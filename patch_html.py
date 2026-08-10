"""
Patch dashboard.html to insert date filter controls into Age-wise and District sections.
"""
with open('dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# ── Age section ────────────────────────────────────────────────────────────────
# Find the closing </p> just before </div> that closes age-section-meta,
# which is right before the Export button.
age_old = (
    '                        </p>\n'
    '                    </div>\n'
    '                    <button class="btn-age-export"'
)
age_new = (
    '                        </p>\n'
    '                        <div class="section-date-filter">\n'
    '                            <div class="sdf-group">\n'
    '                                <label for="ageFrom">From</label>\n'
    '                                <input type="date" id="ageFrom" class="sdf-input">\n'
    '                            </div>\n'
    '                            <div class="sdf-group">\n'
    '                                <label for="ageTo">To</label>\n'
    '                                <input type="date" id="ageTo" class="sdf-input">\n'
    '                            </div>\n'
    '                            <button class="sdf-apply-btn" id="ageApplyFilter">Apply</button>\n'
    '                            <button class="sdf-clear-btn" id="ageClearFilter">Clear</button>\n'
    '                        </div>\n'
    '                    </div>\n'
    '                    <button class="btn-age-export"'
)

if age_old in content:
    content = content.replace(age_old, age_new, 1)
    print('[OK] Age date filter inserted.')
else:
    print('[WARN] Age marker not found — check indentation/encoding.')
    # Debug: show area around btn-age-export
    idx = content.find('btn-age-export')
    print(repr(content[max(0, idx-200):idx+50]))

# ── District section ──────────────────────────────────────────────────────────
# Check if the district filter was successfully added already
if 'districtApplyFilter' in content:
    print('[OK] District date filter already present.')
else:
    district_old = (
        '                        </p>\n'
        '                    </div>\n'
        '                    <button class="btn-district-export"'
    )
    district_new = (
        '                        </p>\n'
        '                        <div class="section-date-filter">\n'
        '                            <div class="sdf-group">\n'
        '                                <label for="districtFrom">From</label>\n'
        '                                <input type="date" id="districtFrom" class="sdf-input">\n'
        '                            </div>\n'
        '                            <div class="sdf-group">\n'
        '                                <label for="districtTo">To</label>\n'
        '                                <input type="date" id="districtTo" class="sdf-input">\n'
        '                            </div>\n'
        '                            <button class="sdf-apply-btn" id="districtApplyFilter">Apply</button>\n'
        '                            <button class="sdf-clear-btn" id="districtClearFilter">Clear</button>\n'
        '                        </div>\n'
        '                    </div>\n'
        '                    <button class="btn-district-export"'
    )
    if district_old in content:
        content = content.replace(district_old, district_new, 1)
        print('[OK] District date filter inserted.')
    else:
        print('[WARN] District marker not found.')

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done.')
