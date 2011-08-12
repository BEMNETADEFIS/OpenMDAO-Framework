
#
# Build OpenMDAO package distributions.
#
import sys, os
import shutil
import logging
from subprocess import Popen, STDOUT, PIPE, check_call
from datetime import date
from optparse import OptionParser
import ConfigParser
import tempfile
import StringIO
import tarfile
import zipfile

# get the list of openmdao subpackages from mkinstaller.py
from openmdao.devtools.mkinstaller import openmdao_packages
from openmdao.devtools.build_docs import build_docs
from openmdao.devtools.utils import get_git_branch, get_git_branches, get_git_log_info, repo_top

relfile_template = """
# This file is automatically generated

__version__ = '%(version)s'
__comments__ = \"\"\"%(comments)s\"\"\"
__date__ = '%(date)s'
__commit__ = '%(commit)s'
"""


def get_releaseinfo_str(version):
    """Creates the content of the releaseinfo.py files"""
    opts = {}
    f = StringIO.StringIO()
    opts['version'] = version
    opts['date'] = get_git_log_info("%ci")
    opts['comments'] = get_git_log_info("%b%+s%+N")
    opts['commit'] = get_git_log_info("%H")
    f.write(relfile_template % opts)
    return f.getvalue()

def create_releaseinfo_file(projname, relinfo_str):
    """Creates a releaseinfo.py file in the current directory"""
    dirs = projname.split('.')
    os.chdir(os.path.join(*dirs))
    print 'updating releaseinfo.py for %s' % projname
    with open('releaseinfo.py', 'w') as f:
        f.write(relinfo_str)
        
def rollback_releaseinfo_file(projname):
    """Creates a releaseinfo.py file in the current directory"""
    dirs = projname.split('.')
    os.chdir(os.path.join(*dirs))
    print 'rolling back releaseinfo.py for %s' % projname
    os.system('git checkout -- releaseinfo.py')


def _has_checkouts():
    cmd = 'git status -s'
    p = Popen(cmd, stdout=PIPE, stderr=STDOUT, env=os.environ, shell=True)
    out = p.communicate()[0]
    ret = p.returncode
    if ret != 0:
        logging.error(out)
        raise RuntimeError(
             'error while getting status of git repository from directory %s (return code=%d): %s'
              % (os.getcwd(), ret, out))
    for line in out.split('\n'):
        line = line.strip()
        if len(line)>1 and not line.startswith('?'):
            return True
    return False


def _build_dist(build_type, destdir):
    cmd = '%s setup.py %s -d %s' % (sys.executable, build_type, destdir)
    p = Popen(cmd, stdout=PIPE, stderr=STDOUT, env=os.environ, shell=True)
    out = p.communicate()[0]
    ret = p.returncode
    if ret != 0:
        logging.error(out)
        raise RuntimeError(
             'error while building %s in %s (return code=%d): %s'
              % (build_type, os.getcwd(), ret, out))

def _build_sdist(projdir, destdir, version):
    """Build an sdist out of a develop egg and place it in destdir."""
    startdir = os.getcwd()
    try:
        os.chdir(projdir)
        # clean up any old builds
        if os.path.exists('build'):
            shutil.rmtree('build')
        _build_dist('sdist', destdir)
        if os.path.exists('build'):
            shutil.rmtree('build', ignore_errors=True)
        if sys.platform.startswith('win'):
            os.chdir(destdir)
            # unzip the .zip file and tar it up so setuptools will find it on the server
            base = os.path.basename(projdir)+'-%s' % version
            zipname = base+'.zip'
            tarname = base+'.tar.gz'
            zarch = zipfile.ZipFile(zipname, 'r')
            zarch.extractall()
            zarch.close()
            archive = tarfile.open(tarname, 'w:gz')
            archive.add(base)
            archive.close()
            os.remove(zipname)
            shutil.rmtree(base)
    finally:
        os.chdir(startdir)

