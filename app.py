"""Streamlit UI for the Academic Research Agent."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

import streamlit as st

from tools.search import search_papers, Paper
from tools.fetch import fetch_paper
from tools.citations import format_citation
from tools.analyze import analyze_paper
from tools.synthesize import find_research_gaps, get_analysis_status
from tools.connected import find_connected_papers
from tools.bib import import_from_bib
from tools.graph import build_graph, render_html
from tools.agent import ResearchAgent, OllamaClient
from memory.store import PaperStore, PaperSummary
from memory.index import PaperIndex
import streamlit.components.v1 as components


# ── shared state ──────────────────────────────────────────────────────────────

store = PaperStore()
index = PaperIndex(store)


# ── page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Academic Research Agent",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# krutikp.com design language — dark theme, Roboto, #8ab4f8 accent, rounded-xl surfaces
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');

/* ── Global font ── */
html, body, [class*="css"], .stApp, .stMarkdown, p, span, div {
    font-family: 'Roboto', 'Segoe UI', system-ui, sans-serif !important;
}

/* ── Selection ── */
::selection { background-color: #1a73e8; color: #fff; }

/* ── Dividers ── */
hr { border-color: rgba(255,255,255,0.08) !important; margin: 1rem 0 !important; }

/* ── Headings ── */
h1 { font-weight: 300 !important; letter-spacing: -0.01em !important; color: #e8eaed !important; }
h2, h3 { font-weight: 400 !important; letter-spacing: 0.01em !important; color: #e8eaed !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: #292a2d !important;
    border-right: 1px solid rgba(255,255,255,0.08) !important;
}
[data-testid="stSidebar"] .stRadio > label {
    font-size: 0.6rem !important;
    letter-spacing: 0.25em !important;
    text-transform: uppercase !important;
    color: #9aa0a6 !important;
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
    border-radius: 0.5rem !important;
    transition: color 0.2s !important;
}
[data-testid="stSidebar"] .stProgress > div > div > div > div {
    background-color: #8ab4f8 !important;
}
[data-testid="stSidebar"] .stProgress > div > div > div {
    background-color: rgba(255,255,255,0.1) !important;
    border-radius: 999px !important;
}

/* ── Metric cards ── */
[data-testid="metric-container"] {
    background-color: #292a2d !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 0.75rem !important;
    padding: 0.85rem 1.1rem !important;
}
[data-testid="metric-container"] label {
    font-size: 0.6rem !important;
    letter-spacing: 0.2em !important;
    text-transform: uppercase !important;
    color: #9aa0a6 !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-weight: 300 !important;
    font-size: 1.8rem !important;
    color: #e8eaed !important;
}

/* ── Buttons ── */
.stButton > button {
    background-color: transparent !important;
    border: 1px solid rgba(138,180,248,0.35) !important;
    border-radius: 0.75rem !important;
    color: #8ab4f8 !important;
    font-family: 'Roboto', sans-serif !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    padding: 0.45rem 1.1rem !important;
    transition: background 0.2s, border-color 0.2s !important;
}
.stButton > button:hover {
    background-color: rgba(138,180,248,0.1) !important;
    border-color: #8ab4f8 !important;
}
.stButton > button:active {
    background-color: rgba(138,180,248,0.18) !important;
}

/* ── Form submit button ── */
.stFormSubmitButton > button {
    background-color: rgba(138,180,248,0.1) !important;
    border: 1px solid rgba(138,180,248,0.4) !important;
    border-radius: 0.75rem !important;
    color: #8ab4f8 !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    transition: all 0.2s !important;
}
.stFormSubmitButton > button:hover {
    background-color: rgba(138,180,248,0.18) !important;
    border-color: #8ab4f8 !important;
}

/* ── Expanders ── */
.streamlit-expanderHeader {
    background-color: #292a2d !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 0.75rem !important;
    color: #bdc1c6 !important;
    font-size: 0.85rem !important;
    transition: color 0.2s !important;
}
.streamlit-expanderHeader:hover { color: #8ab4f8 !important; }
.streamlit-expanderContent {
    background-color: #292a2d !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-top: none !important;
    border-radius: 0 0 0.75rem 0.75rem !important;
}

/* ── Text inputs ── */
.stTextInput > div > div > input {
    background-color: #292a2d !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 0.75rem !important;
    color: #e8eaed !important;
    font-family: 'Roboto', sans-serif !important;
}
.stTextInput > div > div > input:focus {
    border-color: #8ab4f8 !important;
    box-shadow: 0 0 0 2px rgba(138,180,248,0.2) !important;
}
.stTextInput > div > div > input::placeholder { color: #9aa0a6 !important; }

/* ── Selectbox / Multiselect ── */
.stSelectbox > div > div,
.stMultiSelect > div > div {
    background-color: #292a2d !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 0.75rem !important;
}

/* ── Sliders ── */
.stSlider > div > div > div > div {
    background-color: #8ab4f8 !important;
}

/* ── Progress bars (non-sidebar) ── */
.stProgress > div > div > div > div {
    background-color: #8ab4f8 !important;
    border-radius: 999px !important;
}
.stProgress > div > div > div {
    background-color: rgba(255,255,255,0.1) !important;
    border-radius: 999px !important;
}

/* ── Captions ── */
small, .stCaption {
    color: #9aa0a6 !important;
    font-size: 0.75rem !important;
}

/* ── Alert / info / warning / success boxes ── */
.stAlert {
    background-color: #292a2d !important;
    border-radius: 0.75rem !important;
    border-left: 3px solid rgba(138,180,248,0.5) !important;
}

/* ── File uploader ── */
.stFileUploader {
    background-color: #292a2d !important;
    border: 1px dashed rgba(138,180,248,0.3) !important;
    border-radius: 0.75rem !important;
}

/* ── Source + status badges ── */
.badge {
    display: inline-block;
    padding: 0.1rem 0.5rem;
    border-radius: 0.25rem;
    font-size: 0.6rem;
    font-weight: 700;
    font-family: 'Roboto', sans-serif;
    color: #fff;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-right: 0.25rem;
    vertical-align: middle;
}
.badge-arxiv   { background-color: #b91c1c; }
.badge-scholar { background-color: #2563eb; }
.badge-s2      { background-color: #4338ca; }
.badge-done    { background-color: #16a34a; }
.badge-pending { background-color: rgba(255,255,255,0.12); color: #9aa0a6; }
</style>
""", unsafe_allow_html=True)


