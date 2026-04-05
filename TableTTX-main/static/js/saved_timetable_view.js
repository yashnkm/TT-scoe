/**
 * Saved Timetable View — Division / Batch / Faculty rendering
 */

let timetableData = {};
let facultySchedules = {};
let roomSchedules = {};

document.addEventListener('DOMContentLoaded', function () {
    try {
        timetableData = JSON.parse(document.getElementById('timetableData').textContent);

        // Pre-compute faculty and room schedules
        facultySchedules = generateFacultySchedules(timetableData);
        roomSchedules = generateRoomSchedules(timetableData);

        // Event listeners
        document.getElementById('viewSelector').addEventListener('change', onViewChanged);
        document.querySelectorAll('input[name="viewType"]').forEach(radio => {
            radio.addEventListener('change', filterViewOptions);
        });

        // Initialize
        filterViewOptions();
    } catch (error) {
        console.error('Error loading timetable data:', error);
    }
});

/* ------------------------------------------------------------------ */
/*  Faculty schedule generation                                        */
/* ------------------------------------------------------------------ */

function generateFacultySchedules(data) {
    const schedules = {}; // { "Prof Name": { day: { slot: { subject, room, type, span, context, slot_position } } } }

    // Collect days/slots from first available view
    const sampleKey = Object.keys(data)[0];
    if (!sampleKey) return schedules;
    const sampleView = data[sampleKey];
    const days = Object.keys(sampleView);

    Object.keys(data).forEach(viewKey => {
        const isBatchView = viewKey.includes('Batch');
        const viewData = data[viewKey];

        // Parse context from key: "Year_1_Division_1" or "Year_1_Division_1_Batch_2"
        const context = viewKey.replace(/_/g, ' ');

        days.forEach(day => {
            const slots = viewData[day];
            if (!slots) return;

            Object.keys(slots).forEach(timeSlot => {
                const session = slots[timeSlot];
                if (!session || session.type === 'break') return;

                if (session.type === 'practical_block') {
                    // Only process practicals from batch views to avoid double-counting
                    if (!isBatchView) return;

                    const batches = session.batches || {};
                    Object.keys(batches).forEach(bNum => {
                        const bInfo = batches[bNum];
                        if (!bInfo || !bInfo.faculty) return;
                        const fname = bInfo.faculty;
                        const bLetter = String.fromCharCode(64 + parseInt(bNum));
                        if (!schedules[fname]) schedules[fname] = {};
                        if (!schedules[fname][day]) schedules[fname][day] = {};
                        if (!schedules[fname][day][timeSlot]) {
                            schedules[fname][day][timeSlot] = {
                                subject: bInfo.subject,
                                room: bInfo.room || '',
                                type: 'practical',
                                span: session.span || 1,
                                slot_position: session.slot_position || 'start',
                                context: context,
                                batches: ['Batch ' + bLetter]
                            };
                        } else {
                            const existing = schedules[fname][day][timeSlot];
                            if (!existing.batches) existing.batches = [];
                            existing.batches.push('Batch ' + bLetter);
                            if (bInfo.room && !existing.room.includes(bInfo.room)) {
                                existing.room += ', ' + bInfo.room;
                            }
                        }
                    });
                } else if (!isBatchView) {
                    // Theory/tutorial — use division views only (same across batches)
                    const fname = session.faculty;
                    if (!fname) return;
                    if (!schedules[fname]) schedules[fname] = {};
                    if (!schedules[fname][day]) schedules[fname][day] = {};
                    if (!schedules[fname][day][timeSlot]) {
                        schedules[fname][day][timeSlot] = {
                            subject: session.subject,
                            room: session.room || '',
                            type: session.type || 'theory',
                            span: session.span || 1,
                            slot_position: session.slot_position || 'start',
                            context: context
                        };
                    }
                } else {
                    // Batch-view individual practicals (non-block)
                    if (session.type === 'theory' || session.type === 'tutorial') return;
                    const fname = session.faculty;
                    if (!fname) return;
                    const batchPart = viewKey.split('Batch_')[1] || '';
                    if (!schedules[fname]) schedules[fname] = {};
                    if (!schedules[fname][day]) schedules[fname][day] = {};
                    if (!schedules[fname][day][timeSlot]) {
                        schedules[fname][day][timeSlot] = {
                            subject: session.subject,
                            room: session.room || '',
                            type: session.type || 'practical',
                            span: session.span || 1,
                            slot_position: session.slot_position || 'start',
                            context: context,
                            batches: batchPart ? ['Batch ' + batchPart] : []
                        };
                    } else {
                        const existing = schedules[fname][day][timeSlot];
                        if (!existing.batches) existing.batches = [];
                        if (batchPart) existing.batches.push('Batch ' + batchPart);
                        if (session.room && !existing.room.includes(session.room)) {
                            existing.room += ', ' + session.room;
                        }
                    }
                }
            });
        });
    });

    return schedules;
}

