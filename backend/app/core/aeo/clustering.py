"""Topic clustering & Q&A mapping: group related questions, emit an FAQ layout."""
from __future__ import annotations

from collections import Counter

from app.core.aeo.vectorize import content_tokens, cosine_similarity, tfidf_vectors
from app.models.aeo import (
    ClusterMapRequest,
    ClusterMapResult,
    FaqEntry,
    PageRef,
    QuestionCluster,
)
from app.utils.text import tokenize

_ANSWER_TEMPLATE = (
    "Open with a direct answer to \"{q}\" in one sentence of 40 words or fewer, "
    "then add one supporting fact or statistic, and close with a link to a deeper resource."
)


def cluster_questions(questions: list[str], threshold: float = 0.25) -> list[QuestionCluster]:
    """Greedy single-pass clustering over TF-IDF cosine similarity.

    Each question joins the existing cluster whose members it most resembles
    (average pairwise similarity >= ``threshold``) or starts a new cluster.
    Deterministic: input order decides tie-breaks, no randomness anywhere.
    """
    cleaned = [q.strip() for q in questions if q.strip()]
    if not cleaned:
        return []

    vectors = tfidf_vectors([content_tokens(q) for q in cleaned])
    cluster_indices: list[list[int]] = []
    for i in range(len(cleaned)):
        best_cluster, best_sim = None, 0.0
        for cluster in cluster_indices:
            sim = sum(cosine_similarity(vectors[i], vectors[j]) for j in cluster) / len(cluster)
            if sim >= threshold and sim > best_sim:
                best_cluster, best_sim = cluster, sim
        if best_cluster is None:
            cluster_indices.append([i])
        else:
            best_cluster.append(i)

    clusters: list[QuestionCluster] = []
    for indices in cluster_indices:
        members = [cleaned[i] for i in indices]
        term_counts: Counter[str] = Counter()
        for i in indices:
            term_counts.update(content_tokens(cleaned[i]))
        # Counter.most_common breaks count-ties by insertion order -> deterministic.
        label = " ".join(term for term, _ in term_counts.most_common(2)) or members[0]
        clusters.append(
            QuestionCluster(label=label, primary_question=members[0], questions=members)
        )
    return clusters


def _map_target_page(cluster: QuestionCluster, pages: list[PageRef]) -> str | None:
    """Pick the page whose title/URL tokens best overlap the cluster's terms."""
    cluster_terms = set(content_tokens(cluster.primary_question)) | set(cluster.label.split())
    best_url, best_overlap = None, 0
    for page in pages:
        page_terms = set(tokenize(page.title)) | set(tokenize(page.url))
        overlap = len(cluster_terms & page_terms)
        if overlap > best_overlap:
            best_url, best_overlap = page.url, overlap
    if best_url is not None:
        return best_url
    # No matching page: suggest a new answer page for the cluster topic.
    slug = "-".join(tokenize(cluster.label)) or "answers"
    return f"/answers/{slug}"


def build_cluster_map(req: ClusterMapRequest) -> ClusterMapResult:
    """Cluster ``req.questions`` and emit a structured FAQ layout.

    Each cluster becomes one FAQ entry: the primary question, a concise
    answer-writing template, and a target page (best-matching existing page,
    or a suggested ``/answers/<slug>`` URL when nothing matches).
    """
    clusters = cluster_questions(req.questions, threshold=req.similarity_threshold)
    faq = [
        FaqEntry(
            question=cluster.primary_question,
            answer_template=_ANSWER_TEMPLATE.format(q=cluster.primary_question),
            target_page=_map_target_page(cluster, req.pages),
        )
        for cluster in clusters
    ]
    return ClusterMapResult(clusters=clusters, faq=faq)
