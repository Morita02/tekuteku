(() => {
    const script = document.currentScript;
    const soundUrl = script && script.dataset.soundUrl;
    if (!soundUrl) return;

    const clickSound = new Audio(soundUrl);
    clickSound.preload = 'auto';

    function readSavedVolume() {
        try {
            const raw = localStorage.getItem('click_sound_volume');
            if (raw === null) return 1;
            const saved = Number(raw);
            return Number.isFinite(saved) ? Math.min(1, Math.max(0, saved)) : 1;
        } catch {
            return 1;
        }
    }

    function setVolume(volume) {
        clickSound.volume = Math.min(1, Math.max(0, Number(volume)));
    }

    setVolume(readSavedVolume());

    window.addEventListener('tekuteku:click-volume-change', (event) => {
        setVolume(event.detail);
    });

    window.addEventListener('storage', (event) => {
        if (event.key === 'click_sound_volume') setVolume(readSavedVolume());
    });

    document.addEventListener('click', (event) => {
        const button = event.target.closest(
            'button, [role="button"], input[type="button"], input[type="submit"], input[type="reset"]'
        );
        if (!button || button.disabled || button.getAttribute('aria-disabled') === 'true') return;

        clickSound.currentTime = 0;
        const playback = clickSound.play();
        if (playback) playback.catch(() => {});
    }, true);
})();
