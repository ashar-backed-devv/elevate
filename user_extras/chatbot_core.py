import os
import re
import json
import time
import uuid
from tqdm import tqdm
import PyPDF2
import numpy as np
from langchain_core.documents import Document as LangChainDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pinecone import Pinecone, ServerlessSpec
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Configuration
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")  # Replace with your Pinecone API key
PINECONE_ENVIRONMENT = "us-east-1"  # Use your Pinecone environment
INDEX_NAME = "english-book-index"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
HF_MODEL_NAME = "BAAI/bge-large-en-v1.5"  # A good model for English text
DEFAULT_NAMESPACE = "default"  # Default namespace for general use

# Initialize Pinecone
pc = Pinecone(api_key=PINECONE_API_KEY)


from groq import Groq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Initialize the Groq client
client = Groq(
    api_key=GROQ_API_KEY  # Replace with your actual API key
)

# LLM function using Groq API
def llm( question):
    """Simulate the HuggingFacePipeline using Groq API."""
    prompt = f"Question: {question}"
    response = client.chat.completions.create(
        messages=[
            {"role": "user", "content": prompt}
        ],
        model="openai/gpt-oss-20b",
    )
    # Extract and return the content from the Groq API response
    return response.choices[0].message.content  # Adjust based on Groq's API response format

# memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
# Prompt template
prompt_template = """
Respond confidently,briefly , as if you already know everything, without referencing the document. Maintain a helpful tone.

You are a  helpful virtual assistant. Answer the user's questions based solely on the provided context. If the question is outside the scope of the information, politely reply: 'I'm sorry, I can't help with that. Is there anything else I can assist you with?'

Stay conversational and avoid mentioning documents or external sources in your responses.

{context}

<|user|>
{question}

<|assistant|>
"""


prompt = PromptTemplate(
    input_variables=["context", "question"],
    template=prompt_template,
)


llm_chain = prompt | llm | StrOutputParser()

def clean_text(text):
    """Clean and preprocess English text by removing irrelevant content."""
    # Remove page numbers
    text = re.sub(r'\n\s*\d+\s*\n', '\n', text)

    # Remove headers and footers (common patterns in books)
    text = re.sub(r'\n\s*[A-Z\s]+\s*\n', '\n', text)

    # Remove references to index, table of contents sections
    text = re.sub(r'(?i)index\s+\d+', '', text)
    text = re.sub(r'(?i)table\s+of\s+contents', '', text)

    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n\s*\n', '\n\n', text)

    # Remove non-alphabetic characters except punctuation
    text = re.sub(r'[^\w\s.,;:!?\'"-]', '', text)

    return text.strip()

def is_likely_index_or_toc(text):
    """Detect if a page is likely an index or table of contents."""
    # Check for patterns that suggest index or TOC
    if re.search(r'(?i)index|contents|appendix', text):
        return True

    # Check for patterns like "Topic........123" which are common in TOCs
    if re.search(r'\w+\s*\.{3,}\s*\d+', text):
        return True

    # Check for dense number patterns typical in indexes
    if len(re.findall(r'\d+', text)) > len(text.split()) / 5:  # If >20% of tokens are numbers
        return True

    return False

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF file excluding index and table of contents."""
    print(f"Extracting text from {pdf_path}...")

    pdf_reader = PyPDF2.PdfReader(pdf_path)
    num_pages = len(pdf_reader.pages)

    full_text = ""
    skipped_pages = []

    for page_num in tqdm(range(num_pages)):
        page = pdf_reader.pages[page_num]
        text = page.extract_text()

        if text and not is_likely_index_or_toc(text):
            full_text += text + "\n\n"
        else:
            skipped_pages.append(page_num + 1)

    print(f"Skipped {len(skipped_pages)} pages that appear to be index/TOC/irrelevant")

    return clean_text(full_text)

def split_document(text, metadata, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP):
    """Split document into chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""]
    )

    chunks = splitter.split_text(text)
    docs = []

    for i, chunk in enumerate(chunks):
        if len(chunk.strip()) > 50:  # Only keep chunks with substantial content
            docs.append({
                "id": f"{metadata['title']}-chunk-{i}",
                "content": chunk,
                "metadata": {**metadata, "chunk": i}
            })

    return docs

