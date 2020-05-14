# Built-in packages/modules:
from random import triangular


# kg/m^3 convenience
DENSITY_FRESHWATER = 997
DENSITY_SALTWATER = 1029

# Conversion factors (from native unit, mbar)
UNITS_Pa     = 100.0
UNITS_hPa    = 1.0
UNITS_kPa    = 0.1
UNITS_mbar   = 1.0
UNITS_bar    = 0.001
UNITS_atm    = 0.000986923
UNITS_Torr   = 0.750062
UNITS_psi    = 0.014503773773022

# Valid units
UNITS_Centigrade = 1
UNITS_Farenheit  = 2
UNITS_Kelvin     = 3

class MockMS5837_30BA:
    """
    This class exposes the same methods as the MS5837_30BA, but returns
    random 'reasonable' synthetic data instead of hardware sensor data.
    The intent is to use for debugging when a hardware sense is not
    available.  

    Values of constants, and expected temperature conversion factors are
    taken from the MS5837 source code at
    https://github.com/bluerobotics/ms5837-python
    """
    def __init__(self, *args, **kwargs):
        self._fluidDensity = DENSITY_FRESHWATER

    def init(self, *args, **kwargs):
        return True

    def read(self, *args, **kwargs):
        return True

    def setFluidDensity(self, density):
        self._fluidDensity = density

    def pressure(self, conversion=1):
        # Create a random 'reasonable' result; default in mbar units.  
        p = triangular(750, 1250)
        return p * conversion

    def temperature(self, conversion=1):
        # Create a random 'reasonable' result; default in C.  
        deg_c = triangular(5, 45)
        if conversion == UNITS_Farenheit:
            return (9.0/5.0) * deg_c + 32
        elif conversion == UNITS_Kelvin:
            return deg_c + 273
        return deg_c

    def depth(self):
        # Formulate a 'reasonable' result based on a temp reading.
        return (self.pressure(UNIT_Pa)-101300)/(self._fluidDensity*9.80665)

    def altitude(self):
        # Formulate a 'reasonable' result based on a pressure reading.
        return (1-pow((self.pressure()/1013.25), 0.190284))*145366.45*0.3048
