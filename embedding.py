import pandas as pd
import numpy as np
import re
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid
from typing import List, Dict, Tuple

class EmbeddingManager:
    """Manager untuk generate embeddings menggunakan IndoSBERT dan manage Qdrant"""
    
    def __init__(self, model_name: str = 'firqaaa/indo-sentence-bert-base', 
                 qdrant_path: str = './qdrant_storage',
                 collection_name: str = 'papers'):
        """
        Initialize embedding manager
        
        Args:
            model_name: Model IndoSBERT dari Huggingface
            qdrant_path: Path untuk Qdrant persistent storage
        """
        print(f'Loading model: {model_name}...')
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_embedding_dimension()
        print(f'Model loaded. Embedding dimension: {self.embedding_dim}')
        
        print(f'Initializing Qdrant at {qdrant_path}...')
        self.qdrant_client = QdrantClient(path=qdrant_path)
        self.collection_name = collection_name
    
    def create_collection(self, recreate: bool = False):
        """Create Qdrant collection untuk papers"""
        try:
            if recreate:
                self.qdrant_client.delete_collection(self.collection_name)
                print(f'Deleted existing collection: {self.collection_name}')
        except:
            pass
        
        self.qdrant_client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.embedding_dim,
                distance=Distance.COSINE
            )
        )
        print(f'Created collection: {self.collection_name}')
    
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
        embeddings = self.model.encode(texts, batch_size=batch_size, show_progress_bar=True)
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
        Ingest papers dari CSV ke Qdrant dengan embeddings, serta optional title weighting
        
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
        print(f'After year filter: {len(df)} papers')  # Debug

        # Capitalize all the titles
        df['judul'] = df['judul'].str.upper()
        print(f'After capitalize: {len(df)} papers')  # Debug

        # Generate embeddings
        if title_weight is not None:
            judul_cleaned = df['judul'].apply(self.clean_text)
            abstrak_cleaned = df['abstrak'].apply(self.clean_text)

            print(f'Generating weighted embeddings (title_weight={title_weight})...')
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

        # Create collection
        self.create_collection(recreate=recreate)
                
        # Prepare points untuk Qdrant
        points = []
        for idx, (_, row) in enumerate(df.iterrows()):
            point = PointStruct(
                id=idx,  # atau bisa pakai uuid.uuid4().int
                vector=embeddings[idx].tolist(),
                payload={
                    'jenis': str(row['jenis']),
                    'fakultas': str(row['fakultas']),
                    'judul': str(row['judul']),
                    'dosen_pembimbing': str(row['dosen_pembimbing']),
                    'jurusan': str(row['jurusan']),
                    'tahun': str(row['tahun']),
                    'abstrak': str(row['abstrak'])
                }
            )
            points.append(point)
        
        # Upload ke Qdrant
        print(f'Uploading {len(points)} points to Qdrant...')
        self.qdrant_client.upsert(
            collection_name=self.collection_name,
            points=points,
            wait=True
        )
        print(f'Successfully ingested {len(points)} papers')
        
        return len(points)
    
    def search_similar(self, query_text: str, limit: int = 10, 
                       filters: Dict = None) -> List[Dict]:
        """
        Search papers mirip dengan query text
        
        Args:
            query_text: Judul atau deskripsi paper yang dicari
            limit: Jumlah hasil
            filters: Optional filters (e.g., jurusan, tahun)
        
        Returns:
            List of results dengan score dan metadata
        """
        # Generate query embedding
        query_embedding = self.model.encode(query_text)
        
        # Search di Qdrant
        results = self.qdrant_client.query_points(
            collection_name=self.collection_name,
            query=query_embedding.tolist(),
            limit=limit,
            query_filter=filters
        )
        
        # Format results
        output = []
        for result in results.points:
            output.append({
                'score': result.score,
                **result.payload
            })
        
        return output
    
    def get_collection_stats(self) -> Dict:
        """Get stats tentang collection"""
        collection_info = self.qdrant_client.get_collection(self.collection_name)
        return {
            'points_count': collection_info.points_count,
            'vector_size': collection_info.config.params.vectors.size,
            'distance': collection_info.config.params.vectors.distance
        }
    
    def get_all_papers(self, limit: int = 1000) -> List[Dict]:
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
