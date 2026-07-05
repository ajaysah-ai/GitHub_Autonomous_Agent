"""
Hybrid RAG Tool Retriever
==========================
Kya karta hai:
    - `data/tools_registry.json` se saare tools ka meaningful "document"
      (name + description + keywords + example_goals) banata hai.
    - Do retrieval signals combine karta hai:
        1) BM25 (sparse / lexical match)      -> exact keyword overlap ke liye best
        2) TF-IDF cosine similarity (dense-ish)-> paraphrased / semantically close goals ke liye
    - Dono scores ko normalize karke weighted-sum se final "hybrid score" banata hai.
    - Top-k tools return karta hai jo prompt me dynamically inject honge.

Note on embeddings:
    Production me is TF-IDF component ko sentence-transformers / OpenAI-Groq embeddings
    + FAISS/Chroma se replace kiya ja sakta hai for true dense semantic search.
    Abhi sandbox me external model-download allowed nahi hai, isliye TF-IDF
    (pure scikit-learn, offline) use kiya hai — ye ek legitimate "vector search"
    signal hai (cosine similarity over a sparse-but-weighted vector space) aur
    interface badle bina baad me swap kiya ja sakta hai (see `embed_fn` param).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Callable, List, Dict, Any, Optional

import numpy as np
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall(text.lower())


def _tool_to_document(tool: Dict[str, Any]) -> str:
    """Ek tool ke saare metadata ko ek single searchable text blob me convert karo."""
    parts = [
        tool.get("name", ""),
        tool.get("title", ""),
        tool.get("description", ""),
        " ".join(tool.get("keywords", [])),
        " ".join(tool.get("example_goals", [])),
        tool.get("category", ""),
    ]
    return " ".join(p for p in parts if p)


class HybridToolRetriever:
    """
    BM25 + TF-IDF hybrid retriever over the tools registry.

    Usage:
        retriever = HybridToolRetriever(registry_path)
        top_tools = retriever.retrieve(goal="push my folder to github", top_k=5)
        prompt_block = retriever.format_tools_for_prompt(top_tools)
    """

    def __init__(
        self,
        registry_path: str | Path,
        alpha: float = 0.55,
        embed_fn: Optional[Callable[[List[str]], np.ndarray]] = None,
    ):
        """
        alpha: hybrid weighting -> final_score = alpha*bm25_norm + (1-alpha)*vector_norm
        embed_fn: optional pluggable dense-embedding function. If provided it overrides
                  the TF-IDF vector signal with real embeddings (e.g. sentence-transformers,
                  or a Groq/OpenAI embeddings endpoint) without changing any calling code.
        """
        self.registry_path = Path(registry_path)
        self.alpha = alpha
        self.embed_fn = embed_fn

        with open(self.registry_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.tools: List[Dict[str, Any]] = data["tools"]
        self.documents: List[str] = [_tool_to_document(t) for t in self.tools]

        # --- Sparse signal: BM25 ---
        tokenized_docs = [_tokenize(doc) for doc in self.documents]
        self.bm25 = BM25Okapi(tokenized_docs)

        # --- Vector signal: TF-IDF (swap-able for real embeddings via embed_fn) ---
        self.vectorizer = TfidfVectorizer()
        self.doc_matrix = self.vectorizer.fit_transform(self.documents)

        if self.embed_fn is not None:
            self.doc_embeddings = self.embed_fn(self.documents)
        else:
            self.doc_embeddings = None

    @staticmethod
    def _normalize(scores: np.ndarray) -> np.ndarray:
        if scores.size == 0:
            return scores
        lo, hi = scores.min(), scores.max()
        if hi - lo < 1e-9:
            return np.zeros_like(scores)
        return (scores - lo) / (hi - lo)

    def retrieve(
        self,
        goal: str,
        top_k: int = 6,
        min_score: float = 0.0,
        always_include: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Goal ke liye top_k relevant tools return karo (hybrid score se sorted).

        always_include: tool names jo hamesha result me force-included honge
                         (e.g. 'list_repos' jab bhi koi destructive/create action pooch rha ho,
                         kyunki system prompt me already ye rule hai: "pehle list_repos use karo").
        """
        if not goal or not goal.strip():
            goal = ""

        # BM25 score
        bm25_scores = np.array(self.bm25.get_scores(_tokenize(goal)))

        # Vector score
        if self.embed_fn is not None and self.doc_embeddings is not None:
            query_vec = self.embed_fn([goal])
            vector_scores = cosine_similarity(query_vec, self.doc_embeddings)[0]
        else:
            query_tfidf = self.vectorizer.transform([goal])
            vector_scores = cosine_similarity(query_tfidf, self.doc_matrix)[0]

        bm25_norm = self._normalize(bm25_scores)
        vector_norm = self._normalize(vector_scores)

        hybrid = self.alpha * bm25_norm + (1 - self.alpha) * vector_norm

        ranked_idx = np.argsort(-hybrid)

        results: List[Dict[str, Any]] = []
        seen = set()

        # Force-included tools first (still annotated with their real hybrid score)
        for name in always_include or []:
            for i, tool in enumerate(self.tools):
                if tool["name"] == name and name not in seen:
                    results.append({**tool, "_score": float(hybrid[i])})
                    seen.add(name)

        for i in ranked_idx:
            tool = self.tools[i]
            if tool["name"] in seen:
                continue
            if hybrid[i] < min_score:
                continue
            results.append({**tool, "_score": float(hybrid[i])})
            seen.add(tool["name"])
            if len(results) >= top_k:
                break

        # Always guarantee at least a small safe fallback set if nothing matched well
        if not results:
            results = [{**t, "_score": 0.0} for t in self.tools[:top_k]]

        return results

    @staticmethod
    def format_tools_for_prompt(tools: List[Dict[str, Any]]) -> str:
        """Retrieved tools ko exactly usi [Actions] bullet-format me render karo jo prompt expect karta hai."""
        lines = []
        for t in tools:
            params = ", ".join(f'"{k}": {v.split(" - ")[0]}' for k, v in t.get("parameters", {}).items())
            lines.append(
                f'- For {t["description"]} Name: {t["name"]}, Parameters: {{{params}}}'
            )
        return "\n".join(lines)
    
    @staticmethod
    def format_usage_guide() -> str:
        """
        Generates a user-facing bilingual guide explaining how to write a clear prompt
        for the LLM backend, avoiding technical parameter jargon.
        """
        return (
            "============================================================\n"
            "   HOW TO RE-WRITE YOUR PROMPT / APNA PROMPT KAISE LIKHEIN  \n"
            "============================================================\n\n"
            "[ENGLISH - How to reply]\n"
            "- Be Specific: Mention the exact folder name or file name you want to work on.\n"
            "- Clear Action: Clearly state if you want to create, delete, upload (push), or clone (pull).\n"
            "- GitHub Target: If you are working with GitHub, always write the exact repository name.\n"
            "👉 Example: \"Please push my local folder 'my_python_app' to my GitHub repo named 'test-project'\"\n\n"
            "------------------------------------------------------------\n\n"
            "[HINDI/HINGLISH - Kaise jawab dein]\n"
            "- Saaf-Saaf Batayein: Aap jis folder ya file par kaam karna chahte hain, uska sahi naam likhein.\n"
            "- Sahi Action Likhein: Saaf batayein ki aap naya banana chahte hain (create), purana mitana chahte hain (delete),\n"
            "  upload karna chahte hain (push), ya download karna chahte hain (pull).\n"
            "- GitHub Ki Detail: Agar aap GitHub ka kaam kar rahe hain, toh repository ka sahi naam zaroor likhein.\n"
            "👉 Sahi Tarika: \"Mera local folder 'my_python_app' mere GitHub repo 'test-project' me push kar do.\"\n"
            "============================================================"
        )