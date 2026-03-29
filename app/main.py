import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import Settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the agent graph on startup.

    Creates the LLM client, search tool, and compiled graph,
    storing them on app.state for route handlers to access.
    """
    settings = Settings()

    from app.llm import create_llm

    llm = create_llm(settings)

    from tavily import AsyncTavilyClient

    tavily_client = AsyncTavilyClient(api_key=settings.tavily_api_key)

    from app.agent.graph import build_graph

    app.state.graph = build_graph(llm, tavily_client)
    app.state.provider = settings.llm_provider

    logger.info(
        "Agent ready — provider=%s, model=%s",
        settings.llm_provider,
        settings.llm_model,
    )
    yield


def create_app(use_lifespan: bool = False) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        use_lifespan: If True, attach the lifespan handler that initializes
            the real LLM and search tool. False for testing.

    Returns:
        Configured FastAPI app with CORS and routes.
    """
    application = FastAPI(
        title="Financial Research Agent API",
        description="LLM-powered Internet-Search Agent for financial research",
        version="0.1.0",
        lifespan=lifespan if use_lifespan else None,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(router)
    return application


app = create_app(use_lifespan=True)
