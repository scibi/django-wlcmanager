# coding: utf-8

from __future__ import (absolute_import, division,
                        print_function, unicode_literals)

import mock

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import AnonymousUser
from django.contrib import messages
from django.http import Http404
from django.http import HttpRequest
from django.test import TestCase


from ..admin import (WLCAdmin, AutoAccessPointAdmin, RadioProfileAdmin,
                     AccessPointAdmin)
from ..models import WLC, AutoAccessPoint, RadioProfile, AccessPoint

from .factories import WLCFactory, AccessPointFactory, AutoAccessPointFactory

#        RadioProfileFactory


class WLCAdminTest(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.wa = WLCAdmin(WLC, self.site)
        self.wa.message_user = mock.MagicMock()

    def test_compare_config_url_master(self):
        wlc = WLCFactory(master=True)
        rv = self.wa.compare_config_url(wlc)

        self.assertEqual(rv, '')

    def test_compare_config_url_not_master(self):
        wlc = WLCFactory(master=False)
        rv = self.wa.compare_config_url(wlc)

        self.assertRegexpMatches(rv, 'href="compare_config/{}"'.format(wlc.id))

    def test_check_aps_url(self):
        wlc = WLCFactory()
        rv = self.wa.check_aps_url(wlc)

        self.assertRegexpMatches(rv, 'href="check_aps/{}"'.format(wlc.id))

    def test_compare_config_view_no_wlc(self):
        request = HttpRequest()
        self.assertRaises(Http404, self.wa.compare_config_view, request, 1234)

    def test_compare_config_view_no_master_wlc(self):
        request = HttpRequest()
        request.user = AnonymousUser()
        wlc = WLCFactory(master=False)

        response = self.wa.compare_config_view(request, wlc.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['results'], None)
        self.wa.message_user.assert_called_once_with(
            request, 'There is no master WLC defined.', level=messages.ERROR)

    def test_compare_config_view_compare_config_exception(self):
        request = HttpRequest()
        request.user = AnonymousUser()
        wlc = WLCFactory(master=False)
        WLCFactory(master=True)  # Just generate one master

        with mock.patch('wlcmanager.admin.compare_config') \
                as compare_config_mock:
            compare_config_mock.side_effect = RuntimeError('some error')
            response = self.wa.compare_config_view(request, wlc.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['results'], None)
        self.wa.message_user.assert_called_once_with(
            request, 'Error while fetching data: some error',
            level=messages.ERROR)

    def test_compare_config_view_ok(self):
        request = HttpRequest()
        request.user = AnonymousUser()
        wlc = WLCFactory(master=False)
        master_wlc = WLCFactory(master=True)

        with mock.patch('wlcmanager.admin.compare_config') \
                as compare_config_mock:
            response = self.wa.compare_config_view(request, wlc.id)

            compare_config_mock.assert_called_once_with(wlc, master_wlc)
            self.assertEqual(response.context_data['results'],
                             compare_config_mock.return_value)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['wlc'], wlc)
        self.assertEqual(response.context_data['master_wlc'], master_wlc)

    def test_check_aps_view_no_wlc(self):
        request = HttpRequest()
        self.assertRaises(Http404, self.wa.check_aps_view, request, 1234)

    def test_check_aps_view_ok(self):
        request = HttpRequest()
        request.user = AnonymousUser()
        wlc = WLCFactory(master=False)

        with mock.patch('wlcmanager.models.WLC.check_aps') \
                as check_aps_mock:
            response = self.wa.check_aps_view(request, wlc.id)

            check_aps_mock.assert_called_once_with()
            self.assertEqual(response.context_data['results'],
                             check_aps_mock.return_value)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['wlc'], wlc)

    def test_delete_ap_view_get(self):
        # Wrong method (GET instead of POST)
        request = HttpRequest()

        with mock.patch('wlcmanager.models.WLC.delete_ap') \
                as delete_ap_mock:
            response = self.wa.delete_ap_view(request, 1234)

            self.assertFalse(delete_ap_mock.called)

        self.assertEqual(response.status_code, 405)

    def test_delete_ap_view_post_no_wlc(self):
        # Wrong method (GET instead of POST)
        request = HttpRequest()
        request.method = 'POST'

        self.assertRaises(Http404, self.wa.delete_ap_view, request, 1234)

    def test_delete_ap_view_post_no_ap_number(self):
        # Wrong method (GET instead of POST)
        request = HttpRequest()
        request.method = 'POST'

        wlc = WLCFactory(master=False)

        with mock.patch('wlcmanager.models.WLC.delete_ap') \
                as delete_ap_mock:
            response = self.wa.delete_ap_view(request, wlc.id)

            self.assertFalse(delete_ap_mock.called)

        self.assertEqual(response.status_code, 400)

    def test_delete_ap_view_post_delete_error(self):
        ap_num = 123
        request = HttpRequest()
        request.method = 'POST'
        request.POST['ap_number'] = ap_num
        request.META['HTTP_REFERER'] = 'http://google.com/'

        wlc = WLCFactory(master=False)

        with mock.patch('wlcmanager.models.WLC.delete_ap') \
                as delete_ap_mock:
            delete_ap_mock.return_value = {1: 'err1', 2: 'err2'}

            response = self.wa.delete_ap_view(request, wlc.id)

            delete_ap_mock.assert_called_once_with(ap_num)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, request.META['HTTP_REFERER'])
        self.wa.message_user.assert_has_calls([
            mock.call(request, 'Unable to delete AP {}'.format(ap_num),
                      level=messages.ERROR),
            mock.call(request, 'err2', level=messages.ERROR),
            mock.call(request, 'err1', level=messages.ERROR),
        ], any_order=True)

    def test_delete_ap_view_post_ok(self):
        ap_num = 123
        request = HttpRequest()
        request.method = 'POST'
        request.POST['ap_number'] = ap_num
        request.META['HTTP_REFERER'] = 'http://google.com/'

        wlc = WLCFactory(master=False)

        with mock.patch('wlcmanager.models.WLC.delete_ap') \
                as delete_ap_mock:
            delete_ap_mock.return_value = False   # No errors

            response = self.wa.delete_ap_view(request, wlc.id)

            delete_ap_mock.assert_called_once_with(ap_num)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, request.META['HTTP_REFERER'])
        self.wa.message_user.assert_called_once_with(
            request, 'AP {} deleted'.format(ap_num), level=messages.ERROR)

    def test_save_ap_view_get(self):
        # Wrong method (GET instead of POST)
        request = HttpRequest()

        with mock.patch('wlcmanager.models.WLC.save_ap') \
                as save_ap_mock:
            response = self.wa.save_ap_view(request, 1234)

            self.assertFalse(save_ap_mock.called)

        self.assertEqual(response.status_code, 405)

    def test_save_ap_view_post_no_wlc(self):
        # Wrong method (GET instead of POST)
        request = HttpRequest()
        request.method = 'POST'

        self.assertRaises(Http404, self.wa.save_ap_view, request, 1234)

    def test_save_ap_view_post_no_ap_number(self):
        # Wrong method (GET instead of POST)
        request = HttpRequest()
        request.method = 'POST'

        wlc = WLCFactory(master=False)

        with mock.patch('wlcmanager.models.WLC.save_ap') \
                as save_ap_mock:
            response = self.wa.save_ap_view(request, wlc.id)

            self.assertFalse(save_ap_mock.called)

        self.assertEqual(response.status_code, 400)

    def test_save_ap_view_post_wrong_number(self):
        ap_num = 7788
        request = HttpRequest()
        request.method = 'POST'
        request.POST['ap_number'] = ap_num
        request.META['HTTP_REFERER'] = 'http://google.com/'

        wlc = WLCFactory(master=False)

        with mock.patch('wlcmanager.models.WLC.save_ap') \
                as save_ap_mock:

            response = self.wa.save_ap_view(request, wlc.id)

            self.assertFalse(save_ap_mock.called)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, request.META['HTTP_REFERER'])
        self.wa.message_user.assert_called_once_with(
            request, 'AP {} not found'.format(ap_num), level=messages.ERROR)

    def test_save_ap_view_post_save_error(self):
        wlc = WLCFactory(master=False)
        ap = AccessPointFactory()
        request = HttpRequest()
        request.method = 'POST'
        request.POST['ap_number'] = ap.number
        request.META['HTTP_REFERER'] = 'http://google.com/'

        with mock.patch('wlcmanager.models.WLC.save_ap') \
                as save_ap_mock:
            save_ap_mock.side_effect = RuntimeError('some error')

            response = self.wa.save_ap_view(request, wlc.id)

            save_ap_mock.assert_called_once_with(ap)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, request.META['HTTP_REFERER'])
        self.wa.message_user.assert_called_once_with(
            request, 'Error while saving AP {}@{}: some error'.format(
                ap.number, wlc),
            level=messages.ERROR)

    def test_save_ap_view_post_ok(self):
        wlc = WLCFactory(master=False)
        ap = AccessPointFactory()

        request = HttpRequest()
        request.method = 'POST'
        request.POST['ap_number'] = ap.number
        request.META['HTTP_REFERER'] = 'http://google.com/'

        with mock.patch('wlcmanager.models.WLC.save_ap') \
                as save_ap_mock:
            response = self.wa.save_ap_view(request, wlc.id)

            save_ap_mock.assert_called_once_with(ap)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, request.META['HTTP_REFERER'])


