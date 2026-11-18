window.comparisonWaveforms = {};
const waveformLoads = {}, waveformOrder = [];
let plotRequest = 0, plotFrame = null, plottedData = null;

function selectWidth(requested) {
    if (!Number.isFinite(requested)) return;
    selectedWidth = activeWidths().reduce((best, width) => Math.abs(width - requested) < Math.abs(best - requested) ? width : best, activeWidths()[0]);
    document.getElementById('width-slider').value = selectedWidth;
    document.getElementById('width-number').value = selectedWidth;
    document.getElementById('notice').textContent = selectedWidth === requested ? '' : requested + ' bits was not recorded. Showing ' + selectedWidth + ' bits.';
    render();
}

function loadWaveform(key) {
    if (window.comparisonWaveforms[key]) return Promise.resolve(window.comparisonWaveforms[key]);
    if (waveformLoads[key]) return waveformLoads[key];
    waveformLoads[key] = new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = 'comparison_waveforms/' + key + '.js';
        script.onload = () => {
            const payload = window.comparisonWaveforms[key];
            delete waveformLoads[key];
            if (!payload) { reject(new Error('Saved waveform file did not contain ' + key)); return; }
            waveformOrder.push(key);
            while (waveformOrder.length > 24) { const oldest = waveformOrder.shift(); delete window.comparisonWaveforms[oldest]; }
            resolve(payload);
        };
        script.onerror = () => { delete waveformLoads[key]; reject(new Error('Cannot load saved waveform ' + key + '. Keep comparison_waveforms beside this HTML file.')); };
        document.head.appendChild(script);
    });
    return waveformLoads[key];
}

function requestPlotUpdate() {
    if (plotFrame !== null) return;
    plotFrame = requestAnimationFrame(() => { plotFrame = null; updatePlots(); });
}

function clearPlot(identifier, message) {
    const canvas = document.getElementById(identifier), context = canvas.getContext('2d'), ratio = window.devicePixelRatio || 1;
    canvas.width = canvas.clientWidth * ratio; canvas.height = canvas.clientHeight * ratio;
    context.scale(ratio, ratio); context.fillStyle = 'white'; context.fillRect(0, 0, canvas.clientWidth, canvas.clientHeight);
    context.fillStyle = '#536b7c'; context.font = '12px system-ui'; context.textAlign = 'center'; context.fillText(message, canvas.clientWidth / 2, canvas.clientHeight / 2);
}

async function updatePlots() {
    const request = ++plotRequest, current = data.currents[currentIndex], neuron = Number(document.getElementById('neuron').value), limit = Number(document.getElementById('lag-limit').value);
    const row = selectedRow(current, selectedWidth);
    plottedData = null;
    document.getElementById('plot-heading').textContent = selectedWidth + ' bits | ' + current + ' pA | neuron ' + neuron;
    document.getElementById('plot-formats').textContent = row ? Object.entries(row.formats).map(([name,format]) => name + ': Q' + (format[0] - format[1]) + '.' + format[1]).join(' | ') : '';
    if (!row) {
        document.getElementById('plot-status').textContent = 'This width/current combination has not been simulated.';
        ['original-plot', 'aligned-plot', 'correlation-plot'].forEach(identifier => clearPlot(identifier, 'No saved waveform'));
        return;
    }
    document.getElementById('plot-status').textContent = 'Loading saved waveform...';
    try {
        const [reference, candidate] = await Promise.all([loadWaveform(row.reference_key), loadWaveform(row.waveform_key)]);
        if (request !== plotRequest) return;
        const best = row.valid ? alignment(row, neuron, limit) : null;
        plottedData = { row, reference, candidate, neuron, limit, best };
        document.getElementById('plot-status').textContent = !row.valid ? 'Invalid arithmetic: ' + row.faults + '. Original waveform shown for diagnosis only.' : best ? 'Maximum correlation ' + best.score.toFixed(4) + ' at ' + (best.lag > 0 ? '+' : '') + best.lag.toFixed(3) + ' ms; search range +/-' + limit + ' ms.' : 'Correlation is undefined for a constant or nearly constant signal.';
        drawSelectedPlots();
    } catch (error) {
        if (request !== plotRequest) return;
        document.getElementById('plot-status').textContent = error.message;
        ['original-plot', 'aligned-plot', 'correlation-plot'].forEach(identifier => clearPlot(identifier, 'Saved waveform unavailable'));
    }
}

function axesFor(identifier, xlimits, ylimits, xlabel, ylabel) {
    const canvas = document.getElementById(identifier), context = canvas.getContext('2d'), ratio = window.devicePixelRatio || 1, width = canvas.clientWidth, height = canvas.clientHeight;
    canvas.width = width * ratio; canvas.height = height * ratio; context.scale(ratio, ratio);
    context.fillStyle = 'white'; context.fillRect(0, 0, width, height);
    const left = 52, right = width - 16, top = 14, bottom = height - 37;
    const x = value => left + (value - xlimits[0]) / (xlimits[1] - xlimits[0]) * (right - left);
    const y = value => bottom - (value - ylimits[0]) / (ylimits[1] - ylimits[0]) * (bottom - top);
    context.font = '10px system-ui'; context.lineWidth = .6;
    for (let tick = 0; tick <= 4; tick++) {
        const value = ylimits[0] + (ylimits[1] - ylimits[0]) * tick / 4, position = y(value);
        context.strokeStyle = '#e0e7ec'; context.beginPath(); context.moveTo(left, position); context.lineTo(right, position); context.stroke();
        context.fillStyle = '#536b7c'; context.textAlign = 'right'; context.fillText(value.toFixed(2), left - 6, position + 3);
        const time = xlimits[0] + (xlimits[1] - xlimits[0]) * tick / 4;
        context.textAlign = 'center'; context.fillText(time.toFixed(xlimits[1] - xlimits[0] <= 20 ? 1 : 0), x(time), bottom + 15);
    }
    context.strokeStyle = '#7f94a3'; context.strokeRect(left, top, right - left, bottom - top);
    context.fillStyle = '#536b7c'; context.textAlign = 'center'; context.fillText(xlabel, (left + right) / 2, height - 3);
    context.save(); context.translate(11, (top + bottom) / 2); context.rotate(-Math.PI / 2); context.fillText(ylabel, 0, 0); context.restore();
    return { context, x, y, left, right, top, bottom };
}