def embed_documents_in_pinecone(docs, index_name, namespace=None):
    """Embed documents in Pinecone using dense vector embeddings.

    Args:
        docs: List of document dictionaries
        index_name: Name of the Pinecone index
        namespace: Optional namespace for organizing documents (e.g., by book title)
    """
    # Use book title as namespace if not provided
    if namespace is None:
        # Try to get the title from the first document's metadata
        if docs and 'metadata' in docs[0] and 'title' in docs[0]['metadata']:
            namespace = docs[0]['metadata']['title']
        else:
            # Use default namespace with timestamp for uniqueness
            namespace = f"{DEFAULT_NAMESPACE}-{int(time.time())}"

    namespace = namespace.lower().replace(" ", "-")[:63]  # Ensure namespace is valid for Pinecone
    print(f"Using namespace: {namespace}")

    # Check if index exists, otherwise create it
    existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]

    if index_name not in existing_indexes:
        print(f"Creating new Pinecone index: {index_name}")
        pc.create_index(
            name=index_name,
            dimension=1024,  # Dimension size for BAAI/bge-large-en-v1.5
            metric="cosine",  # Changed from dotproduct to cosine for better similarity
            spec=ServerlessSpec(cloud="aws", region=PINECONE_ENVIRONMENT),
        )

        # Wait for index to be ready
        while not pc.describe_index(index_name).status["ready"]:
            time.sleep(1)

    # Initialize HuggingFace embeddings
    embedder = HuggingFaceEmbeddings(model_name=HF_MODEL_NAME)

    # Initialize Pinecone index
    index = pc.Index(index_name)

    # Extract content and metadata
    all_chunks = [doc["content"] for doc in docs]
    all_metadatas = [doc["metadata"] for doc in docs]
    all_ids = [doc["id"] for doc in docs]

    print(f"Embedding {len(all_chunks)} chunks into Pinecone namespace '{namespace}'...")

    # Create PineconeVectorStore with text_key to match data format
    vectorstore = PineconeVectorStore(
        index=index,
        embedding=embedder,
        namespace=namespace,
        text_key="content"  # Store text in 'content' field for consistency
    )

    # Add texts in batches to avoid memory issues
    batch_size = 100
    for i in tqdm(range(0, len(all_chunks), batch_size)):
        end_idx = min(i + batch_size, len(all_chunks))
        batch_chunks = all_chunks[i:end_idx]
        batch_metadata = all_metadatas[i:end_idx]
        batch_ids = all_ids[i:end_idx]

        vectorstore.add_texts(
            texts=batch_chunks,
            metadatas=batch_metadata,
            ids=batch_ids
        )

    print(f"Embedding completed in namespace '{namespace}'!")
    return vectorstore, namespace

def process_pdf_book(pdf_path, namespace=None):
    """Process a PDF book: extract text, split into chunks, and embed.

    Args:
        pdf_path: Path to the PDF file
        namespace: Optional namespace for storing in Pinecone
    """
    # Extract filename without extension for use as title
    filename = os.path.basename(pdf_path)
    title = os.path.splitext(filename)[0]
    print(f"Processing book: {title}")

    # Use title as namespace if not provided
    if namespace is None:
        namespace = title.lower().replace(" ", "-")

    # Extract and clean text from PDF
    text = extract_text_from_pdf(pdf_path)

    # Create metadata
    metadata = {
        "title": title,
        "source": pdf_path,
        "type": "book",
        "processed_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # Split document into chunks
    print(f"Splitting document into chunks (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})...")
    chunks = split_document(text, metadata)
    print(f"Created {len(chunks)} chunks from the book")



    # Create embeddings and store in Pinecone
    vs, used_namespace = embed_documents_in_pinecone(chunks, INDEX_NAME, namespace)

    # Save namespace information for later retrieval
    namespace_info = {
        "title": title,
        "namespace": used_namespace,
        "chunk_count": len(chunks),
        "processed_date": metadata["processed_date"]
    }

    # Save namespace info to a file


    return vs, used_namespace

def search_book(query, namespace=None, top_k=5):
    """Search the book using vector similarity search.

    Args:
        query: Search query string
        namespace: Optional namespace to search within (specific book)
        top_k: Number of results to return
    """
    # Initialize embeddings
    embedder = HuggingFaceEmbeddings(model_name=HF_MODEL_NAME)

    # Initialize Pinecone index
    index = pc.Index(INDEX_NAME)
    print(f'Searching in namespace: {namespace if namespace else "all namespaces"}')

    # Create vector store with text_key parameter to match existing data
    vectorstore = PineconeVectorStore(
        index=index,
        embedding=embedder,
        namespace=namespace,
        text_key="content"  # Use 'content' to match existing hybrid search data format
    )

    # Search using similarity search
    results = vectorstore.similarity_search(query, k=top_k)

    return results

def list_book_namespaces():
    """List all available book namespaces."""
    namespaces_file = "book_namespaces.json"
    if not os.path.exists(namespaces_file):
        print("No books have been processed yet.")
        return []

    with open(namespaces_file, "r") as f:
        try:
            namespaces = json.load(f)
            print("\nAvailable books:")
            for i, ns in enumerate(namespaces):
                print(f"{i+1}. {ns['title']} (Namespace: {ns['namespace']}, Chunks: {ns['chunk_count']})")
            return namespaces
        except json.JSONDecodeError:
            print("Error reading namespaces file.")
            return []


def delete_namespace(index_name, namespace_to_delete):
    """Delete a specific namespace from Pinecone and remove it from local record."""
    try:
        # Delete from Pinecone
        print(f"Deleting namespace '{namespace_to_delete}' from Pinecone index '{index_name}'...")
        index = pc.Index(index_name)
        index.delete(delete_all=True, namespace=namespace_to_delete)
        print("✅ Successfully deleted namespace data from Pinecone.")

        # Delete from local record


    except Exception as e:
        print(f"❌ Error deleting namespace: {e}")