# ── global stats (computed once per run) ──────────────────────────────────────

_all_papers = store.list_papers()

def _is_analyzed(pid: str) -> bool:
    s = store.get_summary(pid)
    return bool(s and (s.limitations or s.future_directions))

_analyzed_ids = {p.paper_id for p in _all_papers if _is_analyzed(p.paper_id)}
_arxiv_n   = sum(1 for p in _all_papers if p.source == "arxiv")
_other_n   = len(_all_papers) - _arxiv_n
_pending_n = len(_all_papers) - len(_analyzed_ids)


# ── sidebar navigation ────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 📚 Research Agent")
    st.markdown("---")
    if _all_papers:
        st.markdown(
            f"**{len(_all_papers)}** papers &nbsp;·&nbsp; "
            f"**{len(_analyzed_ids)}** analyzed",
            unsafe_allow_html=True,
        )
        st.progress(len(_analyzed_ids) / len(_all_papers))
    else:
        st.caption("Library is empty")
    st.markdown("---")
    page = st.radio(
        "Navigation",
        [
            "🔍 Search",
            "🗂 Library",
            "📄 Fetch Full Text",
            "📝 Citations",
            "🔬 Analyze",
            "🕸 Graph",
            "🤖 Agent",
        ],
    )


# ── page header ───────────────────────────────────────────────────────────────

st.title("📚 Academic Research Agent")

if _all_papers:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📄 Papers", len(_all_papers))
    c2.metric("✅ Analyzed", len(_analyzed_ids))
    c3.metric("⬜ Pending", _pending_n)
    c4.metric("🟠 arXiv", _arxiv_n)
    c5.metric("🔵 Scholar / S2", _other_n)
else:
    st.info(
        "**Welcome!** Use **🔍 Search** to find papers — they save automatically. "
        "Then **🔬 Analyze** them to extract limitations and future directions, "
        "or visit **🗂 Library** to discover connected papers."
    )

st.markdown("---")

# ── quick BibTeX import (always visible) ──────────────────────────────────────

with st.expander("📎 Import from BibTeX", expanded=False):
    st.caption(
        "Upload a `.bib` file from Zotero, Mendeley, or any reference manager. "
        "arXiv entries import directly; others are matched by title search on arXiv."
    )
    bib_home_file = st.file_uploader("Choose .bib file", type=["bib"], key="bib_upload_home")

    if bib_home_file is not None:
        col_btn, col_name = st.columns([1, 3])
        with col_btn:
            run_bib_home = st.button("Import", key="bib_home_import_btn")
        with col_name:
            st.caption(f"**{bib_home_file.name}**")

        if run_bib_home:
            bib_h_prog = st.progress(0)
            bib_h_stat = st.empty()

            def _bib_home_progress(current: int, total: int, title: str) -> None:
                bib_h_prog.progress(current / total if total else 1.0)
                bib_h_stat.caption(f"[{current}/{total}] {title[:60]}")

            content = bib_home_file.read().decode("utf-8", errors="replace")
            result  = import_from_bib(content, store, index, progress_cb=_bib_home_progress)
            bib_h_prog.empty()
            bib_h_stat.empty()
            st.session_state["bib_home_result"] = result
            st.experimental_rerun()

    bib_home_res = st.session_state.get("bib_home_result")
    if bib_home_res is not None:
        h1, h2, h3 = st.columns(3)
        h1.metric("Imported", len(bib_home_res.imported))
        h2.metric("Already saved", len(bib_home_res.skipped))
        h3.metric("Not found", len(bib_home_res.not_found))
        if bib_home_res.imported:
            st.success(f"Added **{len(bib_home_res.imported)}** papers to your library.")
        elif bib_home_res.total == 0:
            st.warning("No valid BibTeX entries found in the file.")
        else:
            st.info("No new papers — all entries were already saved or not found on arXiv.")
        if bib_home_res.not_found:
            with st.expander(f"{len(bib_home_res.not_found)} entries not resolved"):
                for t in bib_home_res.not_found:
                    st.markdown(f"- {t}")
        if st.button("Clear", key="bib_home_clear_btn"):
            st.session_state["bib_home_result"] = None
            st.experimental_rerun()

