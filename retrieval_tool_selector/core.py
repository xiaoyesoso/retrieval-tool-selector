import numpy as np
import json
from sklearn.metrics.pairwise import cosine_similarity
import openai


class RetrievalAugmentedToolSelector:
    """
    A retrieval-augmented tool selector that uses semantic embeddings to identify
    relevant API functions and parameters based on user queries.

    This class leverages OpenAI's embedding models to compute semantic similarity between:
    1. User queries and available API functions
    2. User queries and parameter enumeration values

    Args:
        tools (list): List of tool definitions in OpenAI function-calling format
        api_key (str): OpenAI API key
        base_url (str): Base URL for OpenAI API (can be used with alternative endpoints)
        embedding_model (str): Name of embedding model to use (default: "text-embedding-ada-002")

    Attributes:
        client (openai.Client): OpenAI client instance
        tools (list): Original tool definitions
        tool_embeddings (numpy.ndarray): Precomputed embeddings for all tools
        enum_embeddings_cache (dict): Cache of precomputed embeddings for enum values
        tool_names (list): Names of all available tools
        tool_definitions (list): Full tool definitions with parameters
    """

    def __init__(self, tools, api_key, base_url, embedding_model="text-embedding-ada-002"):
        # Initialize OpenAI client
        self.client = openai.Client(api_key=api_key, base_url=base_url)

        # Store configuration
        self.embedding_model = embedding_model
        self.tools = tools

        # Precompute tool embeddings
        self.tool_embeddings = []
        self.tool_names = []
        self.tool_definitions = []

        for tool in tools:
            # Construct semantic text for embedding
            tool_name = tool["function"]["name"]
            tool_description = tool["function"]["description"]
            tool_text = f"{tool_name}: {tool_description}"

            # Compute embedding
            embedding = self._get_embedding(tool_text)
            self.tool_embeddings.append(embedding)
            self.tool_names.append(tool_name)
            self.tool_definitions.append({
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool_description,
                    "parameters": tool["function"]["parameters"]
                }
            })

        self.tool_embeddings = np.array(self.tool_embeddings)

        # Precompute enum embeddings
        self.enum_embeddings_cache = {}
        all_enum_values = set()

        for tool in tools:
            parameters = tool["function"]["parameters"]
            if "properties" in parameters:
                for prop in parameters["properties"].values():
                    if "enum" in prop:
                        for value in prop["enum"]:
                            # Convert to standardized string format
                            str_value = str(value).strip()
                            all_enum_values.add(str_value)

        if all_enum_values:
            enum_values_list = list(all_enum_values)
            embeddings = self._get_embeddings(enum_values_list)

            # Create enum -> embedding mapping
            for value, embedding in zip(enum_values_list, embeddings):
                self.enum_embeddings_cache[value] = embedding

    def _get_embedding(self, text):
        """Get embedding vector for a single text input"""
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=[text]
        )
        return response.data[0].embedding

    def _get_embeddings(self, texts):
        """Batch get embeddings for multiple text inputs"""
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=texts
        )
        return [data.embedding for data in response.data]

    def select_tools(self, query,
                     tool_threshold=0.7,
                     tool_top_k=1,
                     enum_threshold=0.6,
                     enum_top_k=3):
        """
        Select relevant tools and filter enum parameters based on semantic similarity

        Args:
            query (str): User input query
            tool_threshold (float): Minimum cosine similarity for tool selection
            tool_top_k (int): Maximum number of tools to return
            enum_threshold (float): Minimum cosine similarity for enum selection
            enum_top_k (int): Maximum number of enum values to return per parameter

        Returns:
            list: Selected tool definitions with filtered enums
        """
        # Compute query embedding
        query_embedding = self._get_embedding(query)

        # Calculate tool similarities
        similarities = cosine_similarity([query_embedding], self.tool_embeddings)[0]

        # Filter tools
        tool_scores = list(enumerate(similarities))
        tool_scores.sort(key=lambda x: x[1], reverse=True)

        selected_tools = []
        for idx, score in tool_scores:
            if score >= tool_threshold and len(selected_tools) < tool_top_k:
                # Deep copy tool definition
                tool_copy = json.loads(json.dumps(self.tool_definitions[idx]))

                # Filter enum parameters
                parameters = tool_copy["function"]["parameters"]
                if "properties" in parameters:
                    for prop_name, prop in parameters["properties"].items():
                        if "enum" in prop:
                            enum_values = [str(v).strip() for v in prop["enum"]]
                            prop["enum"] = self._filter_enum_values(
                                query_embedding,
                                enum_values,
                                threshold=enum_threshold,
                                top_k=enum_top_k
                            )

                selected_tools.append(tool_copy)

        # Print debug information
        print(f"\nTool similarity analysis:")
        print(f"Embedding model: {self.embedding_model}")
        for idx, score in enumerate(similarities):
            print(f"  - {self.tool_names[idx]}: {score:.4f}")

        return selected_tools

    def _filter_enum_values(self, query_embedding, enum_values, threshold, top_k):
        """
        Filter enum values based on semantic similarity to query

        Args:
            query_embedding: Embedding vector of the user query
            enum_values: List of enum values (strings)
            threshold: Minimum similarity score
            top_k: Maximum number of values to return

        Returns:
            list: Filtered enum values
        """
        if not enum_values:
            return enum_values

        # Get precomputed embeddings
        enum_embeddings = [self.enum_embeddings_cache[value] for value in enum_values]
        enum_embeddings = np.array(enum_embeddings)

        # Calculate similarities
        similarities = cosine_similarity([query_embedding], enum_embeddings)[0]
        enum_scores = [(i, sim, value) for i, (sim, value) in enumerate(zip(similarities, enum_values))]
        enum_scores.sort(key=lambda x: x[1], reverse=True)

        # Apply thresholds
        filtered_enum = []
        for i, sim, value in enum_scores:
            if sim >= threshold and len(filtered_enum) < top_k:
                filtered_enum.append(value)

        print(f"\nEnum filtering results (threshold={threshold}, top_k={top_k}):")
        print(f"  Original: {enum_values}")
        print(f"  Filtered: {filtered_enum}")

        return filtered_enum