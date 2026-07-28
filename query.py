import chromadb
from sentence_transformers import SentenceTransformer
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()
chroma_client = chromadb.PersistentClient('db')
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
collection = chroma_client.get_collection(name="policies") 

def retrieval_query(question):
    questionVector = model.encode(question)
    response = collection.query(query_embeddings=[questionVector], n_results=3)
    context = ' '.join([f"{response['documents'][i][j]} source: {response['metadatas'][i][j]['source']}" for i in range(len(response['documents'])) for j in range(len(response['documents'][i]))])
    return context

if __name__ == '__main__':
    question = 'How long do I have to return an item?'
    context = retrieval_query(question)
    message = client.messages.create(
    max_tokens=1024,
    messages=[
            {
                "role": "user",
                "content": f"""
                                {context}, Answer using only the context above, cite the source file(s) the answer came from, and if the answer isn't in the context, say you don't know rather than guessing. 
                                Question: {question}
                            """,
            }
        ],
        model="claude-opus-4-8",
        )

    for block in message.content:
        if block.type == "text":
            print(block.text)



