"""
Czech NLP pipeline for text analysis using multilingual models and Czech-specific tools.
"""

import json
from typing import List, Dict, Tuple, Optional
from datetime import datetime

import spacy
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.cluster import KMeans
import unidecode
import re

from loguru import logger


class CzechNLPPipeline:
    """Czech language NLP pipeline with sentiment analysis, entity recognition, and topic modeling."""
    
    def __init__(self):
        self.nlp = None
        self.sentiment_pipeline = None
        self.sentence_model = None
        self.vectorizer = None
        self.lda_model = None
        self._initialized = False
        
    async def initialize(self):
        """Initialize all NLP models - this can take a while on first run."""
        if self._initialized:
            return
            
        logger.info("Initializing Czech NLP pipeline...")
        
        try:
            # Load multilingual spaCy model (works well for Czech)
            try:
                self.nlp = spacy.load("xx_ent_wiki_sm")
            except OSError:
                logger.warning("xx_ent_wiki_sm not found, using blank model")
                self.nlp = spacy.blank("cs")
                
            # Initialize multilingual sentiment analysis
            # Using a multilingual model that should work with Czech
            self.sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model="cardiffnlp/twitter-xlm-roberta-base-sentiment",
                return_all_scores=True
            )
            
            # Initialize sentence transformer for semantic similarity
            self.sentence_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            
            # Initialize text preprocessing tools
            self.vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words=None,  # We'll handle Czech stop words manually
                ngram_range=(1, 2),
                min_df=2
            )
            
            self.lda_model = LatentDirichletAllocation(
                n_components=10,
                random_state=42,
                max_iter=10
            )
            
            self._initialized = True
            logger.info("Czech NLP pipeline initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize NLP pipeline: {e}")
            raise
    
    def normalize_czech_text(self, text: str) -> str:
        """Normalize Czech text for better fuzzy matching."""
        # Remove diacritics for search
        normalized = unidecode.unidecode(text.lower())
        # Clean up extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized
    
    def extract_entities(self, text: str) -> List[Dict]:
        """Extract named entities from Czech text."""
        if not self._initialized:
            raise RuntimeError("NLP pipeline not initialized")
            
        doc = self.nlp(text)
        entities = []
        
        for ent in doc.ents:
            entities.append({
                "text": ent.text,
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char,
                "confidence": getattr(ent, 'conf', 0.8)  # Default confidence
            })
            
        # Add some Czech-specific entity patterns
        entities.extend(self._extract_czech_patterns(text))
        
        return entities
    
    def _extract_czech_patterns(self, text: str) -> List[Dict]:
        """Extract Czech-specific patterns like Czech names, places, etc."""
        entities = []
        
        # Czech name patterns (common Czech surnames)
        czech_surnames = [
            r'\b\w+ová\b',  # Female surnames ending in -ová
            r'\b\w+ský\b',  # Male surnames ending in -ský
            r'\b\w+ka\b',   # Some common endings
        ]
        
        for pattern in czech_surnames:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities.append({
                    "text": match.group(),
                    "label": "PERSON",
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.6
                })
        
        # Czech place patterns
        czech_places = [
            r'\bPraha\b', r'\bBrno\b', r'\bOstrava\b', r'\bPlzeň\b',
            r'\bÚstí nad Labem\b', r'\bOlomouc\b', r'\bLiberec\b',
            r'\bČeské Budějovice\b', r'\bHradec Králové\b', r'\bPardubice\b'
        ]
        
        for pattern in czech_places:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities.append({
                    "text": match.group(),
                    "label": "GPE",
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.9
                })
        
        return entities
    
    def analyze_sentiment(self, text: str) -> Dict:
        """Analyze sentiment of Czech text."""
        if not self._initialized:
            raise RuntimeError("NLP pipeline not initialized")
            
        try:
            # Use the multilingual sentiment model
            results = self.sentiment_pipeline(text[:512])  # Limit length for model
            
            # Convert to our format
            sentiment_scores = {}
            for result in results[0]:  # results is a list with one element
                sentiment_scores[result['label'].lower()] = result['score']
                
            # Determine primary sentiment
            primary_sentiment = max(sentiment_scores.items(), key=lambda x: x[1])
            
            # Convert to -1 to 1 scale
            if primary_sentiment[0] == 'positive':
                sentiment_score = primary_sentiment[1]
            elif primary_sentiment[0] == 'negative':
                sentiment_score = -primary_sentiment[1]
            else:  # neutral
                sentiment_score = 0.0
                
            return {
                "sentiment_label": primary_sentiment[0],
                "sentiment_score": sentiment_score,
                "emotion_scores": sentiment_scores,
                "subjectivity": self._calculate_subjectivity(text)
            }
            
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return {
                "sentiment_label": "neutral",
                "sentiment_score": 0.0,
                "emotion_scores": {},
                "subjectivity": 0.5
            }
    
    def _calculate_subjectivity(self, text: str) -> float:
        """Calculate subjectivity score (simple heuristic)."""
        # This is a simple heuristic - could be improved with proper Czech linguistic analysis
        subjective_words = [
            'myslím', 'věřím', 'cítím', 'zdá se', 'možná', 'pravděpodobně',
            'určitě', 'rozhodně', 'bohužel', 'naštěstí', 'skvěle', 'hrozně'
        ]
        
        text_lower = text.lower()
        subjective_count = sum(1 for word in subjective_words if word in text_lower)
        total_words = len(text.split())
        
        return min(subjective_count / max(total_words, 1) * 10, 1.0)
    
    def discover_topics(self, texts: List[str], n_topics: int = 5) -> Dict:
        """Discover topics using LDA and return topic information."""
        if not self._initialized:
            raise RuntimeError("NLP pipeline not initialized")
            
        if len(texts) < 2:
            return {"topics": [], "document_topics": []}
            
        try:
            # Preprocess texts
            processed_texts = [self._preprocess_for_topics(text) for text in texts]
            
            # Fit vectorizer and LDA
            tfidf_matrix = self.vectorizer.fit_transform(processed_texts)
            
            # Update LDA with the right number of components
            if n_topics != self.lda_model.n_components:
                self.lda_model = LatentDirichletAllocation(
                    n_components=min(n_topics, len(texts)),
                    random_state=42,
                    max_iter=10
                )
            
            lda_matrix = self.lda_model.fit_transform(tfidf_matrix)
            
            # Extract topics
            feature_names = self.vectorizer.get_feature_names_out()
            topics = []
            
            for topic_idx, topic in enumerate(self.lda_model.components_):
                top_words_idx = topic.argsort()[-10:][::-1]
                top_words = [feature_names[i] for i in top_words_idx]
                
                topics.append({
                    "id": topic_idx,
                    "name": f"Topic_{topic_idx}",
                    "keywords": top_words,
                    "top_keywords": top_words[:5]
                })
            
            # Get document-topic assignments
            document_topics = []
            for doc_idx, doc_topics in enumerate(lda_matrix):
                top_topic_idx = np.argmax(doc_topics)
                document_topics.append({
                    "document_id": doc_idx,
                    "topic_id": top_topic_idx,
                    "relevance_score": doc_topics[top_topic_idx]
                })
            
            return {
                "topics": topics,
                "document_topics": document_topics
            }
            
        except Exception as e:
            logger.error(f"Topic discovery failed: {e}")
            return {"topics": [], "document_topics": []}
    
    def _preprocess_for_topics(self, text: str) -> str:
        """Preprocess text for topic modeling."""
        # Basic Czech preprocessing
        text = text.lower()
        
        # Remove punctuation and extra whitespace
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        # Remove very common Czech stop words
        czech_stopwords = {
            'a', 'aby', 'ale', 'ani', 'až', 'být', 'co', 'do', 'i', 'ich', 'je', 'jak',
            'jako', 'její', 'jeho', 'jen', 'již', 'ji', 'jsme', 'jsou', 'když', 'má',
            'my', 'na', 'nebo', 'není', 'o', 'po', 'pro', 's', 'se', 'si', 'tak',
            'také', 'te', 'to', 'tu', 'už', 'v', 've', 'za', 'ze', 'že'
        }
        
        words = [word for word in text.split() if word not in czech_stopwords and len(word) > 2]
        return ' '.join(words)
    
    def get_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts."""
        if not self._initialized:
            raise RuntimeError("NLP pipeline not initialized")
            
        try:
            embeddings = self.sentence_model.encode([text1, text2])
            similarity = np.dot(embeddings[0], embeddings[1]) / (
                np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
            )
            return float(similarity)
        except Exception as e:
            logger.error(f"Semantic similarity calculation failed: {e}")
            return 0.0
    
    def cluster_articles(self, texts: List[str], n_clusters: int = 5) -> List[int]:
        """Cluster articles using semantic embeddings."""
        if not self._initialized:
            raise RuntimeError("NLP pipeline not initialized")
            
        if len(texts) < n_clusters:
            return list(range(len(texts)))
            
        try:
            embeddings = self.sentence_model.encode(texts)
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            clusters = kmeans.fit_predict(embeddings)
            return clusters.tolist()
        except Exception as e:
            logger.error(f"Article clustering failed: {e}")
            return list(range(len(texts)))


# Global instance
czech_nlp = CzechNLPPipeline()