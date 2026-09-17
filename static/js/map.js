/**
 * static/js/map.js
 * ─────────────────
 * Leaflet地図の初期化・場所マーカー・フィルタ・ルート案内
 * + リアルタイム現在地トラッキング
 */

let map;
let locations = [];
let posts     = [];
let locationMarkers = [];

let selectedLatLng = null;
let selectedMarker = null;
let editingLocationId = null;

// ルートモード
let routeMode    = false;
let startLatLng  = null;
let goalLatLng   = null;
let startMarker  = null;
let goalMarker   = null;
let routeControl = null;

// 現在地トラッキング
let watchId          = null;   // navigator.geolocation.watchPosition の ID
let myMarker         = null;   // 現在地マーカー
let myAccuracyCircle = null;   // 精度円
let isTracking       = false;
let hasCenteredOnce  = false;  // 初回だけ地図を現在地に移動する

// 秋田県の境界
const AKITA_BOUNDS = [
    [38.85, 139.55],
    [40.60, 141.05]
];

// このズームレベル未満（＝これより引いた状態）ではアイコンを非表示にする
const MIN_ZOOM_FOR_ICONS = 11;

let mapNoticeTimer = null;

function showMapNotice(message, tone = 'success') {
    const notice = document.getElementById('mapNotice');
    if (!notice) return;
    clearTimeout(mapNoticeTimer);
    notice.replaceChildren(document.createTextNode(message));
    notice.dataset.tone = tone;
    notice.hidden = false;
    mapNoticeTimer = setTimeout(() => { notice.hidden = true; }, 3200);
}

function confirmMapAction(message, onConfirm) {
    const notice = document.getElementById('mapNotice');
    if (!notice) return;
    clearTimeout(mapNoticeTimer);
    notice.replaceChildren();
    notice.dataset.tone = 'confirm';
    const text = document.createElement('div');
    text.textContent = message;
    const actions = document.createElement('div');
    actions.className = 'map-notice-actions';
    const cancel = document.createElement('button');
    cancel.type = 'button'; cancel.className = 'btn-outline-theme'; cancel.textContent = 'キャンセル';
    cancel.onclick = () => { notice.hidden = true; };
    const proceed = document.createElement('button');
    proceed.type = 'button'; proceed.className = 'btn-theme'; proceed.textContent = '削除する';
    proceed.onclick = () => { notice.hidden = true; onConfirm(); };
    actions.append(cancel, proceed);
    notice.append(text, actions);
    notice.hidden = false;
}

// ──────────────────────────────────────────────
// 初期化（leaflet.js が確実に読み込まれてから実行）
// ──────────────────────────────────────────────
window.addEventListener('load', async function () {
    [locations, posts] = await Promise.all([
        fetch('/api/locations').then(r => r.json()),
        fetch('/api/posts').then(r => r.json()),
    ]);

    initMap();
    drawLocationMarkers();
    renderLocationList();
    updateMarkerVisibilityByZoom();
    setupViewModeTabs();
    setupLocationForm();
    setupFilterButtons();
    setupRouteButton();
    setupMyLocationButton();
});

function setViewMode(mode, updateHistory = true) {
    const showList = mode === 'list';
    const mapView = document.getElementById('mapView');
    const listView = document.getElementById('listView');
    const mapButton = document.getElementById('mapViewButton');
    const listButton = document.getElementById('listViewButton');
    if (!mapView || !listView || !mapButton || !listButton) return;

    mapView.hidden = showList;
    listView.hidden = !showList;
    mapButton.className = showList ? 'btn-outline-theme' : 'btn-theme';
    listButton.className = showList ? 'btn-theme' : 'btn-outline-theme';
    mapButton.setAttribute('aria-selected', showList ? 'false' : 'true');
    listButton.setAttribute('aria-selected', showList ? 'true' : 'false');

    if (updateHistory) {
        const url = showList
            ? `${window.location.pathname}${window.location.search}#list`
            : `${window.location.pathname}${window.location.search}`;
        window.history.replaceState(null, '', url);
    }

    if (!showList && map) {
        window.requestAnimationFrame(() => map.invalidateSize());
    }
}

