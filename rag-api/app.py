from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.fastembed import FastEmbedEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb, os, json, logging, time

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("rag-api")

app = FastAPI()
OLLAMA_URL = "http://host.containers.internal:11434"
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen3.5:4b")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")

embed_model = FastEmbedEmbedding(model_name=EMBED_MODEL)
llm = Ollama(model=LLM_MODEL, base_url=OLLAMA_URL, request_timeout=99999.0, context_window=32768, is_function_calling_model=False, thinking=False)

chroma_client = chromadb.HttpClient(host="host.containers.internal", port=8001)
collection = chroma_client.get_or_create_collection("documents")
vector_store = ChromaVectorStore(chroma_collection=collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)
index = VectorStoreIndex.from_vector_store(vector_store, embed_model=embed_model)
query_engine = index.as_query_engine(llm=llm, similarity_top_k=2)

class AskRequest(BaseModel):
    question: str

@app.post("/ask")
def ask(req: AskRequest):
    response = query_engine.query(req.question)
    return {"answer": str(response)}

def event(type, **kwargs):
    return json.dumps({"type": type, **kwargs}) + "\n"

@app.post("/ask/stream")
def ask_stream(req: AskRequest):
    def generate():
        log.info("=== NEW REQUEST: %r", req.question[:80])
        t0 = time.time()

        yield event("status", step="Embedding query", pct=20)
        log.debug("Retrieving nodes from ChromaDB...")
        retriever = index.as_retriever(similarity_top_k=2)
        nodes = retriever.retrieve(req.question)
        log.info("Retrieved %d node(s) in %.2fs", len(nodes), time.time() - t0)
        for i, n in enumerate(nodes):
            log.debug("  node[%d]: score=%.4f len=%d chars", i, n.score or 0, len(n.get_content()))

        yield event("status", step="Generating response", pct=60)
        context = "\n\n".join(n.get_content() for n in nodes)
        prompt = f"Context:\n{context}\n\nQuestion: {req.question}\nAnswer in the same language as the question:"
        log.info("Prompt length: %d chars. Calling llm.stream_complete...", len(prompt))

        token_count = 0
        t_first = None
        try:
            for chunk in llm.stream_complete(prompt):
                if chunk.delta:
                    if t_first is None:
                        t_first = time.time()
                        log.info("First token received after %.2fs", t_first - t0)
                    token_count += 1
                    yield event("token", text=chunk.delta)
                else:
                    log.debug("Empty chunk received (delta is falsy): %r", chunk)
        except Exception as e:
            log.error("stream_complete raised an exception: %s", e, exc_info=True)
            return

        log.info("Stream finished: %d token(s), total %.2fs", token_count, time.time() - t0)
        if token_count == 0:
            log.warning("NO TOKENS were generated — model returned empty response")
        yield event("done")
    return StreamingResponse(generate(), media_type="application/x-ndjson")

@app.post("/ingest")
def ingest():
    docs = SimpleDirectoryReader(
        "/app/documents",
        recursive=True,
        exclude=["*.swp", "*.kate-swp", ".*"],
    ).load_data()
    for doc in docs:
        index.insert(doc)
    return {"ingested": len(docs)}

@app.get("/health")
def health():
    return {"status": "ok"}
