# coding: utf-8

from __future__ import (absolute_import, division,
                        print_function, unicode_literals)

from lxml import etree
from mock import MagicMock, call
import unittest

from ..utils import (get_free_from_sequence, ppxml, xml_compare, text_compare,
                     Reporter)


class SeqTest(unittest.TestCase):

    def test_empty(self):
        l = []
        rv = get_free_from_sequence(l, 5)
        self.assertEqual(rv, 5)

    def test_one(self):
        l = [1]
        rv = get_free_from_sequence(l)
        self.assertEqual(rv, 2)

    def test_one_high(self):
        l = [2]
        rv = get_free_from_sequence(l)
        self.assertEqual(rv, 1)

    def test_many(self):
        l = [1, 2, 3, 4]
        rv = get_free_from_sequence(l)
        self.assertEqual(rv, 5)

    def test_gap(self):
        l = [1, 2, 4, 5]
        rv = get_free_from_sequence(l)
        self.assertEqual(rv, 3)


class PpxmlTest(unittest.TestCase):
    def test_simple(self):
        e = etree.Element("root")
        rv = ppxml(e)
        self.assertEqual(rv, "<root/>\n")

    def test_simple_attr(self):
        e = etree.Element("root", aname1="avalue1", aname2="avalue2")
        rv = ppxml(e, attr_num_limit=2)
        self.assertEqual(rv, '<root aname1="avalue1" aname2="avalue2"/>\n')

    def test_simple_multi_attr(self):
        e = etree.Element("root", aname1="avalue1", aname2="avalue2",
                          aname3="avalue3")
        rv = ppxml(e, indent_level=1, attr_num_limit=2, )
        self.assertEqual(rv, """ <root
     aname1="avalue1"
     aname2="avalue2"
     aname3="avalue3"/>\n""")

    def test_children(self):
        e = etree.Element("root", aname1="avalue1")
        e.append(etree.Element("child1"))
        e.append(etree.Element("child2", attr="val"))
        rv = ppxml(e, indent_level=1)
        self.assertEqual(rv, """ <root aname1="avalue1">
   <child1/>
   <child2 attr="val"/>
 </root>\n""")