st.markdown("---")


# ── helpers ───────────────────────────────────────────────────────────────────

def _badge(source: str) -> str:
    label = {"arxiv": "arXiv", "google_scholar": "Scholar", "semantic_scholar": "S2"}.get(source, source)
    cls   = {"arxiv": "badge-arxiv", "google_scholar": "badge-scholar", "semantic_scholar": "badge-s2"}.get(source, "badge-pending")
    return f'<span class="badge {cls}">{label}</span>'


def _paper_card(
    paper: Paper,
    *,
    show_delete: bool = False,
    key_prefix: str = "",
    show_status: bool = False,
) -> None:
    year_str = str(paper.year) if paper.year else "n/a"
    authors_str = ", ".join(paper.authors[:3])
    if len(paper.authors) > 3:
        authors_str += f" +{len(paper.authors) - 3} more"

    src_icon    = {"arxiv": "🟠", "google_scholar": "🔵", "semantic_scholar": "🔷"}.get(paper.source, "⚪")
    status_icon = ("✅ " if paper.paper_id in _analyzed_ids else "⬜ ") if show_status else ""
    label = f"{status_icon}{src_icon} **{paper.title}** ({year_str})"

    with st.expander(label, expanded=False):
        links = []
        if paper.url:
            links.append(f"[Open ↗]({paper.url})")
        if paper.pdf_url:
            links.append(f"[PDF ↗]({paper.pdf_url})")
        link_md = " · ".join(links)
        st.markdown(
            f"{_badge(paper.source)} `{paper.paper_id}` &nbsp; {link_md}",
            unsafe_allow_html=True,
        )

        col_meta, col_status = st.columns([5, 1])
        with col_meta:
            if authors_str:
                st.markdown(f"**Authors:** {authors_str}")
            row2 = []
            if paper.venue:
                row2.append(f"**Venue:** {paper.venue}")
            if paper.citation_count is not None:
                row2.append(f"**Citations:** {paper.citation_count:,}")
            if row2:
                st.markdown(" · ".join(row2))

        if show_status:
            with col_status:
                if paper.paper_id in _analyzed_ids:
                    st.markdown('<span class="badge badge-done">Analyzed</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span class="badge badge-pending">Pending</span>', unsafe_allow_html=True)

        st.markdown("**Abstract**")
        st.write(paper.abstract or "No abstract available.")

        if show_delete:
            if st.button("🗑 Delete", key=f"{key_prefix}_del_{paper.paper_id}"):
                store.delete_paper(paper.paper_id)
                st.success(f"Deleted `{paper.paper_id}`")
                st.experimental_rerun()


# ── page: search ──────────────────────────────────────────────────────────────

if page == "🔍 Search":
    st.subheader("Search Papers")

    with st.form("search_form"):
        query = st.text_input("Query", placeholder="e.g. retrieval augmented generation")
        col1, col2 = st.columns([2, 1])
        with col1:
            sources_sel = st.multiselect(
                "Sources",
                options=["arxiv", "google_scholar"],
                default=["arxiv", "google_scholar"],
                format_func=lambda s: {"arxiv": "arXiv", "google_scholar": "Google Scholar"}[s],
            )
        with col2:
            max_results = st.slider("Max results", min_value=3, max_value=20, value=8)
        submitted = st.form_submit_button("Search")

    if submitted:
        if not query.strip():
            st.warning("Enter a search query first.")
        else:
            with st.spinner(f"Searching for '{query}'…"):
                try:
                    papers = search_papers(query, sources=sources_sel or None, max_results=max_results)
                except Exception as exc:
                    st.error(f"Search failed: {exc}")
                    papers = []

            if not papers:
                st.info("No results found. Try a different query or source.")
            else:
                for p in papers:
                    store.save_paper(p)
                    index.add_paper(p)

                arxiv_n   = sum(1 for p in papers if p.source == "arxiv")
                scholar_n = len(papers) - arxiv_n
                r1, r2, r3 = st.columns(3)
                r1.metric("Results", len(papers))
                r2.metric("arXiv", arxiv_n)
                r3.metric("Google Scholar", scholar_n)
                st.success("Saved to library automatically.")
                st.markdown("---")
                for paper in papers:
                    _paper_card(paper, key_prefix="search")
    else:
        st.info("Enter a query and click **Search** to find papers.")


# ── page: library ─────────────────────────────────────────────────────────────

