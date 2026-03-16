import json
from langchain_google_genai import ChatGoogleGenerativeAI
from utils.config import Config
from utils.utils import setup_logger
from utils.otc_data import OTC_LIST_DATA

logger = setup_logger(__name__)

class OTCManager:
    OTC_LIST = OTC_LIST_DATA
    
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(model=Config.GEMINI_MODEL_NAME, google_api_key=Config.GOOGLE_API_KEY)
        from utils.vector_store import VectorStoreManager
        self.vector_store = VectorStoreManager()
        self.otc_namespace = "otc_medicines"
        self._initialize_otc_db()

    def _initialize_otc_db(self):
        try:
            # Check if namespace already exists and has data
            try:
                stats = self.vector_store.index.describe_index_stats()
                if self.otc_namespace in stats.namespaces and stats.namespaces[self.otc_namespace].vector_count > 0:
                    logger.info(f"OTC DB namespace '{self.otc_namespace}' already populated. Skipping ingestion.")
                    return
            except Exception as e:
                logger.warning(f"Could not check index stats: {e}")

            logger.info("Initializing OTC Vector DB...")
            texts = [item['medicine_name'] for item in self.OTC_LIST]
            metadatas = []
            for item in self.OTC_LIST:
                meta = item.get('metadata', {}).copy()
                meta['source'] = 'general_otc_list'
                metadatas.append(meta)
            self.vector_store.add_texts(texts, metadatas, namespace=self.otc_namespace)
            logger.info("OTC List Ingested into Pinecone.")
        except Exception as e:
            logger.error(f"Failed to initialize OTC DB: {e}")

    def search_otc_db(self, query, top_k=10):
        matches = self.vector_store.search(query, namespace=self.otc_namespace, top_k=top_k)
        results = []
        for m in matches:
             # Find full detail from OTC_LIST using name matched
             full_detail = next((item for item in self.OTC_LIST if item['medicine_name'] == m.metadata['text']), None)
             
             if full_detail:
                 results.append({
                     "name": full_detail['medicine_name'],
                     "category": full_detail.get('category', 'General'),
                     "description": full_detail.get('metadata', {}).get('uses', 'Description not available'),
                     "side_effects": full_detail.get('metadata', {}).get('side_effects', 'N/A'),
                     "contraindications": full_detail.get('metadata', {}).get('warnings', 'N/A')
                 })
             else:
                 # Fallback if list lookup fails
                 results.append({
                     "name": m.metadata['text'],
                     "category": m.metadata.get('type', 'Unknown'),
                     "description": "Details unavailable",
                     "side_effects": "N/A",
                     "contraindications": "N/A"
                 })
        return results

    def get_otc_list(self):
        # Convert OTC_DATA format to Template format
        formatted = []
        for item in self.OTC_LIST:
            formatted.append({
                "name": item['medicine_name'],
                "category": item.get('category', 'General'),
                 "description": item.get('metadata', {}).get('uses', 'Description not available'),
                 "side_effects": item.get('metadata', {}).get('side_effects', 'N/A'),
                 "contraindications": item.get('metadata', {}).get('warnings', 'N/A')
            })
        return formatted

    def check_medicines_with_llm(self, medicine_list):
        logger.info("Checking medicines against OTC list using Vector Search + LLM")
        results = {"otc_medicines": [], "consult_medicines": []}
        for med in medicine_list:
            med_str = str(med)
            matches = self.vector_store.search(med_str, namespace=self.otc_namespace, top_k=3)
            candidates = [m.metadata['text'] for m in matches if m.score > 0.7]
            if not candidates:
                 results["consult_medicines"].append({
                     "name": med_str.split('(')[0],
                     "reason": "No matching approved OTC medicine found in database."
                 })
                 continue
            candidates_str = "\n".join(candidates)
            prompt = f"""
            You are a medical assistant. Verify if the extracted medicine is strictly equivalent to any of the allowed OTC candidates found.

            Extracted Medicine: "{med_str}"

            Allowed OTC Candidates (from database):
            {candidates_str}

            Instructions:
            1. Determine if the 'Extracted Medicine' matches any 'Allowed OTC Candidate' (Brand or Generic).
            2. Match must be safe and exact (e.g., "Crocin" matches "Paracetamol").
            3. Return JSON.

            Output Format:
            {{
                "is_otc": true/false,
                "matched_candidate": "Name of matched OTC item" or null,
                "reason": "Brief explanation"
            }}
            """
            try:
                response = self.llm.invoke(prompt)
                content = response.content.replace("```json", "").replace("```", "").strip()
                verification = json.loads(content)
                name_clean = med_str.split(':')[0].strip("- ").strip()
                if verification.get("is_otc"):
                    results["otc_medicines"].append({
                        "name": name_clean,
                        "reason": f"Matched with {verification.get('matched_candidate')}"
                    })
                else:
                    results["consult_medicines"].append({
                        "name": name_clean,
                        "reason": verification.get("reason", "Not a valid match with allowed list")
                    })
            except Exception as e:
                logger.error(f"Error checking medicine {med_str}: {e}")
                results["consult_medicines"].append({"name": med_str, "reason": "Error verifying safety"})
        return results
