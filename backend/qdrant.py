from qdrant_client import QdrantClient
from qdrant_client.http import models as qm
qc = QdrantClient(host="localhost", port=6333)

def ensure(name, dim):
    try: 
      qc.get_collection(name)
    except:
      qc.recreate_collection(
            name,
            vectors_config=qm.VectorParams(size=dim, distance=qm.Distance.COSINE)
      )

ensure("visual_512", 512)
ensure("text_1536", 1536)