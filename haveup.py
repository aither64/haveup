#!/usr/bin/env python3
# 
# Copyright (C) 2013-2014 Jakub Skokan <aither@havefun.cz>
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3
# as published by the Free Software Foundation.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import argparse
import string
import hashlib
import os
import subprocess
import configparser
import tempfile

class HaveUp(object):
	def __init__(self, args):
		super(HaveUp, self).__init__()
		
		self.files = args.file
		self.config = configparser.ConfigParser()
		self.config.read("{0}/.config/HaveFun.cz/HaveUp.conf".format(os.path.expanduser('~')))
		
		if len(self.files) < 1:
			print("Please specify file name", file=sys.stderr)
			exit(1)
		
		self.has_more = len(self.files) > 1
		self.links = []
		
		if args.file_class == 'DEFAULT' or self.config.has_section(args.file_class):
			self.file_class = self.load_group(args.file_class)
		else:
			for s in self.config.sections():
				if s.startswith(args.file_class):
					self.file_class = self.load_group(s)
					break
			else:
				print("Group '{0}' not found".format(args.file_class), file=sys.stderr)
				exit(1)
		
		if args.subdir:
			self.subdir = "/" + args.subdir
		elif "subdir" in self.file_class:
			self.subdir = "/" + self.file_class["subdir"]
		else:
			self.subdir = ""
		
		if args.hash:
			self.hash = args.hash
		elif "hashname" in self.file_class:
			self.hash = self.config[self.cfg_section].getboolean("hashname")
		else:
			self.hash = False
		
		if args.checksum != None:
			self.checksum = args.checksum
		elif "checksum" in self.file_class and self.file_class['checksum'] != '':
			self.checksum = self.file_class['checksum']
		else:
			self.checksum = False
		
		if args.keep_checksum:
			self.keep_checksum = True
		elif "keep_checksum" in self.file_class:
			self.keep_checksum = self.config[self.cfg_section].getboolean("keep_checksum")
		else:
			self.keep_checksum = False
		
		self.uploadFiles()
	
	def load_group(self, grp = None):
		ret = {}
		self.cfg_section = grp or 'DEFAULT'
		grp = self.config[self.cfg_section]
		
		for key in grp:
			ret[ key ] = grp[ key ]
		
		return ret
	
	def uploadFiles(self):
		for f in self.files:
			base_name = os.path.basename(f)
			parts = base_name.split('.')
			ok = True
			
			if len(parts) > 1:
				suffix = '.' + parts[-1]
			else:
				suffix = ''
			
			if self.hash:
				target_name = hashlib.sha1(bytes(base_name, "UTF-8")).hexdigest() + suffix
			else:
				target_name = base_name
			
			if self.checksum:
				for alg in self.checksum.split(','):
					if not self.do_checksum(f, alg, self.file_class["uploadurl"] + "/" + self.subdir + "/" + target_name):
						ok = False
						break
			
			if not ok:
				break
			
			dl_url = self.file_class["publicurl"] + self.subdir + "/" + target_name
			upload_to = self.file_class["uploadurl"] + "/" + self.subdir + "/" + target_name
			
			if subprocess.call(['scp', f, upload_to], shell=False) == 0:
				self.uploadFinished(f, dl_url)
		
	
	def do_checksum(self, f, alg, target):
		try:
			chksum = subprocess.check_output([alg + 'sum', f], shell=False, universal_newlines=True).strip().split(' ')[0]
			
			if self.keep_checksum:
				chksum_src = "{0}.{1}sum".format(f, alg)
				chksum_file = open(chksum_src, 'w')
				chksum_file.write(chksum)
				chksum_file.write("\n")
				chksum_file.close()
				
			else:
				chksum_file = tempfile.NamedTemporaryFile()
				print (chksum_file.name)
				chksum_src = chksum_file.name
				chksum_file.write(bytes(chksum, 'UTF-8'))
				chksum_file.write(bytes("\n", 'UTF-8'))
				chksum_file.flush()
			
			target = target + ".{0}sum".format(alg)
			ret = subprocess.call(['scp', chksum_src, target], shell=False) == 0
			
			if not self.keep_checksum:
				chksum_file.close()
			
			return ret
			
		except subprocess.CalledProcessError:
			print("Checksum for '{0}' failed".format(f), file=sys.stderr)
			return false
	
	def uploadFinished(self, f, url):
		print("{0}: {1}".format(f, url))
		
		self.links.append(url)
		
		try:
			p = subprocess.Popen(['xsel', '-pi'], stdin=subprocess.PIPE, shell=False)
			p.communicate(bytes("\n".join(self.links), "UTF-8"))
			p.wait()
			
		except OSError as e:
			if e.errno != os.errno.ENOENT:
				raise

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description="Upload file(s) and print links")
	parser.add_argument('-c', '--class', dest='file_class', default='DEFAULT', help="Use settings from specified class")
	parser.add_argument('-d', '--dir', dest='subdir', default='', help="Upload files to specified subdirectory")
	parser.add_argument('-k', '--checksum', dest='checksum', default=None, help="Compute and upload checksum")
	parser.add_argument('-e', '--keep-checksum', action='store_true', dest='keep_checksum', help="Keep checksums locally after upload")
	parser.add_argument('-s', '--hash-name', action='store_true', dest='hash', help="Hash file name for every file")
	parser.add_argument('file', metavar='FILE', nargs='+', help="File(s) to upload")
	args = parser.parse_args()
	
	HaveUp(args)
