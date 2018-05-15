==================================
Authentification and authorization
==================================
When a user is calling a Service, he needs to be identified. If a client opens a connection a :py:class:`~DIRAC.Core.DISET.private.transport.BaseTransport.BaseTransport` 
object is created then Service use the handshake to read certificates, extract informations and store them in a dictionnary so you can use these informations easily. Here an example of possible dictionnary::

	{
		'DN': '/C=ch/O=DIRAC/[...]',
		'group': 'devGroup',
		'CN': u'ciuser', 
		'x509Chain': <X509Chain 2 certs [...][...]>, 
		'isLimitedProxy': False, 
		'isProxy': True
	}


When connection is opened and handshake is done, Service call the :py:class:`~DIRAC.Core.DISET.AuthManager.AuthManager` and gave him this dictionnary in argument to check authorizations. More generally you can get this dictionnary with :py:meth:`~DIRAC.Core.DISET.private.transport.BaseTransport.BaseTransport.getConnectingCredentials()`.


***********
AuthManager
***********
AuthManager.authQuery() returns boolean so it is easy to use, you just have to provide a method you want to call, and credDic. It's easy to use but you have to instanciate correctly the AuthManager. For initialization you need the complete path of your service, to get it you may use the PathFinder::

	from DIRAC.ConfigurationSystem.Client import PathFinder
	authManager = AuthManager( "%s/Authorization" % PathFinder.getServiceSection("Framework/someService") )
	authManager.authQuery( csAuthPath, credDict, hardcodedMethodAuth ) #return boolean
	# csAuthPath is the name of method for RPC or 'typeOfCall/method'
	# credDict came from BaseTransport.getConnectingCredentials()
	# hardcodedMethodAuth is optional

To determine if a query can be authorized or not the AuthManager extract valid properties for a given method.
First AuthManager try to get it from gConfig, then try to get it from hardcoded list (hardcodedMethodAuth) in your service and if nothing was found get default properties from gConfig.


You can also read `Components authentication and authorization <./componentsAuthNandAuthZ.html>`_ for informations about client-side authentification.