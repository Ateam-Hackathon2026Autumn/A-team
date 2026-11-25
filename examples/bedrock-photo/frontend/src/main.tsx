import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './styles.css'

// index.html の #root に画面を描画する。API との接続処理は App → api.ts が担当する。
createRoot(document.getElementById('root')!).render(
  <StrictMode><App /></StrictMode>,
)
