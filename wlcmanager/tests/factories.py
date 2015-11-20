# coding: utf-8

from __future__ import (absolute_import, division,
                        print_function, unicode_literals)

import factory

from ..models import (WLC, RadioProfile, AutoAccessPoint, AccessPoint)


class WLCFactory(factory.django.DjangoModelFactory):
    class Meta(object):
        model = WLC

    name = factory.Sequence(lambda n: "WLC-{:02d}".format(n))
    ip_address = factory.Sequence(lambda n: "192.168.1.{}".format(n))
    username = 'admin'
    password = 'admin123'
    enabled = True
    master = False

    @classmethod
    def _setup_next_sequence(cls):
        return 1


class RadioProfileFactory(factory.django.DjangoModelFactory):
    class Meta(object):
        model = RadioProfile

    name = factory.Sequence(lambda n: "Radio Profile {:02d}".format(n))


class AutoAccessPointFactory(factory.django.DjangoModelFactory):
    class Meta(object):
        model = AutoAccessPoint

    wlc = factory.SubFactory(WLCFactory)
    serial_number = factory.Sequence(lambda n: "99887766{:02d}".format(n))
    fingerprint = factory.Sequence(lambda n: "aa:bb:cc:dd:ee:ff:aa:bb:cc:"
                                   "dd:ee:ff:aa:bb:cc:{:02d}".format(n))
    number = factory.Sequence(lambda n: 8000 + n)
    model = 'MP_432'
    ip_address = factory.Sequence(lambda n: "192.168.1.{}".format(n))


class AccessPointFactory(factory.django.DjangoModelFactory):
    class Meta(object):
        model = AccessPoint
    number = factory.Sequence(lambda n: 8000 + n)
    fingerprint = factory.Sequence(lambda n: "aa:bb:cc:dd:ee:ff:aa:bb:cc:"
                                   "dd:ee:ff:aa:bb:cc:{:02d}".format(n))
    model = 'MP_432'
    name = factory.Sequence(lambda n: "AP{:04d}".format(n))
    serial_number = factory.Sequence(lambda n: "99887766{:02d}".format(n))
    radio_1_profile = factory.SubFactory(RadioProfileFactory)
    radio_1_channel = 0
    radio_1_power = 0
    radio_1_enable = True
    radio_2_profile = factory.SubFactory(RadioProfileFactory)
    radio_2_channel = 0
    radio_2_power = 0
    radio_2_enable = True
    high_latency = False
