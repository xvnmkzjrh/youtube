import streamlit as st
import pandas as pd
import plotly.express as px
from collections import Counter
from youtube_comment_downloader import YoutubeCommentDownloader
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import re
import os

# -------------------
# 페이지 설정
# -------------------

st.set_page_config(
    page_title="유튜브 댓글 분석기",
    page_icon="📺",
    layout="wide"
)

st.title("📺 유튜브 댓글 분석기")

# -------------------
# 폰트 경로
# -------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(BASE_DIR, "NanumGothic.ttf")

# -------------------
# 입력
# -------------------

youtube_url = st.text_input(
    "유튜브 URL 입력",
    placeholder="https://www.youtube.com/watch?v=xxxx"
)

comment_limit = st.slider(
    "수집할 댓글 수",
    min_value=10,
    max_value=10000,
    value=500,
    step=10
)

# -------------------
# 댓글 수집
# -------------------

@st.cache_data
def collect_comments(url, limit):

    downloader = YoutubeCommentDownloader()
    comments = []

    try:

        generator = downloader.get_comments_from_url(
            url,
            sort_by=0
        )

        for idx, comment in enumerate(generator):

            votes = comment.get("votes", 0)

            try:

                votes = str(votes).replace(",", "")

                if "K" in votes:
                    votes = int(float(votes.replace("K", "")) * 1000)

                elif "M" in votes:
                    votes = int(float(votes.replace("M", "")) * 1000000)

                else:
                    votes = int(float(votes))

            except:
                votes = 0

            comments.append(
                {
                    "댓글": comment.get("text", ""),
                    "좋아요": votes
                }
            )

            if idx + 1 >= limit:
                break

        return pd.DataFrame(comments)

    except Exception as e:

        st.error(f"댓글 수집 오류: {e}")
        return pd.DataFrame()

# -------------------
# 분석 시작
# -------------------

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

        st.error("댓글을 수집하지 못했습니다.")
        st.stop()

    # 숫자형 변환

    df["좋아요"] = pd.to_numeric(
        df["좋아요"],
        errors="coerce"
    ).fillna(0).astype(int)

    st.success(
        f"{len(df):,}개의 댓글 수집 완료"
    )

    # -------------------
    # 기본 통계
    # -------------------

    st.subheader("📊 기본 통계")

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "댓글 수",
        f"{len(df):,}"
    )

    c2.metric(
        "평균 좋아요",
        round(df["좋아요"].mean(), 1)
    )

    c3.metric(
        "최대 좋아요",
        int(df["좋아요"].max())
    )

    # -------------------
    # 좋아요 TOP10
    # -------------------

    st.subheader("👍 좋아요 TOP10 댓글")

    top_df = (
        df.sort_values(
            by="좋아요",
            ascending=False
        )
        .head(10)
    )

    fig1 = px.bar(
        top_df,
        x="좋아요",
        y="댓글",
        orientation="h",
        height=600
    )

    st.plotly_chart(
        fig1,
        use_container_width=True
    )

    # -------------------
    # 단어 분석
    # -------------------

    st.subheader("🔥 자주 등장한 단어")

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
        "입니다",
        "그리고",
        "그냥",
        "ㅋㅋ",
        "ㅎㅎ"
    }

    words = [
        word
        for word in words
        if word not in stopwords
    ]

    counter = Counter(words)

    if len(counter) > 0:

        word_df = pd.DataFrame(
            counter.most_common(20),
            columns=["단어", "빈도"]
        )

        fig2 = px.bar(
            word_df,
            x="단어",
            y="빈도",
            title="상위 20개 단어"
        )

        st.plotly_chart(
            fig2,
            use_container_width=True
        )

    # -------------------
    # 워드클라우드
    # -------------------

    st.subheader("☁️ 워드클라우드")

    if len(counter) > 0:

        try:

            if not os.path.exists(FONT_PATH):

                st.error(
                    f"폰트를 찾을 수 없습니다.\n{FONT_PATH}"
                )

            else:

                wc = WordCloud(
                    font_path=FONT_PATH,
                    width=1400,
                    height=700,
                    background_color="white",
                    max_words=100
                ).generate_from_frequencies(counter)

                fig3, ax = plt.subplots(
                    figsize=(14, 7)
                )

                ax.imshow(
                    wc,
                    interpolation="bilinear"
                )

                ax.axis("off")

                st.pyplot(fig3)

        except Exception as e:

            st.error(
                f"워드클라우드 생성 실패: {e}"
            )

    # -------------------
    # 댓글 데이터
    # -------------------

    st.subheader("📄 댓글 데이터")

    st.dataframe(
        df.head(1000),
        use_container_width=True
    )

    st.caption(
        f"전체 {len(df):,}개 댓글 중 1000개만 표시"
    )

    # -------------------
    # CSV 다운로드
    # -------------------

    csv = df.to_csv(
        index=False
    ).encode("utf-8-sig")

    st.download_button(
        label="📥 CSV 다운로드",
        data=csv,
        file_name="youtube_comments.csv",
        mime="text/csv"
    )
