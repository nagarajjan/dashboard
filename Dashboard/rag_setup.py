import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms import Ollama
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA

def create_rag_chain(document_path: str):
    """
    Creates a RetrievalQA chain using Llama 3.1 from a PDF document.
    """
    # 1. Load the PDF document
    loader = PyPDFLoader(document_path)
    documents = loader.load()

    # 2. Split the documents into chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    texts = text_splitter.split_documents(documents)

    # 3. Create vector store from chunks and persist it
    embeddings = OllamaEmbeddings(model="llama3.1")
    vectorstore = Chroma.from_documents(documents=texts, embedding=embeddings)

    # 4. Create a retriever from the vector store
    retriever = vectorstore.as_retriever()

    # 5. Connect to the Llama 3.1 model via Ollama
    llm = Ollama(model="llama3.1")

    # 6. Create a RetrievalQA chain
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
    )
    return qa_chain

if __name__ == '__main__':
    # This is a test run to ensure the RAG system works
    if not os.path.exists("external_doc.pdf"):
        print("Please place your PDF document named 'external_doc.pdf' in the same directory.")
    else:
        rag_chain = create_rag_chain("external_doc.pdf")
        question = "What was the main topic of the document?"
        response = rag_chain.invoke({"query": question})
        print(response['result'])