elif page == "🗂 Library":
    st.subheader("Your Library")

    col_refresh, col_filter = st.columns([1, 4])
    with col_refresh:
        if st.button("🔄 Refresh"):
            st.experimental_rerun()
    with col_filter:
        lib_query = st.text_input("Keyword filter", placeholder="e.g. transformer attention")

    if not _all_papers:
        st.info("Library is empty — run a search first.")
    else:
        if lib_query.strip():
            display_papers = index.search(lib_query.strip(), top_k=50)
            st.caption(f"**{len(display_papers)}** matches for '{lib_query}'")
        else:
            display_papers = _all_papers

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total", len(_all_papers))
            m2.metric("arXiv", _arxiv_n)
            m3.metric("Scholar / S2", _other_n)
            m4.metric("Analyzed", f"{len(_analyzed_ids)} / {len(_all_papers)}")

            year_counts: dict[str, int] = {}
            for p in _all_papers:
                if p.year:
                    yr = str(p.year)
                    year_counts[yr] = year_counts.get(yr, 0) + 1
            if len(year_counts) >= 2:
                st.caption("**Papers by publication year**")
                st.bar_chart(dict(sorted(year_counts.items())))

            st.markdown("---")

        for paper in sorted(display_papers, key=lambda p: p.year or 0, reverse=True):
            _paper_card(paper, show_delete=True, key_prefix="lib", show_status=True)

    # ── Find Connected Papers ─────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🔗 Find Connected Papers")
    st.caption(
        "Discovers papers via **co-citation** (shared reference lists across your library) "
        "and **Semantic Scholar recommendations** — no API key needed. "
        "Requires arXiv papers. Makes ~15 API calls (~10–15 s)."
    )

    rel_max = st.slider("Max new papers", min_value=3, max_value=20, value=8, key="rel_max")

    if st.button("Find Connected Papers", key="find_related_btn"):
        if not _all_papers:
            st.warning("Your library is empty — run a search first.")
        elif not any(p.paper_id.startswith("arxiv:") for p in _all_papers):
            st.warning("No arXiv papers in library — Semantic Scholar requires arXiv IDs.")
        else:
            conn_progress = st.progress(0)
            conn_status   = st.empty()

            def _conn_progress(current: int, total: int, title: str) -> None:
                conn_progress.progress(current / total if total else 1.0)
                conn_status.caption(f"[{current}/{total}] {title[:65]}")

            new_papers, method_used = find_connected_papers(
                store, max_new=rel_max, progress_cb=_conn_progress
            )
            conn_progress.empty()
            conn_status.empty()
            st.session_state["related_papers"] = new_papers
            st.session_state["related_query"]  = method_used

    conn_papers = st.session_state.get("related_papers")
    if conn_papers is not None:
        if not conn_papers:
            st.info("No new connected papers found. Your library may already be comprehensive.")
        else:
            method_used = st.session_state.get("related_query", "")
            p1, p2 = st.columns([1, 3])
            p1.metric("Connected found", len(conn_papers))
            p2.caption(f"via {method_used}")

            if st.button("Save all to library", key="save_related_btn"):
                for p in conn_papers:
                    store.save_paper(p)
                    index.add_paper(p)
                st.session_state["related_papers"] = None
                st.success(f"Saved {len(conn_papers)} papers.")
                st.experimental_rerun()
            for p in conn_papers:
                _paper_card(p, key_prefix="rel")

    # ── BibTeX import ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 📎 Import from BibTeX")
    st.caption(
        "Upload a `.bib` file from Zotero, Mendeley, or any reference manager. "
        "arXiv entries import from metadata directly; others are matched by title search."
    )

    bib_file = st.file_uploader("Choose .bib file", type=["bib"], key="bib_upload")

    if bib_file is not None:
        col_bib_btn, col_bib_info = st.columns([1, 3])
        with col_bib_btn:
            run_bib = st.button("Import papers", key="bib_import_btn")
        with col_bib_info:
            st.caption(f"Ready: **{bib_file.name}**")

        if run_bib:
            bib_progress = st.progress(0)
            bib_status   = st.empty()

            def _bib_progress(current: int, total: int, title: str) -> None:
                bib_progress.progress(current / total if total else 1.0)
                bib_status.caption(f"[{current}/{total}] {title[:60]}")

            bib_content = bib_file.read().decode("utf-8", errors="replace")
            bib_result  = import_from_bib(bib_content, store, index, progress_cb=_bib_progress)
            bib_progress.empty()
            bib_status.empty()
            st.session_state["bib_result"] = bib_result
            st.experimental_rerun()

    bib_res = st.session_state.get("bib_result")
    if bib_res is not None:
        b1, b2, b3 = st.columns(3)
        b1.metric("Imported", len(bib_res.imported))
        b2.metric("Already in library", len(bib_res.skipped))
        b3.metric("Not found on arXiv", len(bib_res.not_found))

        if bib_res.imported:
            st.success(f"Added **{len(bib_res.imported)}** new papers. Refresh the library above to see them.")
        elif bib_res.total == 0:
            st.warning("No valid BibTeX entries found in the file.")
        else:
            st.info("No new papers imported — all entries were already in your library or not found on arXiv.")

        if bib_res.not_found:
            with st.expander(f"{len(bib_res.not_found)} entries not resolved", expanded=False):
                for t in bib_res.not_found:
                    st.markdown(f"- {t}")
        if st.button("Clear", key="bib_clear_btn"):
            st.session_state["bib_result"] = None
            st.experimental_rerun()


# ── page: fetch ───────────────────────────────────────────────────────────────

