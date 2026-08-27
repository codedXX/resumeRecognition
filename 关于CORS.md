Nginx 确实可以处理 CORS，但有两种不同方式：
1. 前端请求 /api/roles
   浏览器实际访问 151312.xyz/api/roles，Nginx 反代。网页与接口同域，不产生 CORS。这是你原本想实现的方式。
2. 前端继续请求 8.134.48.198/api/roles
   Nginx 仍会反代，但必须额外返回 Access-Control-Allow-Origin: http://151312.xyz 这类响应头，明确告诉浏览器“允许这个域名读取”。你当前 Nginx 配置只有 proxy_pass，没有这些 CORS 响应头。
所以不是 Nginx 没有工作；而是当前前端请求的是 IP，导致浏览器进入了 CORS 规则。最省事的处理仍是让前端改为请求 /api/...，让它走 151312.xyz/api/...。



location /api/ {
    if ($request_method = OPTIONS) {
        add_header Access-Control-Allow-Origin "*" always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, PATCH, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Content-Type" always;
        return 204;
    }

    proxy_pass http://172.17.0.1:8000;
    add_header Access-Control-Allow-Origin "*" always;
}