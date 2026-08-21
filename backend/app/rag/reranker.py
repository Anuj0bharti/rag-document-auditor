"""Conservative score ordering hook for future cross-encoder reranking."""


def rerank(hits):
    """Keep vector scores deterministic until a local cross-encoder is configured."""
    return sorted(hits, key=lambda item: item[1], reverse=True)