/* ------------------------------------------------------------------ */
/*  Dropdown population based on active view type                      */
/* ------------------------------------------------------------------ */

function filterViewOptions() {
    const viewType = document.querySelector('input[name="viewType"]:checked').value;
    const selector = document.getElementById('viewSelector');
    selector.innerHTML = '';

    if (viewType === 'division') {
        Object.keys(timetableData).forEach(key => {
            if (!key.includes('Batch')) {
                const opt = document.createElement('option');
                opt.value = key;
                opt.textContent = key.replace(/_/g, ' ');
                selector.appendChild(opt);
            }
        });
    } else if (viewType === 'batch') {
        Object.keys(timetableData).forEach(key => {
            if (key.includes('Batch')) {
                const opt = document.createElement('option');
                opt.value = key;
                opt.textContent = key.replace(/_/g, ' ');
                selector.appendChild(opt);
            }
        });
    } else if (viewType === 'faculty') {
        const names = Object.keys(facultySchedules).sort();
        names.forEach(name => {
            const opt = document.createElement('option');
            opt.value = name;
            opt.textContent = name;
            selector.appendChild(opt);
        });
    } else if (viewType === 'room') {
        const names = Object.keys(roomSchedules).sort();
        names.forEach(name => {
            const opt = document.createElement('option');
            opt.value = name;
            opt.textContent = name;
            selector.appendChild(opt);
        });
    }

    onViewChanged();
}

/* ------------------------------------------------------------------ */
/*  Dispatch rendering based on view type                              */
/* ------------------------------------------------------------------ */

function onViewChanged() {
    const viewType = document.querySelector('input[name="viewType"]:checked').value;
    const selected = document.getElementById('viewSelector').value;
    if (!selected) return;

    if (viewType === 'faculty') {
        document.getElementById('currentViewTitle').innerHTML =
            '<i class="fas fa-chalkboard-teacher me-2"></i>' + selected;
        renderFacultyView(selected);
    } else if (viewType === 'room') {
        document.getElementById('currentViewTitle').innerHTML =
            '<i class="fas fa-door-open me-2"></i>' + selected;
        renderRoomView(selected);
    } else {
        document.getElementById('currentViewTitle').innerHTML =
            '<i class="fas fa-table me-2"></i>' + selected.replace(/_/g, ' ');
        renderStandardView(selected);
    }
}

/* ------------------------------------------------------------------ */
/*  Standard Division / Batch view (mirrors timetable.html logic)      */
/* ------------------------------------------------------------------ */

