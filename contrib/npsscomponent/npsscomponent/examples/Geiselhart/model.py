"""
PARTIAL! Port of Karl's ModelCenter SBJ propulsion process model.

It's a fairly complex example of running multiple linked components
in sequence.  Each NPSS component is run in it's own subdirectory,
which is where the NPSS output is written.  The log file also has some
information written to it in addition to what's shown on screen.

Known problems:
    - The components run, but since the port is only partial,
      the results are quite wrong.
    - 'Design' variables are set as OUTPUTS and 'PropulsionData'
      variables are set as INPUTS.  This looks odd, but is neccessary
      until some more issues in the framework are ironed-out.
"""
import os.path

from enthought.traits.api import Array, Float
from openmdao.main.api import Assembly, Component, Container, FileTrait

from npsscomponent import NPSScomponent

__version__ = '0.1'

# pylint: disable-msg=E1101
# "Instance of <class> has no <attr> member"


class Design(Component):
    """ Design variables. """

    def __init__(self, name='Design', parent=None):
        super(Design, self).__init__(name, parent)

        Float('FanPRdes',        self, iostatus='out', default=3.615)
        Float('TOCThrust',       self, iostatus='out', default=7000)
        Float('MN',              self, iostatus='out', default=1.8)
        Float('alt',             self, iostatus='out', default=53700)
        Float('Knoz',            self, iostatus='out', default=0.88)
        Float('extractionRatio', self, iostatus='out', default=1.05)
        Float('HpcPRdes',        self, iostatus='out', default=6.51937)
        Float('Cfg',             self, iostatus='out', default=0.985)
        Float('maxDiamFact',     self, iostatus='out', default=1.17)
        Float('I_externalFact',  self, iostatus='out', default=0.48)
        Float('I_divergFact',    self, iostatus='out', default=0.5)
        Float('cowl_angle',      self, iostatus='out', default=6)

    def execute(self):
        """ Just to trace execution. """
        print self.get_pathname(), 'execution begins'
        super(Design, self).execute()
        print self.get_pathname(), '    complete'


class PropulsionData(Component):
    """ Computed propulsion data. """

    def __init__(self, name='PropulsionData', parent=None):
        super(PropulsionData, self).__init__(name, parent)

        Float('link_bladeTipRadius', self, iostatus='in', default=0.)
        Float('link_contRingRadialThickness', self, iostatus='in', default=0.)
        Float('link_maxDiamFact', self, iostatus='in', default=0.)
        Float('link_Acapture', self, iostatus='in', default=0.)
        Float('link_inletLength', self, iostatus='in', default=0.)
        Float('link_length', self, iostatus='in', default=0.)

        Float('Acapture', self, iostatus='out', default=0.)

        FLOPSdata(parent=self)
        PlumeData(parent=self)
        USM3Ddata(parent=self)
        NacelleData(parent=self)
        ANOPPdata(parent=self)

    def execute(self):
        """ Evaluate link expressions. """
        print self.get_pathname(), 'execution begins'

#       PropulsionData.FLOPS.dnac =
#           2*(NPSS_WATE.engine.WATE.WATE_fan.bladeTipRadius
#              + NPSS_WATE.engine.WATE.WATE_fan.contRingRadialThickness/12)
#           * Design.maxDiamFact
        self.FLOPS.dnac = \
           2*(self.link_bladeTipRadius \
              + self.link_contRingRadialThickness/12) \
           * self.link_maxDiamFact

#       PropulsionData.Acapture =
#           NPSS_ADP.engine.inlet.S_install.Acapture / 144.
        self.Acapture = \
            self.link_Acapture / 144.

#       PropulsionData.FLOPS.xnac =
#           (NPSS_WATE.engine.WATE.WATE_inlet.length
#            + NPSS_WATE.engine.WATE.length) / 12.
        self.FLOPS.xnac = \
            (self.link_inletLength \
             + self.link_length) / 12.

        print self.get_pathname(), '    complete'


class FLOPSdata(Container):

    engdeck = FileTrait(iostatus='in')
    thrso = Float(0., iostatus='in')
    weng = Float(0., iostatus='in')
    xnac = Float(0., iostatus='in')
    dnac = Float(0., iostatus='in')
        
    def __init__(self, name='FLOPS', parent=None):
        super(FLOPSdata, self).__init__(name, parent)
        self.engdeck.filename = 'engdeck'



