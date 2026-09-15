import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ------------------------------------------------------------
# 기본 설정
# ------------------------------------------------------------
st.set_page_config(
    page_title="서울 100년 기온 변화",
    page_icon="🌡️",
    layout="wide",
)

DATA_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/seoul.csv"

# 한 해 데이터가 이 값보다 적게 있으면 '완전하지 않은 연도'로 보고 그래프에서 제외합니다.
# (예: 데이터의 첫 해와 마지막 해는 1년치가 다 채워지지 않은 경우가 많습니다)
MIN_DAYS_PER_YEAR = 300


# ------------------------------------------------------------
# 데이터 불러오기 & 가공 (캐시로 반복 다운로드 방지)
# ------------------------------------------------------------
@st.cache_data(show_spinner="서울 기온 데이터를 불러오는 중이에요...")
def load_data():
    df = pd.read_csv(DATA_URL, encoding="utf-8-sig")
    df["날짜"] = pd.to_datetime(df["날짜"])
    df["연도"] = df["날짜"].dt.year
    return df


@st.cache_data(show_spinner=False)
def yearly_average(df):
    # 연도별 평균기온의 평균 + 하루라도 기록이 있었는지 개수 세기
    grouped = (
        df.dropna(subset=["평균기온"])
        .groupby("연도")["평균기온"]
        .agg(연평균기온="mean", 기록일수="count")
        .reset_index()
    )
    # 기록이 충분히 쌓인 '완전한 연도'만 남기기
    complete = grouped[grouped["기록일수"] >= MIN_DAYS_PER_YEAR].copy()
    complete = complete.sort_values("연도").reset_index(drop=True)

    # 10년 이동평균(추세를 부드럽게 보기 위한 선)
    complete["10년이동평균"] = complete["연평균기온"].rolling(window=10, center=True, min_periods=3).mean()

    return complete


def linear_trend(complete):
    # 1차 선형회귀로 전체 추세(연도당 상승/하강 °C) 계산
    x = complete["연도"].values.astype(float)
    y = complete["연평균기온"].values.astype(float)
    slope, intercept = np.polyfit(x, y, 1)
    trend_line = slope * x + intercept
    return slope, trend_line


# ------------------------------------------------------------
# 화면 구성
# ------------------------------------------------------------
st.title("🌡️ 서울, 100년의 기온 변화")
st.markdown(
    "서울의 **일별 기온 관측 기록**을 바탕으로, 오랜 기간 동안 "
    "**연평균 기온이 어떻게 변해왔는지** 한눈에 볼 수 있는 그래프예요."
)

df = load_data()
yearly = yearly_average(df)

if yearly.empty:
    st.error("표시할 수 있는 연도별 데이터가 없어요. 데이터 파일을 확인해주세요.")
    st.stop()

slope, trend_line = linear_trend(yearly)
first_year = int(yearly["연도"].iloc[0])
last_year = int(yearly["연도"].iloc[-1])
n_years = len(yearly)
total_rise = slope * (last_year - first_year)

# ---- 핵심 숫자 요약 카드 ----
col1, col2, col3, col4 = st.columns(4)
col1.metric("데이터 기간", f"{first_year} ~ {last_year}년")
col2.metric("집계된 연도 수", f"{n_years}개")
col3.metric("10년당 기온 변화", f"{slope * 10:+.2f} °C")
col4.metric(f"{first_year}~{last_year}년 총 변화", f"{total_rise:+.2f} °C")

st.caption(
    f"※ 하루 기록이 {MIN_DAYS_PER_YEAR}일 미만인 해(대개 데이터의 맨 처음·맨 끝 연도)는 "
    "평균이 왜곡될 수 있어 그래프에서 제외했어요."
)

st.divider()

# ------------------------------------------------------------
# 그래프
# ------------------------------------------------------------
st.subheader("📈 연평균 기온 추이")

show_moving_avg = st.checkbox("10년 이동평균선 함께 보기", value=True)
show_trend = st.checkbox("전체 추세선(직선) 함께 보기", value=True)

fig = go.Figure()

# 연도별 실제 평균기온 (막대보다 선+점이 흐름을 보기 편함)
fig.add_trace(
    go.Scatter(
        x=yearly["연도"],
        y=yearly["연평균기온"],
        mode="lines+markers",
        name="연평균 기온",
        line=dict(color="#4FC3F7", width=1.5),
        marker=dict(size=4),
        hovertemplate="%{x}년<br>연평균 기온: %{y:.2f}°C<extra></extra>",
    )
)

if show_moving_avg:
    fig.add_trace(
        go.Scatter(
            x=yearly["연도"],
            y=yearly["10년이동평균"],
            mode="lines",
            name="10년 이동평균",
            line=dict(color="#1565C0", width=4),
            hovertemplate="%{x}년<br>10년 이동평균: %{y:.2f}°C<extra></extra>",
        )
    )

if show_trend:
    fig.add_trace(
        go.Scatter(
            x=yearly["연도"],
            y=trend_line,
            mode="lines",
            name="전체 추세선",
            line=dict(color="#E53935", width=2, dash="dash"),
            hovertemplate="%{x}년<br>추세선: %{y:.2f}°C<extra></extra>",
        )
    )

fig.update_layout(
    xaxis_title="연도",
    yaxis_title="연평균 기온 (°C)",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    height=520,
    margin=dict(l=10, r=10, t=40, b=10),
    font=dict(size=15),
)

st.plotly_chart(fig, use_container_width=True)

if slope > 0:
    st.info(
        f"📌 {first_year}년부터 {last_year}년까지, 서울의 연평균 기온은 "
        f"10년마다 평균 **{slope * 10:.2f}°C씩 올라가는** 추세를 보여요."
    )
else:
    st.info(
        f"📌 {first_year}년부터 {last_year}년까지, 서울의 연평균 기온은 "
        f"10년마다 평균 **{abs(slope * 10):.2f}°C씩 내려가는** 추세를 보여요."
    )

# ------------------------------------------------------------
# 원본 데이터 살펴보기
# ------------------------------------------------------------
with st.expander("🗂️ 연도별 평균 데이터 표로 보기"):
    st.dataframe(
        yearly[["연도", "연평균기온", "기록일수"]].rename(
            columns={"연평균기온": "연평균 기온(°C)", "기록일수": "관측 일수"}
        ),
        use_container_width=True,
        hide_index=True,
    )

with st.expander("📄 원본 일별 데이터 미리보기 (최근 10개)"):
    st.dataframe(df.tail(10), use_container_width=True, hide_index=True)

st.caption("데이터 출처: greatsong/modudata (GitHub) · 서울 기상 관측 자료")
