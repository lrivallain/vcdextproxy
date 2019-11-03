===========
vcdextproxy
===========


.. image:: https://img.shields.io/pypi/v/vcdextproxy.svg
        :target: https://pypi.python.org/pypi/vcdextproxy

.. image:: https://img.shields.io/travis/lrivallain/vcdextproxy.svg
        :target: https://travis-ci.org/lrivallain/vcdextproxy

.. image:: https://readthedocs.org/projects/vcdextproxy/badge/?version=latest
        :target: https://vcdextproxy.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status

.. image:: https://img.shields.io/github/license/lrivallain/vcdextproxy
        :target: https://opensource.org/licenses/MIT
        :alt: MIT License


Python based proxy looking at multiple AMQP queues for incoming requests of VMware vCloud Director's API Extensions and forwarding to specified REST backends.

* Free software: MIT license
* Documentation: https://vcdextproxy.readthedocs.io.

Features
--------

* Support multiple queues subscriptions
* Can address multiple REST endpoints depending on extension(s)
* 1 REST endpoint is a associated to 1 extension in vCD
* Backend servers:
    * HTTP + HTTPS support
    * Basic authentication
    * Basic URI rewritting
* AMQP server:
    * Multiple Exchange/Queue listening
    * Manage Exchange/Queue declarations
    * SSL support
* Extension lifecyle:
    * Deploy a newly declared extension
    * Redeploy an existing extension
* vCloud Director:
    * Support vCD from 9.1 to 10.0
    * Can check user's right based on per extension setting
    * Can check organization's membership of an user

Planned features
----------------

* #6 - Address some pre-checks like rights management
* #18 - Check organization's membership of an user
* #2 - Manage extension lifecycle (deploy/re-deploy)

User case
---------

In a vCloud Director instance where 2 API extensions are used (`example1`, `example2`):


**vcdextproxy** subscribe to following AMQP queues:

* `example1`
* `example2`

When a message is sent to `example1` queue:

1. A URI path check is made: is `/api/example1` a correct API path for extension named **example1** ?
2. If valid, all fields of the request are converted to REST request (as headers or as body content)
3. REST endpoint handle the request as a standard REST one (with a lot of vCloud information...)
4. REST endpoint replies to **vcdextproxy**
5. **vcdextproxy** reformat the reply as an AMQP reply message

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