function renderStandardView(viewKey) {
    const viewData = timetableData[viewKey];
    if (!viewData) return;

    const tbody = document.getElementById('timetableBody');
    tbody.innerHTML = '';

    const days = Object.keys(viewData);
    const dayOrder = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    days.sort((a, b) => dayOrder.indexOf(a) - dayOrder.indexOf(b));
    const timeSlots = Object.keys(viewData[days[0]] || {});

    // Rebuild header
    const thead = document.getElementById('timetableHead');
    thead.innerHTML = '';
    const headRow = document.createElement('tr');
    const timeTh = document.createElement('th');
    timeTh.textContent = 'Time';
    headRow.appendChild(timeTh);
    days.forEach(d => {
        const th = document.createElement('th');
        th.textContent = d;
        headRow.appendChild(th);
    });
    thead.appendChild(headRow);

    // Track cells to skip due to rowspan
    const skipCells = {};

    timeSlots.forEach((timeSlot, slotIndex) => {
        const row = document.createElement('tr');

        // Time column
        const timeCell = document.createElement('td');
        timeCell.className = 'fw-bold text-center align-middle';
        timeCell.textContent = timeSlot;
        row.appendChild(timeCell);

        // Break check
        const firstDaySession = viewData[days[0]] && viewData[days[0]][timeSlot];
        const isBreak = firstDaySession && firstDaySession.type === 'break';

        if (isBreak) {
            const breakCell = document.createElement('td');
            breakCell.colSpan = days.length;
            breakCell.className = 'break-cell text-center align-middle';
            const breakType = firstDaySession.break_type || 'break';
            const breakIcon = breakType === 'lunch' ? 'fa-utensils' : 'fa-coffee';
            breakCell.innerHTML = `
                <div class="break-slot p-3 rounded" style="background-color: rgba(108, 117, 125, 0.15);">
                    <i class="fas ${breakIcon} me-2"></i>
                    <strong style="font-size: 1.1em;">${firstDaySession.subject}</strong>
                </div>
            `;
            row.appendChild(breakCell);
        } else {
            days.forEach((day, dayIndex) => {
                const cellKey = `${slotIndex}-${dayIndex}`;
                if (skipCells[cellKey]) return;

                const cell = document.createElement('td');
                const session = viewData[day] && viewData[day][timeSlot];

                if (session && session.type === 'practical_block') {
                    if (session.slot_position === 'continuation') return;

                    const blockSpan = session.span || 1;
                    if (blockSpan > 1) {
                        let actualRowspan = 1;
                        for (let offset = 1; offset < blockSpan; offset++) {
                            const nextSlotIdx = slotIndex + offset;
                            if (nextSlotIdx < timeSlots.length) {
                                const nextSession = viewData[days[0]] && viewData[days[0]][timeSlots[nextSlotIdx]];
                                if (!nextSession || nextSession.type !== 'break') {
                                    actualRowspan++;
                                    skipCells[`${nextSlotIdx}-${dayIndex}`] = true;
                                }
                            }
                        }
                        cell.rowSpan = actualRowspan;
                    }
                    cell.className = 'align-middle';

                    const durationLabel = blockSpan > 1 ? ` (${blockSpan} hrs)` : '';
                    let html = `<div class="session-card practical-block">`;
                    html += `<div class="practical-block-header"><i class="fas fa-flask me-1"></i>Practicals${durationLabel}</div>`;
                    html += `<div class="practical-block-batches">`;

                    const batchData = session.batches || {};
                    Object.keys(batchData).sort((a, b) => parseInt(a) - parseInt(b)).forEach(bNum => {
                        const bLetter = String.fromCharCode(64 + parseInt(bNum));
                        const bInfo = batchData[bNum];
                        if (bInfo) {
                            html += `<div class="batch-item">
                                <span class="batch-label">Batch ${bLetter}:</span>
                                <span class="batch-subject">${bInfo.subject}</span>
                                <small class="batch-details">${bInfo.faculty} | ${bInfo.room}</small>
                            </div>`;
                        } else {
                            html += `<div class="batch-item batch-free">
                                <span class="batch-label">Batch ${bLetter}:</span>
                                <span class="batch-subject text-muted">Free</span>
                            </div>`;
                        }
                    });

                    html += `</div></div>`;
                    cell.innerHTML = html;

                } else if (session && session.type !== 'break') {
                    const arr = Array.isArray(session) ? session : [session];
                    const theoryItems = arr.filter(s => s.type === 'theory' || s.type === 'tutorial');
                    const practicalItems = arr.filter(s => s.type !== 'theory' && s.type !== 'tutorial' && s.type !== 'break' && s.type !== 'practical_block');
                    const htmlParts = [];

                    let practicalSpan = 1;
                    if (practicalItems.length > 0) {
                        const sample = practicalItems[0];
                        if (sample.slot_position === 'start' && sample.span > 1) {
                            practicalSpan = sample.span;
                        }
                    }

                    const isContinuation = arr.some(s => s.slot_position === 'continuation');
                    if (isContinuation) return;

                    if (practicalSpan > 1) {
                        let actualRowspan = 1;
                        for (let offset = 1; offset < practicalSpan; offset++) {
                            const nextSlotIdx = slotIndex + offset;
                            if (nextSlotIdx < timeSlots.length) {
                                const nextSession = viewData[days[0]] && viewData[days[0]][timeSlots[nextSlotIdx]];
                                if (!nextSession || nextSession.type !== 'break') {
                                    actualRowspan++;
                                    skipCells[`${nextSlotIdx}-${dayIndex}`] = true;
                                }
                            }
                        }
                        cell.rowSpan = actualRowspan;
                        cell.className = 'align-middle';
                    }

                    theoryItems.forEach(s => {
                        htmlParts.push(`
                            <div class="session-card ${s.type}">
                                <div class="session-subject">${s.subject}</div>
                                <div class="session-details">
                                    <small class="d-block"><i class="fas fa-user me-1"></i>${s.faculty}</small>
                                    <small class="d-block"><i class="fas fa-map-marker-alt me-1"></i>${s.room}</small>
                                    <span class="badge bg-info mt-1">${s.type.toUpperCase()}</span>
                                </div>
                            </div>
                        `);
                    });

                    if (practicalItems.length > 0) {
                        const sample = practicalItems[0];
                        const durationLabel = practicalSpan > 1 ? ` (${practicalSpan} hrs)` : '';
                        htmlParts.push(`
                            <div class="session-card practical">
                                <div class="session-subject">${sample.subject}${durationLabel}</div>
                                <div class="session-details">
                                    <small class="d-block"><i class="fas fa-user me-1"></i>${sample.faculty}</small>
                                    <small class="d-block"><i class="fas fa-map-marker-alt me-1"></i>${sample.room}</small>
                                    <span class="badge bg-warning mt-1">PRACTICAL</span>
                                </div>
                            </div>
                        `);
                    }

                    cell.innerHTML = htmlParts.join('');
                } else {
                    cell.innerHTML = '<div class="empty-slot">Free</div>';
                }

                row.appendChild(cell);
            });
        }

        tbody.appendChild(row);
    });
}

