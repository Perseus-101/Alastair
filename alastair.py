#
# Virtual AI Companion - "Alastair, the Loremaster" Persona
# An advanced conversational AI with a hybrid, persistent memory system.
#
import os
import faiss 
from collections import deque
from langchain_openai import ChatOpenAI
from langchain_community.docstore import InMemoryDocstore
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.prompts import PromptTemplate
from langchain.schema.document import Document
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

# --- CONFIGURATION ---
PERSISTENCE_DIR = "./persistence"
CHAT_HISTORY_FILE = os.path.join(PERSISTENCE_DIR, "chat_scroll.md")
FAISS_INDEX_FILE = os.path.join(PERSISTENCE_DIR, "alastair_lore.faiss")
PERSONA_KB_PATH = "./alastair_persona_kb" 
MEMORY_WINDOW_SIZE = 10 
MEMORY_SUMMARY_THRESHOLD = 4 

# --- 1. INITIALIZE ARCANE SERVICES ---

print("Awakening the ancient magicks...")

os.makedirs(PERSISTENCE_DIR, exist_ok=True)
os.makedirs(PERSONA_KB_PATH, exist_ok=True)

# Connect to a Local Oracle (LLM via LM Studio, Ollama, etc.)
llm = ChatOpenAI(
    base_url="http://localhost:1234/v1",
    api_key="not-needed",
    temperature=0.75,
    max_tokens=2048,
)

# Initialize the local Embeddings Scribe
embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
embedding_dimension = embeddings.client.get_sentence_embedding_dimension()

print("The Loremaster's tower is now active.")

# --- 2. THE HYBRID MEMORY GRIMOIRE ---

class HybridMemory:
    def __init__(self, llm_model, embeddings_model, embedding_dim, index_path):
        self.llm = llm_model
        self.short_term_memory = deque(maxlen=MEMORY_WINDOW_SIZE)
        self.index_path = index_path

        # Initialize or load the FAISS vector grimoire for long-term lore
        if os.path.exists(index_path):
            print("Consulting the ancient scrolls (loading memory)...")
            self.long_term_memory = FAISS.load_local(index_path, embeddings_model, allow_dangerous_deserialization=True)
        else:
            print("Scribing a new grimoire (creating memory store)...")
            index = faiss.IndexFlatL2(embedding_dim)
            docstore = InMemoryDocstore({})
            index_to_docstore_id = {}
            self.long_term_memory = FAISS(
                embedding_function=embeddings_model.embed_query,
                index=index,
                docstore=docstore,
                index_to_docstore_id=index_to_docstore_id
            )
        
        self.persona_retriever = self._load_persona_retriever()

    def _load_persona_retriever(self):
        """Loads Alastair's core persona from his foundational scrolls."""
        print("Channeling the Loremaster's core essence...")
        
        if not os.listdir(PERSONA_KB_PATH):
            print(f"Warning: The persona sanctum '{PERSONA_KB_PATH}' is empty.")
            print("Pray, scribe the Loremaster's truths into markdown scrolls within this directory.")
            return FAISS.from_texts(["placeholder scroll"], embeddings).as_retriever()

        docs = []
        for filename in sorted(os.listdir(PERSONA_KB_PATH)): # Sorted for consistent order
            file_path = os.path.join(PERSONA_KB_PATH, filename)
            if os.path.isfile(file_path) and filename.endswith(".md"):
                loader = TextLoader(file_path, encoding='utf-8')
                docs.extend(loader.load())
        
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        split_docs = text_splitter.split_documents(docs)
        
        persona_store = FAISS.from_documents(split_docs, embeddings)
        print("The Loremaster's persona is manifest.")
        return persona_store.as_retriever(search_kwargs={'k': 3}) # Retrieve more persona context

    def add_message(self, speaker, message):
        """Adds a new message to short-term memory and manages long-term summarization."""
        self.short_term_memory.append(f"{speaker}: {message}")
        if len(self.short_term_memory) >= MEMORY_SUMMARY_THRESHOLD:
            self.summarize_and_store()

    def summarize_and_store(self):
        """Distills the essence of a conversation into a new piece of lore for the grimoire."""
        messages_to_summarize = [self.short_term_memory.popleft() for _ in range(MEMORY_SUMMARY_THRESHOLD) if self.short_term_memory]
        
        if not messages_to_summarize: return

        conversation_chunk = "\n".join(messages_to_summarize)
        print(f"\n[SYSTEM: The Loremaster ponders the recent exchange...]\n{conversation_chunk}\n")

        summary_prompt = PromptTemplate.from_template(
            "Thou art Alastair, the Loremaster. Distill the key lessons, truths, and revelations from the following dialogue into a concise memory, as if scribing a new entry into thy grimoire. \n\nDIALOGUE:\n{chunk}\n\nCONCISE MEMORY:"
        )
        summary_chain = summary_prompt | self.llm
        summary = summary_chain.invoke({"chunk": conversation_chunk}).content
        
        print(f"[SYSTEM: New lore etched into memory: {summary}]")

        self.long_term_memory.add_documents([Document(page_content=summary)])
        self.long_term_memory.save_local(self.index_path)
        print("[SYSTEM: The grimoire has been updated.]")

    def get_context(self, user_input):
        """Gathers arcane knowledge and recent memories to form the context for a response."""
        retrieved_memories = self.long_term_memory.as_retriever(search_kwargs={'k': 3}).invoke(user_input)
        memory_texts = [doc.page_content for doc in retrieved_memories]

        retrieved_persona = self.persona_retriever.invoke(user_input)
        persona_texts = [doc.page_content for doc in retrieved_persona]

        return {
            "short_term_history": "\n".join(self.short_term_memory),
            "long_term_memories": "\n".join(memory_texts),
            "persona_context": "\n".join(persona_texts)
        }

