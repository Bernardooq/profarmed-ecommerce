const modules = import.meta.glob('../images/brand/*.webp', { eager: true });

const brandAssetMap = Object.entries(modules).reduce((acc, [path, mod]) => {
  const filename = path.split('/').pop();
  const url = mod.default || mod;
  acc[filename] = url;
  acc[`/images/brand/${filename}`] = url;
  return acc;
}, {});

/**
 * Resuelve rutas de assets definidos en content.json hacia los archivos
 * optimizados y con hash generados por Vite en `src/images/brand/`.
 */
export function resolveBrandAsset(assetPath) {
  if (!assetPath) return '';
  if (brandAssetMap[assetPath]) return brandAssetMap[assetPath];
  const filename = assetPath.split('/').pop();
  return brandAssetMap[filename] || assetPath;
}

export default resolveBrandAsset;
