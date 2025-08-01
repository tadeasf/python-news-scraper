"""
NLP processing API routes for managing text analysis.
"""

from typing import Dict
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from ..services.nlp.nlp_service import nlp_service


router = APIRouter(prefix="/nlp", tags=["nlp"])


class ProcessArticleRequest(BaseModel):
    article_id: int


class ProcessBatchRequest(BaseModel):
    limit: int = 100


class NLPResponse(BaseModel):
    success: bool
    message: str
    data: Dict = {}


@router.post("/initialize", response_model=NLPResponse)
async def initialize_nlp():
    """Initialize the NLP processing pipeline."""
    try:
        await nlp_service.initialize()
        return NLPResponse(
            success=True,
            message="NLP pipeline initialized successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Initialization failed: {str(e)}")


@router.post("/process-article", response_model=NLPResponse)
async def process_single_article(request: ProcessArticleRequest):
    """Process a single article with NLP analysis."""
    try:
        success = await nlp_service.process_article(request.article_id)
        
        if success:
            return NLPResponse(
                success=True,
                message=f"Article {request.article_id} processed successfully"
            )
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"Failed to process article {request.article_id}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.post("/process-batch", response_model=NLPResponse)
async def process_article_batch(
    request: ProcessBatchRequest,
    background_tasks: BackgroundTasks
):
    """Process a batch of articles in the background."""
    try:
        # Add the task to background tasks
        background_tasks.add_task(nlp_service.process_topics_batch, request.limit)
        
        return NLPResponse(
            success=True,
            message=f"Started processing batch of {request.limit} articles in background"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start batch processing: {str(e)}")


@router.post("/reindex", response_model=NLPResponse)
async def reindex_all_articles(background_tasks: BackgroundTasks):
    """Reindex all articles for search."""
    try:
        background_tasks.add_task(nlp_service.reindex_all_articles)
        
        return NLPResponse(
            success=True,
            message="Started reindexing all articles in background"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start reindexing: {str(e)}")


@router.get("/status", response_model=NLPResponse)
async def get_nlp_status():
    """Get the current status of NLP processing."""
    try:
        stats = await nlp_service.get_processing_stats()
        
        return NLPResponse(
            success=True,
            message="NLP status retrieved successfully",
            data=stats
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.post("/analyze-text")
async def analyze_text(
    text: str,
    include_entities: bool = True,
    include_sentiment: bool = True,
    include_similarity: bool = False,
    comparison_text: str = None
):
    """Analyze arbitrary text with NLP tools."""
    try:
        if not nlp_service._initialized:
            await nlp_service.initialize()
        
        results = {}
        
        if include_entities:
            entities = nlp_service.czech_nlp.extract_entities(text)
            results["entities"] = entities
        
        if include_sentiment:
            sentiment = nlp_service.czech_nlp.analyze_sentiment(text)
            results["sentiment"] = sentiment
        
        if include_similarity and comparison_text:
            similarity = nlp_service.czech_nlp.get_semantic_similarity(text, comparison_text)
            results["similarity"] = {
                "score": similarity,
                "percentage": round(similarity * 100, 2),
                "comparison_text": comparison_text
            }
        
        # Add normalized text for search
        results["normalized_text"] = nlp_service.search_service.normalize_for_search(text)
        
        return {
            "success": True,
            "original_text": text,
            "analysis": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Text analysis failed: {str(e)}")


@router.get("/entities/types")
async def get_entity_types():
    """Get all available entity types."""
    return {
        "entity_types": [
            {"code": "PERSON", "name": "Osoby", "description": "Jména lidí"},
            {"code": "ORG", "name": "Organizace", "description": "Společnosti, instituce, organizace"},
            {"code": "GPE", "name": "Místa", "description": "Země, města, geografické lokace"},
            {"code": "MISC", "name": "Ostatní", "description": "Ostatní pojmenované entity"}
        ]
    }


@router.get("/sentiment/labels")
async def get_sentiment_labels():
    """Get all available sentiment labels."""
    return {
        "sentiment_labels": [
            {"code": "positive", "name": "Pozitivní", "description": "Pozitivní nálada textu"},
            {"code": "negative", "name": "Negativní", "description": "Negativní nálada textu"},
            {"code": "neutral", "name": "Neutrální", "description": "Neutrální nálada textu"}
        ]
    }