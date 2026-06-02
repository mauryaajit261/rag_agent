from pinecone import Pinecone
from config import settings

def check_pinecone_stats():
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    index = pc.Index(settings.PINECONE_INDEX_NAME)
    stats = index.describe_index_stats()
    print("=" * 60)
    print(f"Pinecone Index Stats: {settings.PINECONE_INDEX_NAME}")
    print("=" * 60)
    print(stats)
    print("=" * 60)

if __name__ == "__main__":
    check_pinecone_stats()
