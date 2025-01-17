#    Copyright 2014 Philippe THIRION
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import socketserver
import re
import time
import logging
from json import load as jload


class UDPHandler(socketserver.BaseRequestHandler):
    
    with open("codes.json") as f:
        codes = jload(f)

    lang = "sk"

    rx_register = re.compile("^REGISTER")
    rx_invite = re.compile("^INVITE")
    rx_ack = re.compile("^ACK")
    rx_prack = re.compile("^PRACK")
    rx_cancel = re.compile("^CANCEL")
    rx_bye = re.compile("^BYE")
    rx_options = re.compile("^OPTIONS")
    rx_subscribe = re.compile("^SUBSCRIBE")
    rx_publish = re.compile("^PUBLISH")
    rx_notify = re.compile("^NOTIFY")
    rx_info = re.compile("^INFO")
    rx_message = re.compile("^MESSAGE")
    rx_refer = re.compile("^REFER")
    rx_update = re.compile("^UPDATE")
    rx_from = re.compile("^From:")
    rx_cfrom = re.compile("^f:")
    rx_to = re.compile("^To:")
    rx_cto = re.compile("^t:")
    rx_tag = re.compile(";tag")
    rx_contact = re.compile("^Contact:")
    rx_ccontact = re.compile("^m:")
    rx_uri = re.compile("sip:([^@]*)@([^;>$]*)")
    rx_addr = re.compile("sip:([^ ;>$]*)")
    rx_code = re.compile("^SIP/2.0 ([^ ]*)")
    rx_request_uri = re.compile("^([^ ]*) sip:([^ ]*) SIP/2.0")
    rx_route = re.compile("^Route:")
    rx_contentlength = re.compile("^Content-Length:")
    rx_ccontentlength = re.compile("^l:")
    rx_via = re.compile("^Via:")
    rx_cvia = re.compile("^v:")
    rx_branch = re.compile(";branch=([^;]*)")
    rx_rport = re.compile(";rport$|;rport;")
    rx_contact_expires = re.compile("expires=([^;$]*)")
    rx_expires = re.compile("^Expires: (.*)$")

    # global dictionnary
    recordroute = ""
    topvia = ""
    registrar = {}

    def quotechars(chars):
        return ''.join(['.', c][c.isalnum()] for c in chars)

    def showtime(self):
        logging.debug(time.strftime("(%H:%M:%S)", time.localtime()))

    def debugRegister(self):
        logging.debug("*** REGISTRAR ***")
        logging.debug("*****************")
        for key in self.registrar.keys():
            logging.debug("%s -> %s" % (key, self.registrar[key][0]))
        logging.debug("*****************")

    def hexdump(self, chars, sep, width):
        while chars:
            line = chars[:width]
            chars = chars[width:]
            line = line.ljust(width, '\000')
            logging.debug("%s%s%s" % (sep.join("%02x" % ord(c) for c in line), sep, self.quotechars(line)))

    def changeRequestUri(self):
        # change request uri
        md = self.rx_request_uri.search(self.data[0])
        if md:
            method = md.group(1)
            uri = md.group(2)
            if uri in self.registrar:
                uri = "sip:%s" % self.registrar[uri][0]
                self.data[0] = "%s %s SIP/2.0" % (method, uri)

    def removeRouteHeader(self):
        # delete Route
        data = []
        for line in self.data:
            if not self.rx_route.search(line):
                data.append(line)
        return data

    def addTopVia(self):
        branch = ""
        data = []
        for line in self.data:
            if self.rx_via.search(line) or self.rx_cvia.search(line):
                md = self.rx_branch.search(line)
                if md:
                    branch = md.group(1)
                    via = "%s;branch=%sm" % (self.server.topvia, branch)
                    data.append(via)
                # rport processing
                if self.rx_rport.search(line):
                    text = "received=%s;rport=%d" % self.client_address
                    via = line.replace("rport", text)
                else:
                    text = "received=%s" % self.client_address[0]
                    via = "%s;%s" % (line, text)
                data.append(via)
            else:
                data.append(line)
        return data

    def removeTopVia(self):
        data = []
        for line in self.data:
            if self.rx_via.search(line) or self.rx_cvia.search(line):
                if not line.startswith(self.server.topvia):
                    data.append(line)
            else:
                data.append(line)
        return data

    def checkValidity(self, uri):
        addrport, socket, client_addr, validity = self.registrar[uri]
        now = int(time.time())
        if validity > now:
            return True
        else:
            del self.registrar[uri]
            logging.warning("registration for %s has expired" % uri)
            return False

    def getSocketInfo(self, uri):
        addrport, socket, client_addr, validity = self.registrar[uri]
        return socket, client_addr

    def getDestination(self):
        destination = ""
        for line in self.data:
            if self.rx_to.search(line) or self.rx_cto.search(line):
                md = self.rx_uri.search(line)
                if md:
                    destination = "%s@%s" % (md.group(1), md.group(2))
                break
        return destination

    def getOrigin(self):
        origin = ""
        for line in self.data:
            if self.rx_from.search(line) or self.rx_cfrom.search(line):
                md = self.rx_uri.search(line)
                if md:
                    origin = "%s@%s" % (md.group(1), md.group(2))
                break
        return origin

    def sendResponse(self, code):
        request_uri = "SIP/2.0 " + code
        self.data[0] = request_uri
        index = 0
        data = []
        for line in self.data:
            data.append(line)
            if self.rx_to.search(line) or self.rx_cto.search(line):
                if not self.rx_tag.search(line):
                    data[index] = "%s%s" % (line, ";tag=123456")
            if self.rx_via.search(line) or self.rx_cvia.search(line):
                # rport processing
                if self.rx_rport.search(line):
                    text = "received=%s;rport=%d" % self.client_address
                    data[index] = line.replace("rport", text)
                else:
                    text = "received=%s" % self.client_address[0]
                    data[index] = "%s;%s" % (line, text)
            if self.rx_contentlength.search(line):
                data[index] = "Content-Length: 0"
            if self.rx_ccontentlength.search(line):
                data[index] = "l: 0"
            index += 1
            if line == "":
                break
        data.append("")
        text = "\r\n".join(data)
        self.socket.sendto(text.encode("utf-8"), self.client_address)
        self.showtime()
        logging.info("<<< %s" % data[0])
        logging.debug("---\n<< server send [%d]:\n%s\n---" % (len(text), text))

    def processRegister(self):
        fromm = ""
        contact = ""
        contact_expires = ""
        header_expires = ""
        expires = 0
        validity = 0
        authorization = ""
        index = 0
        auth_index = 0
        data = []
        size = len(self.data)
        for line in self.data:
            if self.rx_to.search(line) or self.rx_cto.search(line):
                md = self.rx_uri.search(line)
                if md:
                    fromm = "%s@%s" % (md.group(1), md.group(2))
            if self.rx_contact.search(line) or self.rx_ccontact.search(line):
                md = self.rx_uri.search(line)
                if md:
                    contact = md.group(2)
                else:
                    md = self.rx_addr.search(line)
                    if md:
                        contact = md.group(1)
                md = self.rx_contact_expires.search(line)
                if md:
                    contact_expires = md.group(1)
            md = self.rx_expires.search(line)
            if md:
                header_expires = md.group(1)

        if len(contact_expires) > 0:
            expires = int(contact_expires)
        elif len(header_expires) > 0:
            expires = int(header_expires)

        if expires == 0:
            if fromm in self.registrar:
                del self.registrar[fromm]
                self.sendResponse(self.codes[self.lang]["200"])
                return
        else:
            now = int(time.time())
            validity = now + expires

        logging.info("From: %s - Contact: %s" % (fromm, contact))
        logging.debug("Client address: %s:%s" % self.client_address)
        logging.debug("Expires= %d" % expires)
        self.registrar[fromm] = [contact, self.socket, self.client_address, validity]
        self.debugRegister()
        self.sendResponse(self.codes[self.lang]["200"])

    def processInvite(self):
        logging.debug("-----------------")
        logging.debug(" INVITE received ")
        logging.debug("-----------------")
        origin = self.getOrigin()
        if len(origin) == 0 or origin not in self.registrar:
            self.sendResponse(self.codes[self.lang]["400"])
            return
        destination = self.getDestination()
        if len(destination) > 0:
            logging.info("destination %s" % destination)
            if destination in self.registrar and self.checkValidity(destination):
                socket, claddr = self.getSocketInfo(destination)
                # self.changeRequestUri()
                self.data = self.addTopVia()
                data = self.removeRouteHeader()
                # insert Record-Route
                data.insert(1, self.server.recordroute)
                text = "\r\n".join(data)
                socket.sendto(text.encode("utf-8"), claddr)
                self.showtime()
                logging.info("<<< %s" % data[0])
                logging.debug("---\n<< server send [%d]:\n%s\n---" % (len(text), text))
            else:
                self.sendResponse(self.codes[self.lang]["480"])
        else:
            self.sendResponse(self.codes[self.lang]["500"])

    def processAck(self):
        logging.debug("--------------")
        logging.debug(" ACK received ")
        logging.debug("--------------")
        destination = self.getDestination()
        if len(destination) > 0:
            logging.info("destination %s" % destination)
            if destination in self.registrar:
                socket, claddr = self.getSocketInfo(destination)
                # self.changeRequestUri()
                self.data = self.addTopVia()
                data = self.removeRouteHeader()
                # insert Record-Route
                data.insert(1, self.server.recordroute)
                text = "\r\n".join(data)
                socket.sendto(text.encode("utf-8"), claddr)
                self.showtime()
                logging.info("<<< %s" % data[0])
                logging.debug("---\n<< server send [%d]:\n%s\n---" % (len(text), text))

    def processNonInvite(self):
        logging.debug("----------------------")
        logging.debug(" NonInvite received   ")
        logging.debug("----------------------")
        origin = self.getOrigin()
        if len(origin) == 0 or origin not in self.registrar:
            self.sendResponse(self.codes[self.lang]["400"])
            return
        destination = self.getDestination()
        if len(destination) > 0:
            logging.info("destination %s" % destination)
            if destination in self.registrar and self.checkValidity(destination):
                socket, claddr = self.getSocketInfo(destination)
                # self.changeRequestUri()
                self.data = self.addTopVia()
                data = self.removeRouteHeader()
                # insert Record-Route
                data.insert(1, self.server.recordroute)
                text = "\r\n".join(data)
                socket.sendto(text.encode("utf-8"), claddr)
                self.showtime()
                logging.info("<<< %s" % data[0])
                logging.debug("---\n<< server send [%d]:\n%s\n---" % (len(text), text))
            else:
                self.sendResponse(self.codes[self.lang]["406"])
        else:
            self.sendResponse(self.codes[self.lang]["500"])

    def processCode(self):
        origin = self.getOrigin()
        if len(origin) > 0:
            logging.debug("origin %s" % origin)
            if origin in self.registrar:
                socket, claddr = self.getSocketInfo(origin)
                self.data = self.removeRouteHeader()
                data = self.removeTopVia()
                text = "\r\n".join(data)
                socket.sendto(text.encode("utf-8"), claddr)
                self.showtime()
                logging.info("<<< %s" % data[0])
                logging.debug("---\n<< server send [%d]:\n%s\n---" % (len(text), text))

    def processRequest(self):
        # print "processRequest"
        if len(self.data) > 0:
            request_uri = self.data[0]
            if self.rx_register.search(request_uri):
                self.processRegister()
            elif self.rx_invite.search(request_uri):
                self.processInvite()
            elif self.rx_ack.search(request_uri):
                self.processAck()
            elif self.rx_bye.search(request_uri):
                self.processNonInvite()
            elif self.rx_cancel.search(request_uri):
                self.processNonInvite()
            elif self.rx_options.search(request_uri):
                self.processNonInvite()
            elif self.rx_info.search(request_uri):
                self.processNonInvite()
            elif self.rx_message.search(request_uri):
                self.processNonInvite()
            elif self.rx_refer.search(request_uri):
                self.processNonInvite()
            elif self.rx_prack.search(request_uri):
                self.processNonInvite()
            elif self.rx_update.search(request_uri):
                self.processNonInvite()
            elif self.rx_subscribe.search(request_uri):
                self.sendResponse(self.codes[self.lang]["200"])
            elif self.rx_publish.search(request_uri):
                self.sendResponse(self.codes[self.lang]["200"])
            elif self.rx_notify.search(request_uri):
                self.sendResponse(self.codes[self.lang]["200"])
            elif self.rx_code.search(request_uri):
                self.processCode()
            else:
                logging.error("request_uri %s" % request_uri)
                # print "message %s unknown" % self.data

    def handle(self):
        # socket.setdefaulttimeout(120)
        global data
        try:
            data = self.request[0].decode("utf-8")
        except UnicodeDecodeError:
            pass
        self.data = data.split("\r\n")
        self.socket = self.request[1]
        request_uri = self.data[0]
        if self.rx_request_uri.search(request_uri) or self.rx_code.search(request_uri):
            self.showtime()
            logging.info(">>> %s" % request_uri)
            logging.debug("---\n>> server received [%d]:\n%s\n---" % (len(data), data))
            logging.debug("Received from %s:%d" % self.client_address)
            self.processRequest()
        else:
            if len(data) > 4:
                self.showtime()
                logging.warning("---\n>> server received [%d]:" % len(data))
                self.hexdump(data, ' ', 16)
                logging.warning("---")
