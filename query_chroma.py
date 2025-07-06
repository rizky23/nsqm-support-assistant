from chromadb import PersistentClient

# 1. Inisialisasi client baru (tanpa Settings)
client = PersistentClient(path="./chroma_db")  # path ke folder chroma kamu

# 2. Ambil koleksi
collection = client.get_collection(name="complaint_knowledge")

# 3. Query ke koleksi
results = collection.query(
    query_texts=["Apa itu DSC?"],
    n_results=1
)

# 4. Tampilkan hasil
print("\n📄 Hasil pencarian:")
print(results['documents'][0][0])
