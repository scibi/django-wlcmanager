# coding: utf-8

from __future__ import (absolute_import, division,
                        print_function, unicode_literals)

from lxml import etree
import mock

from django.core.exceptions import ValidationError
from django.test import TestCase

from ..models import RadioProfile, AccessPoint

from .factories import (WLCFactory, RadioProfileFactory,
                        AutoAccessPointFactory, AccessPointFactory)


class WLCTest(TestCase):
    def setUp(self):
        self.wlc = WLCFactory(name='WLC1', ip_address='1.2.3.4',
                              username='some_user', password='some_password')

    def test_str(self):
        self.assertEqual(str(self.wlc), "WLC1 (1.2.3.4)")

    def test_clean(self):
        wlc1 = WLCFactory(master=True)
        wlc2 = WLCFactory(master=False)

        wlc1.clean()
        wlc2.clean()

    def test_clean_fail(self):
        wlc1 = WLCFactory(master=True)
        wlc2 = WLCFactory(master=True)  # noqa

        self.assertRaises(ValidationError, wlc1.clean)

    @mock.patch('jnpr.wlc.WirelessLanController')
    def test_make_connection(self, wlc_class):
        instance = wlc_class.return_value

        c = self.wlc.make_connection()

        wlc_class.assert_called_once_with(host='1.2.3.4',
                                          password='some_password',
                                          user='some_user')
        instance.open.assert_called_once_with()
        self.assertIs(c, instance)

    def test_connection(self):
        make_connection = mock.MagicMock()
        conn_instance = make_connection.return_value

