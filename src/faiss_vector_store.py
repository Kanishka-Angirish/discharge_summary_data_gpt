import os.path

import faiss
import pandas as pd

from embedding_generator import EmbeddingGenerator
from utils import logger, vector_paths
import json


class FaissVectorStore:

    def __init__(self, embedding_generator: EmbeddingGenerator) -> None:
        self.embedding_generator = embedding_generator

        if os.path.exists(vector_paths['faiss_index']):
            # Referring to the updated Vector Store
            self.index = faiss.read_index(vector_paths['faiss_index'])
        else:
            self.index = faiss.IndexFlatL2(embedding_generator.model.config.hidden_size)

        if os.path.exists(vector_paths['data_store']):
            self.data_store = pd.read_csv(vector_paths['data_store'])
        else:
            logger.info("Data store not found. Creating a new data store")
            self.data_store = pd.DataFrame()

    def add_vector(self, data: dict) -> None:

        #logger.info("Adding vector to the vector store")
        embedding = self.embedding_generator.generate_embeddings(json.dumps(data))

        if embedding.shape[-1] != self.index.d:
            logger.error(f"Embedding dimension mismatch: {embedding.shape[-1]} != {self.index.d}")
            return

        self.index.add(embedding)
        #logger.info("Adding embedding corresponding record to the data store")
        self.data_store = pd.concat([self.data_store, pd.DataFrame([data])], ignore_index=True)

    def retrieve_context(self, query, top_k=3):
        logger.info(f"Retrieving context for query: {query}")

        query_embedding = self.embedding_generator.generate_embeddings(query)
        query_embedding_np = query_embedding.astype('float32').reshape(1, -1)
        distances, index = self.index.search(query_embedding_np, top_k)

        context = "\n".join([row for row in self.data_store.iloc[index[0]].to_dict(orient="records")])
        return context

    def save_index(self, index_path="", data_path=""):

        if index_path == "":
            index_path = vector_paths['faiss_index']
        if data_path == "":
            data_path = vector_paths['data_store']

        logger.info(f"Saving index to {index_path}")
        faiss.write_index(self.index, index_path)

        logger.info(f"Saving data store to {data_path}")
        self.data_store.to_csv(data_path, index=False)
