import os
import orekit
import math
from org.orekit.data import DataContext, ZipJarCrawler
from java.io import File
from org.orekit.orbits import KeplerianOrbit, PositionAngleType
from org.orekit.frames import FramesFactory
from org.orekit.utils import Constants, IERSConventions
from org.orekit.time import AbsoluteDate, TimeScalesFactory
from org.orekit.propagation.analytical import KeplerianPropagator
from org.orekit.bodies import OneAxisEllipsoid, GeodeticPoint

class OrekitManager:
    def __init__(self, zip_path='orekit-data.zip'):
        if not orekit.getVMEnv():
            # JAVA_HOME may need to be configured depending on the local Java/Orekit setup.
            orekit.initVM()
        
        config_file = File(zip_path)
        crawler = ZipJarCrawler(config_file)
        DataContext.getDefault().getDataProvidersManager().addProvider(crawler)
        
        self.mu = Constants.WGS84_EARTH_MU
        self.inertial_frame = FramesFactory.getEME2000()
        self.utc = TimeScalesFactory.getUTC()
        
        # Föld modell a koordinátákhoz
        self.itrf = FramesFactory.getITRF(IERSConventions.IERS_2010, True)
        self.earth = OneAxisEllipsoid(Constants.WGS84_EARTH_EQUATORIAL_RADIUS, 
                                      Constants.WGS84_EARTH_FLATTENING, self.itrf)

    #pályaszámítás
    #letrehoz egy KeplerianOrbit objektumot, leirja a muhold pályáját
    #a_alt: a Föld felszíne feletti magasság
    #inc: inklináció
    #raan: A pálya síkjának elforgatása
    #anomaly: Hol tart éppen a műhold
    def create_propagator(self, a_alt, inc, raan, anomaly, date):
        a = Constants.WGS84_EARTH_EQUATORIAL_RADIUS + a_alt
        orbit = KeplerianOrbit(a, 0.001, math.radians(inc), 0.0, 
                               math.radians(raan), math.radians(anomaly), 
                               PositionAngleType.MEAN, self.inertial_frame, date, self.mu)
        #kiszamolja hol lesz a műhold később
        return KeplerianPropagator(orbit)

    #konstellációt épít
    def create_walker_delta(self, num_planes, sats_per_plane, altitude_m, inclination_deg, date, phasing=1):
        constellation = {}
        #létrehozza és egyenletesen elosztja a pályasíkokat
        for p in range(num_planes):
            raan = p * (360.0 / num_planes)
            #egyenletesen feltölti a síkokat műholdakkal
            for i in range(sats_per_plane):
                base_anomaly = i * (360.0 / sats_per_plane)
                phase_offset = (phasing * p * 360.0) / (num_planes * sats_per_plane)
                anomaly = base_anomaly + phase_offset
                name = f"L{p}_{i}"
                constellation[name] = self.create_propagator(altitude_m, inclination_deg, raan, anomaly, date)
        return constellation

    def get_lat_lon(self, propagator, date):
        pv = propagator.propagate(date).getPVCoordinates(self.itrf)
        pos = pv.getPosition()
        geo_point = self.earth.transform(pos, self.itrf, date)
        return math.degrees(geo_point.getLatitude()), math.degrees(geo_point.getLongitude())
    
    def get_city_xyz(self, lat, lon):
        return self.earth.transform(GeodeticPoint(math.radians(lat), math.radians(lon), 0.0))
    
    #rálátás

    def is_los(self, pos1, pos2):

        R = Constants.WGS84_EARTH_EQUATORIAL_RADIUS + 50000.0 # +50km légkör

       

        mag1 = pos1.getNorm()

        mag2 = pos2.getNorm()

       

        dot = pos1.dotProduct(pos2)

        cos_theta = dot / (mag1 * mag2)



        if cos_theta > 1.0:

            cos_theta = 1.0

        elif cos_theta < -1.0:

            cos_theta = -1.0



        theta = math.acos(cos_theta)

       

        min_dist = (mag1 * mag2 * math.sin(theta)) / pos1.distance(pos2)

       

        if min_dist > R:

            return True

       

        if dot > (mag1**2) or dot > (mag2**2):

            return True

           

        return False