/* ------------------------------------------------------------------ */
/*  Faculty View rendering                                             */
/* ------------------------------------------------------------------ */

function renderFacultyView(facultyName) {
    const schedule = facultySchedules[facultyName];
    if (!schedule) return;

    const tbody = document.getElementById('timetableBody');
    tbody.innerHTML = '';

    // Get days and time slots from the main timetable data
    const sampleKey = Object.keys(timetableData)[0];
    const sampleView = timetableData[sampleKey];
    const days = Object.keys(sampleView);
    const dayOrder = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    days.sort((a, b) => dayOrder.indexOf(a) - dayOrder.indexOf(b));
    const timeSlots = Object.keys(sampleView[days[0]] || {});

    // Rebuild header
    const thead = document.getElementById('timetableHead');
    thead.innerHTML = '';
    const headRow = document.createElement('tr');
    const timeTh = document.createElement('th');
    timeTh.textContent = 'Time';
    headRow.appendChild(timeTh);
    days.forEach(d => {
        const th = document.createElement('th');
        th.textContent = d;
        headRow.appendChild(th);
    });
    thead.appendChild(headRow);

    // Check if a slot is a break in the original timetable
    function isBreakSlot(timeSlot) {
        const firstSession = sampleView[days[0]] && sampleView[days[0]][timeSlot];
        return firstSession && firstSession.type === 'break';
    }

    // Track cells to skip due to rowspan
    const skipCells = {};

    timeSlots.forEach((timeSlot, slotIndex) => {
        const row = document.createElement('tr');

        // Time column
        const timeCell = document.createElement('td');
        timeCell.className = 'fw-bold text-center align-middle';
        timeCell.textContent = timeSlot;
        row.appendChild(timeCell);

        if (isBreakSlot(timeSlot)) {
            const firstSession = sampleView[days[0]][timeSlot];
            const breakCell = document.createElement('td');
            breakCell.colSpan = days.length;
            breakCell.className = 'break-cell text-center align-middle';
            const breakType = firstSession.break_type || 'break';
            const breakIcon = breakType === 'lunch' ? 'fa-utensils' : 'fa-coffee';
            breakCell.innerHTML = `
                <div class="break-slot p-3 rounded" style="background-color: rgba(108, 117, 125, 0.15);">
                    <i class="fas ${breakIcon} me-2"></i>
                    <strong style="font-size: 1.1em;">${firstSession.subject}</strong>
                </div>
            `;
            row.appendChild(breakCell);
        } else {
            days.forEach((day, dayIndex) => {
                const cellKey = `${slotIndex}-${dayIndex}`;
                if (skipCells[cellKey]) return;

                const cell = document.createElement('td');
                const entry = schedule[day] && schedule[day][timeSlot];

                if (entry && entry.slot_position !== 'continuation') {
                    // Apply rowspan for multi-slot sessions
                    const span = entry.span || 1;
                    if (span > 1) {
                        let actualRowspan = 1;
                        for (let offset = 1; offset < span; offset++) {
                            const nextSlotIdx = slotIndex + offset;
                            if (nextSlotIdx < timeSlots.length && !isBreakSlot(timeSlots[nextSlotIdx])) {
                                actualRowspan++;
                                skipCells[`${nextSlotIdx}-${dayIndex}`] = true;
                            }
                        }
                        cell.rowSpan = actualRowspan;
                    }
                    cell.className = 'align-middle';

                    const typeBadgeClass = entry.type === 'practical' ? 'bg-warning' :
                                           entry.type === 'tutorial' ? 'bg-purple' : 'bg-info';
                    const durationLabel = span > 1 ? ` (${span} hrs)` : '';

                    const batchesLabel = entry.batches && entry.batches.length > 0
                        ? `<small class="d-block text-warning"><i class="fas fa-users me-1"></i>${entry.batches.join(', ')}</small>`
                        : '';

                    cell.innerHTML = `
                        <div class="session-card faculty-session">
                            <div class="session-subject">${entry.subject}${durationLabel}</div>
                            <div class="session-details">
                                <small class="d-block"><i class="fas fa-map-marker-alt me-1"></i>${entry.room}</small>
                                ${batchesLabel}
                                <span class="badge ${typeBadgeClass} mt-1">${entry.type.toUpperCase()}</span>
                            </div>
                            <div class="session-context">
                                <i class="fas fa-graduation-cap me-1"></i>${entry.context}
                            </div>
                        </div>
                    `;
                } else if (!entry || entry.slot_position !== 'continuation') {
                    cell.innerHTML = '<div class="free-slot">Free</div>';
                }

                row.appendChild(cell);
            });
        }

        tbody.appendChild(row);
    });
}

