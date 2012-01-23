from django import forms

import sys, os, traceback
import zipfile, jsonpickle
from threading import Timer

import tornado.httpserver
import tornado.ioloop
import tornado.web

from openmdao.gui.util import *
from openmdao.gui.settings import MEDIA_ROOT

from openmdao.gui.consoleserverfactory import ConsoleServerFactory
server_mgr = ConsoleServerFactory()
print 'server_mgr',server_mgr

class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        return self.get_secure_cookie("user")

class AddonForm(forms.Form):
    distribution = forms.CharField(label='Distribution')
    
class AddOnsHandler(BaseHandler):
    ''' addon installation utility
    '''
    addons_url = 'http://openmdao.org/dists'
    addons_url = 'http://torpedo.grc.nasa.gov:31005/'
    
    def post(self):
        ''' easy_install the POST'd addon
        '''
        form = AddonForm(self)
        if form.is_valid():
            distribution = form.cleaned_data['distribution']
            cserver = server_mgr.console_server(self.get_cookie('sessionid'))
            cserver.install_addon(self.addons_url, distribution)
            self.render('tmpl/workspace/closewindow.html')
            
    def get(self):
        ''' show available addons, prompt for addon to be installed
        '''
        form = AddonForm()
        self.render('tmpl/workspace/addons.html', 
                     addons_url=self.addons_url, addon_form=form)
        
class GeometryHandler(BaseHandler):
    def get(self):
        ''' geometry viewer
        '''
        filename = self.get_argument('path')
        self.render('tmpl/workspace/o3dviewer.html',filename=filename)
 
class CloseHandler(BaseHandler):
    def get(self):
        server_mgr.delete_server(self.get_cookie('sessionid'))
        self.redirect('/')

class CommandHandler(BaseHandler):
    ''' get the command, send it to the cserver, return response
    '''
    def post(self):
        history = ''
        command = self.get_argument('command')
        # if there is a command, execute it & get the result
        if command:
            history = history + '>>> '+str(command) + '\n'
            result = ''
            try:
                cserver = server_mgr.console_server(self.get_cookie('sessionid'))
                result = cserver.onecmd(command)
            except Exception,e:
                print e
                result = sys.exc_info()
            if result:
                history = history + str(result) + '\n'
        self.write(history)
        
    def get(self):
        self.write('') # not used for now, could render a form

class ComponentHandler(BaseHandler):
    ''' add, remove or get a component
    '''
    def post(self,name):
        type = self.get_argument('type')
        parent = self.get_argument('parent')
        result = ''
        try:
            cserver = server_mgr.console_server(self.get_cookie('sessionid'))
            cserver.add_component(name,type,parent);
        except Exception,e:
            print e
            result = sys.exc_info()
        self.write(result)
        
    def delete(self,name):
        cserver = server_mgr.console_server(self.get_cookie('sessionid'))
        result = ''
        try:
            result = cserver.onecmd('del '+name)
        except Exception,e:
            print e
            result = sys.exc_info()
        self.write(result)
        
    def get(self,name):
        cserver = server_mgr.console_server(self.get_cookie('sessionid'))
        attr = {}
        try:
            attr = cserver.get_attributes(name)
        except Exception, e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print 'Exception calling get_attributes on',name
            print '-'*60
            print "*** print_exception:"
            traceback.print_exception(exc_type, exc_value, exc_traceback,file=sys.stdout)
            print "*** print_tb:"
            traceback.print_tb(exc_traceback, limit=100, file=sys.stdout)        
        self.write(attr)

class ComponentsHandler(BaseHandler):
    def get(self):
        cserver = server_mgr.console_server(self.get_cookie('sessionid'))
        json = cserver.get_components()
        self.write(json)

class ConnectionsHandler(BaseHandler):
    ''' get/set connections between two components in an assembly
    '''
    def post(self,pathname):
        result = ''
        try:
            src_name = self.get_argument('src_name')
            dst_name = self.get_argument('dst_name')
            connections = self.get_argument('connections')
            cserver = server_mgr.console_server(self.get_cookie('sessionid'))
            cserver.set_connections(pathname,src_name,dst_name,connections);
        except Exception,e:
            print e
            result = sys.exc_info()
        self.write(result)
        
    def get(self,pathname):
        cserver = server_mgr.console_server(self.get_cookie('sessionid'))
        connections = {}
        try:
            src_name = self.get_argument('src_name')
            dst_name = self.get_argument('dst_name')
            connections = cserver.get_connections(pathname,src_name,dst_name);
        except Exception, e:
            print e
        self.write(connections)

class StructureHandler(BaseHandler):
    ''' get the structure of the specified assembly, or of the global 
        namespace if no pathname is specified, consisting of the list
        of components and the connections between them
    '''
    def get(self,name):
        cserver = server_mgr.console_server(self.get_cookie('sessionid'))
        json = cserver.get_structure(name)
        self.write(json)

