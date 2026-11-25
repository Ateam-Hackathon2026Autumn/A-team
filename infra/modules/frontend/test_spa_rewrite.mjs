import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const context = vm.createContext({});
vm.runInContext(readFileSync(new URL('./spa-rewrite.js', import.meta.url), 'utf8'), context);

test('direct UI navigation and reload return index.html', () => {
  for (const method of ['GET', 'HEAD']) {
    for (const uri of ['/', '/products', '/products/42', '/signin', '/dashboard/products/', '/checkout']) {
      const request = { method, uri };
      assert.equal(context.handler({ request }), request);
      assert.equal(request.uri, '/index.html');
    }
  }
});

test('API and asset errors are not replaced with the SPA', () => {
  for (const uri of ['/api', '/api/', '/api/v1/products', '/assets', '/assets/missing', '/assets/index.js', '/favicon.svg', '/missing.css', '/.well-known/test']) {
    const request = { method: 'GET', uri };
    assert.equal(context.handler({ request }).uri, uri);
  }
});

test('unsafe methods are not rewritten', () => {
  for (const method of ['POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']) {
    const request = { method, uri: '/products' };
    assert.equal(context.handler({ request }).uri, '/products');
  }
});

test('navigation keeps query strings and other request attributes', () => {
  const querystring = { orderId: { value: '42' } };
  const headers = { accept: { value: 'text/html' } };
  const request = { method: 'GET', uri: '/checkout', querystring, headers };
  const result = context.handler({ request });
  assert.equal(result.uri, '/index.html');
  assert.equal(result.querystring, querystring);
  assert.equal(result.headers, headers);
});