elif page == "📄 Fetch Full Text":
    st.subheader("Fetch Full Text")
    st.caption("Tries ar5iv HTML first for arXiv papers, then falls back to PDF.")

    fetch_mode = st.radio("Input method", ["Pick from library", "Type paper ID"])

    if fetch_mode == "Pick from library":
        if not _all_papers:
            st.info("No papers saved yet. Run a search first.")
            fetch_id = ""
        else:
            chosen = st.selectbox(
                "Select paper",
                options=_all_papers,
                format_func=lambda p: f"{p.paper_id} — {p.title[:70]}",
            )
            fetch_id = chosen.paper_id if chosen else ""
    else:
        fetch_id = st.text_input("Paper ID", placeholder="e.g. arxiv:2005.11401")

    if st.button("Fetch full text", key="fetch_btn"):
        if not fetch_id.strip():
            st.warning("Enter or select a paper ID.")
        else:
            paper_meta = store.get_paper(fetch_id.strip())
            pdf_url    = paper_meta.pdf_url if paper_meta else None
            title      = paper_meta.title   if paper_meta else ""

            with st.spinner(f"Fetching `{fetch_id}`…"):
                try:
                    content = fetch_paper(fetch_id.strip(), pdf_url=pdf_url, title=title)
                except Exception as exc:
                    st.error(f"Fetch failed: {exc}")
                    content = None

            if content:
                st.success(f"**{content.title or fetch_id}** · {content.page_count} pages")

                if content.sections:
                    st.markdown("### Sections")
                    for sec_name, sec_text in content.sections.items():
                        with st.expander(
                            sec_name.title(),
                            expanded=(sec_name in ("abstract", "introduction")),
                        ):
                            st.write(sec_text[:2000])
                else:
                    st.markdown("### Full text (first 6,000 chars)")
                    st.text_area("Content", value=content.text[:6000], height=400)


# ── page: citations ───────────────────────────────────────────────────────────

elif page == "📝 Citations":
    st.subheader("Format Citations")
    st.caption("Paper must be saved in your library first.")

    cite_mode = st.radio("Input method", ["Pick from library", "Type paper ID"], key="cite_mode")

    if cite_mode == "Pick from library":
        if not _all_papers:
            st.info("No papers saved yet. Run a search first.")
            cite_id = ""
        else:
            chosen_cite = st.selectbox(
                "Select paper",
                options=_all_papers,
                format_func=lambda p: f"{p.paper_id} — {p.title[:70]}",
                key="cite_select",
            )
            cite_id = chosen_cite.paper_id if chosen_cite else ""
    else:
        cite_id = st.text_input("Paper ID", placeholder="e.g. arxiv:2005.11401", key="cite_id_input")

    style = st.selectbox("Citation style", ["apa", "mla", "bibtex"])

    if st.button("Generate citation", key="cite_btn"):
        if not cite_id.strip():
            st.warning("Enter or select a paper ID.")
        else:
            paper = store.get_paper(cite_id.strip())
            if paper is None:
                st.error(f"`{cite_id}` not found in library. Run a search for it first.")
            else:
                st.markdown(f"### {style.upper()} Citation")
                st.code(format_citation(paper, style=style), language="text")


# ── page: analyze ─────────────────────────────────────────────────────────────

