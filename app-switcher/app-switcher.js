/* Pipelet App-Switcher — open/close, outside click, Escape, focus management.
   Vanilla ES5-compatible, no dependencies.
*/
(function () {
    'use strict';

    function init() {
        var root = document.getElementById('pipelet-switcher');
        if (!root) return;
        var trigger = document.getElementById('pipelet-switcher-trigger');
        var panel   = document.getElementById('pipelet-switcher-panel');
        if (!trigger || !panel) return;

        function open() {
            panel.hidden = false;
            // next frame so the [hidden] removal settles before the transition
            window.requestAnimationFrame(function () {
                root.setAttribute('data-open', 'true');
                trigger.setAttribute('aria-expanded', 'true');
            });
        }

        function close() {
            root.removeAttribute('data-open');
            trigger.setAttribute('aria-expanded', 'false');
            // hide after transition so focus can't land inside
            window.setTimeout(function () {
                if (root.getAttribute('data-open') !== 'true') {
                    panel.hidden = true;
                }
            }, 160);
        }

        function toggle() {
            if (root.getAttribute('data-open') === 'true') {
                close();
            } else {
                open();
            }
        }

        trigger.addEventListener('click', function (e) {
            e.stopPropagation();
            toggle();
        });

        // Click outside → close
        document.addEventListener('click', function (e) {
            if (root.getAttribute('data-open') !== 'true') return;
            if (root.contains(e.target)) return;
            close();
        });

        // Escape → close + refocus trigger
        document.addEventListener('keydown', function (e) {
            if (e.key !== 'Escape' && e.keyCode !== 27) return;
            if (root.getAttribute('data-open') !== 'true') return;
            close();
            trigger.focus();
        });

        // Disabled tiles: prevent accidental interaction, announce politely
        var disabled = panel.querySelectorAll('.pipelet-switcher-tile.is-disabled');
        for (var i = 0; i < disabled.length; i++) {
            disabled[i].addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