function setupViewModeTabs() {
    const mapButton = document.getElementById('mapViewButton');
    const listButton = document.getElementById('listViewButton');
    if (!mapButton || !listButton) return;

    mapButton.addEventListener('click', () => setViewMode('map'));
    listButton.addEventListener('click', () => setViewMode('list'));
    window.addEventListener('hashchange', () => {
        setViewMode(window.location.hash === '#list' ? 'list' : 'map', false);
    });
    setViewMode(window.location.hash === '#list' ? 'list' : 'map', false);
}

function renderLocationList() {
    const container = document.getElementById('locationList');
    const summary = document.getElementById('locationListSummary');
    if (!container || !summary) return;

    container.replaceChildren();
    summary.textContent = `${locations.length}件の場所が登録されています。カードを選ぶと地図へ移動します。`;

    if (locations.length === 0) {
        const empty = document.createElement('p');
        empty.style.color = '#888';
        empty.textContent = 'まだ登録された場所がありません。';
        container.appendChild(empty);
        return;
    }

    locations.forEach((location) => {
        const locationPosts = posts.filter(post => post.location_id === location.id);
        const card = document.createElement('button');
        card.type = 'button';
        card.className = 'location-list-card';
        card.setAttribute('aria-label', `${location.name}を地図で見る`);

        const title = document.createElement('span');
        title.className = 'location-list-card-title';
        title.textContent = location.name;

        const meta = document.createElement('span');
        meta.className = 'location-list-card-meta';
        meta.textContent =
            `📍 ${location.city || '未設定'} ｜ 🏷️ ${location.type || 'その他'} ｜ 投稿 ${locationPosts.length}件`;

        const description = document.createElement('span');
        description.className = 'location-list-card-description';
        description.textContent = location.description || '説明はありません。';

        const jump = document.createElement('span');
        jump.className = 'location-list-card-jump';
        jump.textContent = '地図で見る 🗺️';

        card.append(title, meta, description, jump);
        card.addEventListener('click', () => jumpToLocation(location));
        container.appendChild(card);
    });
}

function jumpToLocation(location) {
    setViewMode('map');
    const marker = locationMarkers.find(item => item.locationId === location.id);
    const latlng = L.latLng(location.lat, location.lng);

    map.setView(latlng, 15);
    if (marker) {
        marker._filteredOut = false;
        if (!map.hasLayer(marker)) marker.addTo(map);
        marker.openPopup();
    }
    selectLocation(location, posts.filter(post => post.location_id === location.id));
}


function initMap() {
    map = L.map('map', {
        center: [39.7186, 140.1024],
        zoom: 9,
        minZoom: 8,
        maxZoom: 18,
        maxBounds: AKITA_BOUNDS,
        maxBoundsViscosity: 1.0,
    });

    L.tileLayer(
        'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19,
        }
    ).addTo(map);

    map.fitBounds(AKITA_BOUNDS);

    // ズームアウトしたらマーカーアイコンを非表示にする
    map.on('zoomend', updateMarkerVisibilityByZoom);

    map.on('click', function (e) {
        if (routeMode) {
            if (!startLatLng) {
                setRouteStart(e.latlng, '出発地点');
            } else {
                setRouteGoal(e.latlng, '到着地点');
            }
            return;
        }
        selectedLatLng = e.latlng;
        if (selectedMarker) map.removeLayer(selectedMarker);
        selectedMarker = L.marker(selectedLatLng)
            .addTo(map).bindPopup('ここに建物を追加できます').openPopup();
    });
}


// ──────────────────────────────────────────────
// 現在地トラッキング
// ──────────────────────────────────────────────

/** 現在地マーカーのカスタムアイコン（🐾 を pulse アニメーションで表示） */
function createMyIcon() {
    return L.divIcon({
        className: '',
        html: `
            <div style="
                position:relative;
                width:40px; height:40px;
            ">
                <!-- 外側のパルスリング -->
                <div style="
                    position:absolute;
                    inset:-8px;
                    border-radius:50%;
                    background:var(--main-c,#ff8fa3);
                    opacity:0.25;
                    animation:myLocPulse 2s ease-out infinite;
                "></div>
                <!-- 内側の円 -->
                <div style="
                    position:absolute;
                    inset:4px;
                    border-radius:50%;
                    background:var(--main-c,#ff8fa3);
                    border:3px solid #fff;
                    box-shadow:0 2px 8px rgba(0,0,0,0.3);
                    display:flex; align-items:center; justify-content:center;
                    font-size:14px;
                ">🐾</div>
            </div>
        `,
        iconSize:   [40, 40],
        iconAnchor: [20, 20],
        popupAnchor:[0, -20],
    });
}

