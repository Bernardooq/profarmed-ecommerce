import { useState, useEffect } from 'react';

/**
 * Syncs browser/PWA system bar meta tags (`theme-color`, `msapplication-TileColor`)
 * with the active CSS `--color-primary` variable defined in `tokens/_colors.scss`.
 */
export function syncThemeMeta() {
    if (typeof window === 'undefined' || typeof document === 'undefined') return;
    const root = document.documentElement;
    const primary = getComputedStyle(root).getPropertyValue('--color-primary').trim();
    if (!primary) return;

    document.querySelectorAll('meta[name="theme-color"], meta[name="msapplication-TileColor"]').forEach((el) => {
        el.setAttribute('content', primary);
    });
}

export function useTheme() {
    const [theme, setTheme] = useState(() => {
        // Por defecto siempre tema claro si no hay preferencia previa en localStorage
        if (typeof window !== 'undefined') {
            const savedTheme = localStorage.getItem('theme');
            if (savedTheme) {
                return savedTheme;
            }
        }
        return 'light';
    });

    useEffect(() => {
        const root = document.documentElement;
        if (theme === 'dark') {
            root.setAttribute('data-theme', 'dark');
            root.style.colorScheme = 'dark';
        } else {
            root.removeAttribute('data-theme');
            root.style.colorScheme = 'light';
        }
        localStorage.setItem('theme', theme);
        syncThemeMeta();
        const rafId = window.requestAnimationFrame(syncThemeMeta);
        return () => window.cancelAnimationFrame(rafId);
    }, [theme]);

    const toggleTheme = () => {
        setTheme(prev => (prev === 'light' ? 'dark' : 'light'));
    };

    return { theme, toggleTheme };
}

export default useTheme;