class PlumeData(Container):

    m_dot = Float(0., iostatus='in')
    Ptj = Float(0., iostatus='in')
    Ttj = Float(0., iostatus='in')
    far = Float(0., iostatus='in')
    Astar = Float(0., iostatus='in')
    Ae = Float(0., iostatus='in')
    Amax = Float(0., iostatus='in')
    I_diverg = Float(0., iostatus='in')
    I_external = Float(0., iostatus='in')
    
    def __init__(self, name='Plume', parent=None):
        super(PlumeData, self).__init__(name, parent)


class USM3Ddata(Container):

    fuel = Float(0., iostatus='in')
    gammaj = Float(0., iostatus='in')
    pjet = Float(0., iostatus='in')
    p0jet = Float(0., iostatus='in')
    Rratio = Float(0., iostatus='in')
    T0jet = Float(0., iostatus='in')
    
    def __init__(self, name='USM3D', parent=None):
        super(USM3Ddata, self).__init__(name, parent)

        USM3Dinputs(parent=self)


class USM3Dinputs(Container):

    def __init__(self, name='Inputs', parent=None):
        super(USM3Dinputs, self).__init__(name, parent)

        USM3Dfreestream(parent=self)
        USM3Dplenum(parent=self)
        USM3Dthroat(parent=self)
        USM3Dexit(parent=self)


class USM3Dfreestream(Container):

    a = Float(0., iostatus='in')
    gamma = Float(0., iostatus='in')
    rho = Float(0., iostatus='in')
    R = Float(0., iostatus='in')
    Ps = Float(0., iostatus='in')
    Pt = Float(0., iostatus='in')
    Ts = Float(0., iostatus='in')
    Tt = Float(0., iostatus='in')
    
    def __init__(self, name='Freestream', parent=None):
        super(USM3Dfreestream, self).__init__(name, parent)


class USM3Dplenum(Container):

    gamma_s = Float(0., iostatus='in')
    gamma_t = Float(0., iostatus='in')
    Rt = Float(0., iostatus='in')
    Rs = Float(0., iostatus='in')
    Ps = Float(0., iostatus='in')
    Pt = Float(0., iostatus='in')
    Ts = Float(0., iostatus='in')
    Tt = Float(0., iostatus='in')
    
    def __init__(self, name='Plenum', parent=None):
        super(USM3Dplenum, self).__init__(name, parent)


class USM3Dthroat(Container):

    gamma_s = Float(0., iostatus='in')
    gamma_t = Float(0., iostatus='in')
    Rt = Float(0., iostatus='in')
    Rs = Float(0., iostatus='in')
    Ps = Float(0., iostatus='in')
    Pt = Float(0., iostatus='in')
    Ts = Float(0., iostatus='in')
    Tt = Float(0., iostatus='in')
    
    def __init__(self, name='Throat', parent=None):
        super(USM3Dthroat, self).__init__(name, parent)


class USM3Dexit(Container):

    gamma_s = Float(0., iostatus='in')
    gamma_t = Float(0., iostatus='in')
    Rt = Float(0., iostatus='in')
    Rs = Float(0., iostatus='in')
    Ps = Float(0., iostatus='in')
    Pt = Float(0., iostatus='in')
    Ts = Float(0., iostatus='in')
    Tt = Float(0., iostatus='in')
    
    def __init__(self, name='Exit', parent=None):
        super(USM3Dexit, self).__init__(name, parent)


class NacelleData(Container):

    X = Array('d', shape=(None,), value=[], iostatus='in')
    Y = Array('d', shape=(None,), value=[], iostatus='in')
    
    def __init__(self, name='Nacelle', parent=None):
        super(NacelleData, self).__init__(name, parent)



class ANOPPdata(Container):

    def __init__(self, name='ANOPP', parent=None):
        super(ANOPPdata, self).__init__(name, parent)


class TracingNPSS(NPSScomponent):
    """ Simply overrides execute() to trace start & stop times. """

    def execute(self):
        print self.get_pathname(), 'execution begins'
        super(TracingNPSS, self).execute()
        print self.get_pathname(), '    complete'


