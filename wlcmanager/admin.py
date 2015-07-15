# coding: utf-8

from django.conf.urls import patterns, url
from django.contrib import admin
from django.contrib import messages
from django.http import (HttpResponseRedirect, HttpResponseNotAllowed,
                         HttpResponseBadRequest)
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse


from .models import WLC, AutoAccessPoint, AccessPoint, RadioProfile
from .utils import compare_config, get_free_from_sequence, run_each_context


class WLCAdmin(admin.ModelAdmin):
    list_display = ['name', 'ip_address', 'username', 'enabled', 'master',
                    'compare_config_url', 'check_aps_url']

    def compare_config_url(self, obj):
        if obj.master:
            return ''
        url_fmt = '<a href="compare_config/{}">{}</a>'
        return url_fmt.format(obj.pk, 'Compare configuration')
    compare_config_url.allow_tags = True
    compare_config_url.short_description = 'Compare'

    def check_aps_url(self, obj):
        url_fmt = '<a href="check_aps/{}">{}</a>'
        return url_fmt.format(obj.pk, 'Check APs')
    check_aps_url.allow_tags = True
    check_aps_url.short_description = 'Check APs'

    def get_urls(self):
        urls = super(WLCAdmin, self).get_urls()
        my_urls = patterns(
            "",
            url(r'compare_config/(?P<wlc_id>[0-9]+)',
                self.admin_site.admin_view(self.compare_config_view)),
            url(r'check_aps/(?P<wlc_id>[0-9]+)',
                self.admin_site.admin_view(self.check_aps_view)),
            url(r'delete_ap/(?P<wlc_id>[0-9]+)',
                self.admin_site.admin_view(self.delete_ap_view),
                name='wlcmanager-delete-ap'),
            url(r'save_ap/(?P<wlc_id>[0-9]+)',
                self.admin_site.admin_view(self.save_ap_view),
                name='wlcmanager-save-ap'),
            url(r'save_aps/(?P<wlc_id>[0-9]+)',
                self.admin_site.admin_view(self.save_many_aps_view),
                name='wlcmanager-save-many-aps'),
        )
        return my_urls + urls

    def compare_config_view(self, request, wlc_id):
        wlc = get_object_or_404(WLC, pk=wlc_id)

        res = None
        master_wlc = None
        try:
            master_wlc = WLC.objects.get(master__exact=True)
            res = compare_config(wlc, master_wlc)
        except RuntimeError as e:
            msg = "Error while fetching data: {}"
            self.message_user(request, msg.format(e),
                              level=messages.ERROR)
        except WLC.DoesNotExist as e:
            msg = "There is no master WLC defined."
            self.message_user(request, msg, level=messages.ERROR)

        context = dict(
            # Include common variables for rendering the admin template.
            run_each_context(self.admin_site, request),
            # Anything else you want in the context...
            key=wlc_id,
            opts=self.model._meta,
            wlc=wlc,
            master_wlc=master_wlc,
            results=res,
            media=self.media,

        )

        return TemplateResponse(request,
                                "wlcmanager/admin/compare_config.html",
                                context)

    def check_aps_view(self, request, wlc_id):
        wlc = get_object_or_404(WLC, pk=wlc_id)

        results = wlc.check_aps()

        context = dict(
            # Include common variables for rendering the admin template.
            run_each_context(self.admin_site, request),
            # Anything else you want in the context...
            key=wlc_id,
            opts=self.model._meta,
            wlc=wlc,
            results=results,
            media=self.media,
        )

        return TemplateResponse(request,
                                "wlcmanager/admin/check_aps.html",
                                context)

    def delete_ap_view(self, request, wlc_id):
        if request.method != 'POST':
            return HttpResponseNotAllowed(('POST',))

        wlc = get_object_or_404(WLC, pk=wlc_id)

        try:
            ap_number = request.POST['ap_number']
        except KeyError:
            return HttpResponseBadRequest()

        errors = wlc.delete_ap(ap_number)

        if errors:
            msg = "Unable to delete AP {}"
            self.message_user(request, msg.format(ap_number),
                              level=messages.ERROR)
            for err in errors.itervalues():
                self.message_user(request, err,
                                  level=messages.ERROR)
        else:
            msg = "AP {} deleted"
            self.message_user(request, msg.format(ap_number),
                              level=messages.ERROR)
        return HttpResponseRedirect(request.META["HTTP_REFERER"])

    def save_ap_view(self, request, wlc_id):
        if request.method != 'POST':
            return HttpResponseNotAllowed(('POST',))

        try:
            wlc = WLC.objects.get(pk=wlc_id)
        except WLC.DoesNotExist:
            raise Http404

        try:
            ap_number = request.POST['ap_number']
            ap = AccessPoint.objects.get(number__exact=ap_number)
        except KeyError:
            return HttpResponseBadRequest()
        except AccessPoint.DoesNotExist:
            msg = "AP {} not found"
            self.message_user(request, msg.format(ap_number),
                              level=messages.ERROR)
            return HttpResponseRedirect(request.META["HTTP_REFERER"])

        try:
            wlc.save_ap(ap)
        except RuntimeError as e:
            msg = "Error while saving AP {}@{}: {}"
            self.message_user(request, msg.format(ap_number, wlc, e),
                              level=messages.ERROR)
        return HttpResponseRedirect(request.META["HTTP_REFERER"])

    def save_many_aps_view(self, request, wlc_id):
        if request.method != 'POST':
            return HttpResponseNotAllowed(('POST',))

        try:
            wlc = WLC.objects.get(pk=wlc_id)
        except WLC.DoesNotExist:
            raise Http404

        try:
            ap_numbers = request.POST['ap_numbers'].strip(',').split(',')
        except KeyError:
            return HttpResponseBadRequest()

        if ap_numbers==['']:
            msg = "AP list is empty"
            self.message_user(request, msg, level=messages.ERROR)
            ap_numbers=[]

        for ap_number in ap_numbers:
            try:
                ap = AccessPoint.objects.get(number__exact=ap_number)
                #print("Zapisuje {}".format(ap))
                wlc.save_ap(ap)
            except AccessPoint.DoesNotExist:
                msg = "AP {} not found"
                self.message_user(request, msg.format(ap_number),
                                  level=messages.ERROR)
            except RuntimeError as e:
                msg = "Error while saving AP {}@{}: {}"
                self.message_user(request, msg.format(ap_number, wlc, e),
                                  level=messages.ERROR)
        return HttpResponseRedirect(request.META["HTTP_REFERER"])

    class Media(object):
        js = ('admin/js/collapse.js',)
        css = {
            'all': ('admin/css/base.css', 'admin/css/forms.css'),
        }
