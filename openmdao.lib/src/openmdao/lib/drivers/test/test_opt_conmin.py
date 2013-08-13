"""
Test the CONMIN optimizer component
"""

import unittest
import numpy

# pylint: disable-msg=F0401,E0611
from openmdao.main.api import Assembly, Component, VariableTree, set_as_top
from openmdao.main.datatypes.api import Float, Array, Str, VarTree
from openmdao.lib.casehandlers.api import ListCaseRecorder
from openmdao.lib.drivers.conmindriver import CONMINdriver
from openmdao.util.testutil import assert_rel_error

class OptRosenSuzukiComponent(Component):
    """ From the CONMIN User's Manual:
    EXAMPLE 1 - CONSTRAINED ROSEN-SUZUKI FUNCTION. NO GRADIENT INFORMATION.
    
         MINIMIZE OBJ = X(1)**2 - 5*X(1) + X(2)**2 - 5*X(2) +
                        2*X(3)**2 - 21*X(3) + X(4)**2 + 7*X(4) + 50
    
         Subject to:
    
              G(1) = X(1)**2 + X(1) + X(2)**2 - X(2) +
                     X(3)**2 + X(3) + X(4)**2 - X(4) - 8   .LE.0
    
              G(2) = X(1)**2 - X(1) + 2*X(2)**2 + X(3)**2 +
                     2*X(4)**2 - X(4) - 10                  .LE.0
    
              G(3) = 2*X(1)**2 + 2*X(1) + X(2)**2 - X(2) +
                     X(3)**2 - X(4) - 5                     .LE.0
                     
    This problem is solved beginning with an initial X-vector of
         X = (1.0, 1.0, 1.0, 1.0)
    The optimum design is known to be
         OBJ = 6.000
    and the corresponding X-vector is
         X = (0.0, 1.0, 2.0, -1.0)
    """
    
    x = Array(iotype='in', low=-10, high=99)
    result = Float(iotype='out')
    obj_string = Str(iotype='out')
    opt_objective = Float(iotype='out')
    
    # pylint: disable-msg=C0103
    def __init__(self):
        super(OptRosenSuzukiComponent, self).__init__()
        self.x = numpy.array([1., 1., 1., 1.], dtype=float)
        self.result = 0.
        
        self.opt_objective = 6.
        self.opt_design_vars = [0., 1., 2., -1.]

    def execute(self):
        """calculate the new objective value"""
        self.result = (self.x[0]**2 - 5.*self.x[0] + 
                       self.x[1]**2 - 5.*self.x[1] +
                       2.*self.x[2]**2 - 21.*self.x[2] + 
                       self.x[3]**2 + 7.*self.x[3] + 50)
        self.obj_string = "Bad"
        #print "rosen", self.x


