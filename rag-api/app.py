from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.fastembed import FastEmbedEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb, os, json

app = FastAPI()
OLLAMA_URL = "http://host.containers.internal:11434"
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen3.5:4b")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")

embed_model = FastEmbedEmbedding(model_name=EMBED_MODEL)
llm = Ollama(model=LLM_MODEL, base_url=OLLAMA_URL, request_timeout=99999.0, context_window=4096, additional_kwargs={"think": False})

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
        yield event("status", step="Embedding query", pct=20)
        retriever = index.as_retriever(similarity_top_k=2)
        nodes = retriever.retrieve(req.question)
        yield event("status", step="Generating response", pct=60)
        context = "\n\n".join(n.get_content() for n in nodes)
        prompt = f"Context:\n{context}\n\nQuestion: {req.question}\nAnswer in the same language as the question:"
        for chunk in llm.stream_complete(prompt):
            if chunk.delta:
                yield event("token", text=chunk.delta)
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
