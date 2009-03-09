### Copyright (C) 2002-2006 Stephen Kennedy <stevek@gnome.org>

### This program is free software; you can redistribute it and/or modify
### it under the terms of the GNU General Public License as published by
### the Free Software Foundation; either version 2 of the License, or
### (at your option) any later version.

### This program is distributed in the hope that it will be useful,
### but WITHOUT ANY WARRANTY; without even the implied warranty of
### MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
### GNU General Public License for more details.

### You should have received a copy of the GNU General Public License
### along with this program; if not, write to the Free Software
### Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

#
# pychecker
#
import sys
if "--pychecker" in sys.argv:
    sys.argv.remove("--pychecker")
    import os
    os.environ['PYCHECKER'] = "--no-argsused --no-classattr --stdlib"
        #'--blacklist=gettext,locale,pygtk,gtk,gtk.keysyms,popen2,random,difflib,filecmp,tempfile'
    import pychecker.checker
#
# i18n support
#
sys.path += [ "/usr/share/meld"
]
import paths
import gettext
import locale

try:
    locale.setlocale(locale.LC_ALL, '')
    gettext.bindtextdomain("meld", paths.locale_dir() )
    gettext.textdomain("meld")
    gettext.install("meld", paths.locale_dir(), unicode=1)
except (IOError,locale.Error), e:
    # fake gettext until translations in place
    print "(meld): WARNING **: %s" % e
    __builtins__.__dict__["_"] = lambda x : x
__builtins__.__dict__["ngettext"] = gettext.ngettext

#
# python version
#

pyver = (2,3)
pygtkver = (2,6,0)

def ver2str(ver):
    return ".".join(map(str,ver))

if sys.version_info[:2] < pyver:
    print _("Meld requires %s or higher.") % ("python%s"%ver2str(pyver))
    sys.exit(1)

#
# pygtk 2 
#
try:
    import pygtk
except ImportError, e:
    print e
    print _("Meld requires %s or higher.") % ("pygtk%s"%ver2str(pygtkver))
    sys.exit(1)
else:
    pygtk.require("2.0")

#
# pygtk version
#
import gtk
if gtk.pygtk_version < pygtkver:
    print _("Meld requires %s or higher.") % ("pygtk%s"%ver2str(pygtkver))
    print _("Due to incompatible API changes some functions may not operate as expected.")

#
# We target pygtk 2.6
#
if gtk.pygtk_version >= (2,8,0):
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)

#
# main
#
import meldapp
for ignore in "--sm-config-prefix", "--sm-client-id":
    try: # ignore session management
        smprefix = sys.argv.index(ignore)
        del sys.argv[smprefix]
        del sys.argv[smprefix]
    except (ValueError,IndexError):
        pass
try: # don't pass on the profiling flag
    minusp = sys.argv.index("--profile")
    del sys.argv[minusp]
    import profile
    profile.run("meldapp.main()")
except ValueError:
    meldapp.main()
sys.exit(0)

