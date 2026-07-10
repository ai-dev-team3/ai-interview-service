import logging

from transformers import AutoModel, AutoTokenizer
from sentence_transformers import SentenceTransformer
import torch
import torch.nn.functional as F

logger = logging.getLogger(__name__)


class SimilarityScorer:
    def __init__(self):
        self.model_names = [
            'paraphrase-multilingual-mpnet-base-v2',
            'snunlp/KR-SBERT-V40K-klueNLI-augSTS'
        ]
        self.weights = [0.7, 0.3]
        self.models = self._load_models()

    @staticmethod
    def _load_cached_first(loader, name: str):
        """캐시가 있으면 네트워크 없이 로드한다.

        HuggingFace Hub는 캐시가 있어도 파일마다 ETag 재검증 요청을 보내
        모델 두 개 로드에 6초 가까이 쓴다(실측). local_files_only=True로
        그 왕복을 없애고, 캐시가 없을 때만 평소대로 내려받는다.
        """
        try:
            return loader(local_files_only=True)
        except Exception:
            logger.info("%s 캐시 없음 — HuggingFace Hub에서 내려받는다", name)
            return loader(local_files_only=False)

    def _load_models(self):
        models = {}
        for name in self.model_names:
            if "snunlp" in name:
                tokenizer = self._load_cached_first(
                    lambda local_files_only: AutoTokenizer.from_pretrained(
                        name, local_files_only=local_files_only
                    ),
                    name,
                )
                model = self._load_cached_first(
                    lambda local_files_only: AutoModel.from_pretrained(
                        name, local_files_only=local_files_only
                    ),
                    name,
                )
                models[name] = {"type": "huggingface", "model": model, "tokenizer": tokenizer}
            else:
                model = self._load_cached_first(
                    lambda local_files_only: SentenceTransformer(
                        name, local_files_only=local_files_only
                    ),
                    name,
                )
                models[name] = {"type": "sentence-transformers", "model": model}
        return models

    def _embed(self, model_dict, sentence: str):
        if model_dict["type"] == "huggingface":
            inputs = model_dict["tokenizer"](sentence, return_tensors="pt", truncation=True, padding=True,
                                             max_length=128)
            with torch.no_grad():
                outputs = model_dict["model"](**inputs)
                embedding = outputs.pooler_output[0]
        else:
            embedding = model_dict["model"].encode(sentence, convert_to_tensor=True)
        return F.normalize(embedding, p=2, dim=0)

    def calculate_similarity(self, user_answer: str, model_answer: str) -> float:
        total = 0.0
        for name, weight in zip(self.model_names, self.weights):
            model_dict = self.models[name]
            emb1 = self._embed(model_dict, user_answer)
            emb2 = self._embed(model_dict, model_answer)
            sim = torch.dot(emb1, emb2).item()
            total += sim * weight
        return round(max(0.0, min(1.0, total)), 4)
