import re
from typing import Iterable, List

from hermes_codex_plugin.domain.memory.entities import MemoryEntry


class SkillRuleExtractor:
    RULE_HINT_WORDS = (
        "always",
        "convention",
        "must",
        "need",
        "needed",
        "needs",
        "never",
        "prefer",
        "require",
        "required",
        "requires",
        "remember",
        "rule",
        "run",
        "should",
        "use",
        "debe",
        "deben",
        "necesario",
        "nunca",
        "prefiere",
        "regla",
        "requerido",
        "siempre",
        "usar",
        "usa",
        "immer",
        "muss",
        "nie",
        "regel",
        "sollte",
        "важно",
        "всегда",
        "должен",
        "должна",
        "должно",
        "должны",
        "запомни",
        "запоминать",
        "запускай",
        "запускать",
        "использовать",
        "используй",
        "конвенция",
        "надо",
        "нельзя",
        "никогда",
        "нужно",
        "обязательно",
        "правило",
        "правила",
        "предпочитай",
        "предпочитать",
        "соглашение",
        "следует",
        "требование",
        "требуется",
    )
    QUESTION_PREFIXES = (
        "should i ",
        "what ",
        "how ",
        "why ",
        "зачем ",
        "как ",
        "можно ли ",
        "надо ли ",
        "нужно ли ",
        "почему ",
        "что ",
    )
    RULE_HINTS = re.compile(
        r"\b({})\b".format("|".join(re.escape(word) for word in RULE_HINT_WORDS)),
        re.IGNORECASE,
    )
    SENTENCE_SPLITTER = re.compile(r"(?<=[.!?])\s+|[\r\n]+")
    WHITESPACE = re.compile(r"\s+")

    def extract(self, entries: Iterable[MemoryEntry]) -> List[str]:
        seen = set()
        rules: List[str] = []
        for entry in entries:
            for sentence in self.split_sentences(entry.body.to_raw()):
                clean = self.clean_sentence(sentence)
                if not self.is_rule_candidate(clean):
                    continue
                key = clean.lower()
                if key in seen:
                    continue
                seen.add(key)
                rules.append(clean[:240])
        return rules

    def split_sentences(self, text: str) -> List[str]:
        compact = self.WHITESPACE.sub(" ", text.strip())
        if not compact:
            return []
        parts = self.SENTENCE_SPLITTER.split(compact)
        return [part.strip() for part in parts if part.strip()]

    def clean_sentence(self, sentence: str) -> str:
        return " ".join(sentence.split()).strip(" -")

    def is_rule_candidate(self, sentence: str) -> bool:
        if not sentence or len(sentence) < 12:
            return False
        if self.is_question_like(sentence):
            return False
        return bool(self.RULE_HINTS.search(sentence))

    def is_question_like(self, sentence: str) -> bool:
        clean = sentence.strip().lower()
        return clean.endswith("?") or clean.startswith(self.QUESTION_PREFIXES)


class SkillNameNormalizer:
    VALID_CHARS = re.compile(r"[^a-zA-Z0-9]+")
    DUPLICATE_DASHES = re.compile(r"-{2,}")

    def normalize(self, name: str) -> str:
        normalized = self.VALID_CHARS.sub("-", name.strip().lower()).strip("-")
        return self.DUPLICATE_DASHES.sub("-", normalized) or "learned-workflow"