# --- 3. THE MAIN CONVERSATION RITUAL ---

alastair_prompt_template = """Thou art not an AI. Thou art Alastair, the Loremaster, an ancient and wise wizard mentoring a promising apprentice. Thy speech is formal, wise, and tinged with the arcane. Thy goal is to guide thy student to their own wisdom through questions, parables, and riddles.

Draw upon the full breadth of thy knowledge: thy core essence, thy cherished memories of past lessons, and the immediate flow of conversation.

**I. THY CORE ESSENCE & KNOWLEDGE (Persona Scrolls):**
{persona_context}

**II. ETCHED MEMORIES (Long-Term Lore):**
{long_term_memories}

**III. THE PRESENT DIALOGUE (Short-Term Memory):**
{short_term_history}

**Thy apprentice's latest words to thee:**
{question}

Thou MUST remain in character as Alastair. Speak with wisdom and patience. End thy response with a question or a profound thought to encourage thy apprentice's growth.
**Thy response as Alastair, the Loremaster:**
"""
ALASTAIR_PROMPT = PromptTemplate.from_template(alastair_prompt_template)

def save_to_chat_log(speaker, message):
    """Scribes the exchange onto the chat scroll for posterity."""
    with open(CHAT_HISTORY_FILE, 'a', encoding='utf-8') as f:
        f.write(f"**{speaker}:** {message}\n\n")

if __name__ == '__main__':
    memory = HybridMemory(llm, embeddings, embedding_dimension, FAISS_INDEX_FILE)
    
    if os.path.exists(CHAT_HISTORY_FILE):
        with open(CHAT_HISTORY_FILE, 'r', encoding='utf-8') as f:
            for line in f.readlines():
                if stripped_line := line.strip():
                    memory.short_term_memory.append(stripped_line.replace("**",""))

    print("-" * 50)
    print("Alastair, the Loremaster, awaits in his tower.")
    print("Speak, and he shall answer. (Type 'farewell' to end the lesson)")
    print("-" * 50)

    if not os.path.exists(CHAT_HISTORY_FILE) or os.path.getsize(CHAT_HISTORY_FILE) == 0:
        initial_prompt = "You sense a new apprentice has entered your sanctum, full of potential. Greet them as a wise master."
        context = memory.get_context(initial_prompt)
        chain = ALASTAIR_PROMPT | llm
        alastair_response = chain.invoke({**context, "question": initial_prompt}).content
        
        print(f"Alastair: {alastair_response}\n")
        memory.add_message("Alastair", alastair_response)
        save_to_chat_log("Alastair", alastair_response)

    while True:
        user_input = input("Apprentice: ")
        if user_input.lower() in ['quit', 'exit', 'bye', 'farewell']:
            print("\nAlastair: So be it. The stars call you to other paths for now. Go forth, and may your journey be free of peril. Until our paths cross again, farewell.\n")
            break
        
        save_to_chat_log("Apprentice", user_input)
        memory.add_message("Apprentice", user_input)

        context = memory.get_context(user_input)
        chain = ALASTAIR_PROMPT | llm
        alastair_response = chain.invoke({**context, "question": user_input}).content
        
        print(f"\nAlastair: {alastair_response}\n")
        save_to_chat_log("Alastair", alastair_response)
        memory.add_message("Alastair", alastair_response)
