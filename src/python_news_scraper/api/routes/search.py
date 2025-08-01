"""
Advanced search API routes with NLP capabilities.
"""

from typing import List, Dict, Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from ..services.nlp.nlp_service import nlp_service
from ..services.nlp.advanced_search import advanced_search


router = APIRouter(prefix="/search", tags=["search"])


class SearchRequest(BaseModel):
    query: str
    source_filter: Optional[str] = None
    limit: int = 50
    offset: int = 0


class EntitySearchRequest(BaseModel):
    query: str
    entity_type: Optional[str] = None
    limit: int = 20


class TopicSearchRequest(BaseModel):
    query: str
    limit: int = 10


class SearchResponse(BaseModel):
    results: List[Dict]
    total_count: int
    query: str
    suggestions: List[str]


@router.post("/articles", response_model=SearchResponse)
async def search_articles(request: SearchRequest):
    """Search articles with advanced fuzzy and diacritic-insensitive search."""
    try:
        # Perform the search
        results = await advanced_search.search_articles(
            query=request.query,
            source_filter=request.source_filter,
            limit=request.limit,
            offset=request.offset
        )
        
        # Get search suggestions
        suggestions = await advanced_search.get_search_suggestions(request.query)
        
        return SearchResponse(
            results=results,
            total_count=len(results),  # Note: This is just the current page count
            query=request.query,
            suggestions=suggestions
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/entities", response_model=SearchResponse)
async def search_entities(request: EntitySearchRequest):
    """Search entities (people, places, organizations) with fuzzy matching."""
    try:
        results = await advanced_search.search_entities(
            query=request.query,
            entity_type=request.entity_type,
            limit=request.limit
        )
        
        suggestions = await advanced_search.get_search_suggestions(request.query)
        
        return SearchResponse(
            results=results,
            total_count=len(results),
            query=request.query,
            suggestions=suggestions
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Entity search failed: {str(e)}")


@router.post("/topics", response_model=SearchResponse)
async def search_topics(request: TopicSearchRequest):
    """Search topics with fuzzy matching."""
    try:
        results = await advanced_search.search_topics(
            query=request.query,
            limit=request.limit
        )
        
        suggestions = await advanced_search.get_search_suggestions(request.query)
        
        return SearchResponse(
            results=results,
            total_count=len(results),
            query=request.query,
            suggestions=suggestions
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Topic search failed: {str(e)}")


@router.get("/suggestions")
async def get_search_suggestions(
    query: str = Query(..., description="Partial search query"),
    limit: int = Query(5, description="Maximum number of suggestions")
):
    """Get search suggestions for autocomplete."""
    try:
        suggestions = await advanced_search.get_search_suggestions(query, limit)
        return {"suggestions": suggestions}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get suggestions: {str(e)}")


@router.get("/analyze/{topic}")
async def analyze_topic_coverage(topic: str):
    """Analyze how different news sources cover a specific topic."""
    try:
        analysis = await advanced_search.analyze_source_coverage(topic)
        
        if not analysis:
            raise HTTPException(status_code=404, detail="No coverage found for this topic")
        
        return {
            "topic": topic,
            "source_analysis": analysis,
            "total_sources": len(analysis)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/semantic-similarity")
async def calculate_semantic_similarity(
    text1: str = Query(..., description="First text"),
    text2: str = Query(..., description="Second text")
):
    """Calculate semantic similarity between two texts."""
    try:
        if not nlp_service._initialized:
            await nlp_service.initialize()
            
        similarity = nlp_service.czech_nlp.get_semantic_similarity(text1, text2)
        
        return {
            "text1": text1,
            "text2": text2,
            "similarity_score": similarity,
            "similarity_percentage": round(similarity * 100, 2)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Similarity calculation failed: {str(e)}")


@router.get("/stats")
async def get_search_stats():
    """Get search and NLP processing statistics."""
    try:
        stats = await nlp_service.get_processing_stats()
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")