from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb, os, json

app = FastAPI()
OLLAMA_URL = "http://host.containers.internal:11434"
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen3.5:4b")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")

embed_model = OllamaEmbedding(model_name=EMBED_MODEL, base_url=OLLAMA_URL, request_timeout=99999.0)
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
        yield event("status", step="Searching documents", pct=60)
        from llama_index.core.response_synthesizers import get_response_synthesizer
        synthesizer = get_response_synthesizer(llm=llm, streaming=True)
        yield event("status", step="Generating response", pct=80)
        response = synthesizer.synthesize(req.question, nodes=nodes)
        for token in response.response_gen:
            if token:
                yield event("token", text=token)
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