class ExecHandler(BaseHandler):
    ''' if a filename is POST'd, have the cserver execute the file
        otherwise just run() the project
    '''
    def post(self):
        result = ''
        cserver = server_mgr.console_server(self.get_cookie('sessionid'))
        filename = self.get_argument('filename',default=None)
        if filename:
            try:
                result = cserver.execfile(filename)
            except Exception,e:
                print e
                result = result + str(sys.exc_info()) + '\n'                
        else:
            try:
                cserver.run()
            except Exception,e:
                print e
                result = result + str(sys.exc_info()) + '\n'
        if result:
            self.write(result)

class ExitHandler(BaseHandler):
    ''' close the browser window and shut down the server
        (unfortunately neither of these things actually work)
    '''
    def get(self):
        server_mgr.delete_server(self.get_cookie('sessionid'))
        t = Timer(5, quit) # Quit after 5 seconds
        self.render('tmpl/closewindow.html')
    
class FileHandler(BaseHandler):
    ''' get/set the specified file/folder
    '''
    def post(self,filename):
        cserver = server_mgr.console_server(self.get_cookie('sessionid'))
        isFolder = self.get_argument('isFolder',default=None)
        if isFolder:
            self.write(cserver.ensure_dir(filename))
        else:
            contents = self.get_argument('contents',default='')
            self.write(cserver.write_file(filename,contents))
            
    def delete(self,filename):
        cserver = server_mgr.console_server(self.get_cookie('sessionid'))
        self.write(cserver.delete_file(filename))
        
    def get(self,filename):
        cserver = server_mgr.console_server(self.get_cookie('sessionid'))
        self.write(cserver.get_file(filename))

class FilesHandler(BaseHandler):
    ''' get a list of the users files in JSON format
    '''
    def get(self):
        cserver = server_mgr.console_server(self.get_cookie('sessionid'))
        filedict = cserver.get_files()
        json = jsonpickle.encode(filedict)
        self.write(json)
    
class ModelHandler(BaseHandler):
    ''' POST: get a new model (delete existing console server)
        GET:  get JSON representation of the model
    '''
    def post(self):
        server_mgr.delete_server(session.session.session_key)
        self.redirect('/')
        
    def get(self):
        cserver = server_mgr.console_server(self.get_cookie('sessionid'))
        json = cserver.get_JSON()
        self.write(json)

class OutputHandler(BaseHandler):
    ''' get any outstanding output from the model
    '''
    def get(self):
        cserver = server_mgr.console_server(self.get_cookie('sessionid'))
        self.write(cserver.get_output())

class ProjectHandler(BaseHandler):
    ''' GET:  load model fom the given project archive,
              or reload remebered project for session if no file given
              
        POST: save project archive of the current project
    '''
    def post(self):
        cserver = server_mgr.console_server(self.get_cookie('sessionid'))
        cserver.save_project()
        self.write('Saved.')
        
    def get(self):
        filename = self.get_argument('filename',default=None)
        if filename:
            self.set_secure_cookie('filename',filename)
        else:
            filename = self.get_secure_cookie('filename')
        if filename:
            server_mgr.delete_server(self.get_cookie('sessionid')) # delete old server
            cserver = server_mgr.console_server(self.get_cookie('sessionid'))        
            cserver.load_project(MEDIA_ROOT+'/'+filename)
            self.redirect(self.application.reverse_url('workspace'))
        else:
            self.redirect('/')

class PlotHandler(BaseHandler):
    ''' GET:  open a websocket server to supply updated valaues for the specified variable        
    '''
    def get(self,name):
        cserver = server_mgr.console_server(self.get_cookie('sessionid'))
        port = cserver.get_varserver(name)
        self.write(port)
        
class TypesHandler(BaseHandler):
    ''' get hierarchy of package/types to populate the Palette
    '''
    def get(self):
        cserver = server_mgr.console_server(self.get_cookie('sessionid'))
        types = cserver.get_available_types()
        try:
            types['working'] = cserver.get_workingtypes()
        except Exception, err:
            print "Error adding working types:", str(err)        
        self.write(jsonpickle.encode(types))

class UploadHandler(BaseHandler):
    ''' file upload utility
    '''
    def post(self):
        cserver = server_mgr.console_server(self.get_cookie('sessionid'))
        file = self.get_argument('myfile',default=None)
        if file:
            filename = file.name
            if len(filename) > 0:
                contents = file.read()
                cserver.add_file(filename,contents)
                self.render('tmpl/closewindow.html')

    def get(self):
        self.render('tmpl/workspace/upload.html')

class WorkflowHandler(BaseHandler):
    def get(self,name):
        cserver = server_mgr.console_server(self.get_cookie('sessionid'))
        json = cserver.get_workflow(name)
        self.write(json)
    
class WorkspaceHandler(BaseHandler):
    ''' render the workspace
    '''
    def get(self):
        self.render('tmpl/workspace/workspace.html')

class TestHandler(BaseHandler):
    ''' initialize the server manager &  render the workspace
    '''
    def get(self):
        self.render('tmpl/workspace/test.html')
