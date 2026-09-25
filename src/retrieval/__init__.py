def __getattr__(name):
    if name in {"MiniLMEmbeddings"}:
        from .embeddings import MiniLMEmbeddings

        return MiniLMEmbeddings
    if name in {"LocalEmbeddingIndex", "SearchResult"}:
        from .index import LocalEmbeddingIndex, SearchResult

        return {"LocalEmbeddingIndex": LocalEmbeddingIndex, "SearchResult": SearchResult}[name]
    if name in {"AnswerResult", "answer_question"}:
        from .qa import AnswerResult, answer_question

        return {"AnswerResult": AnswerResult, "answer_question": answer_question}[name]
    if name in {"build_agent", "run_agent_question"}:
        from .agent import build_agent, run_agent_question

        return {"build_agent": build_agent, "run_agent_question": run_agent_question}[name]
    if name == "build_llm":
        from .llm import build_llm

        return build_llm
    raise AttributeError(name)