admin.site.register(WLC, WLCAdmin)


class AutoAccessPointAdmin(admin.ModelAdmin):
    list_display = ['serial_number', 'wlc', 'number', 'model', 'ip_address',
                    'create_ap_url']

    def get_urls(self):
        urls = super(AutoAccessPointAdmin, self).get_urls()
        my_urls = patterns(
            "",
            url(r"^refresh/$", self.admin_site.admin_view(
                self.refresh_autoaps)),
        )
        return my_urls + urls

    def create_ap_url(self, obj):
        if not obj.is_defined:
            return '<a href="{}{}">{}</a>'.format(
                '/admin/wlcmanager/accesspoint/add/?auto_sn=',
                obj.serial_number, 'Create AP')
        return ''
    create_ap_url.allow_tags = True
    create_ap_url.short_description = 'Create AP'

    def refresh_autoaps(self, request):
        for wlc in WLC.objects.filter(enabled__exact=True):
            try:
                wlc.refresh_autoaps()
            except RuntimeError as e:
                msg = "Error while fetching AP data from {}: {}"
                self.message_user(request, msg.format(wlc, e),
                                  level=messages.ERROR)
                # base-mac-addr
                # primary-ip
        return HttpResponseRedirect(request.META["HTTP_REFERER"])
admin.site.register(AutoAccessPoint, AutoAccessPointAdmin)


class RadioProfileAdmin(admin.ModelAdmin):
    list_display = ['name']

    def get_urls(self):
        urls = super(RadioProfileAdmin, self).get_urls()
        my_urls = patterns(
            "",
            url(r"^refresh/$", self.admin_site.admin_view(
                self.refresh_profiles)),
        )
        return my_urls + urls

    def refresh_profiles(self, request):
        try:
            wlc = WLC.objects.get(master__exact=True)
            wlc.refresh_radio_profiles()
        except WLC.DoesNotExist as e:
            msg = "There is no master WLC defined."
            self.message_user(request, msg, level=messages.ERROR)
        except RuntimeError as e:
            msg = "Error while fetching data: {}"
            self.message_user(request, msg.format(e),
                              level=messages.ERROR)

        return HttpResponseRedirect(request.META["HTTP_REFERER"])

admin.site.register(RadioProfile, RadioProfileAdmin)


class AccessPointAdmin(admin.ModelAdmin):
    list_display = ['name', 'number', 'serial_number', 'model',
                    'radio_1_profile', 'radio_2_profile']  # , 'save_ap_url']
    search_fields = ['name', 'number', 'serial_number']

    fieldsets = (
        (None, {
            'classes': ('wlcmanager_ap_form', ),
            'fields': ('number', 'fingerprint', 'model', 'name',
                       'serial_number', 'description', 'location'),
        }),
        ('Radio 1', {
            'classes': ('wlcmanager_ap_form', ),
            'fields': ('radio_1_enable', 'radio_1_profile', 'radio_1_channel',
                       'radio_1_power',),
        }),
        ('Radio 2', {
            'classes': ('collapse', 'wlcmanager_ap_form'),
            'fields': ('radio_2_enable', 'radio_2_profile', 'radio_2_channel',
                       'radio_2_power',),
        }),
    )

    def add_view(self, request, form_url='', extra_context=None):
        print('add_view')
        print(request.GET)
        try:
            auto_ap_sn = request.GET['auto_sn']

            auto_ap = AutoAccessPoint.objects.get(
                serial_number__exact=auto_ap_sn)

            print(auto_ap)

            used_numbers = AccessPoint.objects.values_list('number', flat=True)

            g = request.GET.copy()
            g.update({
                'serial_number': auto_ap.serial_number,
                'fingerprint': auto_ap.fingerprint,
                'number': get_free_from_sequence(used_numbers),
                'model': auto_ap.model,
            })
            request.GET = g
        except KeyError:
            pass
        except AutoAccessPoint.DoesNotExist:
            msg = "There is no auto AP with S/N: {}"
            self.message_user(request, msg.format(auto_ap_sn),
                              level=messages.ERROR)
        print(request.GET)
        return super(AccessPointAdmin, self).add_view(
            request, form_url=form_url, extra_context=extra_context)
admin.site.register(AccessPoint, AccessPointAdmin)
