====================
Configuration System
====================

The configuration system works with master servers and slave servers.

Master & slave can receive requests from another master or slave and from any client who need the configuration.

******
Master
******
The master Server is the only server who have a local configuration plus a configuration file with shared configuration. He can distribute the shared configuration to every client or synchronize it with a slave server.

Master server also check if slaves server are alive, in fact he just verify the date of the last registration request to determine if they are considered dead or alive.

When a slave wants to register in the master server (or renew registration) he call ``export_publishSlaveServer``, then before answering to slave, the master will ping the slave and if ping work, he register the slave and returns ``S_OK`` to slave.

Master Server also disable the refresher, because he have the configuration and he manage it, so he did'nt need the refresher in the background.

******
Slaves
******
The slave server distribute the shared configuration to every client who need it.
He force the refresher to run in background and to actualize configuration after a few time (every 5 minutes by default).

At initialization, slave register hitself to the master and get the configuration, then with every refresh he renew its registration to master.

By refreshing configuration in an automatic way, it disable all refresh methods who can be called by an another way. (They are still available, but they do nothing).
