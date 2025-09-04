import numpy as np
from qdrant_client.http import models as qm
from embed import clip_text_embed, text_embed
from qdrant import qc

def search_multimodal(query, k=30):
    v_clip = clip_text_embed(query)
    v_text = text_embed(query)

    vis = qc.search("visual_512", query_vector=v_clip, limit=k, with_payload=True)
    txt = qc.search("text_1536",  query_vector=v_text, limit=k, with_payload=True)

    # score normalization (min-max per list)
    def norm(scores):
        a, b = min(scores), max(scores)
        return [(s - a)/(b - a + 1e-9) for s in scores]

    vis_scores = norm([h.score for h in vis])  # cosine sim already, higher is better in client
    txt_scores = norm([h.score for h in txt])

    # fuse by ID (collection scoped); keep provenance
    pool = []
    for h,ns in zip(vis, vis_scores):
        pool.append({"col":"visual_512","id":h.id,"score_v":ns,"score_t":0.0,"payload":h.payload})
    for h,ns in zip(txt, txt_scores):
        pool.append({"col":"text_1536","id":h.id,"score_v":0.0,"score_t":ns,"payload":h.payload})

    # combined score: tune weights; start 0.5/0.5
    for p in pool:
        p["score"] = 0.5*p["score_v"] + 0.5*p["score_t"]

    # (optional) MMR over a common 512-d or 1536-d space:
    # quick hack: for MMR diversity use payload['type']/domain clustering or fetch vectors back if needed

    pool.sort(key=lambda x: x["score"], reverse=True)
    return pool[:k]