/* ------------------------------------------------------------------ */
/*  Room schedule generation                                           */
/* ------------------------------------------------------------------ */

function generateRoomSchedules(data) {
    const schedules = {};
    const sampleKey = Object.keys(data)[0];
    if (!sampleKey) return schedules;
    const sampleView = data[sampleKey];
    const days = Object.keys(sampleView);

    Object.keys(data).forEach(viewKey => {
        const isBatchView = viewKey.includes('Batch');
        const viewData = data[viewKey];
        const context = viewKey.replace(/_/g, ' ');

        days.forEach(day => {
            const slots = viewData[day];
            if (!slots) return;

            Object.keys(slots).forEach(timeSlot => {
                const session = slots[timeSlot];
                if (!session || session.type === 'break') return;

                if (session.type === 'practical_block') {
                    if (!isBatchView) return;
                    const batches = session.batches || {};
                    Object.keys(batches).forEach(bNum => {
                        const bInfo = batches[bNum];
                        if (!bInfo || !bInfo.room) return;
                        const roomName = bInfo.room;
                        const bLetter = String.fromCharCode(64 + parseInt(bNum));
                        if (!schedules[roomName]) schedules[roomName] = {};
                        if (!schedules[roomName][day]) schedules[roomName][day] = {};
                        if (!schedules[roomName][day][timeSlot]) {
                            schedules[roomName][day][timeSlot] = {
                                subject: bInfo.subject, faculty: bInfo.faculty || '',
                                type: 'practical', span: session.span || 1,
                                slot_position: session.slot_position || 'start', context: context,
                                batches: ['Batch ' + bLetter]
                            };
                        } else {
                            const existing = schedules[roomName][day][timeSlot];
                            if (!existing.batches) existing.batches = [];
                            existing.batches.push('Batch ' + bLetter);
                            if (bInfo.faculty && !existing.faculty.includes(bInfo.faculty)) {
                                existing.faculty += ', ' + bInfo.faculty;
                            }
                        }
                    });
                } else if (!isBatchView) {
                    const roomName = session.room;
                    if (!roomName) return;
                    if (!schedules[roomName]) schedules[roomName] = {};
                    if (!schedules[roomName][day]) schedules[roomName][day] = {};
                    if (!schedules[roomName][day][timeSlot]) {
                        schedules[roomName][day][timeSlot] = {
                            subject: session.subject, faculty: session.faculty || '',
                            type: session.type || 'theory', span: session.span || 1,
                            slot_position: session.slot_position || 'start', context: context
                        };
                    }
                } else {
                    if (session.type === 'theory' || session.type === 'tutorial') return;
                    const roomName = session.room;
                    if (!roomName) return;
                    const batchPart = viewKey.split('Batch_')[1] || '';
                    if (!schedules[roomName]) schedules[roomName] = {};
                    if (!schedules[roomName][day]) schedules[roomName][day] = {};
                    if (!schedules[roomName][day][timeSlot]) {
                        schedules[roomName][day][timeSlot] = {
                            subject: session.subject, faculty: session.faculty || '',
                            type: session.type || 'practical', span: session.span || 1,
                            slot_position: session.slot_position || 'start', context: context,
                            batches: batchPart ? ['Batch ' + batchPart] : []
                        };
                    } else {
                        const existing = schedules[roomName][day][timeSlot];
                        if (!existing.batches) existing.batches = [];
                        if (batchPart) existing.batches.push('Batch ' + batchPart);
                        if (session.faculty && !existing.faculty.includes(session.faculty)) {
                            existing.faculty += ', ' + session.faculty;
                        }
                    }
                }
            });
        });
    });
    return schedules;
}

