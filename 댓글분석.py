import streamlit as st
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt

from googleapiclient.discovery import build
from collections import Counter
from wordcloud import WordCloud

import re
import os

# -----------------------
# 설정
# -----------------------

st.set_page_config(
    page_title="유튜브 댓글 분석기",
    page_icon="📺",
    layout="wide"
)

st.title("📺 유튜브 댓글 분석기")

API_KEY = st.secrets["YOUTUBE_API_KEY"]

youtube = build(
    "youtube",
    "v3",
    developerKey=API_KEY
)

# -----------------------
# 폰트
# -----------------------

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

FONT_PATH = os.path.join(
    BASE_DIR,
    "NanumGothic.ttf"
)

# -----------------------
# 영상 ID 추출
# -----------------------

def get_video_id(url):

    patterns = [
        r"v=([^&]+)",
        r"youtu\.be/([^?]+)"
    ]

    for p in patterns:

        m = re.search(p, url)

        if m:
            return m.group(1)

    return None

# -----------------------
# 영상 정보
# -----------------------

def get_video_info(video_id):

    response = youtube.videos().list(
        part="snippet,statistics",
        id=video_id
    ).execute()

    if not response["items"]:
        return None

    item = response["items"][0]

    return {
        "title": item["snippet"]["title"],
        "channel": item["snippet"]["channelTitle"],
        "views": int(
            item["statistics"].get(
                "viewCount", 0
            )
        ),
        "likes": int(
            item["statistics"].get(
                "likeCount", 0
            )
        )
    }

# -----------------------
# 댓글 수집
# -----------------------

@st.cache_data
def get_comments(video_id, limit):

    comments = []

    next_page = None

    while len(comments) < limit:

        response = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=min(
                100,
                limit - len(comments)
            ),
            pageToken=next_page,
            textFormat="plainText"
        ).execute()

        for item in response["items"]:

            comment = item["snippet"][
                "topLevelComment"
            ]["snippet"]

            comments.append(
                {
                    "댓글": comment["textDisplay"],
                    "좋아요": comment["likeCount"],
                    "작성일": comment["publishedAt"]
                }
            )

        next_page = response.get(
            "nextPageToken"
        )

        if not next_page:
            break

    return pd.DataFrame(comments)

# -----------------------
# 입력
# -----------------------

url = st.text_input(
    "유튜브 URL"
)

comment_limit = st.slider(
    "댓글 수",
    10,
    10000,
    500,
    10
)

# -----------------------
# 분석
# -----------------------

if st.button("분석 시작"):

    video_id = get_video_id(url)

    if not video_id:

        st.error(
            "유효한 URL이 아닙니다."
        )
        st.stop()

    info = get_video_info(video_id)

    if not info:

        st.error(
            "영상 정보를 가져올 수 없습니다."
        )
        st.stop()

    st.subheader(info["title"])

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "조회수",
        f"{info['views']:,}"
    )

    c2.metric(
        "좋아요",
        f"{info['likes']:,}"
    )

    c3.metric(
        "채널",
        info["channel"]
    )

    with st.spinner(
        "댓글 수집 중..."
    ):

        df = get_comments(
            video_id,
            comment_limit
        )

    if len(df) == 0:

        st.error(
            "댓글이 없습니다."
        )
        st.stop()

    st.success(
        f"{len(df):,}개 댓글 수집 완료"
    )

    # -------------------
    # 좋아요 TOP
    # -------------------

    st.subheader(
        "👍 좋아요 TOP 댓글"
    )

    top_df = (
        df.sort_values(
            "좋아요",
            ascending=False
        )
        .head(10)
    )

    fig = px.bar(
        top_df,
        x="좋아요",
        y="댓글",
        orientation="h",
        height=600
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # -------------------
    # 날짜별 댓글
    # -------------------

    st.subheader(
        "📈 댓글 추이"
    )

    df["작성일"] = pd.to_datetime(
        df["작성일"]
    )

    trend = (
        df.groupby(
            df["작성일"].dt.date
        )
        .size()
        .reset_index(
            name="댓글 수"
        )
    )

    fig2 = px.line(
        trend,
        x="작성일",
        y="댓글 수",
        markers=True
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

    # -------------------
    # 단어 분석
    # -------------------

    st.subheader(
        "🔥 인기 단어"
    )

    text = " ".join(
        df["댓글"].astype(str)
    )

    words = re.findall(
        r"[가-힣A-Za-z]{2,}",
        text
    )

    stopwords = {
        "진짜",
        "정말",
        "너무",
        "영상",
        "댓글",
        "있는",
        "하는",
        "그리고",
        "입니다"
    }

    words = [
        w for w in words
        if w not in stopwords
    ]

    counter = Counter(words)

    word_df = pd.DataFrame(
        counter.most_common(20),
        columns=[
            "단어",
            "빈도"
        ]
    )

    fig3 = px.bar(
        word_df,
        x="단어",
        y="빈도"
    )

    st.plotly_chart(
        fig3,
        use_container_width=True
    )

    # -------------------
    # 워드클라우드
    # -------------------

    st.subheader(
        "☁️ 워드클라우드"
    )

    try:

        wc = WordCloud(
            font_path=FONT_PATH,
            width=1400,
            height=700,
            background_color="white"
        ).generate_from_frequencies(
            counter
        )

        fig4, ax = plt.subplots(
            figsize=(14, 7)
        )

        ax.imshow(wc)
        ax.axis("off")

        st.pyplot(fig4)

    except Exception as e:

        st.error(
            f"워드클라우드 오류: {e}"
        )

    # -------------------
    # 데이터
    # -------------------

    st.subheader(
        "📄 댓글 데이터"
    )

    st.dataframe(
        df,
        use_container_width=True
    )

    csv = df.to_csv(
        index=False
    ).encode(
        "utf-8-sig"
    )

    st.download_button(
        "CSV 다운로드",
        csv,
        "youtube_comments.csv",
        "text/csv"
    )
