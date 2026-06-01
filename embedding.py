import pandas as pd
import numpy as np
import re
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, SparseVector, 
    SparseVectorParams, Modifier, Prefetch, Fusion, FusionQuery
)
import uuid
from typing import List, Dict, Tuple
from fastembed import SparseTextEmbedding

class EmbeddingManager:
    """Manager untuk generate embeddings menggunakan IndoSBERT dan manage Qdrant"""
    
    def __init__(self, model_name: str = 'firqaaa/indo-sentence-bert-base', 
                 qdrant_path: str = './qdrant_storage',
                 collection_name: str = 'hybrid_60'):
        """
        Initialize embedding manager dengan dense + sparse (BM25) support
        
        Args:
            model_name: Model IndoSBERT dari Huggingface (dense)
            qdrant_path: Path untuk Qdrant persistent storage
            collection_name: Collection name di Qdrant
        """
        print(f'Loading dense model: {model_name}...')
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_embedding_dimension()
        print(f'Dense model loaded. Embedding dimension: {self.embedding_dim}')
        
        # Initialize sparse BM25 model dari fastembed
        self.sparse_model = None
        print(f'Loading sparse embedding model (BM25)...')
        self.sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")
        print(f'Sparse BM25 model loaded successfully')
        
        print(f'Initializing Qdrant at {qdrant_path}...')
        self.qdrant_client = QdrantClient(path=qdrant_path)
        self.collection_name = collection_name
    
    def create_collection(self, recreate: bool = False):
        """Create Qdrant collection dengan support dense + sparse (BM25) vectors"""
        try:
            if recreate:
                self.qdrant_client.delete_collection(self.collection_name)
                print(f'Deleted existing collection: {self.collection_name}')
        except:
            pass
        
        # Check if collection already exists
        try:
            collections = self.qdrant_client.get_collections()
            if any(c.name == self.collection_name for c in collections.collections):
                print(f'Collection {self.collection_name} already exists')
                return
        except:
            pass
        
        print(f'Creating collection: {self.collection_name}...')
        self.qdrant_client.create_collection(
            collection_name=self.collection_name,
            vectors_config={
                'dense': VectorParams(
                    size=self.embedding_dim,
                    distance=Distance.COSINE
                )
            },
            sparse_vectors_config={
                'sparse': SparseVectorParams(
                    modifier=Modifier.IDF  # Use IDF for BM25
                )
            }
        )
        print(f'Created collection: {self.collection_name} with dense + sparse support')
    
    def generate_embeddings(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Generate embeddings untuk list of texts
        
        Args:
            texts: List of paper titles/descriptions
            batch_size: Batch size untuk processing
        
        Returns:
            Array of embeddings shape [n, embedding_dim]
        """
        print(f'Generating embeddings for {len(texts)} texts...')
        embeddings = self.model.encode(texts, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=True)
        print(f'Generated embeddings shape: {embeddings.shape}')
        return embeddings
    
    def clean_text(self, text: str) -> str:
        if not isinstance(text, str):
            return ""

        # lowercase / case folding
        text = text.lower()

        # remove html tags
        text = re.sub(r"<.*?>", " ", text)

        # remove urls
        text = re.sub(r"http\S+|www\S+", " ", text)

        # remove email
        text = re.sub(r"\S+@\S+", " ", text)

        # remove newline, tab
        text = re.sub(r"[\n\r\t]", " ", text)

        # remove non-alphanumeric characters
        # keep Indonesian letters/numbers/basic punctuation
        text = re.sub(r"[^a-z0-9\s.,]", " ", text)

        # normalize multiple spaces
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def is_repeated_char(self, text: str, min_repeat: int = 6) -> bool:
        """
        Return True if text consists mostly of one repeated character.
        
        Examples:
        - aaaaaaaa
        - zzzzzzzz
        - 11111111
        """
        # remove spaces
        text = text.replace(" ", "")

        # check if all chars are same
        return len(set(text)) == 1

    def ingest_papers(self, csv_path: str, recreate: bool = True, title_weight: float = None):
        """
        Ingest papers ke Qdrant dengan dense + sparse (BM25) embeddings
        
        Args:
            csv_path: Path ke CSV file dengan columns: [jenis, fakultas, judul, dosen_pembimbing, jurusan, tahun, abstrak]
            recreate: Jika True, delete dan recreate collection
            title_weight: None = combined text (default), 0.7 = 70% title
        """
        # Load data
        print(f'Loading papers from {csv_path}...')
        df = pd.read_csv(csv_path)
        print(f'Loaded {len(df)} papers')
        
        # Remove duplicates based on judul
        df = df.drop_duplicates(subset=['judul'], keep='first')
        print(f'After dedup: {len(df)} papers')
        
        # Clean data
        df = df.fillna('')
        
        # Filter bad data (title with repeated strings)
        df = df[~df['judul'].apply(self.is_repeated_char)]

        # Filter out data with out of range or error year
        df = df[df['tahun'].isin(['2020', '2021', '2022', '2023', '2024', '2025', '2026'])]
        print(f'After year filter: {len(df)} papers')

        # Capitalize all the titles
        df['judul'] = df['judul'].str.upper()

        print('Loading embedded numpy files...')
        title_embs = np.load('embedded_output/title_embeddings.npy')
        abstract_embs = np.load('embedded_output/abstract_embeddings.npy')
        
        if title_embs is not None and abstract_embs is not None:
            embeddings = (title_weight * title_embs + (1 - title_weight) * abstract_embs)
        
        else:
            # Generate dense embeddings
            if title_weight is not None:
                judul_cleaned = df['judul'].apply(self.clean_text)
                abstrak_cleaned = df['abstrak'].apply(self.clean_text)

                print(f'Generating weighted dense embeddings (title_weight={title_weight})...')
                title_embs = self.generate_embeddings(judul_cleaned.tolist())
                abstract_embs = self.generate_embeddings(abstrak_cleaned.tolist())
                embeddings = (title_weight * title_embs + (1 - title_weight) * abstract_embs)
            else:
            # Combine title + abstract
                df['teks'] = (
                    df['judul'].astype(str) + '. ' +
                    df['abstrak'].astype(str)
                )
                df['teks'] = df['teks'].apply(self.clean_text)
                embeddings = self.generate_embeddings(df['teks'].tolist())

        # Generate sparse (BM25) embeddings untuk setiap document
        sparse_embeddings = []

        print(f'Generating sparse BM25 embeddings...')
        texts_for_sparse = (
            df['judul'].astype(str) + ' ' +
            df['abstrak'].astype(str)
        ).tolist()
        
        sparse_embeddings = list(self.sparse_model.embed(texts_for_sparse))
        print(f'Generated {len(sparse_embeddings)} sparse embeddings')

        # Create collection
        self.create_collection(recreate=recreate)
                
        # Prepare points untuk Qdrant dengan dense + sparse vectors (jika tersedia)
        print(f'Preparing {len(df)} points...')
        points = []
        for idx, (_, row) in enumerate(df.iterrows()):
            point_id = str(uuid.uuid4())
            
            # Build point with dense and sparse (bm25) vector
            point_data = {
                'id': point_id,
                'vector': {
                    'dense': embeddings[idx].tolist(),
                    'sparse': SparseVector(
                        indices=sparse_embeddings[idx].indices.tolist(),
                        values=sparse_embeddings[idx].values.tolist(),
                    )
                },
                'payload': {
                    'id_penulisan': point_id,
                    'jenis': str(row['jenis']),
                    'fakultas': str(row['fakultas']),
                    'judul': str(row['judul']),
                    'dosen_pembimbing': str(row['dosen_pembimbing']),
                    'jurusan': str(row['jurusan']),
                    'tahun': str(row['tahun']),
                    'abstrak': str(row['abstrak'])
                }
            }
            
            points.append(PointStruct(**point_data))
        
        # Upload ke Qdrant
        print(f'Uploading {len(points)} points to Qdrant...')
        self.qdrant_client.upsert(
            collection_name=self.collection_name,
            points=points,
            wait=True
        )
        print(f'Successfully ingested {len(points)} papers with dense + sparse embeddings')
        
        return len(points)
    
    def search_similar_by_paper_id(self, paper_id: str, limit: int = 5) -> List[Dict]:
        """
        Search papers mirip dengan paper tertentu (berdasarkan ID/vector)
        
        Args:
            paper_id: ID dari paper yang ingin dicari rekomendasinya
            limit: Jumlah hasil yang ingin ditampilkan (default 5)
        
        Returns:
            List of similar papers dengan score dan metadata, exclude paper_id itu sendiri
        """
        try:
            # Retrieve point dari Qdrant untuk dapatkan vectornya
            points = self.qdrant_client.retrieve(
                collection_name=self.collection_name,
                ids=[paper_id],
                with_vectors=True
            )
            
            if not points:
                return []
            
            paper_vector = points[0].vector
            
            # Query dengan vector, limit+1 untuk bisa exclude paper itu sendiri
            results = self.qdrant_client.query_points(
                collection_name=self.collection_name,
                query=paper_vector.get('dense'),
                using='dense',
                limit=limit + 1
            )
            
            # Format results & filter out paper_id itu sendiri
            output = []
            for result in results.points:
                if result.id != paper_id:
                    output.append({
                        'id': result.id,
                        'score': result.score,
                        **result.payload
                    })
                    if len(output) >= limit:
                        break
            
            return output
        except Exception as e:
            print(f'Error searching similar papers by ID: {str(e)}')
            return []

    def search_hybrid(self, query_text: str, limit: int = 10, 
                     prefetch_limit: int = 30,
                     filters: Dict = None) -> List[Dict]:
        """
        Hybrid search menggunakan dense (semantic) + sparse (BM25) dengan RRF fusion
        
        Args:
            query_text: Query text untuk dicari
            limit: Jumlah final results yang diinginkan
            prefetch_limit: Jumlah results untuk prefetch dari masing-masing path sebelum fusion
            filters: Optional filters (e.g., jurusan, tahun)
        
        Returns:
            List of results dengan score dan metadata, re-ranked via RRF
        """
        # Generate dense embedding
        dense_query = self.model.encode(query_text).tolist()
        
        # Generate sparse (BM25) embedding
        sparse_query_list = list(self.sparse_model.embed([query_text]))
        sparse_query = sparse_query_list[0]
        sparse_query_vec = SparseVector(
            indices=sparse_query.indices.tolist(),
            values=sparse_query.values.tolist()
        )
        
        # Hybrid search dengan Prefetch + Fusion.RRF
        print(f'Running hybrid search for: "{query_text}"')
        results = self.qdrant_client.query_points(
            collection_name=self.collection_name,
            prefetch=[
                Prefetch(
                    query=dense_query,
                    using='dense',
                    limit=prefetch_limit
                ),
                Prefetch(
                    query=sparse_query_vec,
                    using='sparse',
                    limit=prefetch_limit
                )
            ],
            query=FusionQuery(fusion=Fusion.RRF),  # Native RRF fusion dari Qdrant
            limit=limit,
            query_filter=filters
        )
        
        # Format results
        output = []
        for result in results.points:
            output.append({
                'id': result.id,
                'score': result.score,
                **result.payload
            })
        
        print(f'Hybrid search returned {len(output)} results')
        return output

    def get_collection_stats(self) -> Dict:
        """Get stats tentang collection"""
        collection_info = self.qdrant_client.get_collection(self.collection_name)
        
        # Handle both single vector and multi-vector (named vectors) formats
        vectors_config = collection_info.config.params.vectors
        # Get dense vector
        dense_config = vectors_config.get('dense')

        return {
            'points_count': collection_info.points_count,
            'vector_size': dense_config.size,
            'distance': dense_config.distance
        }
    
    def get_all_papers(self, limit: int = 30000) -> List[Dict]:
        """Get semua papers dari collection"""
        # Scroll through all points
        points, _ = self.qdrant_client.scroll(
            collection_name=self.collection_name,
            limit=limit
        )
        
        papers = []
        for point in points:
            papers.append(point.payload)
        
        return papers
    
    def analyze_trends(self) -> Dict:
        """Analyze trends dari papers (distribusi per jurusan, tahun, dll)"""
        papers = self.get_all_papers()
        
        # Count per jurusan
        jurusan_count = {}
        tahun_count = {}
        
        for paper in papers:
            jurusan = paper.get('jurusan', 'Unknown')
            tahun = paper.get('tahun', 'Unknown')
            
            jurusan_count[jurusan] = jurusan_count.get(jurusan, 0) + 1
            tahun_count[tahun] = tahun_count.get(tahun, 0) + 1
        
        return {
            'total_papers': len(papers),
            'jurusan_distribution': jurusan_count,
            'tahun_distribution': tahun_count
        }


class VectorDBHelper:
    """Helper class untuk common vector DB operations"""
    
    @staticmethod
    def filter_by_jurusan(jurusan: str):
        """Create filter untuk jurusan tertentu"""
        from qdrant_client.models import HasFieldCondition, MatchValue
        return HasFieldCondition(field='jurusan', value=MatchValue(value=jurusan))
    
    @staticmethod
    def filter_by_tahun(tahun: str):
        """Create filter untuk tahun tertentu"""
        from qdrant_client.models import HasFieldCondition, MatchValue
        return HasFieldCondition(field='tahun', value=MatchValue(value=tahun))
