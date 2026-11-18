const filesystem = require('fs'), virtualMachine = require('vm'), assert = require('assert'), path = require('path');
const output = path.resolve(__dirname, '../results_fixed_integer'), elements = {}, frames = [];
const drawing = new Proxy({}, {get: (object, key) => object[key] || (() => {}), set: (object, key, value) => (object[key] = value, true)});
const element = identifier => elements[identifier] || (elements[identifier] = {value: identifier === 'neuron' ? '0' : identifier === 'lag-limit' ? '5' : identifier === 'plot-window' ? '60,190' : '', clientWidth: 600, clientHeight: 210, getContext: () => drawing});
const context = {console, Promise, requestAnimationFrame: callback => (frames.push(callback), frames.length), document: {getElementById: element, createElement: () => ({}), head: {appendChild: script => setImmediate(() => {try {virtualMachine.runInContext(filesystem.readFileSync(path.join(output, script.src), 'utf8'), context); script.onload();} catch (error) {script.onerror();}})}}};
context.window = context;
context.addEventListener = () => {};
virtualMachine.createContext(context);
const html = filesystem.readFileSync(path.join(output, 'comparison_table.html'), 'utf8');
for (const match of html.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)) {
    const external = /src="([^"]+)"/.exec(match[1]);
    virtualMachine.runInContext(external ? filesystem.readFileSync(path.join(output, external[1]), 'utf8') : match[2], context);
}
const flush = async () => {while (frames.length) frames.shift()(); await new Promise(resolve => setTimeout(resolve, 60));};
(async () => {
    await flush();
    assert.match(element('plot-heading').textContent, /32 bits.*80 pA/);
    assert.match(element('plot-status').textContent, /Maximum correlation/);
    virtualMachine.runInContext('selectWidth(24)', context);
    await flush();
    assert.equal(element('width-slider').value, 24);
    assert.match(element('results').innerHTML, /data-width="24"[^>]*selected-width/);
    for (const [signalType, minimum] of [['shared', 9], ['matrix', 10], ['current', 18], ['triangle', 11]]) {
        virtualMachine.runInContext(`selectSweep('${signalType}');selectWidth(${minimum})`, context);
        await flush();
        assert.equal(element('width-slider').min, minimum);
        assert.equal(element('current-number').disabled, true);
        assert.match(element('plot-heading').textContent, new RegExp(minimum + ' bits.*80 pA'));
        assert.ok(element('plot-formats').textContent.includes('.0'));
        assert.ok(!element('plot-status').textContent.includes('unavailable'));
        assert.ok(!element('plot-status').textContent.includes('Loading'));
        virtualMachine.runInContext('selectWidth(32)', context);
        await flush();
        assert.match(element('plot-status').textContent, /Maximum correlation/);
    }
    virtualMachine.runInContext('selectSweep("all");typeCurrent("1000")', context);
    await flush();
    assert.equal(element('current-number').disabled, false);
    assert.match(element('plot-heading').textContent, /1000 pA/);
    element('neuron').value = '2';
    element('lag-limit').value = '1';
    virtualMachine.runInContext('render()', context);
    await flush();
    assert.match(element('plot-heading').textContent, /neuron 2/);
    element('plot-window').value = '140,190';
    virtualMachine.runInContext('drawSelectedPlots()', context);
    const rows = virtualMachine.runInContext('data.rows', context);
    assert.equal(rows.length, 936);
    for (const row of rows) for (const key of [row.waveform_key, row.reference_key]) assert.ok(filesystem.existsSync(path.join(output, 'comparison_waveforms', key + '.js')));
    console.log('Passed: original and four individual sweeps, zero-fraction endpoints, baseline sharing, 936 waveform links and plot controls.');
})().catch(error => {console.error(error); process.exitCode = 1;});