/** CSS アニメーションをページに1回だけ注入 */
function injectMyLocCSS() {
    if (document.getElementById('myLocStyle')) return;
    const style = document.createElement('style');
    style.id = 'myLocStyle';
    style.textContent = `
        @keyframes myLocPulse {
            0%   { transform:scale(1);   opacity:0.4; }
            70%  { transform:scale(2.2); opacity:0;   }
            100% { transform:scale(2.2); opacity:0;   }
        }
    `;
    document.head.appendChild(style);
}

/** 位置情報が更新されるたびに呼ばれる */
function onPositionUpdate(pos) {
    const lat = pos.coords.latitude;
    const lng = pos.coords.longitude;
    const acc = pos.coords.accuracy;   // 精度（メートル）
    const latlng = L.latLng(lat, lng);

    // マーカーを作成 or 移動
    if (!myMarker) {
        injectMyLocCSS();
        myMarker = L.marker(latlng, { icon: createMyIcon(), zIndexOffset: 1000 })
            .addTo(map)
            .bindPopup('📍 現在地');
    } else {
        myMarker.setLatLng(latlng);
    }

    // 精度円を作成 or 更新
    if (!myAccuracyCircle) {
        myAccuracyCircle = L.circle(latlng, {
            radius: acc,
            color: 'var(--main-c, #ff8fa3)',
            fillColor: 'var(--main-c, #ff8fa3)',
            fillOpacity: 0.12,
            weight: 1.5,
        }).addTo(map);
    } else {
        myAccuracyCircle.setLatLng(latlng);
        myAccuracyCircle.setRadius(acc);
    }

    // 初回だけ現在地に地図を移動
    if (!hasCenteredOnce) {
        map.setView(latlng, 15);
        hasCenteredOnce = true;
    }

    // サイドパネルのステータスを更新
    updateMyLocStatus(lat, lng, acc);
}

function onPositionError(err) {
    const msg = {
        1: '位置情報の使用が拒否されました。ブラウザの設定を確認してください。',
        2: '位置情報を取得できませんでした。',
        3: '位置情報の取得がタイムアウトしました。',
    }[err.code] || '位置情報の取得に失敗しました。';
    updateMyLocStatus(null, null, null, msg);
    stopTracking();
}

function startTracking() {
    if (!navigator.geolocation) {
        alert('このブラウザはGPS位置情報に対応していません。');
        return;
    }
    isTracking      = true;
    hasCenteredOnce = false;

    watchId = navigator.geolocation.watchPosition(
        onPositionUpdate,
        onPositionError,
        { enableHighAccuracy: true, maximumAge: 5000, timeout: 15000 }
    );

    // ボタン表示を更新
    const btn = document.getElementById('myLocationBtn');
    if (btn) {
        btn.textContent = '📍 現在地追跡 ON';
        btn.style.background    = 'var(--main-c, #ff8fa3)';
        btn.style.color         = '#fff';
        btn.style.borderColor   = 'var(--main-c, #ff8fa3)';
    }
}

function stopTracking() {
    if (watchId !== null) {
        navigator.geolocation.clearWatch(watchId);
        watchId = null;
    }
    isTracking = false;

    // マーカー・精度円を削除
    if (myMarker)         { map.removeLayer(myMarker);         myMarker         = null; }
    if (myAccuracyCircle) { map.removeLayer(myAccuracyCircle); myAccuracyCircle = null; }

    // ボタン表示を戻す
    const btn = document.getElementById('myLocationBtn');
    if (btn) {
        btn.textContent     = '📍 現在地を表示';
        btn.style.background  = '';
        btn.style.color       = '';
        btn.style.borderColor = '';
    }

    // ステータスをリセット
    const statusEl = document.getElementById('myLocStatus');
    if (statusEl) statusEl.innerHTML = '未取得';
}

