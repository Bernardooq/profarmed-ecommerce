import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

/**
 * Extracts `:root` CSS custom properties from `src/styles/tokens/_colors.scss`
 * so `index.html`, `manifest.json`, and `offline.html` always stay in sync
 * with the design tokens used across the React UI.
 */
function readScssColorTokens() {
  const colorsPath = path.resolve(__dirname, 'src/styles/tokens/_colors.scss')
  if (!fs.existsSync(colorsPath)) return {}

  const scss = fs.readFileSync(colorsPath, 'utf-8')
  const rootMatch = scss.match(/:root\s*\{([\s\S]*?)\}/)
  if (!rootMatch) return {}

  const block = rootMatch[1]
  const readVar = (name) => {
    const match = block.match(new RegExp(`${name}\\s*:\\s*([^;\\r\\n/]+)`))
    return match ? match[1].trim() : ''
  }

  return {
    primary: readVar('--color-primary'),
    primaryHover: readVar('--color-primary-hover'),
    secondary: readVar('--color-secondary'),
    bg: readVar('--color-bg'),
    surface: readVar('--color-surface'),
    text: readVar('--color-text'),
    textMuted: readVar('--color-text-muted'),
  }
}

function resolveBrandConfig(mode) {
  const env = loadEnv(mode, process.cwd(), '')
  const scssTokens = readScssColorTokens()

  let content = {}
  try {
    const contentPath = path.resolve(__dirname, 'src/config/content.json')
    if (fs.existsSync(contentPath)) {
      content = JSON.parse(fs.readFileSync(contentPath, 'utf-8'))
    }
  } catch (e) {
    // ignore json read error
  }

  const brandName = env.VITE_BRAND_NAME || content.brand?.name || 'Comercio B2B'
  const themeColor = scssTokens.primary || content.brand?.themeColor || env.VITE_THEME_COLOR || '#10b981'
  const primaryHover = scssTokens.primaryHover || themeColor
  const secondaryColor = scssTokens.secondary || themeColor
  const bgColor = scssTokens.bg || '#ffffff'
  const surfaceColor = scssTokens.surface || bgColor
  const textColor = scssTokens.text || '#1a1a1a'
  const textMutedColor = scssTokens.textMuted || '#666666'
  const apiBaseUrl =
    (env.VITE_API_BASE_URL && !env.VITE_API_BASE_URL.includes('localhost'))
      ? env.VITE_API_BASE_URL
      : (content.brand?.apiBaseUrl || '')

  return {
    brandName,
    themeColor,
    primaryHover,
    secondaryColor,
    bgColor,
    surfaceColor,
    textColor,
    textMutedColor,
    apiBaseUrl,
  }
}

function applyBrandTokens(source, tokens) {
  return source
    .replace(/%VITE_BRAND_NAME%/g, tokens.brandName)
    .replace(/%BRAND_NAME%/g, tokens.brandName)
    .replace(/%VITE_THEME_COLOR%/g, tokens.themeColor)
    .replace(/%BRAND_THEME_COLOR%/g, tokens.themeColor)
    .replace(/%BRAND_PRIMARY_HOVER%/g, tokens.primaryHover)
    .replace(/%BRAND_SECONDARY_COLOR%/g, tokens.secondaryColor)
    .replace(/%BRAND_BG_COLOR%/g, tokens.bgColor)
    .replace(/%BRAND_SURFACE_COLOR%/g, tokens.surfaceColor)
    .replace(/%BRAND_TEXT_COLOR%/g, tokens.textColor)
    .replace(/%BRAND_TEXT_MUTED_COLOR%/g, tokens.textMutedColor)
    .replace(/%BRAND_API_BASE_URL%/g, tokens.apiBaseUrl)
}

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const brandTokens = resolveBrandConfig(mode)
  let outDir = path.resolve(__dirname, 'dist')

  return {
    define: {
      __BRAND_THEME_COLOR__: JSON.stringify(brandTokens.themeColor),
    },
    plugins: [
      react(),
      {
        name: 'brand-assets-transform',
        configResolved(config) {
          outDir = path.resolve(config.root, config.build.outDir)
        },
        transformIndexHtml(html) {
          return applyBrandTokens(html, resolveBrandConfig(mode))
        },
        configureServer(server) {
          const publicFiles = {
            '/manifest.json': 'application/manifest+json; charset=utf-8',
            '/offline.html': 'text/html; charset=utf-8',
          }

          server.middlewares.use((req, res, next) => {
            const urlPath = (req.url || '').split('?')[0]
            const contentType = publicFiles[urlPath]
            if (!contentType) return next()

            const filePath = path.resolve(__dirname, 'public', urlPath.slice(1))
            if (!fs.existsSync(filePath)) return next()

            const content = fs.readFileSync(filePath, 'utf-8')
            res.setHeader('Content-Type', contentType)
            res.end(applyBrandTokens(content, resolveBrandConfig(mode)))
          })
        },
        closeBundle() {
          const tokens = resolveBrandConfig(mode)
          for (const filename of ['manifest.json', 'offline.html']) {
            const targetPath = path.join(outDir, filename)
            if (fs.existsSync(targetPath)) {
              const raw = fs.readFileSync(targetPath, 'utf-8')
              fs.writeFileSync(targetPath, applyBrandTokens(raw, tokens), 'utf-8')
            }
          }
        }
      }
    ],
    server: {
      host: '0.0.0.0',
      port: 5173,
      watch: {
        usePolling: true,
      }
    },
    build: {
      rollupOptions: {
        output: {
          // Asegurar que los archivos PWA se copien al build
          assetFileNames: (assetInfo) => {
            if (assetInfo.name === 'manifest.json' || assetInfo.name === 'sw.js') {
              return '[name][extname]'
            }
            return 'assets/[name]-[hash][extname]'
          }
        }
      }
    }
  }
})
