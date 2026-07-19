"""敏感词过滤引擎 — DFA 算法实现

基于 DFA（Deterministic Finite Automaton）算法，实现 O(n) 复杂度的敏感词检测。
支持两级过滤：
- block 级别：消息拒绝发送
- audit 级别：消息正常发送但标记审计

使用方式:
    from app.utils.sensitive_filter import sensitive_filter
    
    # 加载敏感词（通常在应用启动时）
    sensitive_filter.load_words([
        {"word": "赌博", "level": "block"},
        {"word": "色情", "level": "audit"},
    ])
    
    # 检查文本
    has_block, has_audit, matched_words = sensitive_filter.check("这是一段文本")
"""

from typing import Optional


class DFAFilter:
    """DFA 敏感词过滤器"""

    def __init__(self):
        # DFA 字典树根节点
        # 结构: { "赌": { "博": { "__end__": "block" }, "__end__": None }, ... }
        self._root: dict = {}
        self._loaded = False

    def load_words(self, words: list[dict]) -> None:
        """从数据库加载敏感词列表
        
        Args:
            words: list[dict]，每个 dict 包含 word 和 level 字段
                  例如: [{"word": "赌博", "level": "block"}, ...]
        """
        self._root = {}
        for item in words:
            word = item.get("word", "").strip()
            level = item.get("level", "block")
            if not word:
                continue
            self._add_word(word, level)
        self._loaded = True

    def _add_word(self, word: str, level: str = "block") -> None:
        """添加单个敏感词到字典树"""
        node = self._root
        for char in word:
            if char not in node:
                node[char] = {}
            node = node[char]
        # 叶子节点标记敏感词级别
        node["__end__"] = level

    def check(self, text: str) -> tuple[bool, bool, list[str]]:
        """检查文本是否包含敏感词
        
        Args:
            text: 待检查文本
            
        Returns:
            (has_block, has_audit, matched_words)
            - has_block: 是否包含 block 级别敏感词
            - has_audit: 是否包含 audit 级别敏感词
            - matched_words: 命中的敏感词列表
        """
        if not self._loaded or not text:
            return False, False, []

        has_block = False
        has_audit = False
        matched_words: list[str] = []

        length = len(text)
        i = 0
        while i < length:
            node = self._root
            matched = ""
            matched_level = None
            j = i

            while j < length and text[j] in node:
                matched += text[j]
                node = node[text[j]]
                if "__end__" in node:
                    matched_level = node["__end__"]
                j += 1

            if matched and matched_level:
                # 最长匹配：继续看是否能匹配更长
                # 如果当前节点之后还能继续匹配，但已到文本末尾，则用当前结果
                # 否则继续往后搜索最长匹配
                if matched_level == "block":
                    has_block = True
                elif matched_level == "audit":
                    has_audit = True
                matched_words.append(matched)

                # 跳过已匹配的文本
                i += len(matched)
            else:
                i += 1

        return has_block, has_audit, matched_words

    def reload(self, words: list[dict]) -> None:
        """重新加载敏感词列表（清空旧词后加载新词）"""
        self.load_words(words)


# 全局单例
sensitive_filter = DFAFilter()