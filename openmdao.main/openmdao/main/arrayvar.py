
#public symbols
__all__ = []
__version__ = "0.1"

import numpy

from openmdao.main.variable import Variable, undefined

class ArrayVariable(Variable):
    """A Variable object that wraps a numpy array."""

    def __init__(self, name, parent, iostatus, entry_type=float, 
                 fixed_size=None, num_dims=None, ref_name=None, 
                 default=undefined, desc=None):
        self.dtype = numpy.dtype(entry_type)
        self.fixed_size = fixed_size
        self.numdims = num_dims
        Variable.__init__(self, name, parent, iostatus, 
                          ref_name=ref_name, default=default, desc=desc)

        
    def validate_var(self, var):
        """Raise a TypeError if the connecting Variable is incompatible. 
        This is called on the INPUT side of a connection."""
        Variable.validate_var(self, var)
        if var.dtype is not self.dtype:
            self.raise_exception('numpy data type '+str(self.dtype)+
                                 'is not compatible with type '+
                                 str(var.dtype), ValueError)
        
        
    def _pre_assign(self, val):
        """Returns the transformed, validated value, 
        or raises a ValueError.
        """
        if self.fixed_size is not None:
            mindims = len(self.fixed_size)
        else:
            mindims = 0
        try:
            check_val = numpy.array(val, dtype=self.dtype, subok=True, 
                                    ndmin=mindims)
        except:
            self.raise_exception("new type '"+type(val).__name__+
                                 "'is not compatible with type '"+
                                 type(self.value).__name__, ValueError)
            
            
        if self.fixed_size is not None and self.fixed_size != check_val.shape:
            self.raise_exception('expected array of size '+
                                 str(self.fixed_size)+' but got '+
                                 str(check_val.shape), ValueError)
        return check_val
                
            
    def _pre_assign_entry(self, val, index):
        try:
            myval = self.value[tuple(index)]
        except IndexError:
            self.raise_exception('invalid index: '+str(tuple(index)),IndexError)
        valtype = numpy.obj2sctype(type(val))
        if valtype is not None and numpy.can_cast(valtype, self.value.dtype.type):
                return val
        else:
            self.raise_exception('value type '+type(myval).__name__+
                                 ' at array index '+str(index)+
                                 ' is not compatible with new value type '+
                                 type(val).__name__, ValueError)
        
    def get_entry(self, index):
        return self.value[tuple(index)]
    
    def set_entry(self, val, index):
        tmp = self._pre_assign_entry(val, index)
        try:
            self.value[tuple(index)] = tmp
        except:
            self.raise_exception("assigning index "+str(index)+
                                 " to a value of type "+
                                 str(type(val))+" failed", ValueError)        
            