class XMLCmpTest(unittest.TestCase):
    def test_tag(self):
        e1 = etree.Element("root")
        e2 = etree.Element("root")
        e3 = etree.Element("sthelse")
        e_msg = 'Tags do not match: root (name1) and sthelse (name2)'

        self.assertTrue(xml_compare(e1, e2))
        reporter = MagicMock()
        self.assertFalse(xml_compare(e1, e3, reporter, 'name1', 'name2'))
        reporter.assert_called_once_with(e_msg)

    def test_attrib(self):
        e0 = etree.Element("root")
        e1 = etree.Element("root", a1='v1')
        e2 = etree.Element("root", a1='v1')
        e3 = etree.Element("root", a1='v2')
        e3 = etree.Element("root", a1='v2')
        e4 = etree.Element("root", a1='v1', a2='v2')
        e3_msg = 'Attributes do not match: a1="v1" (name1), a1="v2" (name2)'
        e4_msg = 'name2 has an attribute name1 is missing: a2'
        e0_msg = 'Attributes do not match: a1="v1" (name1), a1="None" (name2)'

        self.assertTrue(xml_compare(e1, e2))
        reporter = MagicMock()
        self.assertFalse(xml_compare(e1, e3, reporter, 'name1', 'name2'))
        reporter.assert_called_once_with(e3_msg)

        reporter.reset_mock()
        self.assertFalse(xml_compare(e1, e0, reporter, 'name1', 'name2'))
        reporter.assert_called_once_with(e0_msg)

        reporter.reset_mock()
        self.assertFalse(xml_compare(e1, e4, reporter, 'name1', 'name2'))
        reporter.assert_called_once_with(e4_msg)

    def test_text(self):
        e1 = etree.Element("root")
        e1.text = 'AAA'
        e2 = etree.Element("root")
        e2.text = 'AAA'
        e3 = etree.Element("root")
        e3.text = 'BBB'
        e3_msg = 'text: AAA (name1) != BBB (name2)'

        self.assertTrue(xml_compare(e1, e2))
        reporter = MagicMock()
        self.assertFalse(xml_compare(e1, e3, reporter, 'name1', 'name2'))
        reporter.assert_called_once_with(e3_msg)

    def test_tail(self):
        e1 = etree.Element("root")
        e1.tail = 'AAA'
        e2 = etree.Element("root")
        e2.tail = 'AAA'
        e3 = etree.Element("root")
        e3.tail = 'BBB'
        e3_msg = 'tail: AAA (name1) != BBB (name2)'

        self.assertTrue(xml_compare(e1, e2))
        reporter = MagicMock()
        self.assertFalse(xml_compare(e1, e3, reporter, 'name1', 'name2'))
        reporter.assert_called_once_with(e3_msg)

    def test_children(self):
        e1 = etree.Element("root")
        etree.SubElement(e1, "child1")
        etree.SubElement(e1, "child2")

        e2 = etree.Element("root")
        etree.SubElement(e2, "child1")
        etree.SubElement(e2, "child2")

        e3 = etree.Element("root")
        etree.SubElement(e3, "child1")
        e3_msg = 'missing tags in name2: child2'
        e3_msg_rev = 'missing tags in name1: child2'

        e4 = etree.Element("root")
        etree.SubElement(e4, "child1", name='v1')
        etree.SubElement(e4, "child2")
        e4_calls = [
            call('name2 has an attribute name1 is missing: name'),
            call('children 1 do not match: child1')
        ]

        e4n = etree.Element("root")
        etree.SubElement(e4n, "child1", name='v2')
        etree.SubElement(e4n, "child2")
        e4n_calls = [
            call('Attributes do not match: name="v1" (name1), '
                 'name="v2" (name2)'),
            call('children 1 do not match: child1 (name=v1)')
        ]

        e5 = etree.Element("root")
        etree.SubElement(e5, "child1")
        etree.SubElement(e5, "child2")
        etree.SubElement(e5, "child2")
        e5_msg = 'children length differs, 2 (name1) != 3 (name2)'

        self.assertTrue(xml_compare(e1, e2))

        reporter = MagicMock()
        self.assertFalse(xml_compare(e1, e3, reporter, 'name1', 'name2'))
        reporter.assert_called_once_with(e3_msg)

        reporter.reset_mock()
        self.assertFalse(xml_compare(e3, e1, reporter, 'name1', 'name2'))
        reporter.assert_called_once_with(e3_msg_rev)

        reporter.reset_mock()
        self.assertFalse(xml_compare(e1, e4, reporter, 'name1', 'name2'))
        self.assertEqual(reporter.call_args_list, e4_calls)

        reporter.reset_mock()
        self.assertFalse(xml_compare(e4, e4n, reporter, 'name1', 'name2'))
        self.assertEqual(reporter.call_args_list, e4n_calls)

        reporter.reset_mock()
        self.assertFalse(xml_compare(e1, e5, reporter, 'name1', 'name2'))
        reporter.assert_called_once_with(e5_msg)


class TextCmpTest(unittest.TestCase):
    def test_empty(self):
        self.assertTrue(text_compare('', ''))
        self.assertTrue(text_compare('  ', None))
        self.assertTrue(text_compare('', ' '))
        self.assertTrue(text_compare(None, None))

    def test_text(self):
        self.assertTrue(text_compare('abc', 'abc'))
        self.assertTrue(text_compare(' abc', 'abc  '))
        self.assertFalse(text_compare(' ABC', 'abc  '))

    def test_asterisk(self):
        self.assertTrue(text_compare('*', '*'))
        self.assertTrue(text_compare('*', None))
        self.assertTrue(text_compare('*', 'abc'))


class TextReporterTest(unittest.TestCase):
    def test_empty(self):
        r = Reporter()
        self.assertEqual(len(r.msg), 0)

    def test_two(self):
        r = Reporter()
        r.report('msg1')
        r.report('msg2')
        self.assertEqual(r.msg, ['msg1', 'msg2'])