class AutoAccessPointAdminTest(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.aaa = AutoAccessPointAdmin(AutoAccessPoint, self.site)
        self.aaa.message_user = mock.MagicMock()

    def test_compare_config_url_master_defined(self):
        autoap = mock.MagicMock()
        autoap.is_defined = True
        autoap.serial_number = 1234
        rv = self.aaa.create_ap_url(autoap)

        self.assertEqual(rv, '')

    def test_compare_config_url_master_not_defined(self):
        autoap = mock.MagicMock()
        autoap.is_defined = False
        autoap.serial_number = 1234
        rv = self.aaa.create_ap_url(autoap)

        self.assertRegexpMatches(rv, 'accesspoint/add/\?auto_sn={}'.format(
            autoap.serial_number))

    def test_refresh_autoaps_not_enabled(self):
        request = HttpRequest()
        request.META['HTTP_REFERER'] = 'http://google.com/'

        wlc = WLCFactory(enabled=False)  # noqa

        with mock.patch('wlcmanager.models.WLC.refresh_autoaps') \
                as refresh_autoaps_mock:
            response = self.aaa.refresh_autoaps(request)

            self.assertFalse(refresh_autoaps_mock.called)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, request.META['HTTP_REFERER'])

    def test_refresh_autoaps_failed(self):
        request = HttpRequest()
        request.META['HTTP_REFERER'] = 'http://google.com/'

        wlc = WLCFactory(enabled=True)

        with mock.patch('wlcmanager.models.WLC.refresh_autoaps') \
                as refresh_autoaps_mock:

            refresh_autoaps_mock.side_effect = RuntimeError('some error')

            response = self.aaa.refresh_autoaps(request)

            refresh_autoaps_mock.assert_called_once_with()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, request.META['HTTP_REFERER'])
        self.aaa.message_user.assert_called_once_with(
            request, 'Error while fetching AP data from {}: some error'.format(
                wlc), level=messages.ERROR)

    def test_refresh_autoaps_ok(self):
        request = HttpRequest()
        request.META['HTTP_REFERER'] = 'http://google.com/'

        wlc1 = WLCFactory(enabled=True)  # noqa
        wlc2 = WLCFactory(enabled=True)  # noqa

        with mock.patch('wlcmanager.models.WLC.refresh_autoaps') \
                as refresh_autoaps_mock:

            response = self.aaa.refresh_autoaps(request)

            self.assertEqual(refresh_autoaps_mock.call_count, 2)
            refresh_autoaps_mock.assert_called_with()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, request.META['HTTP_REFERER'])
        self.assertFalse(self.aaa.message_user.called)


