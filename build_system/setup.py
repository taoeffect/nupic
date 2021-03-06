#!/usr/bin/env python

#
# setup.py
#
# Sets up build system files, including Makefile.am and .vcproj files
# Must be run after a checkout and after adding or deleting files
#

import pybuild.utils as utils
from pybuild.arch import getArch
import os
import sys
import shutil
import getopt
import buildfile_gen.generate_buildfiles as gen
import logging

verbose = False

copyList = ["Makefile.am", "trunk.sln"]
# TODO: add new .build_system_ignore file to these dirs?
# build_system shouldn't be completely ignored because of the post_build project
ignoreList = ["build_system", "scripts", "release", "plugin_quickstart", ".svn",
              ".git"]

log = logging.getLogger('setup')

def copyFiles(trunkdir):
  if verbose:
    log.info("Running copyFiles")
  # This copies the files Makefile.ami and trunk.slni to the correponsing i-less
  copyListi = [l + "i" for l in copyList]
  # Create all of the intermediate Makefile.am's that are not generated by generate_buildfiles.py
  for (path, dirs, files) in os.walk(trunkdir, topdown=True):
    for f in copyList:
      if f in files and verbose:
        log.warn("Warning: %s already exists in %s" % (f, path))
    for file in files:
      if file in copyListi:
        # strip "i" off the end of the filename
        target = file[0:len(file)-1]
        src = os.path.join(path, file)
        dest = os.path.join(path, target)
        if not os.path.exists(dest) or open(src).read() != open(dest).read():
          log.info("Creating %s in %s" % (target, path))
          shutil.copy2(os.path.join(path, file), 
                       os.path.join(path, target))
        else:
          log.debug("Skipping creating %s in %s (unchanged)" % (target, path))

    for dir in dirs:
      if dir in ignoreList:
        dirs.remove(dir)
      elif os.path.exists(os.path.join(path, dir, ".build_system_ignore")):
        dirs.remove(dir)
        
  # Temporary until the Windows build machine migrates to VS 2008
  if sys.version[:3] == '2.5':
    text = open(os.path.join(trunkdir, 'trunk.sln')).read()
    text = text.replace('Format Version 10.00', 'Format Version 9.00')
    text = text.replace('# Visual Studio 2008', '# Visual Studio 2005')
    open(os.path.join(trunkdir, 'trunk.sln'), 'w').write(text)
        
  # Copy configure.ac to the root
  # @todo We will be generating this file
  configurePath = os.path.join(trunkdir, "build_system", "unix", "configure.ac")
  destPath = os.path.join(trunkdir, "configure.ac")
  if os.path.lexists(destPath):
    os.unlink(destPath)
  log.debug("Copying %s to %s" % (configurePath, destPath))
  shutil.copy2(configurePath, trunkdir)

def updateLibs(trunkdir):
  if verbose:
    log.info("Running updateLibs")

  # This can only be run on unix systems
  # We can skip it on win32 because it doesn't actually create
  # build files. 
  if sys.platform == "win32":
    return

  arch = getArch()
  c = 0
  for (path, dirs, files) in os.walk(os.path.join(trunkdir, "external", arch, "lib")):
    if ".svn" in dirs:
      dirs.remove(".svn")
    # performance optimization
    if "site-packages" in dirs:
      dirs.remove("site-packages")
    for file in files:
      if file.endswith(".a"):
        os.system('touch -t 199901011201 %s' % os.path.join(path, file))
        c = c + 1
  log.info("Updated %d libraries in arch %s" % (c, arch))


def clean(path):
  """Remove all auto-generated Makefile.am's. Useful for debugging this script.

  Args:
    path: path to the root of the repo to clean
  """
  for (path, dirs, files) in os.walk(path, topdown=True):
    # Remove generated files.
    for f in copyList:
      if f in files:
        log.info("Removing %s in %s" % (f, path))
        os.remove(os.path.join(path, f))
        files.remove(f)
    # Remove vcproj files.
    for f in files:
      if f.endswith(".vcproj"):
        log.info("Removing %s in %s" % (f, path))
        os.remove(os.path.join(path, f))
    # Skip directories in ignore list or with ignore dotfile.
    for d in list(dirs):
      if (os.path.exists(os.path.join(path, d, ".build_system_ignore")) or
          d in ignoreList):
        dirs.remove(d)

  # Remove the top-level configure.ac.
  configureFile = os.path.join(path, "configure.ac")
  if os.path.exists(configureFile):
    os.remove(configureFile)


def usage():
  print """
Usage: %s [--clean] [--autogen] [--quiet] [--verbose] [--win32BuildDir=<dir>] [--win32InstallDir=<dir>] [--win32PythonDir=<dir>]""" % sys.argv[0]
  sys.exit(1)


def setup(dir, extraSubstitutions=None):
  if verbose:
    log.info("Running setup")
  copyFiles(dir)
  updateLibs(dir)
  if verbose:
    log.info("Running generate_buildfiles")
  gen.generate_buildfiles(dir, True, extraSubstitutions)
  if verbose:
    log.info("Done with generate_buildfiles")
  
if __name__ == "__main__":

  mydir = os.path.dirname(os.path.abspath(__file__))
  trunkdir = os.path.normpath(os.path.join(mydir, os.pardir))
  optionList = ["clean", "autogen", "verbose", "win32BuildDir=", "win32InstallDir=", "win32PythonDir="]
  try:
    (opts, args) = getopt.gnu_getopt(sys.argv[1:], "", optionList)
  except Exception, e:
    print "Error parsing command line: %s" % e
    usage()

  doClean = False
  doAutogen = False
  verbose = False
  extraSubstitutions = dict()
  for (option, val) in opts:
    if option == "--clean":
      doClean = True
    elif option == "--verbose":
      verbose = True
    elif option == "--quiet":
      verbose = False
    elif option == "--autogen":
      doAutogen = True
      if sys.platform == "win32":
        print "--autogen may not be specified on a windows system"
        sys.exit(1)
    elif option == "--win32InstallDir":
      extraSubstitutions["Win32InstallDir"] = val
    elif option == "--win32BuildDir":
      extraSubstitutions["Win32BuildDir"] = val
    elif option == "--win32PythonDir":
      extraSubstitutions["Win32PythonDir"] = val


    
  if doAutogen and doClean:
    print "Only one of --autogen and --clean may be specified"
    sys.exit(1)

  if verbose:
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout, 
                        format="%(message)s")
    logging.getLogger('').setLevel(logging.DEBUG)
  else:
    logging.basicConfig(level=logging.INFO, stream=sys.stdout, 
                        format="%(message)s")
    logging.getLogger('').setLevel(logging.INFO)


  if len(extraSubstitutions) > 0:
    print "The following special values will be used in win32 build files"
    for (key, value) in extraSubstitutions.iteritems():
      print "%s:  '%s'" % (key, value)
      

  if not doClean:
    
    setup(trunkdir, extraSubstitutions)
    if doAutogen:
      os.chdir(trunkdir)
      log.info("Running autogen...")
      command = os.path.join("build_system", "unix", "autogen.sh")
      utils.runCommand(["/bin/bash", command], outputLogLevel=logging.INFO)
      if verbose:
        log.info("Done with autogen.sh")
  else:
    clean(trunkdir)

  log.info("Done")

      

      
