/* Pipelet App-Switcher — open/close, outside click, Escape, focus management.
   Vanilla ES5-compatible, no dependencies.

   The panel is portalled to document.body when opened so it escapes any
   backdrop-filter / opacity / transform stacking contexts on ancestor
   elements (common in apps with a blurred topbar). On close it's
   returned to its original parent so future opens still find it.
*/
(function () {
    'use strict';

    function init() {
        var root = document.getElementById('pipelet-switcher');
        if (!root) return;
        var trigger = document.getElementById('pipelet-switcher-trigger');
        var panel   = document.getElementById('pipelet-switcher-panel');
        if (!trigger || !panel) return;

        // Remember where the panel originally lived so we can put it back
        var panelOrigParent = panel.parentNode;
        var panelOrigNext   = panel.nextSibling;

        function positionPanel() {
            var rect = trigger.getBoundingClientRect();
            // Panel is position:fixed when portalled — coordinates are viewport-relative
            panel.style.position = 'fixed';
            panel.style.top  = (rect.bottom + 8) + 'px';
            panel.style.left = rect.left + 'px';
        }

        function open() {
            // Portal to body so backdrop-filter / transform ancestors don't mute it
            if (panel.parentNode !== document.body) {
                document.body.appendChild(panel);
            }
            panel.hidden = false;
            positionPanel();
            // next frame so the [hidden] removal settles before the transition
            window.requestAnimationFrame(function () {
                root.setAttribute('data-open', 'true');
                panel.setAttribute('data-open', 'true');
                trigger.setAttribute('aria-expanded', 'true');
            });
            window.addEventListener('resize', positionPanel);
            window.addEventListener('scroll', positionPanel, true);
        }

        function close() {
            root.removeAttribute('data-open');
            panel.removeAttribute('data-open');
            trigger.setAttribute('aria-expanded', 'false');
            window.removeEventListener('resize', positionPanel);
            window.removeEventListener('scroll', positionPanel, true);
            // hide after transition so focus can't land inside, then return to origin
            window.setTimeout(function () {
                if (root.getAttribute('data-open') !== 'true') {
                    panel.hidden = true;
                    // Reset inline position styles so the CSS default applies next time
                    panel.style.position = '';
                    panel.style.top = '';
                    panel.style.left = '';
                    // Move back to original parent so the DOM tree stays tidy
                    if (panel.parentNode === document.body && panelOrigParent) {
                        if (panelOrigNext && panelOrigNext.parentNode === panelOrigParent) {
                            panelOrigParent.insertBefore(panel, panelOrigNext);
                        } else {
                            panelOrigParent.appendChild(panel);
                        }
                    }
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

        // Click outside → close. When portalled the panel is no longer
        // inside `root`, so we check both.
        document.addEventListener('click', function (e) {
            if (root.getAttribute('data-open') !== 'true') return;
            if (root.contains(e.target)) return;
            if (panel.contains(e.target)) return;
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
