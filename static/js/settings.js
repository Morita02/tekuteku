/**
 * static/js/settings.js
 * ─────────────────────
 * 設定ページ（/settings）専用。
 * ここで選んだ値を Cookie に保存し、その場で見た目に反映する。
 * 実際の適用処理は theme.js（window.Tekuteku）に置いてある。
 */

const T = window.Tekuteku;

// ── テーマカラー：選ぶと、その色が浮き上がる ──────
function markSelectedColor(color) {
    document.querySelectorAll('.color-btn').forEach(btn => {
        const on = (btn.dataset.color === color);
        btn.classList.toggle('selected', on);
        btn.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
}

function initColorButtons() {
    document.querySelectorAll('.color-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            T.color = btn.dataset.color;
            T.setCookie('theme_color', T.color);
            T.applyTheme(T.color, T.dark);
            markSelectedColor(T.color);

            // 押した瞬間だけ、ぽんっと弾ませる
            btn.classList.remove('popping');
            void btn.offsetWidth;            // アニメーションを巻き戻すための再描画
            btn.classList.add('popping');
        });
        btn.addEventListener('animationend', () => btn.classList.remove('popping'));
    });
}

// ── 昼夜切替 ─────────────────────────────────────
function initModeRadios() {
    document.querySelectorAll('input[name="dark_mode"]').forEach(radio => {
        radio.addEventListener('change', () => {
            T.dark = (radio.value === '1');
            T.setCookie('dark_mode', T.dark ? '1' : '0');
            T.applyTheme(T.color, T.dark);
        });
    });
}

// ── 言葉づかい切替 ───────────────────────────────
function initLangRadios() {
    document.querySelectorAll('input[name="lang"]').forEach(radio => {
        radio.addEventListener('change', () => {
            T.lang = radio.value;
            T.setCookie('lang', T.lang);
            T.applyLang(T.lang);
        });
    });
}

// ── 保存済みの値をフォームに反映 ─────────────────
function syncRadios() {
    const modeRadio = document.querySelector(`input[name="dark_mode"][value="${T.dark ? '1' : '0'}"]`);
    if (modeRadio) modeRadio.checked = true;

    const langRadio = document.querySelector(`input[name="lang"][value="${T.lang}"]`);
    if (langRadio) langRadio.checked = true;
}

// ── ボタン効果音の音量 ──────────────────────────
function initClickSoundVolume() {
    const slider = document.getElementById('click_sound_volume');
    const output = document.getElementById('click_sound_volume_value');
    if (!slider || !output) return;

    let savedVolume = 1;
    try {
        const raw = localStorage.getItem('click_sound_volume');
        if (raw !== null) {
            const saved = Number(raw);
            if (Number.isFinite(saved)) savedVolume = Math.min(1, Math.max(0, saved));
        }
    } catch {
        // 保存領域が利用できない場合は、このページ内だけで設定を反映する。
    }

    slider.value = String(Math.round(savedVolume * 100));
    output.textContent = `${slider.value}%`;

    slider.addEventListener('input', () => {
        const volume = Number(slider.value) / 100;
        output.textContent = `${slider.value}%`;
        try {
            localStorage.setItem('click_sound_volume', String(volume));
        } catch {
            // 音量自体はカスタムイベントで引き続き反映できる。
        }
        window.dispatchEvent(new CustomEvent('tekuteku:click-volume-change', {
            detail: volume,
        }));
    });
}

document.addEventListener('DOMContentLoaded', () => {
    syncRadios();
    markSelectedColor(T.color);
    initColorButtons();
    initModeRadios();
    initLangRadios();
    initClickSoundVolume();
});