elif page == "🔬 Analyze":
    st.subheader("Analyze Papers")
    st.caption(
        "Extracts limitations and future directions from full paper text. "
        "Works best for arXiv papers with explicit section headings."
    )

    if not _all_papers:
        st.info("No papers saved yet. Run a search first.")
    else:
        analyze_mode = st.radio(
            "Input method", ["Pick from library", "Type paper ID"], key="analyze_mode"
        )

        if analyze_mode == "Pick from library":
            chosen_analyze = st.selectbox(
                "Select paper",
                options=_all_papers,
                format_func=lambda p: (
                    f"{'✅' if p.paper_id in _analyzed_ids else '⬜'}  {p.paper_id} — {p.title[:60]}"
                ),
                key="analyze_select",
            )
            analyze_id = chosen_analyze.paper_id if chosen_analyze else ""
        else:
            analyze_id = st.text_input(
                "Paper ID", placeholder="e.g. arxiv:2005.11401", key="analyze_id_input"
            )

        cached    = store.get_summary(analyze_id) if analyze_id else None
        has_cache = bool(cached and (cached.limitations or cached.future_directions))

        if has_cache:
            st.info("Showing cached analysis. Click **Re-analyze** to refresh.")
            col_run, _ = st.columns([1, 3])
            run_analysis = col_run.button("Re-analyze", key="reanalyze_btn")
        else:
            run_analysis = st.button("Analyze paper", key="analyze_btn")

        if run_analysis or (has_cache and not run_analysis):
            if not analyze_id.strip():
                st.warning("Enter or select a paper ID.")
            else:
                if run_analysis:
                    with st.spinner(f"Fetching and parsing `{analyze_id}`…"):
                        result = analyze_paper(analyze_id.strip(), store=store)
                    if result.method == "unavailable":
                        st.error(
                            f"Could not fetch `{analyze_id}`. "
                            "Ensure it's an arXiv paper or has a saved PDF URL."
                        )
                        result = None
                    else:
                        existing = store.get_summary(analyze_id)
                        summary = existing or PaperSummary(
                            paper_id=analyze_id, title=result.title, summary=""
                        )
                        summary.limitations       = result.limitations
                        summary.future_directions = result.future_directions
                        store.save_summary(summary)
                        cached = store.get_summary(analyze_id)
                else:
                    result = None

                display = result or cached
                if display:
                    lim_items = (
                        display.limitations if hasattr(display, "limitations")
                        else (cached.limitations if cached else [])
                    )
                    fut_items = (
                        display.future_directions if hasattr(display, "future_directions")
                        else (cached.future_directions if cached else [])
                    )

                    if run_analysis:
                        method_label = {
                            "sections":    "explicit section headings",
                            "text_search": "keyword search in conclusion/discussion",
                        }.get(getattr(display, "method", ""), "extraction")
                        st.success(f"Extracted via **{method_label}**")
                    else:
                        st.success("Loaded from cache")

                    col_lim, col_fut = st.columns(2)

                    with col_lim:
                        st.markdown(f"### 🔴 Limitations ({len(lim_items)})")
                        if lim_items:
                            for i, item in enumerate(lim_items, 1):
                                st.markdown(f"**{i}.** {item}")
                        else:
                            st.info("No limitations found in paper text.")

                    with col_fut:
                        st.markdown(f"### 🟢 Future Directions ({len(fut_items)})")
                        if fut_items:
                            for i, item in enumerate(fut_items, 1):
                                st.markdown(f"**{i}.** {item}")
                        else:
                            st.info("No future directions found in paper text.")

        elif not has_cache:
            st.info("Select a paper above and click **Analyze paper**.")

    # ── Analysis Progress ─────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 📊 Analysis Progress")

    _statuses = get_analysis_status(store)
    _an  = sum(1 for s in _statuses if s["analyzed"])
    _tot = len(_statuses)

    if _tot > 0:
        a1, a2, a3 = st.columns(3)
        a1.metric("Analyzed", _an)
        a2.metric("Pending",  _tot - _an)
        a3.metric("Coverage", f"{round(100 * _an / _tot)}%")
        st.progress(_an / _tot)
    else:
        st.caption("No papers in library.")

    with st.expander("View per-paper status", expanded=False):
        if not _statuses:
            st.info("No papers in library.")
        else:
            for s in _statuses:
                icon    = "✅" if s["analyzed"] else "⬜"
                lim_str = f"{s['lim_count']} lim."     if s["lim_count"] else "—"
                fut_str = f"{s['fut_count']} fut. dir." if s["fut_count"] else "—"
                short   = s["title"][:65] + ("…" if len(s["title"]) > 65 else "")
                st.markdown(f"{icon} `{s['paper_id']}` · **{short}** · {lim_str} · {fut_str}")

    # ── Research Gaps ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🔬 Research Gaps Across Library")
    st.caption(
        "Clusters shared limitations and future directions across all papers. "
        "Uses cached analyses; only surfaces themes shared by the configured % of papers."
    )

    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        run_gaps = st.button("Find Research Gaps", key="gaps_btn")
    with col_info:
        st.caption(f"{len(_all_papers)} papers · {len(_analyzed_ids)} analyzed")

    overlap_pct = st.slider(
        "Theme overlap threshold — % of analyzed papers that must share a theme",
        min_value=10, max_value=100, value=75, step=5,
        key="overlap_pct",
    )

    if run_gaps:
        if not _all_papers:
            st.warning("Library is empty — run a search first.")
        else:
            gaps_bar    = st.progress(0)
            gaps_status = st.empty()

            def _gaps_progress(current: int, total: int, title: str) -> None:
                gaps_bar.progress(current / total if total else 1.0)
                short = title[:60] + "…" if len(title) > 60 else title
                gaps_status.caption(f"[{current}/{total}] {short}")

            report = find_research_gaps(
                store, progress_cb=_gaps_progress, overlap_fraction=overlap_pct / 100
            )
            gaps_bar.empty()
            gaps_status.empty()
            st.session_state["gaps_report"] = report

    report = st.session_state.get("gaps_report")
    if report is not None:
        if report.analyzed_count == 0:
            st.warning("No papers could be analyzed. Try with arXiv papers.")
        else:
            g1, g2, g3, g4 = st.columns(4)
            g1.metric("Papers analyzed",    report.analyzed_count)
            g2.metric("Skipped",            report.skipped_count)
            g3.metric("Limitation themes",  len(report.common_limitations))
            g4.metric("Future dir. themes", len(report.common_future_directions))

            col_l, col_f = st.columns(2)

            with col_l:
                st.markdown("### 🔴 Common Limitations")
                if not report.common_limitations:
                    st.info("No cross-paper themes found. Analyze more papers or lower the threshold.")
                else:
                    for i, cluster in enumerate(report.common_limitations):
                        freq_frac = cluster.frequency / report.analyzed_count
                        with st.expander(f"🔴 {cluster.theme.title()}", expanded=(i < 3)):
                            st.progress(freq_frac)
                            st.caption(
                                f"**{cluster.frequency}** of {report.analyzed_count} papers "
                                f"({round(freq_frac * 100)}%)"
                            )
                            for sent in cluster.sentences:
                                st.markdown(f"- {sent}")
                            st.caption("In: " + " · ".join(f"`{pid}`" for pid in cluster.papers))

            with col_f:
                st.markdown("### 🟢 Common Future Directions")
                if not report.common_future_directions:
                    st.info("No cross-paper themes found. Analyze more papers or lower the threshold.")
                else:
                    for i, cluster in enumerate(report.common_future_directions):
                        freq_frac = cluster.frequency / report.analyzed_count
                        with st.expander(f"🟢 {cluster.theme.title()}", expanded=(i < 3)):
                            st.progress(freq_frac)
                            st.caption(
                                f"**{cluster.frequency}** of {report.analyzed_count} papers "
                                f"({round(freq_frac * 100)}%)"
                            )
                            for sent in cluster.sentences:
                                st.markdown(f"- {sent}")
                            st.caption("In: " + " · ".join(f"`{pid}`" for pid in cluster.papers))


