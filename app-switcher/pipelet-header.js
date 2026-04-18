/* Pipelet Header — shared dropdown, theme, and language affordances.
   Vanilla ES5, idempotent, no framework assumptions. */
(function () {
    'use strict';

    function toArray(list) {
        return Array.prototype.slice.call(list || []);
    }

    function unique(items) {
        var seen = {};
        var out = [];
        for (var i = 0; i < items.length; i++) {
            var value = String(items[i] || '').trim();
            if (!value || seen[value]) continue;
            seen[value] = true;
            out.push(value);
        }
        return out;
    }

    function themeStorageKeys() {
        var attr = document.documentElement.getAttribute('data-theme-storage') || '';
        return unique(attr.split(',').concat(['theme']));
    }

    function themeControls() {
        return toArray(document.querySelectorAll('[data-theme]')).filter(function (el) {
            return el !== document.documentElement;
        });
    }

    function storedTheme() {
        var keys = themeStorageKeys();
        for (var i = 0; i < keys.length; i++) {
            try {
                var value = window.localStorage.getItem(keys[i]);
                if (value === 'light' || value === 'dark') return value;
            } catch (e) {}
        }
        return null;
    }

    function writeTheme(theme) {
        var next = theme === 'dark' ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', next);
        var keys = themeStorageKeys();
        for (var i = 0; i < keys.length; i++) {
            try { window.localStorage.setItem(keys[i], next); } catch (e) {}
        }
        themeControls().forEach(function (el) {
            if (!el.classList) return;
            var active = el.getAttribute('data-theme') === next;
            el.classList.toggle('active', active);
            if (el.hasAttribute('aria-pressed')) el.setAttribute('aria-pressed', String(active));
        });
    }

    function currentLang() {
        if (document.documentElement.lang) return document.documentElement.lang;
        try {
            return window.localStorage.getItem('pipelet-lang') || '';
        } catch (e) {
            return '';
        }
    }

    function writeLang(lang) {
        if (!lang) return;
        document.documentElement.lang = lang;
        try { window.localStorage.setItem('pipelet-lang', lang); } catch (e) {}
        toArray(document.querySelectorAll('[data-lang]')).forEach(function (el) {
            if (!el.classList) return;
            var active = el.getAttribute('data-lang') === lang;
            el.classList.toggle('active', active);
            if (el.hasAttribute('aria-pressed')) el.setAttribute('aria-pressed', String(active));
        });
    }

    function closeDropdown(root) {
        var toggle = root.querySelector('.prefs-toggle');
        var menu = root.querySelector('.prefs-menu');
        if (!toggle || !menu) return;
        root.classList.remove('open');
        menu.classList.remove('open');
        menu.removeAttribute('data-open');
        toggle.setAttribute('aria-expanded', 'false');
    }

    function openDropdown(root) {
        var toggle = root.querySelector('.prefs-toggle');
        var menu = root.querySelector('.prefs-menu');
        if (!toggle || !menu) return;
        root.classList.add('open');
        menu.classList.add('open');
        menu.setAttribute('data-open', 'true');
        toggle.setAttribute('aria-expanded', 'true');
    }

    function bindDropdown(root) {
        if (!root || root.getAttribute('data-pipelet-header-bound') === 'true') return;
        var toggle = root.querySelector('.prefs-toggle');
        var menu = root.querySelector('.prefs-menu');
        if (!toggle || !menu) return;
        root.setAttribute('data-pipelet-header-bound', 'true');

        if (!toggle.hasAttribute('aria-expanded')) toggle.setAttribute('aria-expanded', 'false');
        toggle.addEventListener('click', function (event) {
            event.preventDefault();
            event.stopPropagation();
            if (menu.classList.contains('open')) closeDropdown(root);
            else openDropdown(root);
        });

        menu.addEventListener('click', function (event) {
            var target = event.target;
            while (target && target !== menu) {
                if (target.matches && target.matches('[data-close-on-click], .prefs-item')) {
                    if (!target.hasAttribute('data-keep-open')) {
                        window.setTimeout(function () { closeDropdown(root); }, 0);
                    }
                    return;
                }
                target = target.parentNode;
            }
        });
    }

    function bindThemeControls() {
        themeControls().forEach(function (el) {
            if (el.getAttribute('data-pipelet-theme-bound') === 'true') return;
            el.setAttribute('data-pipelet-theme-bound', 'true');
            el.addEventListener('click', function (event) {
                var value = el.getAttribute('data-theme');
                if (el.tagName !== 'A') event.preventDefault();
                writeTheme(value);
            });
        });
        writeTheme(storedTheme() || document.documentElement.getAttribute('data-theme') || 'light');
    }

    function bindLangControls() {
        toArray(document.querySelectorAll('[data-lang]')).forEach(function (el) {
            if (el.getAttribute('data-pipelet-lang-bound') === 'true') return;
            el.setAttribute('data-pipelet-lang-bound', 'true');
            el.addEventListener('click', function (event) {
                var value = el.getAttribute('data-lang');
                if (el.tagName !== 'A') event.preventDefault();
                writeLang(value);
            });
        });
        writeLang(currentLang());
    }

    function init() {
        toArray(document.querySelectorAll('.prefs-dropdown')).forEach(bindDropdown);
        bindThemeControls();
        bindLangControls();
    }

    document.addEventListener('click', function (event) {
        toArray(document.querySelectorAll('.prefs-dropdown.open')).forEach(function (root) {
            if (!root.contains(event.target)) closeDropdown(root);
        });
    });

    document.addEventListener('keydown', function (event) {
        if (event.key !== 'Escape' && event.keyCode !== 27) return;
        toArray(document.querySelectorAll('.prefs-dropdown.open')).forEach(function (root) {
            closeDropdown(root);
            var toggle = root.querySelector('.prefs-toggle');
            if (toggle) toggle.focus();
        });
    });

    window.PipeletHeader = window.PipeletHeader || {};
    window.PipeletHeader.init = init;
    window.PipeletHeader.applyTheme = writeTheme;
    window.PipeletHeader.applyLanguage = writeLang;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
