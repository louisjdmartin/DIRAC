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
rpcStub is a dictionnary with some informations about the Client. To call a :py:class:`~DIRAC.TornadoServices.Client.TornadoClient` Interface and usages
are the same as :py:class:`~DIRAC.Core.DISET.RPCClient`.
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

********************
Some notes for later
********************

*WARNING*: Requests library check more than DISET when reading certificates:

- Server certificate must have subject alternative names. Requests check the hostname and you can have connection errors when using "localhost" for example. To avoid them you can add hostname in your /etc/hosts or add subject alternative name in certificate. (First solution is good for dev but in production you may use subject alternative names)
- If server certificates are used by clients, you MUST add clientAuth in the extendedKeyUsage (requests also check that)
- For security purpose, I purpose to remove the CallStack inside the S_ERROR returned by server when error happen before authentication/authorization (or during authorization process, for e.g. when denying access). Or at least, make this choice configurable (so in dev you have the callstack and in prod it's hidden). I think people not authorized to access service did not need callstack who can gave lots of informations.
- Maybe it's possible to add kwargs in HTTPS because when using post, arguments are named.