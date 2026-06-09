import streamlit as st
import pandas as pd
import re
from collections import Counter

import plotly.express as px
import matplotlib.pyplot as plt

from youtube_comment_downloader import YoutubeCommentDownloader
from wordcloud import WordCloud

# -------------------------
# 페이지 설정
# -------------------------

st.set_page_config(
    page_title="YouTube 댓글 분석기",
    page_icon="📺",
    layout="wide"
)

st.title("📺 YouTube 댓글 분석기")
st.markdown("유튜브 영상 URL만 입력하면 댓글을 수집하고 분석합니다.")

# -------------------------
# URL 입력
# -------------------------

youtube_url = st.text_input(
    "🔗 유튜브 영상 URL 입력",
    placeholder="https://www.youtube.com/watch?v=..."
)

comment_limit = st.slider(
    "💬 수집할 댓글 수",
    min_value=10,
    max_value=10000,
    value=1000,
    step=10
)

# -------------------------
# 댓글 수집 함수
# -------------------------

@st.cache_data(show_spinner=False)
def collect_comments(url, limit):

    downloader = YoutubeCommentDownloader()

    comments = []

    try:
        generator = downloader.get_comments_from_url(
            url,
            sort_by=0
        )

        for idx, comment in enumerate(generator):

            comments.append({
                "댓글": comment.get("text", ""),
                "좋아요": comment.get("votes", 0),
                "시간": comment.get("time", "")
            })

            if idx + 1 >= limit:
                break

        return pd.DataFrame(comments)

    except Exception as e:
        st.error(f"댓글 수집 실패: {e}")
        return pd.DataFrame()

# -------------------------
# 텍스트 전처리
# -------------------------

def clean_text(text):

    text = re.sub(r"[^가-힣a-zA-Z ]", " ", str(text))
    return text.lower()

# -------------------------
# 분석 시작
# -------------------------

if st.button("🚀 분석 시작"):

    if youtube_url == "":
        st.warning("유튜브 URL을 입력하세요.")
        st.stop()

    with st.spinner("댓글 수집 중..."):

        df = collect_comments(
            youtube_url,
            comment_limit
        )

    if len(df) == 0:
        st.error("수집된 댓글이 없습니다.")
        st.stop()

    st.success(f"총 {len(df):,}개의 댓글 수집 완료")

    # -------------------------
    # 데이터 보기
    # -------------------------

    st.subheader("📄 댓글 데이터")

    st.dataframe(
        df,
        use_container_width=True
    )

    # -------------------------
    # 기본 통계
    # -------------------------

    st.subheader("📊 기본 통계")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "댓글 수",
        f"{len(df):,}"
    )

    col2.metric(
        "평균 좋아요",
        round(df["좋아요"].mean(), 2)
    )

    col3.metric(
        "최대 좋아요",
        df["좋아요"].max()
    )

    # -------------------------
    # 좋아요 TOP 20
    # -------------------------

    st.subheader("👍 좋아요 많은 댓글 TOP 20")

    top_like = df.sort_values(
        "좋아요",
        ascending=False
    ).head(20)

    fig_like = px.bar(
        top_like,
        x="좋아요",
        y="댓글",
        orientation="h",
        height=700,
        title="좋아요 TOP 20 댓글"
    )

    st.plotly_chart(
        fig_like,
        use_container_width=True
    )

    # -------------------------
    # 시간 분석
    # -------------------------

    st.subheader("⏰ 댓글 시간대 분석")

    def extract_hour(text):

        text = str(text)

        match = re.search(r"(\d+)\s*hour", text)
        if match:
            return int(match.group(1))

        match = re.search(r"(\d+)\s*minute", text)
        if match:
            return 0

        match = re.search(r"(\d+)\s*day", text)
        if match:
            return 24

        return None

    df["hour"] = df["시간"].apply(extract_hour)

    time_df = (
        df["hour"]
        .value_counts()
        .reset_index()
    )

    time_df.columns = [
        "시간대",
        "댓글 수"
    ]

    if len(time_df) > 0:

        fig_time = px.line(
            time_df.sort_values("시간대"),
            x="시간대",
            y="댓글 수",
            markers=True,
            title="시간대별 댓글 추이"
        )

        st.plotly_chart(
            fig_time,
            use_container_width=True
        )

    # -------------------------
    # 단어 분석
    # -------------------------

    st.subheader("🔥 자주 등장하는 단어")

    text_data = " ".join(
        df["댓글"].astype(str)
    )

    text_data = clean_text(text_data)

    words = text_data.split()

    stopwords = {
        "the","and","is","to","of",
        "이","그","저","것","수","좀",
        "진짜","너무","정말","ㅋㅋ","ㅎㅎ",
        "영상","댓글","있는","하는","입니다"
    }

    words = [
        w for w in words
        if len(w) > 1
        and w not in stopwords
    ]

    counter = Counter(words)

    word_df = pd.DataFrame(
        counter.most_common(30),
        columns=["단어", "빈도"]
    )

    fig_word = px.bar(
        word_df,
        x="단어",
        y="빈도",
        title="상위 30개 단어"
    )

    st.plotly_chart(
        fig_word,
        use_container_width=True
    )

    # -------------------------
    # 워드클라우드
    # -------------------------

    st.subheader("☁️ 워드클라우드")

    if len(counter) > 0:

        try:
            wc = WordCloud(
                width=1200,
                height=600,
                background_color="white",
                font_path="NanumGothic.ttf"
            ).generate_from_frequencies(counter)

        except:
            wc = WordCloud(
                width=1200,
                height=600,
                background_color="white"
            ).generate_from_frequencies(counter)

        fig, ax = plt.subplots(figsize=(12,6))

        ax.imshow(wc)
        ax.axis("off")

        st.pyplot(fig)

    # -------------------------
    # CSV 다운로드
    # -------------------------

    st.subheader("⬇️ 데이터 다운로드")

    csv = df.to_csv(
        index=False
    ).encode("utf-8-sig")

    st.download_button(
        label="CSV 다운로드",
        data=csv,
        file_name="youtube_comments.csv",
        mime="text/csv"
    )
