
const { JSDOM } = require('jsdom');
const fs = require('fs');

const html = fs.readFileSync('index.html', 'utf-8');
const dom = new JSDOM(html, { runScripts: 'dangerously', resources: 'usable' });
const window = dom.window;

console.log('Testing openRawDataModal call...');
try {
    window.openRawDataModal('APTNI-A - พัทลุง (Phatthalung)');
    console.log('Modal display style:', window.document.getElementById('rawDataModal').style.display);
    console.log('Record count text:', window.document.getElementById('modalRecordCount').innerText);
} catch (e) {
    console.error('JS EXECUTION ERROR:', e);
}