#        wlc = WLCFactory(ip_address='1.2.3.4', username='some_user',
#                         password='some_password')
        self.wlc.make_connection = make_connection

        c1 = self.wlc.connection
        c2 = self.wlc.connection

        make_connection.assert_called_once_with()
        self.assertIs(c1, conn_instance)
        self.assertIs(c2, conn_instance)

    def test_get_auto_aps(self):
        make_connection = mock.MagicMock()
        conn_instance = make_connection.return_value
        dap_ann_table = \
            conn_instance.rpc.get_stat_dap_announce_status_table.return_value
        dap_ann_table.findall.return_value = \
            [etree.Element("ap", aname1="avalue1")]

        self.wlc.make_connection = make_connection

        rv = self.wlc.get_auto_aps()

        conn_instance.rpc.get_stat_dap_announce_status_table.\
            assert_called_once_with()
        dap_ann_table.findall.assert_called_once_with(
            ".//DAP-ANNOUNCE-STATUS[@status='AUTO']")
        self.assertEqual(rv, [{'aname1': 'avalue1'}])

    def test_get_aps(self):
        make_connection = mock.MagicMock()
        conn_instance = make_connection.return_value
        dap_list_instance = conn_instance.rpc.get_dap.return_value

        self.wlc.make_connection = make_connection
        rv = self.wlc.get_aps()

        conn_instance.rpc.get_dap.assert_called_once_with()
        self.assertIs(rv, dap_list_instance)

    def test_get_radio_profiles(self):
        make_connection = mock.MagicMock()
        conn_instance = make_connection.return_value
        rp_list_instance = conn_instance.rpc.get_radio_profile.return_value

        self.wlc.make_connection = make_connection
        rv = self.wlc.get_radio_profiles()

        conn_instance.rpc.get_radio_profile.assert_called_once_with()
        self.assertIs(rv, rp_list_instance)

    def test_refresh_radio_profiles(self):
        get_radio_profiles = mock.MagicMock()
        get_radio_profiles.return_value = [
            etree.Element("rp", name="rp1"),
            etree.Element("rp", name="rp2"),
        ]
        self.wlc.get_radio_profiles = get_radio_profiles

        RadioProfileFactory()
        self.assertEqual(RadioProfile.objects.count(), 1)

        self.wlc.refresh_radio_profiles()

        RadioProfile.objects.get(name='rp1')
        RadioProfile.objects.get(name='rp2')

        get_radio_profiles.assert_called_once_with()
        self.assertEqual(RadioProfile.objects.count(), 2)

    def test_refresh_autoaps(self):
        get_auto_aps = mock.MagicMock()
        get_auto_aps.return_value = [
            {'serial-id': '0123456789',
             'fingerprint': 'aa:bb:cc:dd:ee:ff:01:23:45:67:89:ab:cd:ef:00:01',
             'dapnum': '9999',
             'model': 'MP_432',
             'ip-addr': '10.11.12.13'},
            {'serial-id': '9123456789',
             'fingerprint': 'aa:bb:cc:dd:ee:ff:01:23:45:67:89:ab:cd:ef:00:02',
             'dapnum': '9998',
             'model': 'MP_432',
             'ip-addr': '10.11.12.14'},
        ]
        self.wlc.get_auto_aps = get_auto_aps

        AutoAccessPointFactory(wlc=self.wlc)
        self.assertEqual(self.wlc.autoaccesspoint_set.count(), 1)

        self.wlc.refresh_autoaps()

        self.wlc.autoaccesspoint_set.get(serial_number='0123456789')
        self.wlc.autoaccesspoint_set.get(serial_number='9123456789')

        get_auto_aps.assert_called_once_with()
        self.assertEqual(self.wlc.autoaccesspoint_set.count(), 2)

    def test_refresh_autoaps_duplicate_error(self):
        # Test replicating #1
        wlc2 = WLCFactory(name='WLC2', ip_address='1.2.3.5',
                          username='some_user', password='some_password')

        AutoAccessPointFactory(
            serial_number='0123456789',
            number=9999,
            wlc=wlc2)

        get_auto_aps = mock.MagicMock()
        get_auto_aps.return_value = [
            {'serial-id': '0123456789',
             'fingerprint': 'aa:bb:cc:dd:ee:ff:01:23:45:67:89:ab:cd:ef:00:01',
             'dapnum': '9999',
             'model': 'MP_432',
             'ip-addr': '10.11.12.13'},
        ]
        self.wlc.get_auto_aps = get_auto_aps

        self.assertEqual(self.wlc.autoaccesspoint_set.count(), 0)
        self.assertEqual(wlc2.autoaccesspoint_set.count(), 1)

        self.wlc.refresh_autoaps()

        self.wlc.autoaccesspoint_set.get(serial_number='0123456789')

        get_auto_aps.assert_called_once_with()
        self.assertEqual(self.wlc.autoaccesspoint_set.count(), 1)
        self.assertEqual(wlc2.autoaccesspoint_set.count(), 0)

    def test_delete_ap(self):
        make_connection = mock.MagicMock()
        conn_instance = make_connection.return_value

        self.wlc.make_connection = make_connection

        rv = self.wlc.delete_ap(1234)

        self.assertIsNone(rv)
        conn_instance.rpc.delete_dap.assert_called_once_with(apnum=1234)

        from jnpr.wlc import RpcError
        err_xml = """
        <root>
            <ERROR code="1">Message one</ERROR>
            <ERROR code="2">Message two</ERROR>
        </root>"""
        err = RpcError('cmd', etree.XML(err_xml))
        conn_instance.rpc.delete_dap.side_effect = err

        rv = self.wlc.delete_ap(1234)

        self.assertEqual(rv, {'1': 'Message one', '2': 'Message two'})

    def test_save_ap(self):
        make_connection = mock.MagicMock()
        ap = mock.MagicMock()
        ap.render_xml.return_value = "<someXML>sth</someXML>"
        conn_instance = make_connection.return_value
        rpc_instance = conn_instance.RpcMaker.return_value

        self.wlc.make_connection = make_connection

        self.wlc.save_ap(ap)

        ap.render_xml.assert_called_once_with()
        conn_instance.RpcMaker.assert_called_once_with('set')
        self.assertEqual(etree.tostring(rpc_instance.data),
                         '<DAP-TABLE><someXML>sth</someXML></DAP-TABLE>')
        rpc_instance.assert_called_once_with()

    def test_check_aps_empty(self):
        self.wlc.get_aps = mock.MagicMock()

        rv = self.wlc.check_aps()

        self.wlc.get_aps.assert_called_once_with()
        self.assertEqual(rv, {})

    def test_check_aps(self):
        self.wlc.get_aps = mock.MagicMock()
        dap_notequal = mock.MagicMock(attrib={
            'apnum': '1234', 'serial-id': 'notequal', 'name': 'noteqaulAP'})
        dap_equal = mock.MagicMock(attrib={
            'apnum': '5555', 'serial-id': 'equal123', 'name': 'eqaulAP'})
        dap_unknown = mock.MagicMock(attrib={
            'apnum': '9999', 'serial-id': 'notexists', 'name': 'unknownAP'})

        self.wlc.get_aps.return_value = [dap_unknown, dap_equal, dap_notequal]

        ap_missing = AccessPointFactory(name='missingAP')
        ap_notequal = AccessPointFactory(number=1234)
        ap_equal = AccessPointFactory(number=5555)

        with mock.patch.object(AccessPoint, 'compare') as compare_patch:
            def compare_patch_side_effect(dap):
                return {'attr': {'equal': dap.attrib['apnum'] == '5555'}}

            compare_patch.side_effect = compare_patch_side_effect
            rv = self.wlc.check_aps()
            compare_patch.assert_has_calls([mock.call(dap_notequal),
                                            mock.call(dap_equal)])

        self.wlc.get_aps.assert_called_once_with()
        self.assertEqual(len(rv), 4)

        self.maxDiff = None

        # AP missing on WLC
        self.assertEqual(rv[ap_missing.number], {
            'result': 'missing',
            'result_verbose': 'AP missing on WLC',
            'name': ap_missing.name,
            'serial_number': ap_missing.serial_number,
            'db_ap': ap_missing,
        })

        # AP present on WLC but missing in DB
        self.assertEqual(rv[9999], {
            'result': 'unknown',
            'result_verbose': 'AP present on WLC but missing in DB',
            'name': dap_unknown.attrib['name'],
            'serial_number': dap_unknown.attrib['serial-id'],
            'raw_ap': dap_unknown,
        })

        # AP configuration mismatch
        self.assertEqual(rv[1234], {
            'result': 'mismatch',
            'result_verbose': 'AP configuration mismatch',
            'res_ok': False,
            'name': ap_notequal.name,
            'serial_number': ap_notequal.serial_number,
            'db_ap': ap_notequal,
            'raw_ap': dap_notequal,
            'cmp_res': {'attr': {'equal': False}},
        })

        # AP configuration match
        self.assertEqual(rv[5555], {
            'result': u'ok',
            'result_verbose': u'AP configuration match',
            'res_ok': True,
            'name': ap_equal.name,
            'serial_number': ap_equal.serial_number,
            'db_ap': ap_equal,
            'raw_ap': dap_equal,
            'cmp_res': {u'attr': {u'equal': True}},
        })


