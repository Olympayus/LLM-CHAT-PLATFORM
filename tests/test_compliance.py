"""合规审计模块测试 — DFA 敏感词过滤引擎"""

import pytest
from app.utils.sensitive_filter import DFAFilter


@pytest.fixture
def filter_with_words():
    """预加载敏感词的过滤器实例"""
    f = DFAFilter()
    f.load_words([
        {"word": "赌博", "level": "block"},
        {"word": "色情", "level": "block"},
        {"word": "毒品", "level": "block"},
        {"word": "暴力", "level": "audit"},
        {"word": "歧视", "level": "audit"},
        {"word": "fuck", "level": "block"},
    ])
    return f


class TestDFAFilter:
    """DFA 敏感词过滤器测试"""

    def test_normal_text(self, filter_with_words):
        """正常文本不应触发任何敏感词"""
        has_block, has_audit, matched = filter_with_words.check("今天天气不错，我们去公园散步吧。")
        assert has_block is False
        assert has_audit is False
        assert matched == []

    def test_empty_text(self, filter_with_words):
        """空文本应返回无敏感词"""
        has_block, has_audit, matched = filter_with_words.check("")
        assert has_block is False
        assert has_audit is False
        assert matched == []

    def test_not_loaded(self):
        """未加载敏感词时，任何文本都应返回无敏感词"""
        f = DFAFilter()
        has_block, has_audit, matched = f.check("赌博色情暴力")
        assert has_block is False
        assert has_audit is False
        assert matched == []

    def test_block_level_word(self, filter_with_words):
        """block 级别敏感词应正确检测"""
        has_block, has_audit, matched = filter_with_words.check("他在网上参与赌博活动")
        assert has_block is True
        assert has_audit is False
        assert "赌博" in matched

    def test_audit_level_word(self, filter_with_words):
        """audit 级别敏感词应正确检测"""
        has_block, has_audit, matched = filter_with_words.check("这篇文章充满了暴力内容")
        assert has_block is False
        assert has_audit is True
        assert "暴力" in matched

    def test_block_and_audit(self, filter_with_words):
        """同时包含 block 和 audit 敏感词"""
        has_block, has_audit, matched = filter_with_words.check("赌博和暴力都是违法行为")
        assert has_block is True
        assert has_audit is True
        assert "赌博" in matched
        assert "暴力" in matched

    def test_multiple_block_words(self, filter_with_words):
        """多个 block 级别敏感词"""
        has_block, has_audit, matched = filter_with_words.check("赌博、色情、毒品都是违法的")
        assert has_block is True
        assert has_audit is False
        assert len(matched) >= 1

    def test_multiple_audit_words(self, filter_with_words):
        """多个 audit 级别敏感词"""
        has_block, has_audit, matched = filter_with_words.check("暴力和歧视都是不被允许的")
        assert has_block is False
        assert has_audit is True
        assert "暴力" in matched
        assert "歧视" in matched

    def test_english_sensitive_word(self, filter_with_words):
        """英文敏感词检测"""
        has_block, has_audit, matched = filter_with_words.check("don't say fuck here")
        assert has_block is True
        assert "fuck" in matched

    def test_chinese_english_mixed(self, filter_with_words):
        """中英文混合文本"""
        f = DFAFilter()
        f.load_words([
            {"word": "VIP", "level": "block"},
            {"word": "作弊", "level": "block"},
        ])
        has_block, has_audit, matched = f.check("请勿在考试中作弊，VIP会员也不行")
        assert has_block is True
        assert "VIP" in matched or "作弊" in matched

    def test_word_boundary(self, filter_with_words):
        """敏感词边界：包含敏感词作为子串的正常词不应误判"""
        f = DFAFilter()
        f.load_words([
            {"word": "色", "level": "block"},
        ])
        has_block, has_audit, matched = f.check("颜色")
        assert has_block is True  # "颜色" 包含 "色"
        assert "色" in matched

    def test_reload_words(self, filter_with_words):
        """reload 应清除旧词并加载新词"""
        f = filter_with_words
        # 先确认旧词存在
        has_block, _, _ = f.check("赌博活动")
        assert has_block is True

        # reload 为新词
        f.reload([
            {"word": "诈骗", "level": "block"},
        ])
        
        # 旧词应不再匹配
        has_block, _, _ = f.check("赌博活动")
        assert has_block is False

        # 新词应匹配
        has_block, _, _ = f.check("诈骗电话")
        assert has_block is True

    def test_longest_match(self, filter_with_words):
        """最长匹配：优先匹配更长的敏感词"""
        f = DFAFilter()
        f.load_words([
            {"word": "赌", "level": "block"},
            {"word": "赌博", "level": "block"},
        ])
        has_block, _, matched = f.check("他在赌博")
        assert "赌博" in matched  # 应该匹配更长的"赌博"而非"赌"
        assert has_block is True

    def test_special_characters(self, filter_with_words):
        """特殊字符包围的敏感词"""
        has_bloc