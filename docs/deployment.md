# Deployment Architecture

## Production AWS Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              AWS Cloud                                   │
│                                                                          │
│  Route53 → CloudFront (CDN/TLS) → ALB (HTTPS termination)              │
│                                      │                                   │
│                    ┌─────────────────────────────────────┐              │
│                    │        ECS Cluster (Fargate)         │              │
│                    │                                      │              │
│                    │  ┌──────────────────────────────┐   │              │
│                    │  │ API Service (auto-scale 2-10) │   │              │
│                    │  │ FastAPI tasks (CPU)            │   │              │
│                    │  └──────────┬───────────────────┘   │              │
│                    │             │                        │              │
│                    │  ┌──────────▼───────────────────┐   │              │
│                    │  │ Ollama Service (optional)     │   │              │
│                    │  │ GPU instances (g5.xlarge)     │   │              │
│                    │  │ Only when LLM_PROVIDER=ollama │   │              │
│                    │  └──────────────────────────────┘   │              │
│                    └─────────────────────────────────────┘              │
│                                                                          │
│  ElastiCache (Redis)     CloudWatch + X-Ray     Secrets Manager         │
│  - Response caching      - Logs, metrics        - TAVILY_API_KEY        │
│  - Rate limiting         - Latency P50/95/99    - OPENAI_API_KEY        │
│                          - GPU utilization                               │
│                          - Alarms → SNS                                  │
│                                                                          │
│  ECR (container registry)                                                │
└─────────────────────────────────────────────────────────────────────────┘

External: Tavily API, OpenAI API (when LLM_PROVIDER=openai)
```

## Scalability
- API tasks auto-scale on CPU/request count (2-10 tasks)
- Ollama tasks scale on GPU utilization (when used)
- Redis caches repeated queries to reduce LLM/search load
- ALB distributes SSE connections with sticky sessions

## Reliability
- Multi-AZ deployment for all services
- Health checks with automatic task replacement
- CloudWatch alarms → SNS for alerting
- Circuit breaker on external APIs (Tavily, OpenAI)

## Security
- TLS termination at CloudFront and ALB
- API keys stored in AWS Secrets Manager
- ECS tasks run in private subnets (no public IPs)
- WAF on CloudFront for rate limiting and DDoS protection

## Observability
- CloudWatch Logs for structured application logs
- X-Ray for distributed tracing across API → LLM → Search
- Custom CloudWatch metrics: query latency, route distribution, cache hit rate
- Dashboards for GPU utilization and model inference throughput