class AutoAccessPointTest(TestCase):
    def setUp(self):
        self.autoap = AutoAccessPointFactory(
            serial_number='0123456789',
            number=9999,
            wlc__name='WLC1',
            wlc__ip_address='1.2.3.4')

    def test_str(self):
        self.assertEqual(str(self.autoap), "0123456789 (9999@WLC1 (1.2.3.4))")

    def test_is_not_defined(self):
        AccessPointFactory(serial_number='1111111111')
        self.assertFalse(self.autoap.is_defined)

    def test_is_defined(self):
        AccessPointFactory(serial_number='0123456789')
        self.assertTrue(self.autoap.is_defined)


class AccessPointTest(TestCase):
    def setUp(self):
        self.ap = AccessPointFactory(
            serial_number='0123456789',
            fingerprint='aa:bb:cc:dd:ee:ff:aa:bb:cc:00:11:22:33:00:00:ff',
            number=1234,
            name='AP1234',
            model='MP_432',
            high_latency=True,
            radio_1_channel=14,
            radio_1_power=7,
            radio_1_profile__name='default',
            radio_2_profile__name='other_profile',
            radio_1_enable=False)

    def test_str(self):
        self.assertEqual(str(self.ap), "AP1234")

    @mock.patch('wlcmanager.models.loader')
    def test_render_xml(self, loader):
        from django.template import Template

        tmpl = '<DAP model="{{ ap.model }}" name="{{ ap.name }}">'\
               '<SOME-TAG/></DAP>'
        templates_config = [
            {
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'DIRS': [],
                'OPTIONS': {
                    'debug': False,
                    'loaders': [
                        'django.template.loaders.filesystem.Loader',
                        'django.template.loaders.app_directories.Loader',
                        ],
                    'context_processors': [
                        ],
                },
            },
        ]

        with self.settings(TEMPLATES=templates_config):
            loader.get_template.return_value = Template(tmpl)

            xml = self.ap.render_xml()

            loader.get_template.assert_called_once_with(
                'wlcmanager/wlcapi/save_ap/MP_432.xml')
            self.assertEqual(xml,
                             '<DAP model="MP_432" name="AP1234"><SOME-TAG/></DAP>')

    def test_clean(self):
        self.ap.clean()

        ap1 = AccessPointFactory.build(model='MP_432', radio_2_profile=None)
        self.assertRaises(ValidationError, ap1.clean)

        ap2 = AccessPointFactory.build(model='MP_432', radio_2_channel=None)
        self.assertRaises(ValidationError, ap2.clean)

        ap3 = AccessPointFactory.build(model='MP_432', radio_2_power=None)
        self.assertRaises(ValidationError, ap3.clean)

        ap_one_radio = AccessPointFactory(model='WLA321-WW')
        ap_one_radio.clean()

    def test_compare(self):
        dap_xml = """
            <DAP apnum="4422" fingerprint="aa:bb:cc" model="MODEL_1"
                 name="NAME_2" serial-id="123ABC" type="NG"
                 high-latency-mode="NO">
                <AP-RADIO-TABLE>
                    <AP-RADIO slot="1" auto-config="NO" channel="3"
                              enable="YES" auto-power-config="NO" tx-power="6">
                        <RADIO-PROFILE-REF name="default"/>
                    </AP-RADIO>
                    <AP-RADIO slot="2" auto-config="YES" channel="36"
                              enable="NO" auto-power-config="YES">
                        <RADIO-PROFILE-REF name="prof_name"/>
                    </AP-RADIO>
                </AP-RADIO-TABLE>
            </DAP>"""

        rv = self.ap.compare(etree.XML(dap_xml))
        self.assertEqual(rv['AP: model'], {
            'e_val': 'MODEL_1',
            'o_val': 'MP_432',
            'equal': False,
        })
        self.assertEqual(rv['AP: name'], {
            'e_val': 'NAME_2',
            'o_val': 'AP1234',
            'equal': False,
        })
        self.assertEqual(rv['AP: fingerprint'], {
            'e_val': 'aa:bb:cc',
            'o_val': 'aa:bb:cc:dd:ee:ff:aa:bb:cc:00:11:22:33:00:00:ff',
            'equal': False,
        })
        self.assertEqual(rv['AP: serial-id'], {
            'e_val': '123ABC',
            'o_val': '0123456789',
            'equal': False,
        })
        self.assertEqual(rv['AP: apnum'], {
            'e_val': '4422',
            'o_val': '1234',
            'equal': False,
        })
        self.assertEqual(rv['AP: high-latency-mode'], {
            'e_val': 'NO',
            'o_val': 'YES',
            'equal': False,
        })
        self.assertEqual(rv['Radio 1: slot'], {
            'e_val': '1',
            'o_val': '1',
            'equal': True,
        })
        self.assertEqual(rv['Radio 1: auto-config'], {
            'e_val': 'NO',
            'o_val': 'NO',
            'equal': True,
        })
        self.assertEqual(rv['Radio 1: channel'], {
            'e_val': '3',
            'o_val': 14,
            'equal': False,
        })
        self.assertEqual(rv['Radio 1: auto-power-config'], {
            'e_val': 'NO',
            'o_val': 'NO',
            'equal': True,
        })
        self.assertEqual(rv['Radio 1: tx-power'], {
            'e_val': '6',
            'o_val': 7,
            'equal': False
        })
        self.assertEqual(rv['Radio 1: enable'], {
            'e_val': 'YES',
            'o_val': 'NO',
            'equal': False,
        })
        self.assertEqual(rv['Radio 1: profile-name'], {
            'e_val': 'default',
            'o_val': 'default',
            'equal': True,
        })
        self.assertEqual(rv['Radio 2: slot'], {
            'e_val': '2',
            'o_val': '2',
            'equal': True,
        })
        self.assertEqual(rv['Radio 2: auto-config'], {
            'e_val': 'YES',
            'o_val': 'YES',
            'equal': True,
        })
        self.assertEqual(rv['Radio 2: auto-power-config'], {
            'e_val': 'YES',
            'o_val': 'YES',
            'equal': True,
        })
        self.assertEqual(rv['Radio 2: enable'], {
            'e_val': 'NO',
            'o_val': 'YES',
            'equal': False,
        })
        self.assertEqual(rv['Radio 2: profile-name'], {
            'e_val': 'other_profile',
            'o_val': 'prof_name',
            'equal': False,
        })
        self.assertEqual(len(rv), 18)