class RadioProfileAdminTest(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.rpa = RadioProfileAdmin(RadioProfile, self.site)
        self.rpa.message_user = mock.MagicMock()

    def test_refresh_profiles_failed(self):
        request = HttpRequest()
        request.META['HTTP_REFERER'] = 'http://google.com/'

        wlc = WLCFactory(master=True)  # noqa

        with mock.patch('wlcmanager.models.WLC.refresh_radio_profiles') \
                as refresh_radio_profiles_mock:

            refresh_radio_profiles_mock.side_effect = RuntimeError(
                'some error')

            response = self.rpa.refresh_profiles(request)

            refresh_radio_profiles_mock.assert_called_once_with()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, request.META['HTTP_REFERER'])
        self.rpa.message_user.assert_called_once_with(
            request, 'Error while fetching data: some error',
            level=messages.ERROR)

    def test_refresh_profiles_no_master(self):
        request = HttpRequest()
        request.META['HTTP_REFERER'] = 'http://google.com/'

        wlc = WLCFactory(master=False)  # noqa

        with mock.patch('wlcmanager.models.WLC.refresh_radio_profiles') \
                as refresh_radio_profiles_mock:

            response = self.rpa.refresh_profiles(request)

            self.assertFalse(refresh_radio_profiles_mock.called)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, request.META['HTTP_REFERER'])
        self.rpa.message_user.assert_called_once_with(
            request, 'There is no master WLC defined.', level=messages.ERROR)

    def test_refresh_profiles_ok(self):
        request = HttpRequest()
        request.META['HTTP_REFERER'] = 'http://google.com/'

        wlc = WLCFactory(master=True)  # noqa

        with mock.patch('wlcmanager.models.WLC.refresh_radio_profiles') \
                as refresh_radio_profiles_mock:

            response = self.rpa.refresh_profiles(request)

            refresh_radio_profiles_mock.assert_called_once_with()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, request.META['HTTP_REFERER'])
        self.assertFalse(self.rpa.message_user.called)


