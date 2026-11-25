// 実ソースを実行し、通信先と指定した依存だけを置き換えるテスト用ランタイム。
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const React = require('react');

const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
function runtime({ replies = [], reply, overrides = {}, mock = false } = {}) {
  const calls = [], cache = new Map(), storage = new Map();
  function load(filename) {
    if (cache.has(filename)) return cache.get(filename).exports;
    const source = fs.readFileSync(filename, 'utf8').replaceAll('import.meta.env', JSON.stringify({ DEV: true, VITE_USE_MOCK: String(mock) }));
    const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX } }).outputText;
    const module = { exports: {} };
    cache.set(filename, module);
    const context = vm.createContext({ module, exports: module.exports, Response, Request, Headers, URL, URLSearchParams,
      AbortController, AbortSignal, FormData, Blob, File, console, setTimeout, clearTimeout, structuredClone,
      crypto: require('node:crypto').webcrypto,
      window: { location: { origin: 'http://localhost' }, sessionStorage: { getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value) } },
      fetch: async (url, init) => {
        calls.push({ url, init });
        if (reply) return reply(url, init);
        assert.ok(replies.length, `Unexpected request: ${url}`);
        const result = replies.shift();
        if (result instanceof Error) throw result;
        return typeof result === 'function' ? result(url, init) : result;
      },
      require: name => {
        if (Object.hasOwn(overrides, name)) return overrides[name];
        if (!name.startsWith('.')) return require(name);
        const base = path.resolve(path.dirname(filename), name);
        const resolved = ['.tsx', '.ts', '/index.tsx', '/index.ts'].map(ext => base + ext).find(fs.existsSync);
        assert.ok(resolved, `Module not found: ${name}`);
        return load(resolved);
      },
    });
    new vm.Script(code, { filename }).runInContext(context);
    return module.exports;
  }
  return { calls, load: name => load(path.resolve(__dirname, '../../src', name)) };
}

// 画面本体の状態とイベントを確認する軽量fixture。DOM・ブラウザーの代用ではない。
function hooksFixture() {
  const values = [], effects = [];
  let cursor = 0;
  const react = { ...React,
    useState: initial => { const i = cursor++; if (!(i in values)) values[i] = typeof initial === 'function' ? initial() : initial; return [values[i], next => { values[i] = typeof next === 'function' ? next(values[i]) : next; }]; },
    useRef: initial => { const i = cursor++; return values[i] ??= { current: initial }; },
    useEffect: (fn, deps) => { const i = cursor++; if (!values[i] || !deps || deps.some((dep, j) => dep !== values[i][j])) { values[i] = deps; effects.push(fn); } },
    useCallback: fn => fn, useMemo: fn => fn(),
  };
  return { react, render(Component, props = {}) { cursor = 0; const tree = Component(props); effects.splice(0).forEach(fn => fn()); return tree; } };
}
function nodes(tree) {
  if (Array.isArray(tree)) return tree.flatMap(nodes);
  if (!tree || typeof tree !== 'object') return [];
  return [tree, ...nodes(tree.props?.children)];
}
const tick = () => new Promise(resolve => setImmediate(resolve));
const deferred = () => { let resolve; const promise = new Promise(done => { resolve = done; }); return { promise, resolve }; };
module.exports = { runtime, json, hooksFixture, nodes, tick, deferred };
