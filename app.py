import streamlit as st
import pandas as pd
import plotly.express as px
from embedding import EmbeddingManager
from main import generate_paper_link
import os

# Page config
st.set_page_config(
    page_title="Sistem Rekomendasi Karya Ilmiah",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5em;
        font-weight: bold;
    }   
    .score-badge {
        display: inline-block;
        background-color: #4CAF50;
        color: white;
        padding: 5px 10px;
        border-radius: 4px;
        font-size: 0.9em;
        margin-left: 10px;
    }
    .paper-link {
        text-decoration: none !important; 
        color: inherit !important; 
        font-family: inherit;
    }
    .paper-link:hover {
        text-decoration: underline !important;
        color: #0073bb !important;
    }
    .tip-card{
        background:#1f2128;
        border:1px solid #333;
        border-radius:8px;
        padding:14px 16px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
@st.cache_resource
def load_embedding_manager():
    """Load embedding manager (cached for performance)"""
    collection_name = os.getenv('COLLECTION_NAME', 'hybrid_60')
    
    try:
        qdrant_url = st.secrets["QDRANT_URL"]
        qdrant_api_key = st.secrets["QDRANT_API_KEY"]
        is_cloud = True
    except Exception:
        is_cloud = False

    if is_cloud:
        return EmbeddingManager(
            collection_name=collection_name,
            qdrant_url=qdrant_url,
            qdrant_api_key=qdrant_api_key
        )
    else:
        qdrant_path = './qdrant_storage'
        if not os.path.exists(qdrant_path):
            st.error("❌ Vector database tidak ditemukan. Silakan jalankan main.py terlebih dahulu.")
            st.stop()
        
        return EmbeddingManager(qdrant_path=qdrant_path, collection_name=collection_name)

# Load manager
em = load_embedding_manager()

# Get collection stats
stats = em.get_collection_stats()

# Header
st.markdown('<h1 class="main-header">📚 Sistem Rekomendasi Karya Ilmiah</h1>', 
            unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Dataset Info")
    st.metric("Total Dokumen", stats['points_count'])
    
    # Get trend data
    trends = em.analyze_trends()
    min_year = min(trends['tahun_distribution'])
    max_year = max(trends['tahun_distribution'])
    # st.metric("Total Jurusan", len(trends['jurusan_distribution']))
    st.metric("Total Jurusan", len(trends['jurusan_distribution']))
    st.metric("Rentang Tahun", f"{min_year}-{max_year}")
    
    st.header("📌 Tips")
    st.markdown("""
    <div class="tip-card">
    <ul>
    <li>Gunakan judul, kata kunci, atau topik penelitian</li>
    <li>Bisa memakai kata kunci</li>
    <li>Gunakan bahasa Indonesia</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

# Callback function to maintain state
def buka_detail(data_paper):
    st.session_state.selected_paper = data_paper

# Initialize session state untuk detail view
if 'selected_paper' not in st.session_state:
    st.session_state.selected_paper = None
if 'search_results' not in st.session_state:
    st.session_state.search_results = None
if 'last_query' not in st.session_state:
    st.session_state.last_query = ""

# Main tabs
tab1, tab2 = st.tabs(["🔍 Rekomendasi", "📊 Tren Analisis"])

# ============= TAB 1: RECOMMENDATION =============
with tab1:
    # ===== CONDITIONAL RENDERING: SEARCH VIEW vs DETAIL VIEW =====
    if st.session_state.selected_paper is None:
        # ===== SEARCH VIEW (EXISTING) =====
        st.markdown('<h2 class="subheader-custom">Telusuri Karya Ilmiah Sejenis</h2>', 
                    unsafe_allow_html=True)
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            query = st.text_input(
                "Masukkan judul, topik, atau kata kunci karya ilmiah yang Anda cari:",
                placeholder="Cari disini",
                key="search_query"
            )
        
        with col2:
            k_results = st.slider(
                "Jumlah hasil",
                min_value=5,
                max_value=30,
                value=10,
                key="k_results"
            )
        
        # Filters (sidebar-like)
        st.markdown("### Filter Hasil")
        col_f1, col_f2 = st.columns(2)
        
        with col_f1:
            filter_jurusan = st.selectbox(
                "Filter by Jurusan:",
                ["Semua"] + sorted(list(trends['jurusan_distribution'].keys())),
                key="filter_jurusan"
            )
        
        with col_f2:
            filter_tahun = st.selectbox(
                "Filter by Tahun:",
                ["Semua"] + sorted(list(trends['tahun_distribution'].keys()), reverse=True),
                key="filter_tahun"
            )
        
        # Search button & rendering logic
        btn_pressed = st.button("🚀 Cari Rekomendasi", type="primary", use_container_width=True)

        # Render jika tombol ditekan ATAU ada cache hasil pencarian sebelumnya
        if btn_pressed or st.session_state.search_results is not None:
            if not query.strip() and st.session_state.search_results is None:
                st.warning("⚠️ Silakan masukkan judul atau topik pencarian")
            else:
                with st.spinner("🔄 Mencari rekomendasi..."):
                    try:
                        # Logika Cache: Cari baru jika query berubah, atau ambil dari cache jika kembali dari halaman detail
                        if btn_pressed or st.session_state.last_query != query:
                            results = em.search_hybrid(query, limit=k_results)
                            st.session_state.search_results = results
                            st.session_state.last_query = query
                        else:
                            results = st.session_state.search_results
                        
                        if not results:
                            st.warning("❌ Tidak ada hasil yang ditemukan")
                        else:
                            # Apply additional filtering if needed
                            filtered_results = results.copy()
                            
                            if filter_jurusan != "Semua":
                                filtered_results = [r for r in filtered_results 
                                                if r['jurusan'] == filter_jurusan]
                            
                            if filter_tahun != "Semua":
                                filtered_results = [r for r in filtered_results 
                                                if r['tahun'] == filter_tahun]
                            
                            if not filtered_results:
                                st.warning("⚠️ Tidak ada hasil yang sesuai dengan filter")
                            else:
                                st.success(f"✅ Ditemukan {len(filtered_results)} karya ilmiah yang sejenis")
                                
                                # Display results
                                for idx, paper in enumerate(filtered_results, 1):
                                    with st.container(border=True):
                                        col_num, col_score = st.columns([15, 1])
                                        
                                        with col_num:
                                            paper_link = generate_paper_link(paper['judul'])
                                            st.markdown(
                                                f"""
                                                <a href="{paper_link}" target="_blank" class="paper-link">
                                                    <strong>{idx}. {paper['judul']}</strong>
                                                </a>
                                                """,
                                                unsafe_allow_html=True
                                            )
                                        
                                        with col_score:
                                            score_pct = round(paper['score'] * 100, 1)
                                            st.markdown(f"""
                                            <div class="score-badge">{score_pct}%</div>
                                            """, unsafe_allow_html=True)
                                        
                                        # Metadata
                                        col_m1, col_m2, col_m3 = st.columns(3, vertical_alignment='center')

                                        with col_m1:
                                            st.caption(f"**{paper['jenis']}  |  {paper['jurusan']}  |  {paper['tahun']}**", text_alignment='center')
                                        
                                        with col_m2:
                                            # MENGGUNAKAN CALLBACK UNTUK TOMBOL DETAIL
                                            st.html("""
                                                <style>                                                
                                                /* Efek Hover */
                                                div[data-testid="stColumn"] button:hover {
                                                    color: #0073bb !important; /* Warna biru */
                                                    text-decoration: underline !important; /* Garis bawah */
                                                    background: transparent !important;
                                                }
                                                
                                                /* Menghilangkan efek warna abu-abu bawaan streamlit saat tombol diklik/fokus */
                                                div[data-testid="stColumn"] button:focus:not(:active) {
                                                    background: transparent !important;
                                                    color: #0000FF !important;
                                                }
                                                </style>
                                            """)
                                            st.button(
                                                "📖 Lihat Detail & Karya Serupa", 
                                                key=f"view_{idx}_{paper['judul']}", 
                                                use_container_width=True,
                                                on_click=buka_detail,
                                                args=(paper,),
                                                type='tertiary'
                                            )

                                        # Detailed stats
                                        with st.expander("Lihat Abstrak"):
                                            st.write(paper['abstrak'])

                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
        
    else:
        # ===== DETAIL VIEW =====
        paper = st.session_state.selected_paper
        
        # Back button
        col_back, col_spacer = st.columns([1, 10])
        with col_back:
            if st.button("⬅️ Kembali", use_container_width=True):
                st.session_state.selected_paper = None
                st.rerun()
        
        st.markdown("---")
        
        # Paper detail metadata
        st.markdown(f"## {paper['judul']}")
        
        col_d1, col_d2, col_d3, col_d4 = st.columns(4)
        with col_d1:
            st.caption(f"📋 **Jenis:** {paper['jenis']}")
        with col_d2:
            st.caption(f"🎓 **Jurusan:** {paper['jurusan']}")
        with col_d3:
            st.caption(f"📅 **Tahun:** {paper['tahun']}")
        with col_d4:
            st.caption(f"🏢 **Fakultas:** {paper['fakultas']}")
        
        st.markdown("### Abstrak")
        st.write(paper['abstrak'])
        
        st.markdown("### Informasi Tambahan")
        col_info1, col_info2 = st.columns(2)
        with col_info1:
            st.caption(f"👨‍🏫 **Dosen Pembimbing:** {paper['dosen_pembimbing']}")
        with col_info2:
            paper_link = generate_paper_link(paper['judul'])
            st.link_button("🔗 Buka Dokumen", paper_link, use_container_width=True)
        
        st.markdown("---")
        
        # Similar papers section
        st.markdown("### 📚 Karya Serupa")
        
        with st.spinner("🔄 Mencari karya serupa..."):
            try:
                similar_papers = em.search_similar_by_paper_id(paper['id'], limit=5)
                
                if not similar_papers:
                    st.info("ℹ️ Tidak ada karya serupa yang ditemukan")
                else:
                    st.write(f"**Ditemukan {len(similar_papers)} karya serupa:**")
                    
                    for idx, similar_paper in enumerate(similar_papers, 1):
                        with st.container(border=True):
                            col_sim_num, col_sim_score = st.columns([15, 1])
                            
                            with col_sim_num:
                                st.markdown(f"**{idx}. {similar_paper['judul']}**")
                            
                            with col_sim_score:
                                score_pct = round(similar_paper['score'] * 100, 1)
                                st.markdown(f"""
                                <div class="score-badge">{score_pct}%</div>
                                """, unsafe_allow_html=True)
                            
                            # Metadata
                            col_sim_m1, col_sim_m2, col_sim_m3 = st.columns(3)
                            with col_sim_m1:
                                st.caption(f"📋 **Jenis:** {similar_paper['jenis']}")
                            with col_sim_m2:
                                st.caption(f"🎓 **Jurusan:** {similar_paper['jurusan']}")
                            with col_sim_m3:
                                st.caption(f"📅 **Tahun:** {similar_paper['tahun']}")
                            
                            # Detail button for similar papers
                            col_sim_detail, col_sim_doc = st.columns(2)
                            with col_sim_detail:
                                # MENGGUNAKAN CALLBACK UNTUK TOMBOL KARYA SERUPA
                                st.button(
                                    "📖 Lihat Detail", 
                                    key=f"detail_{similar_paper['id']}", 
                                    use_container_width=True,
                                    on_click=buka_detail,
                                    args=(similar_paper,)
                                )
                            
                            with col_sim_doc:
                                similar_link = generate_paper_link(similar_paper['judul'])
                                st.link_button("🔗 Buka", similar_link, use_container_width=True)
                            
                            # Abstract expander
                            with st.expander("Lihat Abstrak"):
                                st.write(similar_paper['abstrak'])
            
            except Exception as e:
                st.error(f"❌ Error mencari karya serupa: {str(e)}")

# ============= TAB 2: TREND ANALYSIS =============
with tab2:
    st.markdown('<h2 class="subheader-custom">Analisis Tren Karya Ilmiah</h2>', 
                unsafe_allow_html=True)
    
    # Get all papers for detailed analysis
    all_papers = em.get_all_papers()
    papers_df = pd.DataFrame(all_papers)
    
    # Convert tahun to numeric for sorting
    papers_df['tahun_numeric'] = pd.to_numeric(papers_df['tahun'], errors='coerce')
    
    col_trend1, col_trend2 = st.columns(2)
    
    # Tren 1: Per Jurusan
    with col_trend1:
        st.markdown("### 📌 Distribusi per Jurusan")
        
        jurusan_dist = papers_df['jurusan'].value_counts().reset_index()
        jurusan_dist.columns = ['Jurusan', 'Jumlah']
        
        fig_jurusan = px.bar(
            jurusan_dist,
            x='Jurusan',
            y='Jumlah',
            title='Jumlah Karya Ilmiah per Jurusan',
            labels={'Jumlah': 'Jumlah Karya', 'Jurusan': ''},
            color='Jumlah',
            color_continuous_scale='Blues'
        )
        fig_jurusan.update_layout(
            height=400,
            xaxis_tickangle=-45,
            showlegend=False
        )
        st.plotly_chart(fig_jurusan, width='stretch')
        
        # Detailed stats
        with st.expander("📊 Detail Statistik Jurusan"):
            st.dataframe(jurusan_dist.sort_values('Jumlah', ascending=False), width='stretch')
    
    # Tren 2: Per Tahun
    with col_trend2:
        st.markdown("### 📅 Tren per Tahun")
        
        tahun_dist = papers_df.groupby('tahun_numeric').size().reset_index(name='Jumlah')
        tahun_dist = tahun_dist.sort_values('tahun_numeric')
        tahun_dist['Tahun'] = tahun_dist['tahun_numeric'].astype(int).astype(str)
        
        fig_tahun = px.line(
            tahun_dist,
            x='Tahun',
            y='Jumlah',
            title='Trend Karya Ilmiah per Tahun',
            labels={'Jumlah': 'Jumlah Karya', 'Tahun': ''},
            markers=True,
            line_shape='linear'
        )
        fig_tahun.update_traces(line=dict(color='#1f77b4', width=3))
        fig_tahun.update_layout(height=400)
        st.plotly_chart(fig_tahun, width='stretch')
        
        # Detailed stats
        with st.expander("📊 Detail Statistik Tahun"):
            st.dataframe(tahun_dist[['Tahun', 'Jumlah']].sort_values('Tahun', ascending=False), width='stretch')
    
    # Advanced Analytics
    st.markdown("### 🔬 Analisis Lanjutan")
    
    col_adv1, col_adv2, col_adv3 = st.columns(3)
    
    with col_adv1:
        top_jurusan = papers_df['jurusan'].value_counts().head(1)
        st.metric(
            "Jurusan Terbanyak",
            top_jurusan.index[0],
            f"{top_jurusan.values[0]} karya"
        )
    
    with col_adv2:
        top_tahun = papers_df['tahun'].value_counts().head(1)
        st.metric(
            "Tahun Terbanyak",
            top_tahun.index[0],
            f"{top_tahun.values[0]} karya"
        )
    
    with col_adv3:
        avg_per_jurusan = papers_df.groupby('jurusan').size().mean()
        st.metric(
            "Rata-rata per Jurusan",
            f"{avg_per_jurusan:.1f}",
            "karya ilmiah"
        )
    
    # Heatmap: Jurusan x Tahun
    st.markdown("### 🔥 Heatmap: Jurusan vs Tahun")
    try:
        pivot_data = papers_df.pivot_table(
            index='jurusan',
            columns='tahun',
            aggfunc='size',
            fill_value=0
        ).rename_axis(index=None, columns=None)
        
        fig_heatmap = px.imshow(
            pivot_data,
            labels=dict(color="Jumlah Karya"),
            color_continuous_scale='YlOrRd'
        )
        fig_heatmap.update_layout(height=500)
        st.plotly_chart(fig_heatmap, width='stretch')
    except Exception as e:
        st.warning(f"Tidak dapat membuat heatmap: {str(e)}")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9em;'>
    <p>📚 Sistem Rekomendasi Karya Ilmiah | Powered by IndoSBERT + Qdrant | Built with Streamlit</p>
</div>
""", unsafe_allow_html=True)