class CONMINdriverTestCase(unittest.TestCase):
    """test CONMIN optimizer component"""

    def setUp(self):
        self.top = set_as_top(Assembly())
        self.top.add('driver', CONMINdriver())
        self.top.add('comp', OptRosenSuzukiComponent())
        self.top.driver.workflow.add('comp')
        self.top.driver.iprint = 0
        self.top.driver.itmax = 30
        
    def tearDown(self):
        self.top = None
        
    def test_opt1(self):
        self.top.driver.add_objective('comp.result')
        map(self.top.driver.add_parameter, 
            ['comp.x[0]', 'comp.x[1]','comp.x[2]', 'comp.x[3]'])
        
        # pylint: disable-msg=C0301
        map(self.top.driver.add_constraint, [
            'comp.x[0]**2+comp.x[0]+comp.x[1]**2-comp.x[1]+comp.x[2]**2+comp.x[2]+comp.x[3]**2-comp.x[3] < 8',
            'comp.x[0]**2-comp.x[0]+2*comp.x[1]**2+comp.x[2]**2+2*comp.x[3]**2-comp.x[3] < 10',
            '2*comp.x[0]**2+2*comp.x[0]+comp.x[1]**2-comp.x[1]+comp.x[2]**2-comp.x[3] < 5'])
        self.top.driver.recorders = [ListCaseRecorder()]
        self.top.driver.printvars = ['comp.opt_objective']  
        self.top.driver.iprint = 0
        self.top.run()
        
        # pylint: disable-msg=E1101
        self.assertAlmostEqual(self.top.comp.opt_objective, 
                               self.top.driver.eval_objective(), places=2)
        self.assertAlmostEqual(self.top.comp.opt_design_vars[0], 
                               self.top.comp.x[0], places=1)
        self.assertAlmostEqual(self.top.comp.opt_design_vars[1], 
                               self.top.comp.x[1], places=2)
        assert_rel_error(self, self.top.comp.opt_design_vars[2],
                         self.top.comp.x[2], 0.01)
        self.assertAlmostEqual(self.top.comp.opt_design_vars[3], 
                               self.top.comp.x[3], places=1)
        
        cases = self.top.driver.recorders[0].get_iterator()
        end_case = cases[-1]
        
        self.assertEqual(self.top.comp.x[1],
                         end_case.get_input('comp.x[1]'))
        self.assertEqual(self.top.comp.opt_objective,
                         end_case.get_output('comp.opt_objective'))

    def test_opt1_with_CONMIN_gradient(self):
        # Note: all other tests use OpenMDAO gradient
        self.top.driver.add_objective('comp.result')
        self.top.driver.add_parameter('comp.x[0]', fd_step=.00001)
        self.top.driver.add_parameter('comp.x[1]', fd_step=.00001)
        self.top.driver.add_parameter('comp.x[2]', fd_step=.00001)
        self.top.driver.add_parameter('comp.x[3]', fd_step=.00001)
        
        # pylint: disable-msg=C0301
        map(self.top.driver.add_constraint, [
            'comp.x[0]**2+comp.x[0]+comp.x[1]**2-comp.x[1]+comp.x[2]**2+comp.x[2]+comp.x[3]**2-comp.x[3] < 8',
            'comp.x[0]**2-comp.x[0]+2*comp.x[1]**2+comp.x[2]**2+2*comp.x[3]**2-comp.x[3] < 10',
            '2*comp.x[0]**2+2*comp.x[0]+comp.x[1]**2-comp.x[1]+comp.x[2]**2-comp.x[3] < 5'])  
        
        self.top.driver.conmin_diff = True
        self.top.run()
        
        # pylint: disable-msg=E1101
        self.assertAlmostEqual(self.top.comp.opt_objective, 
                               self.top.driver.eval_objective(), places=1)
        self.assertAlmostEqual(self.top.comp.opt_design_vars[0], 
                               self.top.comp.x[0], places=1)
        self.assertAlmostEqual(self.top.comp.opt_design_vars[1], 
                               self.top.comp.x[1], places=2)
        self.assertAlmostEqual(self.top.comp.opt_design_vars[2], 
                               self.top.comp.x[2], places=2)
        self.assertAlmostEqual(self.top.comp.opt_design_vars[3], 
                               self.top.comp.x[3], places=1)

    def test_opt1_flippedconstraints(self):
        self.top.driver.add_objective('comp.result')
        map(self.top.driver.add_parameter, 
            ['comp.x[0]', 'comp.x[1]','comp.x[2]', 'comp.x[3]'])
        
        # pylint: disable-msg=C0301
        map(self.top.driver.add_constraint, [
            '8 > comp.x[0]**2+comp.x[0]+comp.x[1]**2-comp.x[1]+comp.x[2]**2+comp.x[2]+comp.x[3]**2-comp.x[3]',
            '10 > comp.x[0]**2-comp.x[0]+2*comp.x[1]**2+comp.x[2]**2+2*comp.x[3]**2-comp.x[3]',
            '5 > 2*comp.x[0]**2+2*comp.x[0]+comp.x[1]**2-comp.x[1]+comp.x[2]**2-comp.x[3]'])
        self.top.run()
        # pylint: disable-msg=E1101
        self.assertAlmostEqual(self.top.comp.opt_objective, 
                               self.top.driver.eval_objective(), places=2)
        self.assertAlmostEqual(self.top.comp.opt_design_vars[0], 
                               self.top.comp.x[0], places=1)
        self.assertAlmostEqual(self.top.comp.opt_design_vars[1], 
                               self.top.comp.x[1], places=2)
        assert_rel_error(self, self.top.comp.opt_design_vars[2],
                         self.top.comp.x[2], 0.01)
        self.assertAlmostEqual(self.top.comp.opt_design_vars[3], 
                               self.top.comp.x[3], places=1)


    def test_gradient_step_size_large(self):
        # Test that a larger value of fd step-size is less acurate
        
        self.top.driver.add_objective('comp.result')
        map(self.top.driver.add_parameter, ['comp.x[0]', 'comp.x[1]',
                                            'comp.x[2]', 'comp.x[3]'])
        
        # pylint: disable-msg=C0301
        map(self.top.driver.add_constraint, [
            'comp.x[0]**2+comp.x[0]+comp.x[1]**2-comp.x[1]+comp.x[2]**2+comp.x[2]+comp.x[3]**2-comp.x[3] < 8.',
            'comp.x[0]**2-comp.x[0]+2*comp.x[1]**2+comp.x[2]**2+2*comp.x[3]**2-comp.x[3] < 10.',
            '2*comp.x[0]**2+2*comp.x[0]+comp.x[1]**2-comp.x[1]+comp.x[2]**2-comp.x[3] < 5.'])        
        
        self.top.run()
        baseerror = abs(self.top.comp.opt_objective - self.top.driver.eval_objective())
        
        self.top.driver.fdch = .3
        self.top.driver.fdchm = .3
        self.top.comp.x = numpy.array([1., 1., 1., 1.], dtype=float)
        self.top.run()
        newerror = abs(self.top.comp.opt_objective - self.top.driver.eval_objective())

        # pylint: disable-msg=E1101
        if baseerror > newerror:
            self.fail("Coarsening CONMIN gradient step size did not make the objective worse.")
        
        
    def test_linear_constraint_specification(self):
        # Note, just testing problem specification and setup
        
        self.top.driver.add_objective('comp.result')
        map(self.top.driver.add_parameter, 
            ['comp.x[0]', 'comp.x[1]','comp.x[2]', 'comp.x[3]'])
        
        map(self.top.driver.add_constraint, ['comp.x[1] + 3.0*comp.x[2] > 3.0',
                                             'comp.x[2] + comp.x[3] > 13.0',
                                             'comp.x[1] - 0.73*comp.x[3]*comp.x[2] > -12.0'])
        self.top.driver.cons_is_linear = [1, 1, 0]
        self.top.driver.itmax = 1

        self.top.run()
        
    def test_max_iteration(self):
        
        self.top.driver.add_objective('comp.result')
        map(self.top.driver.add_parameter, ['comp.x[0]', 'comp.x[1]',
                                            'comp.x[2]', 'comp.x[3]'])
        self.top.driver.nscal = -1
        
        self.top.driver.itmax = 2
        
        # pylint: disable-msg=C0301
        self.top.run()
        
        # pylint: disable-msg=E1101
        self.assertEqual(self.top.driver.iter_count, 2)

    def test_remove(self):
        self.top.driver.add_objective('comp.result')
        map(self.top.driver.add_parameter, 
            ['comp.x[0]', 'comp.x[1]','comp.x[2]', 'comp.x[3]'])
        
        # pylint: disable-msg=C0301
        map(self.top.driver.add_constraint, [
            'comp.x[0]**2+comp.x[0]+comp.x[1]**2-comp.x[1]+comp.x[2]**2+comp.x[2]+comp.x[3]**2-comp.x[3] < 8',
            'comp.x[0]**2-comp.x[0]+2*comp.x[1]**2+comp.x[2]**2+2*comp.x[3]**2-comp.x[3] < 10',
            '2*comp.x[0]**2+2*comp.x[0]+comp.x[1]**2-comp.x[1]+comp.x[2]**2-comp.x[3] < 5'])

        self.top.remove('comp')
        self.assertEqual(self.top.driver.list_param_targets(), [])
        self.assertEqual(self.top.driver.list_constraints(), [])
        self.assertEqual(self.top.driver.get_objectives(), {})


class TestContainer(VariableTree):
    dummy1 = Float(desc='default value of 0.0') #this value is being grabbed by the optimizer
    dummy2 = Float(11.0) 

class TestComponent(Component):
    dummy_data = VarTree(TestContainer(), iotype='in')
    x = Float(iotype='out')

    def execute(self):
        self.x = (self.dummy_data.dummy1-3)**2 - self.dummy_data.dummy2

class TestAssembly(Assembly):
    def configure(self):
        self.add('dummy_top', TestContainer())
        self.add('comp', TestComponent())
        self.add('driver', CONMINdriver())

        self.driver.workflow.add(['comp'])
        #self.driver.iprint = 4 #debug verbosity
        self.driver.add_objective('comp.x') 
        self.driver.add_parameter('comp.dummy_data.dummy1', low=-10.0 , high=10.0)

class CONMINdriverTestCase2(unittest.TestCase):

    def test_vartree_opt(self):
        blah = set_as_top(TestAssembly())
        blah.run()
        self.assertAlmostEqual(blah.comp.dummy_data.dummy1, 3.0, 1) #3.0 should be minimum
    
if __name__ == "__main__":
    unittest.main()


