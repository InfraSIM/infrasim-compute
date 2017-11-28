'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''

import unittest
from infrasim.helper import version_parser, version_match


class TestVersionMatch(unittest.TestCase):

    def test_ge_1(self):
        e = ">=2.10.1"
        r = "2.11"
        assert version_match(e, r) is True

    def test_ge_2(self):
        e = ">=2.10.1"
        r = "2.10"
        assert version_match(e, r) is True

    def test_ge_3(self):
        e = ">=2.10.1"
        r = "2.9"
        assert version_match(e, r) is False

    def test_gt_1(self):
        e = ">2.10.1"
        r = "2.11"
        assert version_match(e, r) is True

    def test_gt_2(self):
        e = ">2.10.1"
        r = "2.10"
        assert version_match(e, r) is False

    def test_gt_3(self):
        e = ">2.10.1"
        r = "2.9"
        assert version_match(e, r) is False

    def test_eq_1(self):
        e = "==2.10.1"
        r = "2.11"
        assert version_match(e, r) is False

    def test_eq_2(self):
        e = "==2.10.1"
        r = "2.10"
        assert version_match(e, r) is True

    def test_eq_3(self):
        e = "==2.10.1"
        r = "2.9"
        assert version_match(e, r) is False

    def test_le_1(self):
        e = "<=2.10.1"
        r = "2.11"
        assert version_match(e, r) is False

    def test_le_2(self):
        e = "<=2.10.1"
        r = "2.10"
        assert version_match(e, r) is True

    def test_le_3(self):
        e = "<=2.10.1"
        r = "2.9"
        assert version_match(e, r) is True

    def test_lt_1(self):
        e = "<2.10.1"
        r = "2.11"
        assert version_match(e, r) is False

    def test_lt_2(self):
        e = "<2.10.1"
        r = "2.10"
        assert version_match(e, r) is False

    def test_lt_3(self):
        e = "<2.10.1"
        r = "2.9"
        assert version_match(e, r) is True


class TestVersionParser(unittest.TestCase):

    def test_normal_expression(self):
        e = ">=2.10.1"
        p, v = version_parser(e)
        assert p == ">="
        assert v == "2.10.1"

    def test_no_punctuation(self):
        e = "2.10.1"
        p, v = version_parser(e)
        assert p is None
        assert v == "2.10.1"

    def test_no_revision(self):
        e = ">="
        p, v = version_parser(e)
        assert p is None
        assert v is None

    def test_empty_expression(self):
        e = ""
        p, v = version_parser(e)
        assert p is None
        assert v is None

    def test_less_than(self):
        e = "<2.10.1"
        p, v = version_parser(e)
        assert p == "<"
        assert v == "2.10.1"

    def test_more_than(self):
        e = ">2.10.1"
        p, v = version_parser(e)
        assert p == ">"
        assert v == "2.10.1"

    def test_short_revision(self):
        e = ">=2"
        p, v = version_parser(e)
        assert p == ">="
        assert v == "2"

    def test_expression_with_blank(self):
        e = " >=\t2.10.1"
        p, v = version_parser(e)
        assert p == ">="
        assert v == "2.10.1"

    def test_fault_punctuation(self):
        e = "?2.10.1"
        p, v = version_parser(e)
        assert p is None
        assert v == "2.10.1"

    def test_fault_revision(self):
        e = "==a.b.c"
        p, v = version_parser(e)
        assert p is None
        assert v is None
