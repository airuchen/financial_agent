from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Request body for POST /query."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The user's research query",
    )
    stream: bool = Field(
        default=True, description="Whether to stream the response via SSE"
    )


class Source(BaseModel):
    """A source reference from web search results."""

    title: str
    url: str
    snippet: str


class QueryResponse(BaseModel):
    """JSON response body for POST /query when stream=false."""

    response: str
    route: str
    sources: list[Source] = Field(default_factory=list)


class RouteDecision(BaseModel):
    """Structured output from the router node."""

    route: str = Field(..., description="Either 'search' or 'direct'")
    reasoning: str = Field(..., description="Why this route was chosen")
