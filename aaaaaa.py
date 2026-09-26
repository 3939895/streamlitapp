import streamlit as st
import requests
import pandas as pd
import math
import time


# ========================================
# ページ設定
# ========================================

st.set_page_config(
    page_title="近くのコンビニ検索",
    page_icon="🏪"
)

st.title("🏪 近くのコンビニ検索")
st.write("場所を入力すると、その周辺にあるコンビニを表示します。")


# ========================================
# User-Agent
# ========================================
# Nominatimの利用規約に対応するため、
# アプリを識別できるUser-Agentを設定します。
#
# 公開する場合は、自分の連絡先を入れることをおすすめします。

USER_AGENT = (
    "ConvenienceStoreSearchApp/1.0 "
    "(contact: your-email@example.com)"
)


# ========================================
# 2地点間の距離を計算する関数
# ========================================

def calculate_distance(lat1, lon1, lat2, lon2):

    R = 6371  # 地球の半径 km

    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    dlat = lat2 - lat1
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return R * c


# ========================================
# 場所 → 緯度・経度
# ========================================

@st.cache_data(ttl=3600)
def get_location(place):

    url = "https://nominatim.openstreetmap.org/search"

    params = {
        "q": place,
        "format": "jsonv2",
        "limit": 1,
        "countrycodes": "jp"
    }

    headers = {
        "User-Agent": USER_AGENT
    }

    response = requests.get(
        url,
        params=params,
        headers=headers,
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    if not data:
        return None

    return (
        float(data[0]["lat"]),
        float(data[0]["lon"])
    )


# ========================================
# 周辺のコンビニを検索
# ========================================

@st.cache_data(ttl=300)
def get_convenience_stores(lat, lon, radius):

    query = f"""
    [out:json];

    (
      node["shop"="convenience"](around:{radius},{lat},{lon});
      way["shop"="convenience"](around:{radius},{lat},{lon});
    );

    out center;
    """

    url = "https://overpass-api.de/api/interpreter"

    headers = {
        "User-Agent": USER_AGENT
    }

    response = requests.post(
        url,
        data=query,
        headers=headers,
        timeout=30
    )

    response.raise_for_status()

    return response.json()["elements"]


# ========================================
# 入力欄
# ========================================

place = st.text_input(
    "📍 場所を入力してください",
    placeholder="例：豊橋駅、東京駅、大阪城"
)

radius = st.slider(
    "検索範囲（km）",
    min_value=0.5,
    max_value=5.0,
    value=2.0,
    step=0.5
)


# ========================================
# 検索
# ========================================

if st.button("🔍 コンビニを検索"):

    # ------------------------------------
    # 入力チェック
    # ------------------------------------

    place = place.strip()

    if not place:

        st.warning("場所を入力してください。")
        st.stop()

    # 長すぎる入力を防止
    if len(place) > 100:

        st.error("場所の名前は100文字以内で入力してください。")
        st.stop()


    # ------------------------------------
    # Nominatimへのアクセス
    # ------------------------------------

    with st.spinner("場所を検索しています..."):

        try:

            location = get_location(place)

        except requests.exceptions.RequestException:

            location = None

    if location is None:

        st.error(
            "場所が見つからないか、場所検索サービスに接続できませんでした。"
        )

        st.stop()


    # ====================================
    # 検索地点
    # ====================================

    lat, lon = location

    st.success(
        f"検索地点：緯度 {lat:.5f} / 経度 {lon:.5f}"
    )


    # ====================================
    # 検索地点の地図
    # ====================================

    st.subheader("📍 検索地点")

    map_data = pd.DataFrame(
        {
            "lat": [lat],
            "lon": [lon]
        }
    )

    st.map(map_data)


    # ====================================
    # コンビニ検索
    # ====================================

    with st.spinner("近くのコンビニを検索しています..."):

        try:

            stores = get_convenience_stores(
                lat,
                lon,
                int(radius * 1000)
            )

        except requests.exceptions.RequestException:

            st.error(
                "コンビニの検索に失敗しました。"
            )

            st.stop()


    # ====================================
    # 結果を整理
    # ====================================

    results = []

    for store in stores:

        # -------------------------------
        # 座標を取得
        # -------------------------------

        if store["type"] == "node":

            store_lat = store["lat"]
            store_lon = store["lon"]

        else:

            if "center" not in store:
                continue

            store_lat = store["center"]["lat"]
            store_lon = store["center"]["lon"]


        # -------------------------------
        # 店舗情報
        # -------------------------------

        tags = store.get("tags", {})

        name = tags.get(
            "name",
            "名前なし"
        )


        # -------------------------------
        # 距離計算
        # -------------------------------

        distance = calculate_distance(
            lat,
            lon,
            store_lat,
            store_lon
        )


        results.append(
            {
                "名前": name,
                "距離(km)": round(distance, 2),
                "緯度": store_lat,
                "経度": store_lon
            }
        )


    # ====================================
    # 距離順に並べる
    # ====================================

    results.sort(
        key=lambda x: x["距離(km)"]
    )


    # ====================================
    # 結果表示
    # ====================================

    if not results:

        st.warning(
            f"{radius}km以内にコンビニが見つかりませんでした。"
        )

    else:

        st.subheader(
            f"🏪 コンビニ {len(results)}件"
        )


        # --------------------------------
        # 一覧
        # --------------------------------

        for store in results:

            st.write(
                f"**{store['名前']}**　"
                f"約 {store['距離(km)']} km"
            )


        # --------------------------------
        # コンビニの地図
        # --------------------------------

        store_map = pd.DataFrame(
            {
                "lat": [lat] + [
                    x["緯度"] for x in results
                ],

                "lon": [lon] + [
                    x["経度"] for x in results
                ]
            }
        )

        st.subheader("🗺️ コンビニの場所")

        st.map(store_map)


# ========================================
# 出典・帰属表示
# ========================================

st.divider()

st.caption(
    "地図・地理情報：© OpenStreetMap contributors"
)

st.caption(
    "場所検索：Nominatim / OpenStreetMap"
)

st.caption(
    "コンビニ情報：OpenStreetMap / Overpass API"
)