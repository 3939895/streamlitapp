
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

# 公開するときは自分の連絡先に変更してください
USER_AGENT = (
    "ConvenienceStoreSearchApp/1.0 "
    "(contact: your-email@example.com)"
)

# アプリのURL
# Streamlit Community Cloudに公開したら、
# 自分のアプリURLに変更してください。
APP_URL = "https://example.streamlit.app/"


# ========================================
# 2地点間の距離を計算
# ========================================

def calculate_distance(lat1, lon1, lat2, lon2):

    R = 6371

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
# Nominatim
# ========================================

@st.cache_data(ttl=3600)
def get_location_nominatim(place):

    url = "https://nominatim.openstreetmap.org/search"

    params = {
        "q": place,
        "format": "jsonv2",
        "limit": 1,
        "countrycodes": "jp"
    }

    headers = {
        "User-Agent": USER_AGENT,
        "Referer": APP_URL,
        "Accept": "application/json"
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
# Photon
# ========================================

@st.cache_data(ttl=3600)
def get_location_photon(place):

    url = "https://photon.komoot.io/api/"

    params = {
        "q": place,
        "limit": 1
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

    features = data.get("features", [])

    if not features:
        return None

    coordinates = features[0]["geometry"]["coordinates"]

    lon = float(coordinates[0])
    lat = float(coordinates[1])

    return lat, lon


# ========================================
# 場所検索
# ========================================

def get_location(place):

    # -------------------------------
    # Nominatim
    # -------------------------------

    try:

        location = get_location_nominatim(place)

        if location is not None:
            return location, "Nominatim"

    except requests.exceptions.RequestException:
        pass


    # -------------------------------
    # Photon
    # -------------------------------

    try:

        location = get_location_photon(place)

        if location is not None:
            return location, "Photon"

    except requests.exceptions.RequestException:
        pass


    return None, None


# ========================================
# Overpass API
# ========================================

def get_convenience_stores(lat, lon, radius):

    query = f"""
    [out:json][timeout:25];

    (
      node["shop"="convenience"](around:{radius},{lat},{lon});
      way["shop"="convenience"](around:{radius},{lat},{lon});
    );

    out center;
    """


    # ====================================
    # Overpassサーバー候補
    # ====================================

    servers = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.openstreetmap.jp/api/interpreter"
    ]


    headers = {
        "User-Agent": USER_AGENT,
        "Referer": APP_URL,
        "Accept": "application/json"
    }


    last_error = None


    # ====================================
    # サーバーを順番に試す
    # ====================================

    for server in servers:

        try:

            response = requests.post(
                server,
                data={"data": query},
                headers=headers,
                timeout=40
            )


            # --------------------------------
            # 406の場合
            # --------------------------------

            if response.status_code == 406:

                last_error = (
                    f"406 Not Acceptable: {server}"
                )

                # 公式案内に従って少し待つ
                time.sleep(30)

                continue


            response.raise_for_status()

            data = response.json()

            return data.get("elements", [])


        except requests.exceptions.RequestException as e:

            last_error = str(e)

            continue


    # ====================================
    # 全サーバー失敗
    # ====================================

    raise requests.exceptions.RequestException(
        last_error
    )


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

if st.button("検索"):

    # ====================================
    # 入力チェック
    # ====================================

    if not place.strip():

        st.warning(
            "場所を入力してください。"
        )

        st.stop()


    # ====================================
    # 場所検索
    # ====================================

    with st.spinner(
        "場所を検索しています..."
    ):

        location, service = get_location(place)


    if location is None:

        st.error(
            "場所が見つかりませんでした。"
        )

        st.stop()


    lat, lon = location


    st.success(
        "場所が見つかりました！"
    )

    st.write(
        f"検索サービス：{service}"
    )

    st.write(
        f"緯度：{lat:.5f}"
    )

    st.write(
        f"経度：{lon:.5f}"
    )


    # ====================================
    # 検索地点の地図
    # ====================================

    st.subheader(
        "📍 検索地点"
    )

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

    with st.spinner(
        "近くのコンビニを検索しています..."
    ):

        try:

            stores = get_convenience_stores(
                lat,
                lon,
                int(radius * 1000)
            )

        except requests.exceptions.RequestException as e:

            st.error(
                "コンビニの検索に失敗しました。"
            )

            st.code(
                str(e)
            )

            st.stop()


    # ====================================
    # 結果を整理
    # ====================================

    results = []


    for store in stores:

        # -------------------------------
        # 座標
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

        tags = store.get(
            "tags",
            {}
        )

        name = tags.get(
            "name",
            "名前なし"
        )


        # -------------------------------
        # 距離
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
                "距離(km)": round(
                    distance,
                    2
                ),
                "緯度": store_lat,
                "経度": store_lon
            }
        )


    # ====================================
    # 距離順
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

        st.info(
            "OpenStreetMapに登録されているコンビニを検索しています。"
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
        # 地図
        # --------------------------------

        store_map = pd.DataFrame(
            {
                "lat": [lat] + [
                    x["緯度"]
                    for x in results
                ],

                "lon": [lon] + [
                    x["経度"]
                    for x in results
                ]
            }
        )

        st.subheader(
            "🗺️ コンビニの場所"
        )

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
    "場所検索（予備）：Photon"
)

st.caption(
    "コンビニ情報：OpenStreetMap / Overpass API"
)

