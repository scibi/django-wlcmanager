# coding: utf-8

from __future__ import (absolute_import, division,
                        print_function, unicode_literals)

from django.core.exceptions import ValidationError
from django.db import models
from django.db import transaction
from django.template import Context
from django.template import loader
from django.utils.encoding import python_2_unicode_compatible

from jnpr import wlc as jnpr_wlc


@python_2_unicode_compatible
class WLC(models.Model):
    name = models.CharField(max_length=64, unique=True)
    ip_address = models.GenericIPAddressField(verbose_name='IP address',
                                              unique=True)
    username = models.CharField(max_length=64)
    password = models.CharField(max_length=64)
    enabled = models.BooleanField(default=True)
    master = models.BooleanField(default=False)

    def __str__(self):
        return '{} ({})'.format(self.name, self.ip_address)

    def clean(self):
        """Make sure that there is only one master"""
        if self.master:
            try:
                wlc = WLC.objects.exclude(pk=self.pk).get(master__exact=True)
                raise ValidationError('Only one master is permited. '
                                      'Current master: {}'.format(wlc))
            except WLC.DoesNotExist:
                pass

    def make_connection(self):
        wlc = jnpr_wlc.WirelessLanController(host=self.ip_address,
                                             user=self.username,
                                             password=self.password)
        wlc.open()
        return wlc

    @property
    def connection(self):
        try:
            self._connection
        except AttributeError:
            self._connection = self.make_connection()

        return self._connection

    def get_auto_aps(self):
        announce_table = \
            self.connection.rpc.get_stat_dap_announce_status_table()
        auto_aps = \
            announce_table.findall(".//DAP-ANNOUNCE-STATUS[@status='AUTO']")
        return [ap.attrib for ap in auto_aps]

    def get_aps(self):
        ap_list = self.connection.rpc.get_dap()
        return ap_list

    def get_radio_profiles(self):
        rp_list = self.connection.rpc.get_radio_profile()
        return rp_list

    @transaction.atomic
    def refresh_radio_profiles(self):
        RadioProfile.objects.all().delete()
        for radio_profile in self.get_radio_profiles():
            RadioProfile.objects.create(name=radio_profile.attrib['name'])

    @transaction.atomic
    def refresh_autoaps(self):
        self.autoaccesspoint_set.all().delete()
        for ap in self.get_auto_aps():
            self.autoaccesspoint_set.create(serial_number=ap['serial-id'],
                                            fingerprint=ap['fingerprint'],
                                            number=ap['dapnum'],
                                            model=ap['model'],
                                            ip_address=ap['ip-addr'])
            # base-mac-addr
            # primary-ip

    def delete_ap(self, ap_number):

        """Delete AP on WLC.

        Returns:
            None on success or errors dictionary on failure.
        """

        try:
            self.connection.rpc.delete_dap(apnum=ap_number)
        except jnpr_wlc.RpcError as e:
            return e.errors

    def save_ap(self, ap):
        return self._save_aps([ap])

    def _save_aps(self, ap_iter):
        from lxml.builder import E
        from lxml import etree

        rpc = self.connection.RpcMaker('set')
        rpc.data = E('DAP-TABLE')

        for ap in ap_iter:
            apxml = ap.render_xml()
            rpc.data.append(etree.XML(apxml))

        rpc()

    def check_aps(self):
        res = self.get_aps()

        configured_ap_numbers = set(AccessPoint.objects.values_list('number',
                                                                    flat=True))
        present_ap_numbers = set([int(ap.attrib['apnum']) for ap in res])

        ap_dict = {int(ap.attrib['apnum']): ap for ap in res}

        results = {}
        for apnum in sorted(configured_ap_numbers | present_ap_numbers):
            if apnum not in configured_ap_numbers:
                raw_ap = ap_dict[apnum]
                results[apnum] = dict(
                    result='unknown',
                    result_verbose='AP present on WLC but missing in DB',
                    raw_ap=raw_ap,
                    serial_number=raw_ap.attrib['serial-id'],
                    name=raw_ap.attrib['name'],
                )
            elif apnum not in present_ap_numbers:
                db_ap = AccessPoint.objects.get(number__exact=apnum)
                results[apnum] = dict(
                    result='missing',
                    result_verbose='AP missing on WLC',
                    db_ap=db_ap,
                    serial_number=db_ap.serial_number,
                    name=db_ap.name,
                )
            else:
                db_ap = AccessPoint.objects.get(number__exact=apnum)
                raw_ap = ap_dict[apnum]
                cmp_res = db_ap.compare(raw_ap)
                res_ok = all([r['equal'] for r in cmp_res.itervalues()])
                results[apnum] = dict(
                    result='ok' if res_ok else 'mismatch',
                    result_verbose='AP configuration match' if res_ok else
                                   'AP configuration mismatch',
                    raw_ap=raw_ap,
                    db_ap=db_ap,
                    serial_number=db_ap.serial_number,
                    name=db_ap.name,
                    cmp_res=cmp_res,
                    res_ok=res_ok,
                )

        return results

    class Meta(object):
        verbose_name = 'WLC'
        ordering = ['name']


