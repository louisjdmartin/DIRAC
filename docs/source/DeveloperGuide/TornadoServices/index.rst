===========================
HTTPS Services with Tornado
===========================


*******
Service
*******

.. graphviz::

   digraph {
   TornadoServer -> YourServiceHandler [label=use];
   YourServiceHandler ->  TornadoService[label=inherit];
   

   TornadoServer  [shape=polygon,sides=4, label = "DIRAC.TornadoServices.Server.TornadoServer"];
   TornadoService  [shape=polygon,sides=4, label = "DIRAC.TornadoServices.Server.TornadoService"];
   YourServiceHandler  [shape=polygon,sides=4];

   }

Service returns to Client S_OK/S_ERROR encoded in JSON

*********************************************************
Important changes between DISET server and Tornado Server
*********************************************************

Internal structure
******************

- :py:class:`~DIRAC.Core.DISET.ServiceReactor` is now :py:class:`~DIRAC.TornadoServices.Server.TornadoServer`
- :py:class:`~DIRAC.Core.DISET.private.Service` and :py:class:`~DIRAC.Core.DISET.RequestHandler` are now merge into :py:class:`~DIRAC.TornadoServices.Server.TornadoService`
- (to discuss) CallStack from S_ERROR are deleted for every error who happen before authentication.cd 

How to write service
********************
Nothing better than example::

  from DIRAC.TornadoServices.Server.TornadoService import TornadoService
  class yourServiceHandler(TornadoService):

    @classmethod
    def initializeHandler(cls, infosDict):
      ## Called 1 time, at first request

    def initializeRequest(self):
      ## Called at each request

    auth_someMethod = ['all']
    def export_someMethod(self):
      #Insert your method here, don't forgot the return

Write a service is similar in tornado and diset. You have to define your method starting with ``export_``, your initialization method is a class method called ``initializeHandler``
Main changes in tornado are:

- Service are initialized at first request
- You **should not** write method called ``initialize`` because Tornado already use it, so the ``initialize`` from diset handlers became ``initialize_request``
- infosDict, arguments of initializedHandler is not really the same as one from diset, all things relative to transport are removed, to write on the transport you can use self.write() but I recommend to avoid his usage, Tornado will encode and write what you return.

How to start server
*******************
The easy way, use ``DIRAC/TornadoService/script/tornado-start-all.py`` it will start all services registered in configuration !

The configurable way::

  from DIRAC.TornadoServices.Server.TornadoServer import TornadoServer
  serverToLaunch = TornadoServer(youroptions)
  serverToLaunch.startTornado()

Options availlable are:

- services, should be a list, to start only these services
- debug, True or False, activate debug mode of Tornado: more logs when there is a error, autoreload server when you edit a script
- port, an int, if you don't want to use the 443

******
Client
******

.. graphviz::

   digraph {
   TornadoClient -> TornadoBaseClient [label=inherit]
   TornadoBaseClient -> Requests [label=use]

   TornadoClient  [shape=polygon,sides=4, label="DIRAC.TornadoServices.Client.TornadoClient"];
   TornadoBaseClient  [shape=polygon,sides=4, label="DIRAC.TornadoServices.Client.private.TornadoBaseClient"];
   Requests [shape=polygon,sides=4]
   }


When you invoque a RPC throught :py:class:`~DIRAC.TornadoServices.Client.TornadoClient` it returns server response and the rpcStub in a S_OK/S_ERROR,
rpcStub is a dictionnary with some informations about the Client. Interface and usages are the same as :py:class:`~DIRAC.Core.DISET.RPCClient`.
So, you can also use :py:class:`~DIRAC.TornadoServices.Client.RPCClientSelector` instead of :py:class:`~DIRAC.TornadoServices.Client.TornadoClient`
or :py:class:`~DIRAC.Core.DISET.RPCClient`. :py:class:`~DIRAC.TornadoServices.Client.RPCClientSelector` will choose for your the right client to use.


Behind :py:class:`~DIRAC.TornadoServices.Client.TornadoClient` the `requests <http://docs.python-requests.org/>`_ library sends a HTTP POST request with:

- procedure: str with procedure name
- args: your arguments encoded in JSON
- clientVO: The VO of client
- extraCredentials: (if apply) Extra informations to authenticate client

Service is determined by server thanks to URL rooting, not port like in DISET.

By default server listen on port 443, default port for HTTPS.

(Note: add kwargs ?)

*****************************
Client / Service interactions
*****************************

.. image:: clientservice.png
    :align: center
    :alt: Client/Service interactions

*****************************************************
Important changes between TornadoClient and RPCClient
*****************************************************

Internal structure
******************

- :py:class:`~DIRAC.Core.DISET.private.innerRPCClient` and :py:class:`~DIRAC.Core.DISET.RPCClient` are now a single class: :py:class:`~DIRAC.TornadoServices.Client.TornadoClient`. Interface and usage stay the same.
- :py:class:`~DIRAC.TornadoServices.Client.private.TornadoBaseClient` is the new :py:class:`~DIRAC.Core.DISET.private.BaseClient`. Most of code is copied from :py:class:`~DIRAC.Core.DISET.private.BaseClient` but some method have been rewrited to use `Requests <http://docs.python-requests.org/>`_ instead of Transports. Code duplication is done to fully separate DISET and HTTPS but later, some parts can be merged by using a new common class between DISET and HTTPS (these parts are explicitly given in the docstrings).
- :py:class:`~DIRAC.Core.DISET.private.Transports.BaseTransport`, :py:class:`~DIRAC.Core.DISET.private.Transports.PlainTransport` and :py:class:`~DIRAC.Core.DISET.private.Transports.SSLTransport` are replaced by `Requests <http://docs.python-requests.org/>`_ 
- keepAliveLapse is removed from rpcStub returned by Client because `Requests <http://docs.python-requests.org/>`_  manage it himself.


Connections and certificates
****************************
`Requests <http://docs.python-requests.org/>`_ library check more than DISET when reading certificates and do some stuff for us:

- Server certificate **must** have subject alternative names. Requests also check the hostname and you can have connection errors when using "localhost" for example. To avoid them add subject alternative name in certificate. (You can also see https://github.com/shazow/urllib3/issues/497 ).
- If server certificates are used by clients, you must add clientAuth in the extendedKeyUsage (requests also check that).
- In server side M2Crypto is used instead of GSI (but not for a long time, see https://github.com/DIRACGrid/DIRAC/pull/3469 ) and conflict are possible between GSI and M2Crypto, to avoid them you can comment 4 lasts lines at ``DIRAC/Core/Security/__init__.py``
- ``_connect()``, ``_disconnect()`` and ``_purposeAction()`` are removed, ``_connect``/``_disconnect`` are now managed by `requests <http://docs.python-requests.org/>`_ and ``_purposeAction`` is no longer used is in HTTPS protocol. 




********************
Some notes for later
********************

- For security purpose, I purpose to remove the CallStack inside the S_ERROR returned by server when error happen before authentication/authorization (or during authorization process, for example: when denying access). Or at least, make this choice configurable (so in dev you have the callstack and in prod it's hidden). I think people not authorized to access service did not need callstack who can gave lots of informations.
- Maybe it's possible to add kwargs in HTTPS because when using post, arguments are named.