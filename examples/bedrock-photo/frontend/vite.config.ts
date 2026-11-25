import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    // この開発用 origin は Lambda Function URL の CORS 設定と合わせている。
    port: 5174,
    strictPort: true,
    proxy: {
      '/api': {
        // シェルで指定した API へ転送する。8787 番のサーバーは別途用意する必要がある。
        // S3 配信時はこの proxy を使わず、public/config.json の接続先を直接呼ぶ。
        target: process.env.PHOTO_API_PROXY_TARGET || 'http://127.0.0.1:8787',
        changeOrigin: true,
      },
    },
  },
})