function drawOverlay(identifier, state, shift, limits, voltageLimits) {
    const chart = axesFor(identifier, limits, voltageLimits, 'Time (ms)', 'Vmem (normalised)'), context = chart.context, time = state.reference.time_ms;
    context.save(); context.beginPath(); context.rect(chart.left, chart.top, chart.right - chart.left, chart.bottom - chart.top); context.clip();
    context.fillStyle = '#f6efdf'; context.fillRect(chart.x(60), chart.top, chart.x(140.001) - chart.x(60), chart.bottom - chart.top);
    context.strokeStyle = '#a2acb3'; context.setLineDash([2, 4]); context.beginPath(); context.moveTo(chart.left, chart.y(1.4542)); context.lineTo(chart.right, chart.y(1.4542)); context.stroke(); context.setLineDash([]);
    for (const [payload, offset, colour] of [[state.reference, 0, '#176b9a'], [state.candidate, shift, '#d0642f']]) {
        context.beginPath(); context.strokeStyle = colour; context.lineWidth = 1.15; let started = false;
        time.forEach((value, index) => {
            const position = value + offset;
            if (position < limits[0] || position > limits[1]) return;
            const voltage = payload.voltage[index][state.neuron];
            if (started) context.lineTo(chart.x(position), chart.y(voltage)); else { context.moveTo(chart.x(position), chart.y(voltage)); started = true; }
        });
        context.stroke(); context.fillStyle = colour;
        payload.peak_indices[state.neuron].forEach(index => {
            const position = time[index] + offset;
            if (position >= limits[0] && position <= limits[1]) { context.beginPath(); context.arc(chart.x(position), chart.y(payload.voltage[index][state.neuron]), 2.4, 0, 2 * Math.PI); context.fill(); }
        });
    }
    context.restore();
}

function drawCorrelation(state) {
    if (!state.row.valid) { clearPlot('correlation-plot', 'No similarity score: invalid arithmetic'); return; }
    if (!state.best) { clearPlot('correlation-plot', 'Correlation is undefined'); return; }
    const chart = axesFor('correlation-plot', [-state.limit, state.limit], [-1, 1], 'Shift applied to candidate (ms)', 'Normalised correlation'), context = chart.context;
    context.strokeStyle = '#9eacb5'; context.setLineDash([3, 4]); context.beginPath(); context.moveTo(chart.x(0), chart.top); context.lineTo(chart.x(0), chart.bottom); context.stroke(); context.setLineDash([]);
    context.beginPath(); context.strokeStyle = '#176b9a'; context.lineWidth = 1.6; let started = false;
    state.row.lags_ms.forEach((lag, index) => {
        const score = state.row.correlation_by_neuron[state.neuron][index];
        if (Math.abs(lag) > state.limit || score === null) { started = false; return; }
        if (started) context.lineTo(chart.x(lag), chart.y(score)); else { context.moveTo(chart.x(lag), chart.y(score)); started = true; }
    });
    context.stroke(); context.strokeStyle = '#c45d2e'; context.setLineDash([3, 3]); context.beginPath(); context.moveTo(chart.x(state.best.lag), chart.top); context.lineTo(chart.x(state.best.lag), chart.bottom); context.stroke(); context.setLineDash([]);
    context.fillStyle = '#c45d2e'; context.beginPath(); context.arc(chart.x(state.best.lag), chart.y(state.best.score), 3.5, 0, 2 * Math.PI); context.fill();
}

function drawSelectedPlots() {
    if (!plottedData) return;
    const state = plottedData, limits = document.getElementById('plot-window').value.split(',').map(Number), shift = state.best ? state.best.lag : 0;
    let minimum = Infinity, maximum = -Infinity;
    state.reference.time_ms.forEach((time, index) => {
        if (time < limits[0] - Math.abs(shift) || time > limits[1] + Math.abs(shift)) return;
        minimum = Math.min(minimum, state.reference.voltage[index][state.neuron], state.candidate.voltage[index][state.neuron]);
        maximum = Math.max(maximum, state.reference.voltage[index][state.neuron], state.candidate.voltage[index][state.neuron]);
    });
    if (!Number.isFinite(minimum) || !Number.isFinite(maximum)) { minimum = -3; maximum = 6; }
    const padding = Math.max(.2, (maximum - minimum) * .1), voltageLimits = [minimum - padding, maximum + padding];
    drawOverlay('original-plot', state, 0, limits, voltageLimits);
    drawOverlay('aligned-plot', state, shift, limits, voltageLimits);
    document.getElementById('aligned-heading').textContent = state.best ? 'Candidate shifted ' + (shift > 0 ? '+' : '') + shift.toFixed(3) + ' ms' : 'No defined alignment; unshifted diagnostic view';
    drawCorrelation(state);
}

window.addEventListener('resize', () => requestAnimationFrame(drawSelectedPlots));
