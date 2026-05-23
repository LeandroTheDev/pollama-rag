from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

app = FastAPI()
OLLAMA_URL = "http://host.containers.internal:11434"

embed_model = OllamaEmbedding(model_name="nomic-embed-text", base_url=OLLAMA_URL, request_timeout=None)
llm = Ollama(model="qwen3.5:4b", base_url=OLLAMA_URL, request_timeout=None, context_window=4096)

chroma_client = chromadb.HttpClient(host="host.containers.internal", port=8001)
collection = chroma_client.get_or_create_collection("documents")
vector_store = ChromaVectorStore(chroma_collection=collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)
index = VectorStoreIndex.from_vector_store(vector_store, embed_model=embed_model)
query_engine = index.as_query_engine(llm=llm, similarity_top_k=2)
streaming_engine = index.as_query_engine(llm=llm, similarity_top_k=2, streaming=True)

class AskRequest(BaseModel):
    question: str

@app.post("/ask")
def ask(req: AskRequest):
    response = query_engine.query(req.question)
    return {"answer": str(response)}

@app.post("/ask/stream")
def ask_stream(req: AskRequest):
    response = streaming_engine.query(req.question)
    def generate():
        for token in response.response_gen:
            yield token
    return StreamingResponse(generate(), media_type="text/plain")

@app.post("/ingest")
def ingest():
    docs = SimpleDirectoryReader("/app/documents").load_data()
    for doc in docs:
        index.insert(doc)
    return {"ingested": len(docs)}

@app.get("/health")
def health():
    return {"status": "ok"}
