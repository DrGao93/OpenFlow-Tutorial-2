from pox.core import core
import pox
log = core.getLogger()

from pox.lib.packet.ethernet import ETHER_BROADCAST
from pox.lib.packet.arp import arp
from pox.lib.util import str_to_bool, dpid_to_str
from pox.lib.recoco import Timer
import pox.lib.packet as pkt
import pox.lib.addresses as addr
from pox.lib.packet.icmp import unreach

import pox.openflow.libopenflow_01 as of

from pox.lib.revent import *

import time

# Timeout for flows
FLOW_IDLE_TIMEOUT = 100

# Timeout for ARP entries
ARP_TIMEOUT = 60 * 2

class Entry (object):
  """
  Storing input port and source MAC address of frame arriving at that port
  """
  def __init__ (self, port, mac):
    self.timeout = time.time() + ARP_TIMEOUT
    self.port = port
    self.mac = mac


def dpid_to_mac (dpid):
  return addr.EthAddr("%012x" % (dpid & 0x123456789876,))


class router (EventMixin):
  def __init__ (self, subnets = [], arp_for_unknowns = False):
    # These are gateways for a subnet" -- we'll answer ARPs for them with MAC
    # of the switch they're connected to.
    self.subnets = set(subnets)
    #Routing table
    self.node_list = {'10.0.1.100', '10.0.2.100', '10.0.3.100', '10.0.3.1', '10.0.1.1', '10.0.2.1'}
    # If this is true and we see a packet for an unknown
    # host, we'll ARP for it.
    self.arp_for_unknowns = arp_for_unknowns
    self.outstanding_arps = {}
    # For each switch, we map IP addresses to Entries
    self.mac_table = {}
    self.listenTo(core)

  def _handle_GoingUpEvent (self, event):
    self.listenTo(core.openflow)
    log.debug("Up...")

  def _handle_PacketIn (self, event):
    dpid = event.connection.dpid
    inport = event.port
    packet = event.parsed
    flag = 1
    packet_in = event.ofp
    self.connection = event.connection
    if not packet.parsed:
      log.warning("Router %i, input port = %i: ignoring unparsed packet", dpid, inport)
      return

    icmp_packet = packet.find('icmp')
    if icmp_packet is not None:
      if icmp_packet.type == pkt.TYPE_ECHO_REQUEST:
        log.debug("Received ICMP request message")
        found = 0	#To check if destination is reachable by ping
        for node in self.node_list:
          if packet.payload.dstip.inNetwork(node):	#If the destination IP is in the network
            found = node
            break
        if found == 0:
          log.debug("Destination Unreachable")
          icmp_reply = pkt.icmp()
          icmp_reply.type = pkt.TYPE_DEST_UNREACH
          icmp_reply.code = pkt.ICMP.CODE_UNREACH_HOST
          icmp_reply_payload = packet.find('ipv4').pack()
          icmp_reply_payload = icmp_reply_payload[:packet.find('ipv4').hl * 4 + 8]
          import struct
          icmp_reply_payload = struct.pack("!HH", 0,0) + icmp_reply_payload
          icmp_reply.payload = icmp_reply_payload
          #Making the IPv4 packet around it
          icmp_reply_packet = pkt.ipv4()
          icmp_reply_packet.protocol = icmp_reply_packet.ICMP_PROTOCOL
          icmp_reply_packet.srcip = packet.find("ipv4").dstip
          icmp_reply_packet.dstip = packet.find("ipv4").srcip
          #Putting this packet in an ethernet frame
          icmp_ethernet_frame = pkt.ethernet()
          icmp_ethernet_frame.type = pkt.ethernet.IP_TYPE
          icmp_ethernet_frame.dst = packet.src
          icmp_ethernet_frame.src = packet.dst
          #Encapsulating...
          icmp_reply_packet.payload = icmp_reply
          icmp_ethernet_frame.payload = icmp_reply_packet
          #Sending the ping reply back through the port it came in at
          msg = of.ofp_packet_out()
          msg.data = icmp_ethernet_frame.pack()
          msg.actions.append(of.ofp_action_output(port = packet_in.in_port))
          self.connection.send(msg)
          log.debug("Sent 'Dest Unreachable' message")
        else:
          if found == "10.0.1.1" or "10.0.2.1" or "10.0.3.1":
            log.debug("Trying to reach = %s" % found)
            #Making the ping reply
            icmp_reply = pkt.icmp()
            icmp_reply.type = pkt.TYPE_ECHO_REPLY
            icmp_reply.payload = icmp_packet.payload
            #Making the IPv4 packet around it
            icmp_reply_packet = pkt.ipv4()
            icmp_reply_packet.protocol = icmp_reply_packet.ICMP_PROTOCOL
            icmp_reply_packet.srcip = packet.find("ipv4").dstip
            icmp_reply_packet.dstip = packet.find("ipv4").srcip
            #Putting this packet in an ethernet frame
            icmp_ethernet_frame = pkt.ethernet()
            icmp_ethernet_frame.type = pkt.ethernet.IP_TYPE
            icmp_ethernet_frame.dst = packet.src
            icmp_ethernet_frame.src = packet.dst
            #Encapsulating...
            icmp_reply_packet.payload = icmp_reply
            icmp_ethernet_frame.payload = icmp_reply_packet
            #Sending the ping reply back through the port it came in at
            msg = of.ofp_packet_out()
            msg.data = icmp_ethernet_frame.pack()
            msg.actions.append(of.ofp_action_output(port = packet_in.in_port))
            self.connection.send(msg)
            log.debug("Sent ICMP reply")
            flag = 0

    if dpid not in self.mac_table:
      # New switch -- create an empty table
      self.mac_table[dpid] = {}
      for subnet in self.subnets:
        self.mac_table[dpid][addr.IPAddr(subnet)] = Entry(of.OFPP_NONE, dpid_to_mac(dpid))

    if isinstance(packet.next, pkt.ipv4):
      log.debug("Router %i, input port = %i: Received an IP packet from %s to %s", dpid,inport, packet.next.srcip,packet.next.dstip)
      #Update MAC table
      self.mac_table[dpid][packet.next.srcip] = Entry(inport, packet.src)
      dstaddr = packet.next.dstip
      if dstaddr in self.mac_table[dpid]:
        #We know where to send the packet
        prt = self.mac_table[dpid][dstaddr].port
        mac = self.mac_table[dpid][dstaddr].mac
        log.debug("Router %i:Forwarding the packet to dst_MAC address = %s through port = %i",dpid,mac,prt)
        if flag == 1:
          actions = []
          actions.append(of.ofp_action_dl_addr.set_dst(mac))
          actions.append(of.ofp_action_output(port = prt))
          match = of.ofp_match.from_packet(packet, inport)
          match.dl_src = None
          msg = of.ofp_flow_mod(command=of.OFPFC_ADD, idle_timeout=FLOW_IDLE_TIMEOUT, hard_timeout=of.OFP_FLOW_PERMANENT, buffer_id=event.ofp.buffer_id, actions=actions, match=of.ofp_match.from_packet(packet, inport))
          event.connection.send(msg.pack())
      elif self.arp_for_unknowns:
        r = arp()
        r.hwtype = r.HW_TYPE_ETHERNET
        r.prototype = r.PROTO_TYPE_IP
        r.hwlen = 6
        r.protolen = r.protolen
        r.opcode = r.REQUEST
        r.hwdst = ETHER_BROADCAST
        r.protodst = dstaddr
        r.hwsrc = packet.src
        r.protosrc = packet.next.srcip
        e = pkt.ethernet(type=pkt.ethernet.ARP_TYPE, src=packet.src, dst=ETHER_BROADCAST)
        e.set_payload(r)
        log.debug("Router %i: ARPing for %s on behalf of %s" % (dpid, str(r.protodst), str(r.protosrc)))
        msg = of.ofp_packet_out()
        msg.data = e.pack()
        msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
        msg.in_port = inport
        event.connection.send(msg)

    elif isinstance(packet.next, arp):
      a = packet.next
      log.debug("Router %i, received an ARP packet at port = %i", dpid, inport)
      if a.prototype == arp.PROTO_TYPE_IP:
        if a.hwtype == arp.HW_TYPE_ETHERNET:
          if a.protosrc != 0:
            #Update MAC table
            self.mac_table[dpid][a.protosrc] = Entry(inport, packet.src)
            if a.opcode == arp.REQUEST:
              if a.protodst in self.mac_table[dpid]:
                #We can answer the ARP ourselves
                r = arp()
                r.hwtype = a.hwtype
                r.prototype = a.prototype
                r.hwlen = a.hwlen
                r.protolen = a.protolen
                r.opcode = arp.REPLY
                r.hwdst = a.hwsrc
                r.protodst = a.protosrc
                r.protosrc = a.protodst
                r.hwsrc = self.mac_table[dpid][a.protodst].mac
                e = pkt.ethernet(type=packet.type, src=dpid_to_mac(dpid), dst=a.hwsrc)
                e.set_payload(r)
                log.debug("Router %i, input port %i answering ARP for %s" % (dpid, inport, str(r.protosrc)))
                msg = of.ofp_packet_out()
                msg.data = e.pack()
                msg.actions.append(of.ofp_action_output(port = of.OFPP_IN_PORT))
                msg.in_port = inport
                event.connection.send(msg)
                return
              else:
                # Didn't know how to answer or otherwise handle this ARP, so just flood it
                log.debug("Flooding to all ports since we don't have the MAC address in mac_table")
                msg = of.ofp_packet_out(in_port = inport, data = event.ofp, action = of.ofp_action_output(port = of.OFPP_FLOOD))
                event.connection.send(msg)

def launch ():
  subnets="10.0.1.1 10.0.2.1 10.0.3.1" 
  subnets = subnets.split()
  subnets = [addr.IPAddr(x) for x in subnets]
  arp_for_unknowns = len(subnets) > 0
  core.registerNew(router, subnets, arp_for_unknowns)