# ── page: graph ───────────────────────────────────────────────────────────────

elif page == "🕸 Graph":
    st.subheader("Paper Similarity Graph")
    st.caption(
        "Nodes are papers in your library. Edges connect papers with overlapping "
        "title + abstract keywords (Jaccard similarity). Node size scales with citation count; "
        "color indicates source. Hover over a node for details."
    )

    if len(_all_papers) < 2:
        st.info("Add at least 2 papers to your library to build a graph.")
    else:
        col_thresh, col_build = st.columns([3, 1])
        with col_thresh:
            threshold = st.slider(
                "Edge similarity threshold (lower = more edges)",
                min_value=0.05, max_value=0.40, value=0.12, step=0.01,
                key="graph_threshold",
            )
        with col_build:
            st.markdown("<br>", unsafe_allow_html=True)
            build_btn = st.button("Build Graph", key="graph_build_btn")

        if build_btn:
            with st.spinner(f"Building graph for {len(_all_papers)} papers…"):
                graph_data = build_graph(_all_papers, threshold=threshold)
            st.session_state["graph_data"] = graph_data
            st.session_state["graph_threshold_used"] = threshold

        graph_data = st.session_state.get("graph_data")
        if graph_data is not None:
            n_nodes = len(graph_data.get("nodes", []))
            n_edges = len(graph_data.get("edges", []))
            threshold_used = st.session_state.get("graph_threshold_used", threshold)

            gm1, gm2, gm3 = st.columns(3)
            gm1.metric("Nodes", n_nodes)
            gm2.metric("Edges", n_edges)
            gm3.metric("Threshold", f"{threshold_used:.2f}")

            if n_edges == 0:
                st.warning(
                    "No edges found at this threshold. "
                    "Try lowering it (e.g. 0.05) to reveal more connections."
                )

            st.markdown(
                '<span class="badge badge-arxiv">arXiv</span>'
                '<span class="badge badge-scholar">Scholar</span>'
                '<span class="badge badge-s2">S2</span>'
                " &nbsp; Node size = citation count · Drag to rearrange · Scroll to zoom",
                unsafe_allow_html=True,
            )
            components.html(render_html(graph_data), height=640, scrolling=False)
        else:
            st.info("Click **Build Graph** to generate the visualization.")


# ── page: agent ───────────────────────────────────────────────────────────────

