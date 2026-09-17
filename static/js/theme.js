/**
 * static/js/theme.js
 * ──────────────────
 * 全ページ共通。Cookie に保存された設定（色・昼夜・ことば）を読み込み、
 * CSS変数 (--main-c など) と文言に適用するだけを担当する。
 *
 * 設定を「変更する」UI の処理は settings.js（設定ページ専用）にある。
 * base.html から全ページで読み込む。
 */

// ── Cookie ユーティリティ ──────────────────────
function setCookie(name, value, days = 365) {
    const expires = new Date(Date.now() + days * 864e5).toUTCString();
    document.cookie = `${name}=${encodeURIComponent(value)};expires=${expires};path=/;SameSite=Lax`;
}
function getCookie(name) {
    return document.cookie.split('; ').reduce((acc, c) => {
        const [k, v] = c.split('=');
        return k === name ? decodeURIComponent(v) : acc;
    }, null);
}

// ── 設定値 ───────────────────────────────────────
const COLOR_PALETTE = {
    'さくらピンク':    { c: '#ff8fa3', fg: '#ffffff' },
    'なまはげレッド':  { c: '#e63946', fg: '#ffffff' },
    'ふきいろグリーン': { c: '#11caa0', fg: '#ffffff' },
    'ババヘライエロー': { c: '#ffb703', fg: '#443300' },  // 明るいので文字は濃い茶
    '日本海ブルー':    { c: '#219ebc', fg: '#ffffff' },
};

/** テーマカラーに対して読みやすい文字色を返す */
function foregroundFor(color) {
    const hit = Object.values(COLOR_PALETTE).find(v => v.c.toLowerCase() === String(color).toLowerCase());
    return hit ? hit.fg : '#ffffff';
}

let currentColor = getCookie('theme_color') || '#ff8fa3';
let isDark       = (getCookie('dark_mode') === '1');
let currentLang  = getCookie('lang') || '標準語';

// ── CSS変数への適用 ────────────────────────────
// 背景・影・文字色は style.css 側が --main-c から color-mix() で派生させるので、
// ここで渡すのは「テーマカラー」「その上の文字色」「昼夜」の 3 つだけでよい。
function applyTheme(color, dark) {
    const root = document.documentElement;
    root.style.setProperty('--main-c', color);
    root.style.setProperty('--on-main', foregroundFor(color));
    root.dataset.mode = dark ? 'dark' : 'light';

    // 降るアイテムの絵文字（CSS変数からは textContent に入れられないので JS で）
    document.querySelectorAll('.falling-item').forEach(el => {
        el.textContent = dark ? '✨' : '🌸';
    });
}

// ── 言語 ─────────────────────────────────────────
const TEXTS = {
    '標準語': {
        tab_map:       '🔍 場所検索',
        tab_event:     '🎈 イベント情報',
        tab_road:      '🚧 道路状況',
        nav_settings:  '設定',
        settings_title:'⚙️ もっとかわいくする設定',
        settings_lead: '色・明るさ・ことばづかいを、お好みに変えられます 🐾',
        mode_label:    '👹 昼夜の切り替え',
        mode_day:      '☀️ 昼のおさんぽ',
        mode_night:    '🌙 夜のおさんぽ（ダークモード）',
        lang_label:    '👹 言葉づかいの切り替え',
        color_label:   '🎨 お好みのテーマカラー',
        color_hint:    '押すと、その色がふわっと浮き上がります',
    },
    '秋田弁': {
        tab_map:       '🔍 さがしもの',
        tab_event:     '🎈 催しもの',
        tab_road:      '🚧 道路の様子',
        nav_settings:  '設定',
        settings_title:'⚙️ もっとかわいくしれ',
        settings_lead: '色っこも明るさもしゃべり方も、好きに変えでけれ 🐾',
        mode_label:    '👹 明るさ変えるべ',
        mode_day:      '☀️ 昼のおさんぽ',
        mode_night:    '🌙 夜のおさんぽ（暗い画面）',
        lang_label:    '👹 しゃべり方選んでけれ',
        color_label:   '🎨 好きな色っこ選んでけれ',
        color_hint:    '押せば、その色っこがふわっと浮ぐよ',
    },
};

function applyLang(lang) {
    const t = TEXTS[lang] || TEXTS['標準語'];
    // data-i18n="キー" が付いた要素をまとめて差し替える
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const text = t[el.dataset.i18n];
        if (text !== undefined) el.textContent = text;
    });
}

// ── 起動（全ページ） ─────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    applyTheme(currentColor, isDark);
    applyLang(currentLang);
});

// 設定ページ（settings.js）から使えるように公開
window.Tekuteku = {
    setCookie, getCookie,
    applyTheme, applyLang,
    COLOR_PALETTE, TEXTS,
    get color() { return currentColor; }, set color(v) { currentColor = v; },
    get dark()  { return isDark;       }, set dark(v)  { isDark = v;       },
    get lang()  { return currentLang;  }, set lang(v)  { currentLang = v;  },
};