class AccessPointAdminTest(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.apa = AccessPointAdmin(AccessPoint, self.site)
        self.apa.message_user = mock.MagicMock()

    def test_add_view_no_auto_sn(self):
        request = HttpRequest()
        form_url = 'some url'
        extra_context = 'some value'

        with mock.patch('django.contrib.admin.ModelAdmin.add_view') as ma_mock:
            self.apa.add_view(request, form_url=form_url,
                              extra_context=extra_context)

            ma_mock.assert_called_once_with(request, form_url=form_url,
                                            extra_context=extra_context)

        self.assertFalse(self.apa.message_user.called)

    def test_add_view_autoap_doesnt_exists(self):
        request = HttpRequest()
        request.GET['auto_sn'] = '123456'
        form_url = 'some url'
        extra_context = 'some value'

        with mock.patch('django.contrib.admin.ModelAdmin.add_view') as ma_mock:
            self.apa.add_view(request, form_url=form_url,
                              extra_context=extra_context)

            ma_mock.assert_called_once_with(request, form_url=form_url,
                                            extra_context=extra_context)

        self.apa.message_user.assert_called_once_with(
            request, 'There is no auto AP with S/N: {}'.format(
                request.GET['auto_sn']), level=messages.ERROR)

    def test_add_view_ok(self):
        request = HttpRequest()
        form_url = 'some url'
        extra_context = 'some value'

        autoap = AutoAccessPointFactory()
        request.GET['auto_sn'] = autoap.serial_number

        with mock.patch('django.contrib.admin.ModelAdmin.add_view') \
                as add_view_mock:
            self.apa.add_view(request, form_url=form_url,
                              extra_context=extra_context)

            add_view_mock.assert_called_once_with(request, form_url=form_url,
                                                  extra_context=extra_context)

        # request is modified in add_view
        self.assertEqual(request.GET['serial_number'], autoap.serial_number)
        self.assertEqual(request.GET['model'], autoap.model)
        # There are no APs present so the new AP should have number 1
        self.assertEqual(request.GET['number'], 1)
        self.assertEqual(request.GET['fingerprint'], autoap.fingerprint)

        self.assertFalse(self.apa.message_user.called)