/** サイドパネルのステータス表示を更新 */
function updateMyLocStatus(lat, lng, acc, errorMsg) {
    const el = document.getElementById('myLocStatus');
    if (!el) return;
    if (errorMsg) {
        el.style.color = '#e63946';
        el.innerHTML   = `❌ ${errorMsg}`;
        return;
    }
    el.style.color = '#11caa0';
    el.innerHTML =
        `✅ 緯度 ${lat.toFixed(5)}<br>` +
        `　 経度 ${lng.toFixed(5)}<br>` +
        `　 精度 ±${Math.round(acc)}m`;
}

function setupMyLocationButton() {
    const btn = document.getElementById('myLocationBtn');
    if (!btn) return;
    btn.addEventListener('click', () => {
        if (isTracking) {
            stopTracking();
        } else {
            startTracking();
        }
    });

    // 「現在地を出発点にする」ボタン
    const useAsStartBtn = document.getElementById('useMyLocAsStart');
    if (useAsStartBtn) {
        useAsStartBtn.addEventListener('click', () => {
            if (!myMarker) {
                alert('先に現在地追跡をONにしてください。');
                return;
            }
            if (!routeMode) document.getElementById('routeToggleButton').click();
            setRouteStart(myMarker.getLatLng(), '出発地点（現在地）');
        });
    }
}


// ──────────────────────────────────────────────
// 場所マーカー
// ──────────────────────────────────────────────
function drawLocationMarkers() {
    clearLocationMarkers();
    locations.forEach(addLocationMarker);
}

function clearLocationMarkers() {
    locationMarkers.forEach(m => map.removeLayer(m));
    locationMarkers = [];
}

function addLocationMarker(location) {
    const locPosts = posts.filter(p => p.location_id === location.id);
    const marker = L.marker([location.lat, location.lng], { icon: buildIcon(location) })
        .addTo(map)
        .bindTooltip(`${location.name}<br>${location.type}`,
            { permanent: true, direction: 'right', offset: [10, 0], className: 'map-label' })
        .bindPopup(buildPopupHtml(location, locPosts))
        .on('click', () => selectLocation(location, locPosts));

    marker.locationType = location.type;
    marker.locationId   = location.id;
    locationMarkers.push(marker);
}

function canManageLocation(location) {
    const currentUserId = window.MAP_CURRENT_USER_ID;
    return currentUserId !== null && currentUserId !== undefined &&
        (window.MAP_CURRENT_USER_IS_ADMIN || Number(location.author_id) === Number(currentUserId));
}

/** ポップアップの中身（自分の場所だけ編集・削除できる） */
function buildPopupHtml(location, locPosts) {
    const canManage = canManageLocation(location);
    const swatches = Object.values(TYPE_DEFAULT_COLORS).map(c =>
        `<button onclick="changeLocationColor(${location.id}, '${c}')" title="${c}"
            style="width:18px;height:18px;border-radius:50%;background:${c};
                   border:2px solid #fff;box-shadow:0 1px 3px rgba(0,0,0,.3);
                   cursor:pointer;padding:0;"></button>`
    ).join('');
    const postLinks = locPosts.length
        ? locPosts.map(post => `<a href="/post/${post.id}" style="display:block;margin-top:4px;color:var(--main-c,#ff8fa3);font-size:.82rem;">${post.title}</a>`).join('')
        : '<span style="font-size:.8rem;color:#888;">まだ投稿はありません</span>';

    return `
        <div style="min-width:190px;">
            <strong>${location.name}</strong><br>
            市町村：${location.city}<br>
            種類：${location.type}<br>
            投稿数：${locPosts.length}<br>
            ${location.description}
            <div style="margin-top:7px;"><strong style="font-size:.82rem;">この場所の投稿</strong>${postLinks}</div>
            <a href="/post_page?location_id=${location.id}&tab=location"
               style="display:block;margin-top:8px;text-align:center;background:var(--main-c,#ff8fa3);color:#fff;text-decoration:none;border-radius:8px;padding:7px 0;font-size:.85rem;cursor:pointer;">この場所に投稿する</a>
            ${canManage ? `
                <button onclick="editLocation(${location.id})"
                    style="margin-top:10px;width:100%;background:var(--main-c,#ff8fa3);color:#fff;border:none;
                           border-radius:8px;padding:7px 0;font-size:0.8rem;font-weight:bold;cursor:pointer;">
                    ✏️ この場所を編集
                </button>
                <div style="margin:8px 0 4px;font-size:0.75rem;color:#888;">アイコンの色を変える</div>
                <div style="display:flex;flex-wrap:wrap;gap:4px;">${swatches}</div>
                <button onclick="deleteLocation(${location.id})"
                    style="margin-top:10px;width:100%;background:#e63946;color:#fff;border:none;
                           border-radius:8px;padding:6px 0;font-size:0.8rem;cursor:pointer;">
                    🗑️ この場所を削除
                </button>` : ''}
        </div>
    `;
}

