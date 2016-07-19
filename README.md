# OpenFlow-Tutorial
--------------------------------------------------------------------------------
				PART 1
--------------------------------------------------------------------------------
Files :
	of_tutorial.py  : Implementation of a Layer 2 switch
	router1.py	: Implementation of a Router
	mytopo.py	: Custom Topology
--------------------------------------------------------------------------------
System :
	All development and testing was done on an Ubuntu 14.04 machine. The mininet VM was not used, instead all files corresponding to pox and mininet were downloaded and run locally
--------------------------------------------------------------------------------
Build and Run :
	Firstly, place the of_tutorial.py and router1.py files inside the xyz/pox/pox/misc subfolder, where xyz is the location of your pox files. Place the mytopo.py file in the abc/mininet/custom subfolder, where abc is the location of your mininet files. For example, if your pox files are located in your Desktop, you would have to 
        copy the first two files to Desktop/pox/pox/misc
To run and test the above scripts, first open two terminals 

Since I am running both pox and mininet inside the same system, I did not need
to ssh into mininet. If you are running these codes on two different systems, 
ensure that you ssh from whichever system you would be running pox into whichever
system you are running mininet in.

To test the learning switch,
In one terminal (system from where you are running pox), enter
  $./pox.py log.level --DEBUG misc.of_tutorial
In another terminal (system in which you are running mininet, enter
  $sudo mn --topo single,3 --mac --switch ovsk --controller remote
Test commands such as ping and iperf can now be successfully run in the mininet terminal.

To test the router,
In one terminal (system from where you are running pox), enter
  $./pox.py log.level --DEBUG misc.router1 misc.full_payload 
In another terminal (system in which you are running mininet, enter
  $sudo mn --custom mytopo.py --topo mytopo --mac --switch ovsk --controller remote
Test commands such as ping and iperf can now be successfully run in the mininet terminal.
--------------------------------------------------------------------------------
--------------------------------------------------------------------------------
				PART 2
--------------------------------------------------------------------------------
Files :
	router2.py	: Implementation of a Router
	advtopo.py	: Custom Topology
--------------------------------------------------------------------------------
System :
	All development and testing was done on an Ubuntu 14.04 machine. The 
mininet VM was not used, instead all files corresponding to pox and mininet were
downloaded and run locally
--------------------------------------------------------------------------------
Build and Run :
	Firstly, place the router2.py file inside the xyz/pox/pox/misc subfolder where xyz is the location of your pox files.
	Place the mytopo.py file in the abc/mininet/custom subfolder, where abc is the location of your mininet files.
        For example, if your pox files are located in your Desktop, you would have to copy the first two files to Desktop/pox/pox/misc

To run and test the above scripts, first open two terminals 

Since I am running both pox and mininet inside the same system, I did not need
to ssh into mininet. If you are running these codes on two different systems, 
ensure that you ssh from whichever system you would be running pox into whichever
system you are running mininet in.

To test the router,
In one terminal (system from where you are running pox), enter
  $./pox.py log.level --DEBUG misc.router2 misc.full_payload 
In another terminal (system in which you are running mininet, enter
  $sudo mn --custom advtopo.py --topo mytopo --mac --switch ovsk --controller remote
Test commands such as ping and iperf can now be successfully run in the mininet terminal.
--------------------------------------------------------------------------------