elif page == "🤖 Agent":
    st.subheader("Research Viability Agent")

    # ── How it works explainer ────────────────────────────────────────────────
    with st.expander("How this agent works", expanded=False):
        st.markdown("""
**ReAct (Reason + Act)** is the pattern this agent uses. Each iteration:

1. **Thought** — The LLM reasons about what it knows and what it needs to find out.
2. **Action** — It picks one of four tools:
   - `read_section` — re-reads a section of the paper (intro, conclusion, limitations…)
   - `search_web` — searches the general web via SerpAPI for recent news and discussion
   - `search_arxiv` — searches arXiv for academic papers that might solve the same problem
   - `finish` — delivers the final verdict as structured JSON
3. **Observation** — The tool runs and returns a result, which is added to the LLM's context.

The agent **revisits the same paper multiple times** — each re-read is informed by what
web and arXiv searches revealed, deepening the analysis with each pass.

The final verdict is one of: `worth_pursuing` · `partially_covered` · `well_covered` · `unclear`
        """)

    # ── Ollama status ─────────────────────────────────────────────────────────
    _ollama = OllamaClient(model="llama3.1")
    _ollama_ok = _ollama.is_available()

    st.markdown(
        '<span class="badge badge-done">Ollama ✓ online</span>'
        if _ollama_ok else
        '<span class="badge badge-pending">Ollama ✗ offline</span>',
        unsafe_allow_html=True,
    )

    if not _ollama_ok:
        st.error(
            "Ollama is not running. Start it in a terminal with: `ollama serve`  \n"
            "Then pull a model: `ollama pull llama3.1`"
        )
    else:
        models_available = _ollama.list_models()
        if models_available:
            st.caption(f"Available models: {', '.join(models_available)}")

    st.markdown("---")

    if not _all_papers:
        st.info("Add papers to your library first (use **🔍 Search** or import a BibTeX file).")
    else:
        # ── Configuration ─────────────────────────────────────────────────────
        col_paper, col_iter = st.columns([3, 1])
        with col_paper:
            agent_paper = st.selectbox(
                "Select paper to analyze",
                options=_all_papers,
                format_func=lambda p: f"{p.paper_id} — {p.title[:65]}",
                key="agent_paper_select",
            )
        with col_iter:
            agent_iters = st.slider(
                "Max iterations",
                min_value=3, max_value=8, value=5,
                key="agent_iters",
            )

        run_agent = st.button(
            "Run Agent",
            key="agent_run_btn",
            disabled=(not _ollama_ok),
        )

        if run_agent and agent_paper:
            agent_bar    = st.progress(0)
            agent_status = st.empty()

            def _agent_progress(current: int, total: int, msg: str) -> None:
                agent_bar.progress(current / total if total else 1.0)
                agent_status.caption(msg[:80])

            try:
                researcher = ResearchAgent(
                    model="llama3.1",
                    max_iterations=agent_iters,
                )
                report = researcher.run(
                    agent_paper.paper_id,
                    store=store,
                    progress_cb=_agent_progress,
                )
                agent_bar.empty()
                agent_status.empty()
                st.session_state["agent_report"] = report
            except Exception as exc:
                agent_bar.empty()
                agent_status.empty()
                st.error(f"Agent failed: {exc}")

        # ── Report display ────────────────────────────────────────────────────
        report = st.session_state.get("agent_report")
        if report is not None:
            st.markdown("---")

            # Verdict badge
            _VERDICT_STYLE = {
                "worth_pursuing":    ("badge-done",    "Worth Pursuing ✓"),
                "partially_covered": ("badge-scholar", "Partially Covered"),
                "well_covered":      ("badge-arxiv",   "Well Covered ✗"),
                "unclear":           ("badge-pending", "Unclear"),
            }
            v_cls, v_label = _VERDICT_STYLE.get(
                report.verdict, ("badge-pending", report.verdict.replace("_", " ").title())
            )
            conf_pct = round(report.confidence * 100)

            r1, r2, r3 = st.columns(3)
            r1.metric("Verdict", v_label)
            r2.metric("Confidence", f"{conf_pct}%")
            r3.metric("Iterations", report.total_iterations)

            st.markdown(
                f'<span class="badge {v_cls}">{v_label}</span> '
                f'<span style="color:#9aa0a6;font-size:0.75rem;">confidence</span>',
                unsafe_allow_html=True,
            )
            st.progress(report.confidence)

            st.markdown("#### Reasoning")
            st.markdown(report.reasoning)

            # Gaps + directions
            if report.gaps or report.directions:
                gc, dc = st.columns(2)
                with gc:
                    st.markdown("#### Open Gaps")
                    if report.gaps:
                        for g in report.gaps:
                            st.markdown(f"- {g}")
                    else:
                        st.caption("None identified.")
                with dc:
                    st.markdown("#### Research Directions")
                    if report.directions:
                        for d in report.directions:
                            st.markdown(f"- {d}")
                    else:
                        st.caption("None identified.")

            # Competing work
            if report.competing_work:
                st.markdown("#### Competing / Related Work Found")
                for c in report.competing_work:
                    st.markdown(f"- {c}")

            # Step-by-step trace
            st.markdown("---")
            st.markdown("#### Agent Trace")
            st.caption(
                f"Model: {report.model} · "
                f"{report.total_iterations} iterations · "
                "Expand each step to see the full Thought / Action / Observation"
            )

            _ACTION_BADGE = {
                "search_web":    ("badge-scholar", "🌐 search_web"),
                "search_arxiv":  ("badge-arxiv",   "📄 search_arxiv"),
                "read_section":  ("badge-s2",      "📖 read_section"),
                "finish":        ("badge-done",     "✓ finish"),
            }

            for step in report.steps:
                a_cls, a_label = _ACTION_BADGE.get(
                    step.action, ("badge-pending", step.action)
                )
                header = (
                    f"Iteration {step.iteration} · "
                    f"<span class='badge {a_cls}'>{a_label}</span> "
                    f"<code>{step.action_input[:55]}{'…' if len(step.action_input) > 55 else ''}</code> "
                    f"<span style='color:#9aa0a6;font-size:0.7rem;'>({step.elapsed_s:.1f}s)</span>"
                )
                with st.expander(f"Iteration {step.iteration} — {step.action}({step.action_input[:40]}…)", expanded=False):
                    st.markdown("**Thought**")
                    st.markdown(step.thought)
                    st.markdown(
                        f"**Action** &nbsp; <span class='badge {a_cls}'>{a_label}</span>",
                        unsafe_allow_html=True,
                    )
                    st.code(step.action_input, language="text")
                    st.markdown("**Observation**")
                    st.text(step.observation[:800])

            # Save button
            st.markdown("---")
            if st.button("Save analysis to library", key="agent_save_btn"):
                existing = store.get_summary(report.paper_id)
                summary = existing or PaperSummary(
                    paper_id=report.paper_id,
                    title=report.title,
                    summary="",
                )
                summary.summary           = report.reasoning
                summary.limitations       = report.gaps
                summary.future_directions = report.directions
                store.save_summary(summary)
                st.success(
                    "Saved to library. View it on the **🔬 Analyze** page."
                )

            if st.button("Clear", key="agent_clear_btn"):
                st.session_state["agent_report"] = None
                st.experimental_rerun()