/* ------------------------------------------------------------------ */
/*  Room View rendering                                                */
/* ------------------------------------------------------------------ */

function renderRoomView(roomName) {
    const schedule = roomSchedules[roomName];
    if (!schedule) return;

    const tbody = document.getElementById('timetableBody');
    tbody.innerHTML = '';

    const sampleKey = Object.keys(timetableData)[0];
    const sampleView = timetableData[sampleKey];
    const days = Object.keys(sampleView);
    const dayOrder = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    days.sort((a, b) => dayOrder.indexOf(a) - dayOrder.indexOf(b));
    const timeSlots = Object.keys(sampleView[days[0]] || {});

    const thead = document.getElementById('timetableHead');
    thead.innerHTML = '';
    const headRow = document.createElement('tr');
    const timeTh = document.createElement('th');
    timeTh.textContent = 'Time';
    headRow.appendChild(timeTh);
    days.forEach(d => {
        const th = document.createElement('th');
        th.textContent = d;
        headRow.appendChild(th);
    });
    thead.appendChild(headRow);

    function isBreakSlot(timeSlot) {
        const firstSession = sampleView[days[0]] && sampleView[days[0]][timeSlot];
        return firstSession && firstSession.type === 'break';
    }

    const skipCells = {};

    timeSlots.forEach((timeSlot, slotIndex) => {
        const row = document.createElement('tr');
        const timeCell = document.createElement('td');
        timeCell.className = 'fw-bold text-center align-middle';
        timeCell.textContent = timeSlot;
        row.appendChild(timeCell);

        if (isBreakSlot(timeSlot)) {
            const firstSession = sampleView[days[0]][timeSlot];
            const breakCell = document.createElement('td');
            breakCell.colSpan = days.length;
            breakCell.className = 'break-cell text-center align-middle';
            const breakType = firstSession.break_type || 'break';
            const breakIcon = breakType === 'lunch' ? 'fa-utensils' : 'fa-coffee';
            breakCell.innerHTML = `
                <div class="break-slot p-3 rounded" style="background-color: rgba(108, 117, 125, 0.15);">
                    <i class="fas ${breakIcon} me-2"></i>
                    <strong style="font-size: 1.1em;">${firstSession.subject}</strong>
                </div>
            `;
            row.appendChild(breakCell);
        } else {
            days.forEach((day, dayIndex) => {
                const cellKey = `${slotIndex}-${dayIndex}`;
                if (skipCells[cellKey]) return;

                const cell = document.createElement('td');
                const entry = schedule[day] && schedule[day][timeSlot];

                if (entry && entry.slot_position !== 'continuation') {
                    const span = entry.span || 1;
                    if (span > 1) {
                        let actualRowspan = 1;
                        for (let offset = 1; offset < span; offset++) {
                            const nextSlotIdx = slotIndex + offset;
                            if (nextSlotIdx < timeSlots.length && !isBreakSlot(timeSlots[nextSlotIdx])) {
                                actualRowspan++;
                                skipCells[`${nextSlotIdx}-${dayIndex}`] = true;
                            }
                        }
                        cell.rowSpan = actualRowspan;
                    }
                    cell.className = 'align-middle';

                    const typeBadgeClass = entry.type === 'practical' ? 'bg-warning' :
                                           entry.type === 'tutorial' ? 'bg-purple' : 'bg-info';
                    const durationLabel = span > 1 ? ` (${span} hrs)` : '';

                    const batchesLabel = entry.batches && entry.batches.length > 0
                        ? `<small class="d-block text-warning"><i class="fas fa-users me-1"></i>${entry.batches.join(', ')}</small>`
                        : '';

                    cell.innerHTML = `
                        <div class="session-card room-session">
                            <div class="session-subject">${entry.subject}${durationLabel}</div>
                            <div class="session-details">
                                <small class="d-block"><i class="fas fa-chalkboard-teacher me-1"></i>${entry.faculty}</small>
                                ${batchesLabel}
                                <span class="badge ${typeBadgeClass} mt-1">${entry.type.toUpperCase()}</span>
                            </div>
                            <div class="session-context">
                                <i class="fas fa-graduation-cap me-1"></i>${entry.context}
                            </div>
                        </div>
                    `;
                } else if (!entry || entry.slot_position !== 'continuation') {
                    cell.innerHTML = '<div class="free-slot">Free</div>';
                }

                row.appendChild(cell);
            });
        }

        tbody.appendChild(row);
    });
}
