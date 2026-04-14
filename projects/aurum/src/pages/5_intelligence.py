"""Page 5: Intelligence Feed — News + Polymarket prediction markets."""
import streamlit as st
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

st.set_page_config(page_title="AURUM • Intelligence", layout="wide", page_icon="📡")
st.title("📡 Intelligence Feed")
st.caption("Metals-relevant news and prediction market signals")

from src.data.polymarket import fetch_active_markets
from src.data.news_feed import fetch_all_news

# ─────────────────────────────────────────────
# POLYMARKET
# ─────────────────────────────────────────────
st.subheader("🔮 Polymarket — Metals-Relevant Bets")
st.caption("Prediction markets on geopolitics, Fed policy, trade wars, commodities")

with st.spinner("Loading prediction markets..."):
    poly = fetch_active_markets(limit=100)

if poly is not None and not poly.empty:
    # ── Filter controls ──
    ctrl1, ctrl2, ctrl3 = st.columns([2, 2, 1])
    with ctrl1:
        categories = ["All"] + sorted(poly["category"].unique().tolist())
        selected_cat = st.selectbox("Category", categories, key="poly_cat")
    with ctrl2:
        sort_by_poly = st.selectbox("Sort by", ["Volume (High→Low)", "Probability (High→Low)", "Probability (Low→High)", "End Date"], key="poly_sort")
    with ctrl3:
        min_vol = st.number_input("Min Volume ($)", value=0, step=10000, format="%d", key="poly_minvol")

    filtered_poly = poly.copy()
    if selected_cat != "All":
        filtered_poly = filtered_poly[filtered_poly["category"] == selected_cat]
    if min_vol > 0:
        filtered_poly = filtered_poly[filtered_poly["volume"] >= min_vol]

    sort_map = {
        "Volume (High→Low)": ("volume", False),
        "Probability (High→Low)": ("probability", False),
        "Probability (Low→High)": ("probability", True),
        "End Date": ("end_date", True),
    }
    sort_col, sort_asc = sort_map[sort_by_poly]
    filtered_poly = filtered_poly.sort_values(sort_col, ascending=sort_asc)

    # ── Load-more state ──
    if "poly_page" not in st.session_state:
        st.session_state.poly_page = 1
    page_size = 15
    display_count = st.session_state.poly_page * page_size
    page_df = filtered_poly.head(display_count)

    st.caption(f"Showing {len(page_df)} of {len(filtered_poly)} markets")

    for _, row in page_df.iterrows():
        with st.container():
            c1, c2, c3, c4 = st.columns([5, 1, 1, 1])
            with c1:
                prob = row["probability"]
                color = "#10b981" if prob > 60 else "#ef4444" if prob < 40 else "#F5A623"
                st.markdown(f"**{row['question']}**")
                end_str = f" · Expires: {row['end_date']}" if row['end_date'] else ""
                st.caption(f"{row['category']} · Keywords: {row['keywords']}{end_str}")
            with c2:
                st.metric("YES Prob", f"{prob:.0f}%")
            with c3:
                vol = row["volume"]
                if vol >= 1_000_000:
                    st.metric("Volume", f"${vol/1e6:.1f}M")
                elif vol >= 1_000:
                    st.metric("Volume", f"${vol/1e3:.0f}K")
                else:
                    st.metric("Volume", f"${vol:,.0f}")
            with c4:
                if row.get("url"):
                    st.markdown(f"[Open ↗]({row['url']})")
            st.divider()

    # ── Load more button ──
    if display_count < len(filtered_poly):
        if st.button(f"Load more ({len(filtered_poly) - display_count} remaining)", key="poly_loadmore"):
            st.session_state.poly_page += 1
            st.rerun()
    else:
        if st.session_state.poly_page > 1:
            st.caption("All markets loaded.")
else:
    st.warning("Polymarket data unavailable. Check network connectivity.")
    if st.button("Retry", key="poly_retry"):
        st.cache_data.clear()
        st.rerun()

# ─────────────────────────────────────────────
# NEWS FEED
# ─────────────────────────────────────────────
st.divider()
st.subheader("📰 Metals News Feed")
st.caption("Aggregated from RSS feeds, scored by metals relevance")

with st.spinner("Loading news..."):
    news = fetch_all_news()

if news is not None and not news.empty:
    # ── Controls ──
    nc1, nc2, nc3 = st.columns([3, 2, 2])
    with nc1:
        search_term = st.text_input("🔍 Search keywords", placeholder="e.g. Fed rate cut, China, tariff", key="news_search")
    with nc2:
        sort_by_news = st.selectbox("Sort by", ["Relevance Score", "Date (Newest)", "Date (Oldest)"], key="news_sort")
    with nc3:
        min_score = st.slider("Min relevance score", 1, 10, 2, key="news_minscore")

    filtered_news = news[news["score"] >= min_score].copy()

    if search_term.strip():
        term_lower = search_term.lower()
        filtered_news = filtered_news[
            filtered_news["title"].str.lower().str.contains(term_lower, na=False) |
            filtered_news["summary"].str.lower().str.contains(term_lower, na=False)
        ]

    if sort_by_news == "Relevance Score":
        filtered_news = filtered_news.sort_values("score", ascending=False)
    elif sort_by_news == "Date (Newest)":
        filtered_news = filtered_news.sort_values("published", ascending=False)
    elif sort_by_news == "Date (Oldest)":
        filtered_news = filtered_news.sort_values("published", ascending=True)

    # ── Load-more state ──
    if "news_page" not in st.session_state:
        st.session_state.news_page = 1
    news_page_size = 20
    news_display_count = st.session_state.news_page * news_page_size
    page_news = filtered_news.head(news_display_count)

    st.caption(f"Showing {len(page_news)} of {len(filtered_news)} articles")

    for _, article in page_news.iterrows():
        score = article["score"]
        score_bar = "▓" * min(score, 10)
        score_color = "#10b981" if score >= 7 else "#F5A623" if score >= 4 else "#888"
        with st.container():
            col_a, col_b = st.columns([8, 1])
            with col_a:
                st.markdown(f"**{article['title']}**")
                st.caption(f"📌 {article['source']} · Score: {score} `{score_bar}` · {article.get('published', '')[:16]}")
                if article.get("summary"):
                    st.markdown(f"<small style='color:#aaa'>{article['summary'][:250]}...</small>", unsafe_allow_html=True)
            with col_b:
                if article.get("url"):
                    st.markdown(f"[Read →]({article['url']})")
            st.divider()

    # ── Load more button ──
    if news_display_count < len(filtered_news):
        remaining = len(filtered_news) - news_display_count
        if st.button(f"Load {min(news_page_size, remaining)} more articles", key="news_loadmore"):
            st.session_state.news_page += 1
            st.rerun()

    if not filtered_news.empty and search_term:
        st.caption(f"Found {len(filtered_news)} articles matching '{search_term}'")
    elif filtered_news.empty:
        st.info("No articles match your filters. Try lowering the score threshold or clearing the search.")
else:
    st.info("No news available. Install `feedparser` for RSS support: `pip install feedparser`")
