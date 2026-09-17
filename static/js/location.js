/**
 * static/js/location.js
 * ─────────────────────
 * GPS位置情報の取得 + 逆ジオコーディングによる場所名自動入力
 * post.html から読み込まれる。
 *
 * 呼び出し方:
 *   getGPSLocation(statusId, latId, lngId, placeId)
 *     statusId : 取得状況を表示する <span> の id
 *     latId    : 緯度を格納する <input hidden> の id
 *     lngId    : 経度を格納する <input hidden> の id
 *     placeId  : 場所名テキスト欄の id（空のときだけ自動入力）
 */
function getGPSLocation(statusId, latId, lngId, placeId) {
    const status = document.getElementById(statusId);

    if (!navigator.geolocation) {
        status.style.color = '#e63946';
        status.textContent = '❌ このブラウザはGPS位置情報に対応していません。';
        return;
    }

    status.style.color = '#888';
    status.textContent = '📡 位置情報を取得中...';

    navigator.geolocation.getCurrentPosition(
        (pos) => {
            const lat = pos.coords.latitude;
            const lng = pos.coords.longitude;

            document.getElementById(latId).value = lat;
            document.getElementById(lngId).value = lng;

            status.style.color = '#11caa0';
            status.textContent =
                `✅ 取得成功！ 緯度 ${lat.toFixed(4)}, 経度 ${lng.toFixed(4)} ` +
                `（サーバー側でプライバシー保護のぼかし処理が行われます）`;

            // 場所名が空なら逆ジオコーディングで自動入力
            const placeEl = placeId ? document.getElementById(placeId) : null;
            if (placeEl && !placeEl.value.trim()) {
                fetch(
                    `https://nominatim.openstreetmap.org/reverse` +
                    `?format=json&lat=${lat}&lon=${lng}&zoom=16&addressdetails=1`,
                    { headers: { 'Accept-Language': 'ja' } }
                )
                .then(r => r.json())
                .then(data => {
                    const a = data.address || {};
                    // 道路 → 丁目 → 近隣 → 地区 → 市区町村 の優先順で取得
                    const name =
                        a.road            ||
                        a.neighbourhood   ||
                        a.suburb          ||
                        a.quarter         ||
                        a.city_district   ||
                        a.town            ||
                        a.city            ||
                        '';
                    if (name) placeEl.value = name;
                })
                .catch(() => {}); // ネットワークエラーは無視
            }
        },
        (_err) => {
            status.style.color = '#e63946';
            status.textContent =
                '❌ 位置情報の取得が拒否されたか、失敗しました。' +
                'ブラウザの許可設定を確認してください。';
        },
        { enableHighAccuracy: true, timeout: 10000 }
    );
}