function applyLocationUpdate(updated) {
    const idx = locations.findIndex(location => location.id === updated.id);
    if (idx !== -1) locations[idx] = updated;
    const marker = locationMarkers.find(item => item.locationId === updated.id);
    if (marker) {
        marker.setLatLng([updated.lat, updated.lng]);
        marker.setIcon(buildIcon(updated));
        marker.setTooltipContent(`${updated.name}<br>${updated.type}`);
        marker.setPopupContent(buildPopupHtml(updated, posts.filter(post => post.location_id === updated.id)));
    }
    renderLocationList();
}

function editLocation(id) {
    const location = locations.find(item => item.id === id);
    if (!location || !canManageLocation(location)) return;

    editingLocationId = id;
    selectedLatLng = L.latLng(location.lat, location.lng);
    document.getElementById('locationName').value = location.name || '';
    document.getElementById('locationType').value = location.type || '';
    document.getElementById('locationDescription').value = location.description || '';
    document.getElementById('locationEditor').open = true;
    document.getElementById('locationEditorTitle').textContent = '✏️ 場所を編集';
    document.getElementById('locationEditorHint').textContent = '場所を移動する場合は地図上をクリック';
    document.getElementById('locationSubmitButton').textContent = '変更を保存';
    document.getElementById('locationCancelButton').style.display = '';

    if (location.icon_file) {
        document.querySelector('input[name="icon_mode"][value="upload"]').checked = true;
        switchIconMode('upload');
    } else {
        document.querySelector('input[name="icon_mode"][value="color"]').checked = true;
        switchIconMode('color');
        selectColor(location.icon_color || TYPE_COLORS[location.type] || '#546e7a');
    }
    map.closePopup();
    map.setView([location.lat, location.lng], Math.max(map.getZoom(), 15));
}

