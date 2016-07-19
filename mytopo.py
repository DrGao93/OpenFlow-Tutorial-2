"""Custom topology example

   host --- switch --- host
	       |
	      host

Adding the 'topos' dict with a key/value pair to generate our newly defined
topology enables one to pass in '--topo=mytopo' from the command line.
"""

from mininet.topo import Topo

class MyTopo( Topo ):
    "Simple topology example."

    def __init__( self ):
        "Create custom topo."

        # Initialize topology
        Topo.__init__( self )

        # Add hosts and switches

	#host1 = self.addHost( 'h1' )
	#host2 = self.addHost( 'h2' )
	#host3 = self.addHost( 'h3' )
	host1 = self.addHost( 'h1', ip="10.0.1.100/24", defaultRoute = "via 10.0.1.1" )
	host2 = self.addHost( 'h2', ip="10.0.2.100/24", defaultRoute = "via 10.0.2.1" )
	host3 = self.addHost( 'h3', ip="10.0.3.100/24", defaultRoute = "via 10.0.3.1" )
        Switch = self.addSwitch( 's1' )

        # Add links
        self.addLink( Switch, host1 )
        self.addLink( Switch, host2 )
        self.addLink( Switch, host3 )



topos = { 'mytopo': ( lambda: MyTopo() ) }
