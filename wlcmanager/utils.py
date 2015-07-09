# coding: utf-8


def get_free_from_sequence(seq, start_value=1):
    """Get next missing value form sequence starting with start_value"""
    if start_value not in seq:
        return start_value

    i = start_value
    while i in seq:
        i += 1

    return i


def ppxml(element, indent_level=0, attr_num_limit=1):
    indent = " " * indent_level
    res = "{}<{}".format(indent, element.tag)
    attr_list = sorted(element.attrib)
    attr_prefix = ' '
    if len(attr_list) > attr_num_limit:
        attr_prefix = '\n{}    '.format(indent)
    for k in attr_list:
        res += '{}{}="{}"'.format(attr_prefix, k, element.attrib[k])

    if len(element) > 0:
        res += '>\n'
        for child in element:
            res += ppxml(child, indent_level=indent_level + 2,
                         attr_num_limit=attr_num_limit)
        res += "{}</{}>\n".format(indent, element.tag)
    else:
        res += '/>\n'

    return res


def xml_compare(e1, e2, reporter=None, e1_name='e1', e2_name='e2'):
    if e1.tag != e2.tag:
        if reporter:
            reporter('Tags do not match: {} ({}) and {} ({})'.format(
                e1.tag, e1_name, e2.tag, e2_name))
        return False
    for name, value in e1.attrib.items():
        if e2.attrib.get(name) != value:
            if reporter:
                reporter('Attributes do not match: {}="{}" ({}), '
                         '{}="{}" ({})'.format(name, value, e1_name, name,
                                               e2.attrib.get(name), e2_name))
            return False
    for name in e2.attrib.keys():
        if name not in e1.attrib:
            if reporter:
                reporter('{} has an attribute {} is missing: {}'.format(
                    e2_name, e1_name, name))
            return False
    if not text_compare(e1.text, e2.text):
        if reporter:
            reporter('text: {} ({}) != {} ({})'.format(e1.text, e1_name,
                                                       e2.text, e2_name))
        return False
    if not text_compare(e1.tail, e2.tail):
        if reporter:
            reporter('tail: {} ({}) != {} ({})'.format(e1.tail, e1_name,
                                                       e2.tail, e2_name))
        return False
    cl1 = e1.getchildren()
    cl2 = e2.getchildren()

    cl1_names = set([c.tag for c in cl1])
    cl2_names = set([c.tag for c in cl2])
    cl1_diff = cl2_names.difference(cl1_names)
    cl2_diff = cl1_names.difference(cl2_names)
    if cl1_diff:
        if reporter:
            reporter('missing tags in {}: {}'.format(e1_name,
                                                     ", ".join(cl1_diff)))
        return False
    if cl2_diff:
        if reporter:
            reporter('missing tags in {}: {}'.format(e2_name,
                                                     ", ".join(cl2_diff)))
        return False

    if len(cl1) != len(cl2):
        if reporter:
            reporter('children length differs, {} ({}) != '
                     '{} ({})'.format(len(cl1), e1_name, len(cl2), e2_name))
        return False
    i = 0
    for c1, c2 in zip(cl1, cl2):
        i += 1
        if not xml_compare(c1, c2, reporter=reporter,
                           e1_name=e1_name, e2_name=e2_name):
            if reporter:
                if 'name' in c1.attrib:
                    reporter('children {} do not match: {} (name={})'.format(
                        i, c1.tag, c1.attrib['name']))
                else:
                    reporter('children {} do not match: {}'.format(i, c1.tag))
            return False
    return True


def text_compare(t1, t2):
    if not t1 and not t2:
        return True
    if t1 == '*' or t2 == '*':
        return True
    return (t1 or '').strip() == (t2 or '').strip()


class Reporter(object):
    def __init__(self):
        self.msg = []

    def report(self, msg):
        self.msg.append(msg)


def compare_config(wlc1, wlc2):
    configuration_parts = [{
        'name': 'Radio Profiles',
        'fn': 'radio_profile',
    }, {
        'name': 'Service Profiles',
        'fn': 'service_profile',
    }, {
        'name': 'Access Points',
        'fn': 'dap',
    }]
    for conf in configuration_parts:
        f = getattr(wlc1.connection.rpc, 'get_{}'.format(conf['fn']))
        conf['element1'] = f(wlc1.connection.rpc)
        f = getattr(wlc2.connection.rpc, 'get_{}'.format(conf['fn']))
        conf['element2'] = f(wlc2.connection.rpc)

        conf['element1_raw'] = ppxml(conf['element1'])
        conf['element2_raw'] = ppxml(conf['element2'])

        r = Reporter()
        conf['is_equal'] = xml_compare(conf['element1'], conf['element2'],
                                       r.report, str(wlc1), str(wlc2))
        conf['errors'] = r.msg

    return configuration_parts

def run_each_context(admin_site, request):
    try:
        return admin_site.each_context(request)
    except TypeError as e: # Django 1.7
        return admin_site.each_context()