class Model(Assembly):
    """ SBJ propulsion model. """

    def connect(self, src_path, dst_path):
        """ Overriding default to dynamically publicise/hoist variables. """
        comp, rest = src_path.split('.', 1)
        src_comp = getattr(self, comp)
        if rest.find('.') > 0:
            src_path = self.hoist(src_comp, rest, 'out')
        else:
            if src_comp.trait(rest) is None:
                src_comp.make_public((rest, '', 'out'))
                self._var_graph.add_node(src_path)

        comp, rest = dst_path.split('.', 1)
        dst_comp = getattr(self, comp)
        if rest.find('.') > 0:
            dst_path = self.hoist(dst_comp, rest, 'in')
        else:
            if dst_comp.trait(rest) is None:
                dst_comp.make_public(rest)
                self._var_graph.add_node(dst_path)

        super(Model, self).connect(src_path, dst_path)

    def hoist(self, comp, path, io_status):
        """ Hoist a variable so that it may be connected. """
        name = '_'+path.replace('.', '_')
        trait = comp.trait(path)
        if trait is None:
            comp.make_public((name, path, io_status))
            trait = comp.trait(name)

        newpath = '.'.join([comp.name,name])
        if newpath not in self._var_graph:
            self.create_passthru(newpath)
            #passthru = var.create_passthru(comp, name)
            #comp.make_public(passthru)
            #self._var_graph.add_node(newpath)
        return newpath

    def __init__(self, name='SBJ_Propulsion', *args, **kwargs):
        super(Model, self).__init__(name, *args, **kwargs)
        self.external_files.append({'path':'README.txt'})

        model_dir = os.path.join('..', 'Full_Model', 'Cycle', 'run')
        includes = [
            '-I', '../Full_Model/Components',
            '-I', '../Full_Model/Cycle',
            '-I', '../Full_Model/Cycle/view',
            '-I', '../Full_Model/Cycle/src',
            '-I', '../Full_Model/Cycle/maps',
            '-I', '../Full_Model/Cycle/run',
            '-I', '../Full_Model/ROSE',
            '-I', '../Full_Model/ROSE/BaseClasses']

        # Design variables.
        Design(parent=self)

        # ADP.
        arglist = []
        arglist.extend(includes)
        arglist.append(os.path.join(model_dir, 'MC_ADP.mdl'))
        TracingNPSS('NPSS_ADP', self, directory='NPSS_ADP',
                    arglist=arglist, output_filename='NPSS.out')
        self.NPSS_ADP.external_files.append(
            {'path':os.path.join(model_dir, 'MC_ADP.run')})
        self.NPSS_ADP.run_command = 'mcRun()'
        self.NPSS_ADP.reload_flag = 'mcReload'

        self.connect('Design.alt',       'NPSS_ADP.engine.alt')
        self.connect('Design.extractionRatio', 'NPSS_ADP.engine.extractionRatio')
        self.connect('Design.FanPRdes',  'NPSS_ADP.engine.FanPRdes')
        self.connect('Design.HpcPRdes',  'NPSS_ADP.engine.HpcPRdes')
        self.connect('Design.Knoz',      'NPSS_ADP.engine.Knoz')
        self.connect('Design.MN',        'NPSS_ADP.engine.MN')
        self.connect('Design.Cfg',       'NPSS_ADP.engine.nozzle.Cfg')
        self.connect('Design.TOCThrust', 'NPSS_ADP.engine.TOCThrust')

        # SLS.
        arglist = []
        arglist.extend(includes)
        arglist.append(os.path.join(model_dir, 'MC_SLS.mdl'))
        TracingNPSS('NPSS_SLS', self, directory='NPSS_SLS',
                    arglist=arglist, output_filename='NPSS.out')
        self.NPSS_SLS.external_files.append(
            {'path':os.path.join(model_dir, 'MC_SLS.run')})
        self.NPSS_SLS.run_command = 'mcRun()'
        self.NPSS_SLS.reload_flag = 'mcReload'

        self.connect('Design.alt',       'NPSS_SLS.engine.alt')
        self.connect('Design.extractionRatio', 'NPSS_SLS.engine.extractionRatio')
        self.connect('Design.FanPRdes',  'NPSS_SLS.engine.FanPRdes')
        self.connect('Design.HpcPRdes',  'NPSS_SLS.engine.HpcPRdes')
        self.connect('Design.Knoz',      'NPSS_SLS.engine.Knoz')
        self.connect('Design.MN',        'NPSS_SLS.engine.MN')
        self.connect('Design.Cfg',       'NPSS_SLS.engine.nozzle.Cfg')
        self.connect('Design.TOCThrust', 'NPSS_SLS.engine.TOCThrust')

        # WATE.
        wate_dir = os.path.join('..', 'Full_Model', 'Weight', 'run')
        arglist = [
            '-I', '../Full_Model/Components',
            '-I', '../Full_Model/Weight',
            '-I', '../Full_Model/Weight/view',
            '-I', '../Full_Model/Weight/src',
            '-I', '../Full_Model/Weight/maps',
            '-I', '../Full_Model/Weight/run',
            '-I', '../Full_Model/ROSE',
            '-I', '../Full_Model/ROSE/BaseClasses']
        arglist.append(os.path.join(wate_dir, 'MCengine.mdl'))
        TracingNPSS('NPSS_WATE', self, directory='NPSS_WATE',
                    arglist=arglist, output_filename='NPSS.out')
        self.NPSS_WATE.external_files.append(
            {'path':os.path.join(wate_dir, 'MCengine.run')})
        self.NPSS_WATE.run_command = 'mcRun()'
        self.NPSS_WATE.reload_flag = 'mcReload'

        self.connect('Design.alt',       'NPSS_WATE.engine.ambient.Zalt')
        self.connect('Design.MN',        'NPSS_WATE.engine.ambient.ZMN')
        self.connect('Design.extractionRatio', 'NPSS_WATE.engine.extractionRatio')
        self.connect('Design.FanPRdes',  'NPSS_WATE.engine.FanPRdes')
        self.connect('Design.HpcPRdes',  'NPSS_WATE.engine.HpcPRdes')
        self.connect('Design.Cfg',       'NPSS_WATE.engine.nozzle.Cfg')
        self.connect('Design.TOCThrust', 'NPSS_WATE.engine.TOCThrust')

        # FLOPS.
        arglist = []
        arglist.extend(includes)
        arglist.append(os.path.join(model_dir, 'MCengine.mdl'))
        TracingNPSS('NPSS_FLOPS', self, directory='NPSS_FLOPS',
                    arglist=arglist, output_filename='NPSS.out')
        self.NPSS_FLOPS.external_files.append(
            {'path':os.path.join(model_dir, 'MCengine.run')})
        self.NPSS_FLOPS.run_command = 'mcRun()'
        self.NPSS_FLOPS.reload_flag = 'mcReload'

        self.connect('Design.alt',       'NPSS_FLOPS.engine.alt')
        self.connect('Design.extractionRatio', 'NPSS_FLOPS.engine.extractionRatio')
        self.connect('Design.FanPRdes',  'NPSS_FLOPS.engine.FanPRdes')
        self.connect('Design.HpcPRdes',  'NPSS_FLOPS.engine.HpcPRdes')
        self.connect('Design.Knoz',      'NPSS_FLOPS.engine.Knoz')
        self.connect('Design.MN',        'NPSS_FLOPS.engine.MN')
        self.connect('Design.Cfg',       'NPSS_FLOPS.engine.nozzle.Cfg')
        self.connect('Design.TOCThrust', 'NPSS_FLOPS.engine.TOCThrust')

        # ANOPP
        arglist = []
        arglist.extend(includes)
        arglist.append(os.path.join(model_dir, 'MCnoise.mdl'))
        TracingNPSS('NPSS_ANOPP', self, directory='NPSS_ANOPP',
                    arglist=arglist, output_filename='NPSS.out')
        self.NPSS_ANOPP.external_files.append(
            {'path':os.path.join(model_dir, 'MCnoise.run')})
        self.NPSS_ANOPP.run_command = 'mcRun()'
        self.NPSS_ANOPP.reload_flag = 'mcReload'

        self.connect('Design.alt',       'NPSS_ANOPP.engine.alt')
        self.connect('Design.extractionRatio', 'NPSS_ANOPP.engine.extractionRatio')
        self.connect('Design.FanPRdes',  'NPSS_ANOPP.engine.FanPRdes')
        self.connect('Design.HpcPRdes',  'NPSS_ANOPP.engine.HpcPRdes')
        self.connect('Design.Knoz',      'NPSS_ANOPP.engine.Knoz')
        self.connect('Design.MN',        'NPSS_ANOPP.engine.MN')
        self.connect('Design.Cfg',       'NPSS_ANOPP.engine.nozzle.Cfg')
        self.connect('Design.TOCThrust', 'NPSS_ANOPP.engine.TOCThrust')

        self.connect('NPSS_SLS.engine.PERF.Fn', 'NPSS_ANOPP.MaxThrust')

