from sqlalchemy.orm import Session
from .retriever import retrieve
from .llm import get_llm
from .reranker import rerank
from .context_builder import build_context


def answer_question(db: Session, workspace_id: str, question: str):
    hits = rerank(retrieve(db, workspace_id, question))
    if not hits:
        return "I couldn't find sufficient evidence in the uploaded documents to answer this question.", []
    context = build_context(hits)
    answer = get_llm().answer(question, context)
    return answer, hits
