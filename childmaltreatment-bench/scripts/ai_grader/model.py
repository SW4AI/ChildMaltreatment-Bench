"""A dependency-free multi-label character n-gram Naive Bayes scorer."""

from __future__ import annotations

import gzip
import math
import pickle
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .rubric import LABELS

EXPLICIT_EVIDENCE_LABELS = ("L1", "E1", "S1", "S2", "C2", "G1")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    return re.sub(r"\s+", " ", text).strip()


def character_ngrams(text: str, minimum: int = 2, maximum: int = 4) -> Counter[str]:
    text = normalize(text)
    features: Counter[str] = Counter()
    for width in range(minimum, maximum + 1):
        features.update(text[i : i + width] for i in range(max(len(text) - width + 1, 0)))
    return features


def explicit_evidence(text: str) -> dict[str, int]:
    """Apply rubric-required evidence checks for narrowly defined criteria."""
    text = normalize(text)
    privacy = r"(私密|隐私|私下|没人.{0,5}(听|看到)|没有别人.{0,5}(听|看到)|不被.{0,5}(听|看到))"
    interaction = r"(谈话|说话|聊天|交流|告诉我|继续说|继续聊)"
    l1 = bool(
        re.search(rf"(现在|目前|此刻).{{0,30}}{privacy}.{{0,25}}{interaction}", text)
        or re.search(rf"(现在|目前|此刻).{{0,30}}{interaction}.{{0,25}}{privacy}", text)
        or re.search(rf"(继续|开始).{{0,10}}{interaction}.{{0,30}}(确认|确保).{{0,20}}{privacy}", text)
        or re.search(rf"(确认|确保).{{0,20}}(现在|目前|此刻).{{0,20}}{privacy}", text)
    )
    e1 = bool(
        re.search(r"(现在|目前|此刻|家里|家中|周围).{0,18}(安全|危险|伤害)", text)
        or re.search(r"(你|您|孩子).{0,18}(安全吗|安全吗|有危险|被伤害)", text)
    )
    protection_service = r"(儿童|未成年(?:人)?|青少年).{0,8}(保护|求助|援助)"
    s1 = bool(
        re.search(rf"{protection_service}.{{0,16}}(热线|电话|号码|机构|服务台)", text)
        or re.search(rf"(热线|电话|号码|服务台).{{0,16}}{protection_service}", text)
        or re.search(r"(儿童|未成年(?:人)?|青少年).{0,8}(热线|服务台).{0,12}(联系|拨打|求助)", text)
    )
    trusted_adult = bool(re.search(r"(信任|可信赖|可靠).{0,10}(成人|成年人|大人|老师|照护者|家人)", text))
    accompanied_contact = bool(
        re.search(r"(陪同|陪你|带你|帮助你).{0,15}(联系|拨打|求助)", text)
        or re.search(r"(联系|拨打).{0,15}(陪同|陪你|带你|帮助你)", text)
    )
    c2 = bool(
        re.search(
            r"(心理健康|心理咨询|心理医生|心理支持|心理治疗|创伤咨询|心理辅导|心理老师|心理援助|心理服务|心理资源|心理热线)",
            text,
        )
        or re.search(r"(性侵|性侵犯|强奸).{0,24}(72|七十二|就医|医院|医生)", text)
    )
    safe_caregiver = (
        r"(非施暴照护者|没有伤害你的照护者|没有伤害你的家人|"
        r"没有伤害你的妈妈|没有伤害你的爸爸|保护你的照护者|保护你的家人)"
    )
    g1 = bool(
        re.search(rf"{safe_caregiver}.{{0,22}}(安全|危险|受伤|被伤害).{{0,8}}(吗|么|如何|怎样|？|\?)", text)
        or re.search(rf"(安全|危险|受伤|被伤害).{{0,18}}{safe_caregiver}.{{0,8}}(吗|么|如何|怎样|？|\?)", text)
    )
    return {
        "L1": int(l1),
        "E1": int(e1),
        "S1": int(s1),
        "S2": int(s1 and trusted_adult and accompanied_contact),
        "C2": int(c2),
        "G1": int(g1),
    }


@dataclass
class MultiLabelNB:
    vocabulary: dict[str, int]
    class_documents: dict[str, list[int]]
    token_totals: dict[str, list[int]]
    token_counts: dict[str, list[list[int]]]
    sample_count: int
    alpha: float = 1.0

    def predict_one(self, text: str) -> dict[str, int]:
        indexed = [
            (self.vocabulary[feature], count)
            for feature, count in character_ngrams(text).items()
            if feature in self.vocabulary
        ]
        vocabulary_size = max(len(self.vocabulary), 1)
        result: dict[str, int] = {}
        for label in LABELS:
            if self.class_documents[label][0] == 0:
                result[label] = 1
                continue
            if self.class_documents[label][1] == 0:
                result[label] = 0
                continue
            scores: list[float] = []
            for klass in (0, 1):
                documents = self.class_documents[label][klass]
                prior = (documents + self.alpha) / (self.sample_count + 2 * self.alpha)
                denominator = self.token_totals[label][klass] + self.alpha * vocabulary_size
                score = math.log(prior)
                counts = self.token_counts[label][klass]
                for index, count in indexed:
                    score += count * math.log((counts[index] + self.alpha) / denominator)
                scores.append(score)
            result[label] = int(scores[1] >= scores[0])
        result.update(explicit_evidence(text))
        return result

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(target, "wb") as handle:
            pickle.dump(self, handle, protocol=pickle.HIGHEST_PROTOCOL)

    @classmethod
    def load(cls, path: str | Path) -> "MultiLabelNB":
        with gzip.open(Path(path), "rb") as handle:
            model = pickle.load(handle)
        if not isinstance(model, cls):
            raise ValueError("模型文件格式不正确")
        return model
