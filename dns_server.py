import socket
import socketserver
from typing import List, Any, Dict, Callable, Tuple

import dns
from dns import resolver, rdatatype, message, opcode, flags, rdatatype, rrset
from dns.rdtypes.IN import A, AAAA

import sys
import dns_over_ipfs

AddressTupple = Tuple[str, int]

classNameMap: Dict[int, str] = {
  dns.rdatatype.A: "A",
  dns.rdatatype.AAAA: "AAAA",
}


class DNSServer(socketserver.UDPServer):
  def __init__(self, addr: AddressTupple, lookup: Callable[[str], List[str]]):
    self.allow_reuse_address = True
    super().__init__(addr, DNSHandler)
    self.lookup = lookup


class DNSHandler(socketserver.BaseRequestHandler):
  def __init__(self, tup: Tuple[bytes, socket.socket], client_addr: AddressTupple, server: DNSServer):
    (data, sock) = tup
    req: dns.message.Message = dns.message.from_wire(data)
    res: dns.message.Message = dns.message.make_response(req)

    #self.client_addr: AddressTupple = client_addr
    #self.data: bytes = data
    if req.opcode() != dns.opcode.QUERY:
      print("Error: unexpected opcode %d" % req.opcode())
      return
    if len(req.question) != 1:
      print("Error: unexpected number of questions %d" % len(req.question))
      return
    # TODO: understand + check flags - usually dns.flags.{AD,RD}
    q = req.question[0]
    #print(q.name, q.rdclass, q.rdtype)
    if q.rdclass != dns.rdataclass.IN or q.rdtype not in [dns.rdatatype.A]:
      print("Error: Unexpected rdata class or type class=%d type=%d" %
            (q.rdclass, q.rdtype))
      return
    res.flags |= dns.flags.RA
    lookup_res = server.lookup(q.name.to_text()[:-1])
    if lookup_res:
      answer = dns.rrset.RRset(q.name, q.rdclass, q.rdtype)
      for ip in lookup_res:
        answer.add(dns.rdtypes.IN.A.A(q.rdclass, q.rdtype, ip))
      res.answer.append(answer)
    else:
      res.set_rcode(dns.rcode.NXDOMAIN)
      # TODO: consider if dns.rdtypes.ANY.SOA.SOA should be added
    sock.sendto(res.to_wire(), client_addr)


if __name__ == '__main__':
    data_path = sys.argv[1]
    print(f'Using data path: {data_path}')

    ipfs = dns_over_ipfs.IPFS(data_path)

    def resolve(domain_name):
        res = ipfs.resolve_dns_lookup(domain_name)
        if res is not None:
            return [res]

    s = DNSServer(("127.0.0.53", 53), resolve)

    try:
      s.serve_forever()
    except KeyboardInterrupt:
      print("Exiting due to interrupt")