def _build_bdist_eggs(projdirs, destdir, hosts, configfile):
    """Builds binary eggs on the specified hosts and places them in destdir.
    If 'localhost' is an entry in hosts, then it builds a binary egg on the
    current host as well.
    """
    startdir = os.getcwd()
    hostlist = hosts[:]
    try:
        if 'localhost' in hostlist:
            hostlist.remove('localhost')
            for pdir in projdirs:
                os.chdir(pdir)
                _build_dist('bdist_egg', destdir)
            
        os.chdir(startdir)
        if hostlist:
            cmd = ['remote_build', 
                   '-d', destdir, '-c', configfile]
            for pdir in projdirs:
                cmd.extend(['-s', pdir])
            for host in hostlist:
                cmd.append('--host=%s' % host)
                check_call(cmd)
    finally:
        os.chdir(startdir)


def update_releaseinfo_files(version):
    startdir = os.getcwd()
    topdir = repo_top()
    
    releaseinfo_str = get_releaseinfo_str(version)
    
    try:
        for project_name, pdir, pkgtype in openmdao_packages:
            pdir = os.path.join(topdir, pdir, project_name)
            if 'src' in os.listdir(pdir):
                os.chdir(os.path.join(pdir, 'src'))
            else:
                os.chdir(pdir)
            create_releaseinfo_file(project_name, releaseinfo_str)
    finally:
        os.chdir(startdir)
    
def rollback_releaseinfo_files():
    startdir = os.getcwd()
    topdir = repo_top()
    
    try:
        for project_name, pdir, pkgtype in openmdao_packages:
            pdir = os.path.join(topdir, pdir, project_name)
            if 'src' in os.listdir(pdir):
                os.chdir(os.path.join(pdir, 'src'))
            else:
                os.chdir(pdir)
            rollback_releaseinfo_file(project_name)
    finally:
        os.chdir(startdir)
    
    
