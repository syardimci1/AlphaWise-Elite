"""LlamaIndex'in mevcut ChromaDB koleksiyonunu okuyabildigini dogrular."""
import chromadb, os
try:
    c = chromadb.HttpClient(host=os.getenv("CHROMA_HOST","chromadb"), port=8000)
    cols = c.list_collections()
    print(f"Mevcut RAG (ChromaDB): {len(cols)} koleksiyon", flush=True)
    for col in cols:
        print(f"  - {col.name}: {c.get_collection(col.name).count():,} dokuman", flush=True)
    from llama_index.vector_stores.chroma import ChromaVectorStore
    if cols:
        ChromaVectorStore(chroma_collection=c.get_collection(cols[0].name))
        print(f"\nLlamaIndex AYNI koleksiyona baglandi -> veri tasimaya GEREK YOK", flush=True)
        print(f"SONUC: karsilastirma icin ayni veri uzerinde calisilabilir", flush=True)
except Exception as e:
    print(f"HATA: {type(e).__name__}: {e}", flush=True)