/** 場所を削除する */
async function deleteLocation(id) {
    confirmMapAction('この場所を削除しますか？', async () => {
        const res = await fetch(`/delete_location/${id}`, { method: 'POST', headers: { 'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content } }).then(r => r.json());
        if (res.error) { showMapNotice(res.error, 'error'); return; }

        const marker = locationMarkers.find(m => m.locationId === id);
        if (marker) {
            map.removeLayer(marker);
            locationMarkers = locationMarkers.filter(m => m !== marker);
        }
        locations = locations.filter(l => l.id !== id);
        renderLocationList();
        showMapNotice('場所を削除しました。');
    });
}

/** 場所のアイコン色を変更する */
async function changeLocationColor(id, color) {
    const formData = new FormData();
    formData.append('icon_color', color);

    const updated = await fetch(`/update_location_color/${id}`, { method: 'POST', headers: { 'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content }, body: formData })
        .then(r => r.json());
    if (updated.error) { showMapNotice(updated.error, 'error'); return; }
    applyLocationUpdate(updated);
}

/** ズームレベルに応じてマーカーの表示/非表示を切り替える */
function updateMarkerVisibilityByZoom() {
    const zoom = map.getZoom();
    locationMarkers.forEach(marker => {
        // フィルタで既に非表示にされているものは触らない
        const filteredOut = marker._filteredOut === true;
        if (filteredOut) return;

        if (zoom < MIN_ZOOM_FOR_ICONS) {
            if (map.hasLayer(marker)) map.removeLayer(marker);
        } else {
            if (!map.hasLayer(marker)) marker.addTo(map);
        }
    });
}

function selectLocation(location, locPosts) {
    document.getElementById('selectedName').textContent = location.name;
    document.getElementById('selectedInfo').innerHTML =
        `市町村：${location.city}<br>種類：${location.type}<br>` +
        `投稿数：${locPosts.length}<br>${location.description}`;

    if (routeMode) {
        const latlng = L.latLng(location.lat, location.lng);
        if (!startLatLng) {
            setRouteStart(latlng, `出発地点（${location.name}）`);
        } else {
            setRouteGoal(latlng, `到着地点（${location.name}）`);
        }
    }
}

// ──────────────────────────────────────────────
// アイコン生成（カスタム色 / アップロード画像 / 種類デフォルト色）
// ──────────────────────────────────────────────

/** 種類ごとのデフォルト色（map.htmlのTYPE_COLORSと同期） */
const TYPE_DEFAULT_COLORS = {
    '駅':     '#1976d2',
    '飲食店': '#e53935',
    '雑貨':   '#8e24aa',
    '学校':   '#f4511e',
    '公園':   '#2e7d32',
    '病院':   '#00838f',
    '行政施設':'#5d4037',
    '観光地': '#f9a825',
    'その他': '#546e7a',
};

/**
 * location オブジェクトを受け取り適切な Leaflet アイコンを返す。
 * 優先順: アップロード画像 > カスタム色 > 種類デフォルト色
 */
function buildIcon(location) {
    // ① アップロード画像がある場合
    if (location.icon_file) {
        return L.icon({
            iconUrl:    `/static/uploads/${location.icon_file}`,
            iconSize:   [36, 36],
            iconAnchor: [18, 36],
            popupAnchor:[0, -36],
        });
    }

    // ② カラー丸マーカー（カスタム色 or 種類デフォルト色）
    const color = location.icon_color
        || TYPE_DEFAULT_COLORS[location.type]
        || '#546e7a';

    // 種類の頭文字を1文字ラベルとして表示
    const label = (location.type || '?').charAt(0);

    return L.divIcon({
        className: '',
        html: `
            <div style="
                width:36px; height:36px;
                background:${color};
                border-radius:50% 50% 50% 0;
                transform:rotate(-45deg);
                border:3px solid #fff;
                box-shadow:0 2px 8px rgba(0,0,0,0.3);
                display:flex; align-items:center; justify-content:center;
            ">
                <span style="
                    transform:rotate(45deg);
                    color:#fff; font-size:13px; font-weight:bold;
                    line-height:1; user-select:none;
                ">${label}</span>
            </div>
        `,
        iconSize:   [36, 36],
        iconAnchor: [18, 36],
        popupAnchor:[0, -40],
    });
}

/** 後方互換：type文字列だけで呼ばれる場合（既存コード用） */
function getIconByType(type) {
    return buildIcon({ type, icon_color: '', icon_file: '' });
}


// ──────────────────────────────────────────────
// フィルタボタン
// ──────────────────────────────────────────────
function setupFilterButtons() {
    document.querySelectorAll('.filter-buttons button').forEach(btn => {
        btn.addEventListener('click', function () {
            document.querySelectorAll('.filter-buttons button').forEach(b => {
                b.classList.remove('btn-theme');
                b.classList.add('btn-outline-theme');
            });
            this.classList.remove('btn-outline-theme');
            this.classList.add('btn-theme');

            const type = this.dataset.type;
            locationMarkers.forEach(marker => {
                if (type === 'all' || marker.locationType === type) {
                    marker._filteredOut = false;
                } else {
                    marker._filteredOut = true;
                    map.removeLayer(marker);
                }
            });
            updateMarkerVisibilityByZoom();
        });
    });
}


// ──────────────────────────────────────────────
// ルート案内
// ──────────────────────────────────────────────
function setupRouteButton() {
    const btn = document.getElementById('routeToggleButton');
    btn.addEventListener('click', () => {
        if (!routeMode) {
            routeMode = true;
            clearRoute();
            btn.textContent = 'ルート表示 ON';
            btn.style.background  = 'var(--main-c,#ff8fa3)';
            btn.style.color       = '#fff';
            btn.style.borderColor = 'var(--main-c,#ff8fa3)';
            alert('ルートモード: まず地図上または場所マーカーをクリックして出発地点を選択してください。次の地図クリックまたは場所マーカークリックが到着地点になります。\n「現在地を出発点にする」ボタンも使えます。');
        } else {
            clearRoute();
            routeMode = false;
            btn.textContent     = 'ルート表示 OFF';
            btn.style.background  = '';
            btn.style.color       = '';
            btn.style.borderColor = '';
        }
    });
}

function drawRoute(start, goal) {
    if (routeControl) map.removeControl(routeControl);
    routeControl = L.Routing.control({
        // API キーを必要としない OSRM のルート検索サーバーを明示的に使用する。
        router: L.Routing.osrmv1({
            serviceUrl: 'https://router.project-osrm.org/route/v1',
            profile: 'driving',
        }),
        waypoints: [start, goal],
        routeWhileDragging: false,
        addWaypoints: false,
        draggableWaypoints: false,
        show: false,
    }).addTo(map);
}

function setRouteStart(latlng, label) {
    startLatLng = latlng;
    goalLatLng = null;
    if (routeControl) { map.removeControl(routeControl); routeControl = null; }
    if (startMarker) map.removeLayer(startMarker);
    if (goalMarker) { map.removeLayer(goalMarker); goalMarker = null; }
    startMarker = L.marker(startLatLng).addTo(map).bindPopup(label).openPopup();
    const btn = document.getElementById('routeToggleButton');
    if (btn) btn.textContent = '到着地点を選択';
}

function setRouteGoal(latlng, label) {
    goalLatLng = latlng;
    if (goalMarker) map.removeLayer(goalMarker);
    goalMarker = L.marker(goalLatLng).addTo(map).bindPopup(label).openPopup();
    drawRoute(startLatLng, goalLatLng);
    const btn = document.getElementById('routeToggleButton');
    if (btn) btn.textContent = 'ルート表示 ON（再選択可）';
}

function clearRoute() {
    if (routeControl) { map.removeControl(routeControl); routeControl = null; }
    if (startMarker)  { map.removeLayer(startMarker);   startMarker  = null; }
    if (goalMarker)   { map.removeLayer(goalMarker);    goalMarker   = null; }
    startLatLng = goalLatLng = null;
}


// ──────────────────────────────────────────────
// 場所登録フォーム（AJAX送信）
// ──────────────────────────────────────────────
function setupLocationForm() {
    const form = document.getElementById('locationForm');
    const cancelButton = document.getElementById('locationCancelButton');

    function resetLocationEditor() {
        form.reset();
        editingLocationId = null;
        document.getElementById('locationEditorTitle').textContent = '＋ 新しい場所を追加';
        document.getElementById('locationEditorHint').textContent = '地図上をクリックして位置を選択してください。';
        document.getElementById('locationSubmitButton').textContent = '建物を追加';
        cancelButton.style.display = 'none';
        document.querySelector('input[name="icon_mode"][value="color"]').checked = true;
        switchIconMode('color');
        if (typeof clearIconPreview === 'function') clearIconPreview();
        if (selectedMarker) { map.removeLayer(selectedMarker); selectedMarker = null; }
        selectedLatLng = null;
    }

    cancelButton.addEventListener('click', resetLocationEditor);

    form.addEventListener('submit', async function (e) {
        e.preventDefault();
        if (!selectedLatLng) {
            showMapNotice('先に地図をクリックして位置を選択してください。', 'error');
            return;
        }

        // FormData でそのまま送る（ファイルも含む）
        const formData = new FormData();
        formData.append('name',        document.getElementById('locationName').value);
        formData.append('type',        document.getElementById('locationType').value);
        formData.append('description', document.getElementById('locationDescription').value);
        formData.append('lat',         selectedLatLng.lat);
        formData.append('lng',         selectedLatLng.lng);

        // アイコン設定
        const iconMode = document.querySelector('input[name="icon_mode"]:checked')?.value || 'color';
        formData.append('icon_mode', iconMode);
        if (iconMode === 'color') {
            formData.append('icon_color', document.getElementById('iconColorValue').value);
        } else {
            const iconFile = document.getElementById('iconImageInput')?.files[0];
            if (iconFile) formData.append('icon_image', iconFile);
        }

        const endpoint = editingLocationId ? `/update_location/${editingLocationId}` : '/add_location';
        const newLoc = await fetch(endpoint, { method: 'POST', headers: { 'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content }, body: formData })
            .then(r => r.json());

        if (newLoc.error) { showMapNotice(newLoc.error, 'error'); return; }

        if (editingLocationId) {
            applyLocationUpdate(newLoc);
            showMapNotice(`場所「${newLoc.name}」を更新しました。`);
        } else {
            locations.push(newLoc);
            addLocationMarker(newLoc);
            renderLocationList();
            showMapNotice(`${newLoc.city} の場所「${newLoc.name}」を追加しました。`);
        }
        resetLocationEditor();
    });
}
