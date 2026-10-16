const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const html = fs.readFileSync(path.join(__dirname, '../fasta2a/static/docs.html'), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1]
    .replace('__FASTA2A_API_ROOT_JSON__', '""');

function createPage() {
    const task = {
        id: 'task-1', contextId: 'context-1', status: { state: 'completed' },
        history: [{ role: 'agent', messageId: 'reply-1', parts: [{ text: 'hello' }] }],
    };
    const messages = [];
    const requests = [];
    const input = { value: 'hello' };
    const button = {};
    const page = vm.createContext({
        console,
        document: {
            addEventListener() {},
            getElementById(id) { return id === 'message-input' ? input : button; },
        },
        fetch: async (_url, options) => {
            const request = JSON.parse(options.body);
            requests.push(request);
            const result = request.method === 'message/send' ? { task } : task;
            return { ok: true, json: async () => ({ jsonrpc: '2.0', id: request.id, result }) };
        },
        setTimeout() { throw new Error('A completed task must not be polled again'); },
    });
    vm.runInContext(script, page);
    page.addMessage = (text, sender, id) => messages.push({ text, sender, id });
    page.showError = message => { throw new Error(message); };
    return { page, messages, requests };
}

test('sendMessage reads the task wrapper and retains its context', async () => {
    const { page, requests } = createPage();
    await vm.runInContext('sendMessage()', page);
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(requests.length, 2);
    assert.equal(requests[1].params.id, 'task-1');
    assert.equal(vm.runInContext('contextId', page), 'context-1');
});

test('pollTaskStatus displays a flat text Part from the completed task', async () => {
    const { page, messages } = createPage();
    await vm.runInContext('currentTaskId = "task-1"; pollTaskStatus()', page);
    assert.deepEqual(messages, [{ text: 'hello', sender: 'agent', id: 'task-1' }]);
    assert.equal(vm.runInContext('currentTaskId', page), null);
});
