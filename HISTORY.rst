.. :changelog:

History
-------

0.2.0 (unreleased)
++++++++++++++++++

* Added high latency mode support.
  Default value is ``false`` unless ``WLCMANAGER_HIGHLATENCY_DEFAULT`` is set
  in ``settings``. You can set it before running migrations so existing APs
  will be updated correctly.

* Added support for Django 1.9 and 1.10

* Added on_delete=models.PROTECT to Radio Profile FK

0.1.0 (2015-07-27)
++++++++++++++++++

* First release.
