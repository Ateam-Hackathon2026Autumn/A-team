// 画面 URL の直アクセス・リロード時は React の index.html を返す。
// API のレスポンスや、見つからない JS・CSS を HTML で置き換えない。
function handler(event) {
    var request = event.request;
    var uri = request.uri;

    if (request.method !== 'GET' && request.method !== 'HEAD') {
        return request;
    }
    if (uri === '/api' || uri.indexOf('/api/') === 0 ||
        uri === '/assets' || uri.indexOf('/assets/') === 0 ||
        uri === '/.well-known' || uri.indexOf('/.well-known/') === 0) {
        return request;
    }

    var lastSegment = uri.substring(uri.lastIndexOf('/') + 1);
    if (lastSegment.indexOf('.') === -1) {
        request.uri = '/index.html';
    }
    return request;
}