#       NPSS_ANOPP.A_ref =
#           pi*144*NPSS_WATE.engine.WATE.WATE_fan.bladeTipRadius**2
        self.connect('NPSS_WATE.engine.WATE.WATE_fan.bladeTipRadius',
                     'NPSS_ANOPP.link_bladeTipRadius')

#       NPSS_ANOPP.last_LPT_stg =
#           NPSS_WATE.engine.WATE.WATE_LPT.numStages-1
        self.connect('NPSS_WATE.engine.WATE.WATE_LPT.numStages',
                     'NPSS_ANOPP.link_numStages')

#       NPSS_ANOPP.LP_RPM_scalar =
#           NPSS_WATE.engine.WATE.WATE_fan.spoolRPM
#               / NPSS_WATE.engine.WATE.WATE_LP_Shaft.speed
        self.connect('NPSS_WATE.engine.WATE.WATE_fan.spoolRPM',
                     'NPSS_ANOPP.link_spoolRPM')
        self.connect('NPSS_WATE.engine.WATE.WATE_LP_Shaft.speed',
                     'NPSS_ANOPP.link_speed')

        self.connect('NPSS_WATE.engine.WATE.WATE_burner.innerDiam',
                     'NPSS_ANOPP.WATE_Burner.innerDiam')
        self.connect('NPSS_WATE.engine.WATE.WATE_burner.outerDiam',
                     'NPSS_ANOPP.WATE_Burner.outerDiam')

        self.connect('NPSS_WATE.engine.WATE.WATE_Nozzle.outPort.axialPosition',
                     'NPSS_ANOPP.WATE_Byp_Nozz.outPort.axialPosition')
        self.connect('NPSS_WATE.engine.WATE.WATE_Nozzle.outPort.innerRadius',
                     'NPSS_ANOPP.WATE_Byp_Nozz.outPort.innerRadius')
        self.connect('NPSS_WATE.engine.WATE.WATE_Nozzle.outPort.outerRadius',
                     'NPSS_ANOPP.WATE_Byp_Nozz.outPort.outerRadius')
        self.connect('NPSS_WATE.engine.WATE.WATE_Nozzle.outPort.axialPosition',
                     'NPSS_ANOPP.WATE_Core_Nozz.outPort.axialPosition')
        self.connect('NPSS_WATE.engine.WATE.WATE_Nozzle.outPort.innerRadius',
                     'NPSS_ANOPP.WATE_Core_Nozz.outPort.innerRadius')
        self.connect('NPSS_WATE.engine.WATE.WATE_Nozzle.outPort.outerRadius',
                     'NPSS_ANOPP.WATE_Core_Nozz.outPort.outerRadius')

        self.connect('NPSS_WATE.engine.WATE.WATE_fan.AR_stg',
                     'NPSS_ANOPP.WATE_Fan.AR_stg')
        self.connect('NPSS_WATE.engine.WATE.WATE_fan.areaIn',
                     'NPSS_ANOPP.WATE_Fan.areaIn')
        self.connect('NPSS_WATE.engine.WATE.WATE_fan.bypassLen_stg',
                     'NPSS_ANOPP.WATE_Fan.bypassLen_stg')
        self.connect('NPSS_WATE.engine.WATE.WATE_fan.hubRadius_stg',
                     'NPSS_ANOPP.WATE_Fan.hubRadius_stg')
        self.connect('NPSS_WATE.engine.WATE.WATE_fan.maxSpdRatio',
                     'NPSS_ANOPP.WATE_Fan.maxSpdRatio')
        self.connect('NPSS_WATE.engine.WATE.WATE_fan.numBlades_stg',
                     'NPSS_ANOPP.WATE_Fan.numBlades_stg')
        self.connect('NPSS_WATE.engine.WATE.WATE_fan.numStatorBlades_stg',
                     'NPSS_ANOPP.WATE_Fan.numStatorBlades_stg')
        self.connect('NPSS_WATE.engine.WATE.WATE_fan.spoolRPM',
                     'NPSS_ANOPP.WATE_Fan.spoolRPM')
        self.connect('NPSS_WATE.engine.WATE.WATE_fan.stg1TipRadius',
                     'NPSS_ANOPP.WATE_Fan.stg1TipRadius')
        self.connect('NPSS_WATE.engine.WATE.WATE_fan.tipRadius_stg',
                     'NPSS_ANOPP.WATE_Fan.tipRadius_stg')

        self.connect('NPSS_WATE.engine.WATE.WATE_inlet.avgCowlDiam',
                     'NPSS_ANOPP.WATE_Inlet.avgCowlDiam')
        self.connect('NPSS_WATE.engine.WATE.WATE_inlet.fanExhaustLength',
                     'NPSS_ANOPP.WATE_Inlet.fanExhaustLength')
        self.connect('NPSS_WATE.engine.WATE.WATE_inlet.fanLength',
                     'NPSS_ANOPP.WATE_Inlet.fanLength')
        self.connect('NPSS_WATE.engine.WATE.WATE_inlet.mostFwdToEngFFLength',
                     'NPSS_ANOPP.WATE_Inlet.mostFwdToEngFFLength')
        self.connect('NPSS_WATE.engine.WATE.WATE_LPT.area_stg',
                     'NPSS_ANOPP.WATE_LPT.area_stg')
        self.connect('NPSS_WATE.engine.WATE.WATE_LPT.hubRadius_stg',
                     'NPSS_ANOPP.WATE_LPT.hubRadius_stg')
        self.connect('NPSS_WATE.engine.WATE.WATE_LPT.numBlades_stg',
                     'NPSS_ANOPP.WATE_LPT.numBlades_stg')
        self.connect('NPSS_WATE.engine.WATE.WATE_LPT.numStages',
                     'NPSS_ANOPP.WATE_LPT.numStages')
        self.connect('NPSS_WATE.engine.WATE.WATE_LPT.tipRadius_stg',
                     'NPSS_ANOPP.WATE_LPT.tipRadius_stg')

        # Propulsion data.
        PropulsionData(parent=self)

