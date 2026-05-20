import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
        color: #1f77b4;
        font-weight: bold;
    }
    .subheader-custom {
        font-size: 1.3em;
        color: #555;
        margin-top: 20px;
    }
    .paper-card {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        background-color: #f9f9f9;
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
</style>
""", unsafe_allow_html=True)

# Initialize session state
@st.cache_resource
def load_embedding_manager():
    """Load embedding manager (cached for performance)"""
    qdrant_path = './qdrant_storage'
    collection_name = os.getenv('COLLECTION_NAME', 'papers')
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
st.markdown(f"**Database:** {stats['points_count']} karya ilmiah | **Embedding Model:** IndoBERT Lite | **Vector Dimension:** {stats['vector_size']}")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings & Info")
    
    st.markdown("### Dataset Info")
    st.metric("Total Papers", stats['points_count'])
    
    # Get trend data
    trends = em.analyze_trends()
    st.metric("Total Jurusan", len(trends['jurusan_distribution']))
    st.metric("Total Tahun", len(trends['tahun_distribution']))
    
    st.markdown("### About")
    st.info("""
    **Sistem Rekomendasi Karya Ilmiah** menggunakan:
    - 🤗 IndoSBERT untuk embedding text
    - 🔍 Qdrant untuk vector search
    - 🎯 Hybrid search (similarity + filtering)
    """)

# Main tabs
tab1, tab2 = st.tabs(["🔍 Rekomendasi", "📊 Tren Analisis"])

# ============= TAB 1: RECOMMENDATION =============
with tab1:
    st.markdown('<h2 class="subheader-custom">Cari Karya Ilmiah Sejenis</h2>', 
                unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        query = st.text_input(
            "📖 Masukkan judul atau topik karya ilmiah yang Anda cari:",
            placeholder="Contoh: sistem rekomendasi menggunakan machine learning",
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
    st.markdown("### 🔎 Filter Hasil")
    col_f1, col_f2 = st.columns(2)
    
    with col_f1:
        filter_jurusan = st.selectbox(
            "Filter by Jurusan (opsional):",
            ["Semua"] + sorted(list(trends['jurusan_distribution'].keys())),
            key="filter_jurusan"
        )
    
    with col_f2:
        filter_tahun = st.selectbox(
            "Filter by Tahun (opsional):",
            ["Semua"] + sorted(list(trends['tahun_distribution'].keys()), reverse=True),
            key="filter_tahun"
        )
    
    # Search button
    if st.button("🚀 Cari Rekomendasi", type="primary", width='stretch'):
        if not query.strip():
            st.warning("⚠️ Silakan masukkan judul atau topik pencarian")
        else:
            with st.spinner("🔄 Mencari rekomendasi..."):
                try:
                    # Search
                    results = em.search_similar(query, limit=k_results)
                    
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
                                        st.markdown(f"**{idx}. {paper['judul']}**")
                                    
                                    with col_score:
                                        score_pct = round(paper['score'] * 100, 1)
                                        st.markdown(f"""
                                        <div class="score-badge">{score_pct}%</div>
                                        """, unsafe_allow_html=True)
                                    
                                    # Metadata
                                    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                                    
                                    with col_m1:
                                        st.caption(f"📋 **Jenis:** {paper['jenis']}")
                                    
                                    with col_m2:
                                        st.caption(f"🎓 **Jurusan:** {paper['jurusan']}")
                                    
                                    with col_m3:
                                        st.caption(f"📅 **Tahun:** {paper['tahun']}")

                                    col_n1, col_n2, col_n3 = st.columns(3)
                                                                        
                                    # Link
                                    with col_n1:
                                        paper_link = generate_paper_link(paper['judul'])
                                        st.link_button("🔗 Buka Dokumen", paper_link)

                                    # Detailed stats
                                    with col_n2:
                                        with st.expander("Detail Abstrak"):
                                            st.write(paper['abstrak'])

                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

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
            labels={'Jumlah': 'Jumlah Karya', 'Jurusan': 'Jurusan'},
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
            labels={'Jumlah': 'Jumlah Karya', 'Tahun': 'Tahun'},
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
        )
        
        fig_heatmap = px.imshow(
            pivot_data,
            labels=dict(color="Jumlah Karya"),
            title='Distribusi Karya Ilmiah: Jurusan vs Tahun',
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