@python_2_unicode_compatible
class AutoAccessPoint(models.Model):
    wlc = models.ForeignKey(WLC, verbose_name='WLC')
    serial_number = models.CharField(max_length=64, primary_key=True)
    fingerprint = models.CharField(max_length=64)
    number = models.IntegerField('AP number')
    model = models.CharField(max_length=16)
    ip_address = models.GenericIPAddressField(verbose_name='IP address',
                                              unique=True)

    def __str__(self):
        return '{} ({}@{})'.format(self.serial_number, self.number, self.wlc)

    @property
    def is_defined(self):
        try:
            AccessPoint.objects.get(serial_number__exact=self.serial_number)
            return True
        except AccessPoint.DoesNotExist:
            pass
        return False

    class Meta(object):
        ordering = ['serial_number']


@python_2_unicode_compatible
class RadioProfile(models.Model):
    name = models.CharField(max_length=64, primary_key=True)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class AccessPoint(models.Model):
    MODELS = (
        ('WLA321-WW', 'WLA321-WW'),
        ('WLA322-WW', 'WLA322-WW'),
        ('MP_432', 'MP-432'),
        ('MP_522', 'MP-522'),
    )
    RADIO_COUNT = {
        'MP_432': 2,
        'MP_522': 2,
        'WLA321-WW': 1,
        'WLA322-WW': 2,
    }
    number = models.IntegerField(primary_key=True)
    fingerprint = models.CharField(max_length=64)
    model = models.CharField(max_length=16, choices=MODELS)
    name = models.CharField(max_length=64, unique=True)
    serial_number = models.CharField(max_length=16, unique=True)
    description = models.CharField(max_length=128)
    location = models.CharField(max_length=128)
    radio_1_profile = models.ForeignKey(RadioProfile, related_name='+')
    radio_1_channel = models.IntegerField(default=0, help_text="0 = auto")
    radio_1_power = models.IntegerField(default=0, help_text="0 = auto")
    radio_1_enable = models.BooleanField(default=True)
    radio_2_profile = models.ForeignKey(RadioProfile, related_name='+',
                                        null=True, blank=True)
    radio_2_channel = models.IntegerField(default=0, null=True, blank=True)
    radio_2_power = models.IntegerField(default=0, null=True, blank=True)
    radio_2_enable = models.BooleanField(default=False)

    class Meta(object):
        ordering = ['name']

    def __str__(self):
        return self.name

    def render_xml(self):
        """Render model specific XML to be send to WLC"""
        context = Context({'ap': self})
        template = loader.get_template(
            'wlcmanager/wlcapi/save_ap/{}.xml'.format(self.model))
        return template.render(context)

    def compare(self, dap):
        attr_map = {
            'apnum': str(self.number),
            'fingerprint': self.fingerprint,
            'model': self.model,
            'name': self.name,
            'serial-id': self.serial_number,
        }
        results = self.cmp_elem_attr(dap, attr_map, 'AP: {}')

        radio_list = dap.xpath('.//AP-RADIO')
        for radio in radio_list:
            rnum = radio.attrib['slot']
            attr_map = {
                'slot': rnum,
                'auto-config': 'NO',
                'auto-power-config': 'NO',
                'enable': 'NO',
            }
            if getattr(self, 'radio_{}_enable'.format(rnum)):
                attr_map['enable'] = 'YES'

            if getattr(self, 'radio_{}_channel'.format(rnum)) == 0:
                attr_map['auto-config'] = 'YES'
            else:
                attr_map['channel'] = getattr(self,
                                              'radio_{}_channel'.format(rnum))

            if getattr(self, 'radio_{}_power'.format(rnum)) == 0:
                attr_map['auto-power-config'] = 'YES'
            else:
                attr_map['tx-power'] = getattr(self,
                                               'radio_{}_power'.format(rnum))

            radio_results = self.cmp_elem_attr(radio, attr_map,
                                               "Radio {}: {}".format(rnum,
                                                                     '{}'))

            radio_profile = getattr(self, 'radio_{}_profile'.format(rnum))

            e_val = radio_profile.name if radio_profile else None
            o_val = radio[0].attrib['name']
            radio_results['Radio {}: profile-name'.format(rnum)] = dict(
                equal=(e_val == o_val),
                e_val=e_val,
                o_val=o_val)

            results.update(radio_results)
        return results

    def cmp_elem_attr(self, elem, attr_map, kfmt='{}'):
        res = {}
        for k, v in attr_map.iteritems():
            e_val = elem.attrib[k]
            o_val = v
            res[kfmt.format(k)] = dict(
                equal=(e_val == o_val),
                e_val=e_val,
                o_val=o_val)
        return res

    def clean(self):
        """Make sure that radio 2 properties are set if there are 2 radios"""
        if AccessPoint.RADIO_COUNT[self.model] > 1:
            msg = 'For model {} radio 2 {} has to be set.'
            if self.radio_2_profile is None:
                raise ValidationError(msg.format(self.get_model_display(),
                                                 'profile'))

            if self.radio_2_channel is None:
                raise ValidationError(msg.format(self.get_model_display(),
                                                 'channel'))

            if self.radio_2_power is None:
                raise ValidationError(msg.format(self.get_model_display(),
                                                 'power'))
