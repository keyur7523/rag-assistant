from pathlib import Path
from sentence_transformers import SentenceTransformer
import chromadb

textDictionary = {}
chunkDictionary = {}
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
chroma_client = chromadb.PersistentClient('db')

files = [p for p in Path().glob("docs/*.md")]

# files chunking
def chunkGenerator(text, words, overlap):
    chunks = []
    wordsList = text.split()
    totalWords = len(wordsList)
    i, endloop = 0, 0
    while not endloop:
        start = i * (words-overlap)
        end = start + words
        if end >= totalWords:
            endloop = 1
            end = totalWords
#        print(f'start={start} end={end}')
        chunks.append(' '.join(wordsList[start: end]))
        i += 1
    return chunks

# files reading
for f in files:
    with (f.open('r') as file):
        textDictionary[f.name] = file.read()
        chunkDictionary[f.name] = chunkGenerator(textDictionary[f.name], words = 50, overlap = 10)
#        print(chunkDictionary)

# files encoding
embeddingsDict = {}
for (f, chunk) in chunkDictionary.items():
    embeddingsDict[f] = model.encode(chunk)
    print(embeddingsDict[f].shape)

# creating chroma vector database
collection = chroma_client.get_or_create_collection(name="policies")

# Flattening the data: ids, embeddings, documents, metadata
ids = []
embeddings = []
documents = []
metadatas = []

for (f, chunks) in chunkDictionary.items():
    for i in range(len(chunks)):
        ids.append(f'{f[:len(f)-3]}-{i}')
        embeddings.append(embeddingsDict[f][i])
        documents.append(chunks[i])
        metadatas.append({"source": f})

# adding data to collections
collection.add(
    ids=ids,
    embeddings=embeddings,
    documents=documents,
    metadatas=metadatas,
)

print(collection.count())




