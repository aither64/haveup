#!/usr/bin/env python3

import sys
import notify2
import argparse
import string
import hashlib
import os
from subprocess import Popen, PIPE
from PySide.QtCore import *
from PySide.QtNetwork import *

class HaveUp(QObject):
	def __init__(self, args):
		super(HaveUp, self).__init__()
		
		self.files = args.file
		
		if len(self.files) < 1:
			print("Please specify file name")
			exit(1)
		
		self.has_more = len(self.files) > 1
		self.links = []
		self.settings = QSettings()
		self.file_class = self.load_group()
		
		if args.file_class != "General":
			for grp in self.settings.childGroups():
				if grp.startswith(args.file_class):
					self.file_class.update(self.load_group(grp))
					break
		
		if args.subdir:
			self.subdir = "/" + args.subdir
		elif "SubDir" in self.file_class:
			self.subdir = "/" + str(self.file_class["SubDir"])
		else:
			self.subdir = ""
		
		if args.hash:
			self.hash = args.hash
		elif "HashName" in self.file_class:
			self.hash = bool(self.file_class["HashName"])
		else:
			self.hash = False
		
		self.manager = QNetworkAccessManager(self)
		self.manager.finished.connect(self.uploadFinished)
		self.manager.authenticationRequired.connect(self.authenticate)
		
		self.uploadFile()
	
	def load_group(self, grp = None):
		ret = {}
		
		if grp:
			self.settings.beginGroup(grp)
		
		for key in self.settings.childKeys():
			ret[key] = self.settings.value(key)
		
		if grp:
			self.settings.endGroup()
		
		return ret
	
	def uploadFile(self):
		self.tries = 0
		
		if len(self.files) == 0:
			exit(0)
			return
		
		self.cur_file = QFile(self.files.pop(0))
		base_name = os.path.basename(self.cur_file.fileName())
		
		if not self.cur_file.open(QIODevice.ReadOnly):
			print("Unable to open", self.cur_file.fileName())
			self.uploadFile()
			return
		
		if self.hash:
			target_name = hashlib.sha1(bytes(self.cur_file.fileName(), "UTF-8")).hexdigest() + "." + base_name.split('.')[-1]
		else:
			target_name = base_name
		
		self.url = str(self.settings.value("PublicUrl")) + self.subdir + "/" + target_name
		
		self.request = QNetworkRequest(QUrl(str(self.settings.value("UploadUrl")) + self.subdir + "/" + target_name))
		self.reply = self.manager.put(self.request, self.cur_file)
		self.reply.error.connect(self.errorOccured)
	
	@Slot(QNetworkReply, QAuthenticator)
	def authenticate(self, reply, auth):
		self.tries += 1
		
		if self.tries > 3:
			print("Authentication failed")
			self.reply.abort()
			self.reply.deleteLater()
			exit(2)
			return
		
		auth.setUser(str(self.settings.value("User")))
		auth.setPassword(str(self.settings.value("Password")))
	
	@Slot(QNetworkReply.NetworkError)
	def errorOccured(self, err):
		print("Error occured:", err)
	
	def uploadFinished(self):
		self.cur_file.close()
		self.reply.deleteLater()
		
		notify2.Notification(
			"File uploaded" if self.has_more and len(self.files) > 0 else "Upload finished",
			"File <b>%s</b> was successfuly uploaded" % self.cur_file.fileName()
		).show()
		
		print("{0}: {1}".format(self.cur_file.fileName(), self.url))
		
		self.links.append(self.url)
		
		p = Popen(['xsel', '-pi'], stdin=PIPE, shell=True)
		p.communicate(bytes("\n".join(self.links), "UTF-8"))
		p.wait()
		
		self.uploadFile()
	
	def exit(self, code):
		QCoreApplication.exit(code)

parser = argparse.ArgumentParser(description="Upload file(s) and print links")
parser.add_argument('-c', '--class', dest='file_class', default='General', help="Use settings from specified class")
parser.add_argument('-d', '--dir', dest='subdir', default='', help="Upload files to specified subdirectory")
parser.add_argument('-s', '--hash-name', action='store_true', dest='hash', help="Hash file name for every file")
parser.add_argument('file', metavar='FILE', nargs='+', help="File(s) to upload")
args = parser.parse_args()

QCoreApplication.setOrganizationName("HaveFun.cz")
QCoreApplication.setOrganizationDomain("havefun.cz")
QCoreApplication.setApplicationName("HaveUp")

notify2.init('HaveUp')

app = QCoreApplication(sys.argv)

hup = HaveUp(args)

sys.exit(app.exec_())