def main():
    """Create an OpenMDAO release, placing the following files in the 
    specified destination directory:
    
        - source distribs of all of the openmdao subpackages
        - binary eggs for openmdao subpackages with compiled code
        - an installer script for the released version of openmdao that will
          create a virtualenv and populate it with all of the necessary
          dependencies needed to use openmdao
        - Sphinx documentation
          
    In order to run this, you must be in a git repository with no uncommitted
    changes. A release branch will be created from the specified base branch, 
    and in the process of running, a number of releaseinfo.py files will be 
    updated with new version information and committed.
        
    """
    parser = OptionParser()
    parser.add_option("-d", "--destination", action="store", type="string", 
                      dest="destdir",
                      help="directory where distributions will be placed")
    parser.add_option("-v", "--version", action="store", type="string", dest="version",
                      help="version string applied to all openmdao distributions")
    parser.add_option("-m", action="store", type="string", dest="comment",
                      help="optional comment for version tag")
    parser.add_option("-b", "--basebranch", action="store", type="string", dest="base",
                      default='master', help="base branch for release. defaults to master")
    parser.add_option("-t", "--test", action="store_true", dest="test",
                      help="used for testing. A release branch will not be created")
    parser.add_option("-n", "--nodocbuild", action="store_true", dest="nodocbuild",
                      help="used for testing. The docs will not be rebuilt if they already exist")
    parser.add_option("--host", action='append', dest='hosts', metavar='HOST',
                      default=[],
                      help="host from config file to build bdist_eggs on. "
                           "Multiple --host args are allowed.")
    parser.add_option("-c", "--config", action='store', dest='cfg', metavar='CONFIG',
                      default='~/.openmdao/testhosts.cfg',
                      help="path of config file where info for hosts is located")
    (options, args) = parser.parse_args(sys.argv[1:])
    
    if not options.version or not options.destdir:
        parser.print_help()
        sys.exit(-1)
        
    options.cfg = os.path.expanduser(options.cfg)
    
    config = ConfigParser.ConfigParser()
    config.readfp(open(options.cfg))
    
    haswin = False
    for host in options.hosts:
        if host == 'localhost':
            if sys.platform.startswith('win'):
                haswin = True
        elif config.has_section(host):
            platform = config.get(host, 'platform')
            if platform == 'windows':
                haswin = True
    if not haswin:
        print "no windows host was specified, so can't build binary eggs for windows"
        sys.exit(-1)
        
    orig_branch = get_git_branch()
    if not orig_branch:
        print "You must run mkrelease from within a git repository. aborting"
        sys.exit(-1)

    if not options.test:
        if orig_branch != options.base:
            print "Your current branch '%s', is not the specified base branch '%s'" % (orig_branch, options.base)
            sys.exit(-1)
    
        if _has_checkouts():
            print "There are uncommitted changes. You must run mkrelease.py from a clean branch"
            sys.exit(-1)
        
        if orig_branch == 'master':
            print "pulling master"
            os.system("git pull origin master")
            if _has_checkouts():
                print "something went wrong during pull.  aborting"
                sys.exit(-1)
        else:
            print "WARNING: base branch is not 'master' so it has not been"
            print "automatically brought up-to-date."
            answer = raw_input("Proceed? (Y/N) ")
            if answer.lower() not in ["y", "yes"]:
                sys.exit(-1)
        
        relbranch = "release_%s" % options.version
        if relbranch in get_git_branches():
            print "release branch %s already exists in this repo" % relbranch
            sys.exit(-1)

        print "creating release branch '%s' from base branch '%s'" % (relbranch, orig_branch)
        check_call(['git', 'branch', relbranch])
        print "checking out branch '%s'" % relbranch
        check_call(['git', 'checkout', relbranch])
    
    destdir = os.path.abspath(options.destdir)
    if not os.path.exists(destdir):
        os.makedirs(destdir)

    startdir = os.getcwd()
    topdir = repo_top()
    
    cfgpath = os.path.expanduser(options.cfg)
    
    try:
        update_releaseinfo_files(options.version)
        
        # build the docs
        docdir = os.path.join(topdir, 'docs')
        idxpath = os.path.join(docdir, '_build', 'html', 'index.html')
        
        if not os.path.isfile(idxpath) or not options.nodocbuild:
            build_docs(argv=['-v', options.version])
        shutil.copytree(os.path.join(topdir,'docs','_build', 'html'), 
                    os.path.join(destdir,'docs'))

        if not options.test:
            # commit the changes to the release branch
            print "committing all changes to branch '%s'" % relbranch
            check_call(['git', 'commit', '-a', '-m', 
                        '"updating releaseinfo files for release %s"' % 
                        options.version])

        # build openmdao package distributions
        proj_dirs = []
        for project_name, pdir, pkgtype in openmdao_packages:
            pdir = os.path.join(topdir, pdir, project_name)
            if 'src' in os.listdir(pdir):
                os.chdir(os.path.join(pdir, 'src'))
            else:
                os.chdir(pdir)
            print 'building %s' % project_name
            _build_sdist(pdir, destdir, options.version)
            if pkgtype == 'bdist_egg':
                proj_dirs.append(pdir)
                
        os.chdir(startdir)
        _build_bdist_eggs(proj_dirs, destdir, options.hosts, cfgpath)
            
        print 'creating bootstrapping installer script go-openmdao.py'
        installer = os.path.join(os.path.dirname(__file__),
                                 'mkinstaller.py')
        
        check_call([sys.executable, installer, '--dest=%s'%destdir])

        if options.comment:
            comment = options.comment
        else:
            comment = 'creating release %s' % options.version
        
        if options.test:
            rollback_releaseinfo_files()
        else:
            # tag the current revision with the release version id
            print "tagging release with '%s'" % options.version
            check_call(['git', 'tag', '-f', '-a', options.version, '-m', comment])
            
            check_call(['git', 'checkout', orig_branch])
            print "\n*REMEMBER* to push '%s' up to the master branch if this release is official" % relbranch
        
        print "new release files have been placed in %s" % destdir
        
    finally:
        os.chdir(startdir)
    
if __name__ == '__main__':
    main()
