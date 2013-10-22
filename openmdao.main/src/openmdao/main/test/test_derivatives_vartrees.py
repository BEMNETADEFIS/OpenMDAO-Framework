from cStringIO import StringIO
import re
import unittest

try:
    from numpy import zeros, array, identity, ones, linalg
except ImportError as err:
    from openmdao.main.numpy_fallback import zeros, array, identity

from openmdao.main.api import Component, VariableTree, Driver, Assembly, set_as_top
from openmdao.main.datatypes.api import Array, Float, VarTree
from openmdao.main.derivatives import applyJ, applyJT
from openmdao.main.hasparameters import HasParameters
from openmdao.main.hasobjective import HasObjective
from openmdao.main.hasconstraints import HasConstraints
from openmdao.main.interfaces import IHasParameters, implements
from openmdao.test.execcomp import ExecCompWithDerivatives, ExecComp
from openmdao.util.decorators import add_delegate
from openmdao.util.testutil import assert_rel_error

class Tree1(VariableTree):

    x1 = Float()
    x2 = Float()

class Tree2(VariableTree):

    y = Float(3.)
    x = VarTree(Tree1())

class Tree3(VariableTree):

    z = Float(3.)


class CompWithVarTree(Component): 

    ins = VarTree(Tree2(), iotype="in")
    outs = VarTree(Tree3(), iotype="in")
    z = Float(iotype='out')

    def execute(self): 

        self.outs.z = 2*self.ins.x.x1 + 3*self.ins.x.x2 + 4*self.ins.y
        self.z = self.outs.z

    def linearize(self): 

        self.J = ones((2,3))
        self.J[:,0] *= 2 
        self.J[:,0] *= 3
        self.J[:,0] *= 4

    def provideJ(self): 
        ins = ('ins.x.x1', 'ins.x.x2', 'ins.y')
        outs = ('outs.z','z')

        return ins, outs, self.J

        




@add_delegate(HasParameters, HasObjective, HasConstraints)
class SimpleDriver(Driver):
    """Driver with Parameters"""

    implements(IHasParameters)    


class TestDerivativeVarTree(unittest.TestCase): 

    def test_varTree_parameter(self):
        
        top = set_as_top(Assembly())
        top.add('comp', CompWithVarTree())
        top.add('driver', SimpleDriver())
        top.driver.workflow.add(['comp'])
        top.driver.add_parameter('comp.ins.x.x1', low=-1000, high=1000)
        top.driver.add_parameter('comp.ins.x.x2', low=-1000, high=1000)
        top.driver.add_parameter('comp.ins.y', low=-1000, high=1000)

        top.driver.add_objective('comp.z')

        top.comp.ins.x.x1 = 3
        top.comp.ins.x.x2 = 3
        top.comp.ins.y = 5
        top.comp.run()

        inputs = top.driver.list_param_group_targets()

        obj = ["%s.out0" % item.pcomp_name for item in \
               top.driver.get_objectives().values()]
        con = ["%s.out0" % item.pcomp_name for item in \
               top.driver.get_constraints().values()]
        
        J_fd = top.driver.workflow.calc_gradient(inputs, obj, fd=True)
        J_forward = top.driver.workflow.calc_gradient(inputs, obj, mode="forward")
        J_reverse = top.driver.workflow.calc_gradient(inputs, obj, mode="adjoint")
        
        J_true = array([[2., 3., 4.],[2., 3., 4.]])

        assert_rel_error(self, linalg.norm(J_true - J_fd), 0, .00001)
        assert_rel_error(self, linalg.norm(J_true - J_forward), 0, .00001)
        assert_rel_error(self, linalg.norm(J_true - J_reverse), 0, .00001)




 


if __name__ == "__main__": 
    unittest.main()