#       PropulsionData.FLOPS.dnac =
#           2*(NPSS_WATE.engine.WATE.WATE_fan.bladeTipRadius
#              + NPSS_WATE.engine.WATE.WATE_fan.contRingRadialThickness/12)
#           * Design.maxDiamFact
        self.connect('Design.maxDiamFact',
                     'PropulsionData.link_maxDiamFact')
        self.connect('NPSS_WATE.engine.WATE.WATE_fan.bladeTipRadius',
                     'PropulsionData.link_bladeTipRadius')
        self.connect('NPSS_WATE.engine.WATE.WATE_fan.contRingRadialThickness',
                     'PropulsionData.link_contRingRadialThickness')

#       PropulsionData.Acapture =
#           NPSS_ADP.engine.inlet.S_install.Acapture / 144.
        self.connect('NPSS_ADP.engine.inlet.S_install.Acapture',
                     'PropulsionData.link_Acapture')

#       PropulsionData.FLOPS.xnac =
#           (NPSS_WATE.engine.WATE.WATE_inlet.length
#            + NPSS_WATE.engine.WATE.length) / 12.
        self.connect('NPSS_WATE.engine.WATE.WATE_inlet.length',
                     'PropulsionData.link_inletLength')
        self.connect('NPSS_WATE.engine.WATE.length',
                     'PropulsionData.link_length')

        self.connect('NPSS_WATE.engine.weight',
                     'PropulsionData.FLOPS.weng')

        self.connect('NPSS_FLOPS.engine.FLOPsheetStream',
                     'PropulsionData.FLOPS.engdeck')

        self.connect('NPSS_FLOPS.engine.PERF.Fn',
                     'PropulsionData.FLOPS.thrso')


if __name__ == '__main__':
#    Model().run()
    Model().check_save_load()

