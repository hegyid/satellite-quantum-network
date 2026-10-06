import matplotlib.pyplot as plt
import cartopy.crs as ccrs

from orekit_manager import OrekitManager
from network_sim import NetworkSimulator
from stats_manager import StatsManager
from org.orekit.time import AbsoluteDate


# -----------------------------
# KONFIGURÁCIÓ
# -----------------------------

ENABLE_VISUALIZATION = True

ENABLE_STATS = False

USE_GEO = True


NUM_CHANNELS = 100
DAMAGE_FRACTION = 0.1

# never/always/adaptive/e2e_adaptive
EPP_MODE = "never"
TARGET_LINK_FIDELITY = 0.92
TARGET_E2E_FIDELITY = 0.8
MAX_E2E_EPP_ROUNDS = 10

NUM_PLANES = 8
SATS_PER_PLANE = 5

LEO_ALTITUDE_M = 1200000.0
LEO_INCLINATION_DEG = 53.0

GEO_ALTITUDE_M = 35786000.0

LEO_LEO_MAX_DIST_KM = 4500.0
CITY_LEO_MAX_DIST_KM = 3000.0
GEO_LINK_MAX_DIST_KM = 50000.0

PROCESSING_DELAY_MS = 1.0
EPP_DELAY_MS = 5.0

SIMULATION_LENGTH_SEC = 7200
TIME_STEP_SEC = 60


# -----------------------------
# OBJEKTUMOK LÉTREHOZÁSA
# -----------------------------

om = OrekitManager()
sim = NetworkSimulator(
    channels=NUM_CHANNELS,
    damage_fraction=DAMAGE_FRACTION,
    epp_mode = EPP_MODE,
    target_link_fidelity=TARGET_LINK_FIDELITY,
    target_e2e_fidelity=TARGET_E2E_FIDELITY,
    max_e2e_epp_rounds=MAX_E2E_EPP_ROUNDS,
    processing_delay_ms=PROCESSING_DELAY_MS,
    epp_delay_ms=EPP_DELAY_MS
)
stats = StatsManager()

start_date = AbsoluteDate(2026, 3, 17, 12, 0, 0.0, om.utc)


# -----------------------------
# KONSTELLÁCIÓK
# -----------------------------

sats_leo = om.create_walker_delta(
    num_planes=NUM_PLANES,
    sats_per_plane=SATS_PER_PLANE,
    altitude_m=LEO_ALTITUDE_M,
    inclination_deg=LEO_INCLINATION_DEG,
    date=start_date,
    phasing=1
)

sats_geo = {}

if USE_GEO:
    for i in range(3):
        name = f"GEO_{i}"
        sats_geo[name] = om.create_propagator(
            a_alt=GEO_ALTITUDE_M,
            inc=0.1,
            raan=i * 120.0,
            anomaly=0.0,
            date=start_date
        )


cities = {
    "Stockholm": (59.3293, 18.0686),
    "Sao Paulo": (-23.5505, -46.6333)
}


# -----------------------------
# VIZUALIZÁCIÓ SETUP
# -----------------------------

is_running = True

if ENABLE_VISUALIZATION:
    plt.ion()

    fig = plt.figure(figsize=(15, 9))
    ax = plt.axes(projection=ccrs.Robinson())

    def on_close(event):
        global is_running
        is_running = False

    fig.canvas.mpl_connect("close_event", on_close)


print("\n" + "=" * 70)
print(" MŰHOLDAS KVANTUMKOMMUNIKÁCIÓS SZIMULÁCIÓ")
print("=" * 70)

print("\n[Konfiguráció]")
print(f"  LEO konstelláció      : {NUM_PLANES} sík × {SATS_PER_PLANE} műhold")
print(f"  GEO használata        : {USE_GEO}")
print(f"  Csatornák száma (W)   : {NUM_CHANNELS}")
print(f"  Damage fraction       : {DAMAGE_FRACTION}")
print(f"  EPP mód               : {EPP_MODE}")
print(f"  Target link fidelity  : {TARGET_LINK_FIDELITY}")
print(f"  Processing delay      : {PROCESSING_DELAY_MS} ms / hop")
print(f"  EPP delay             : {EPP_DELAY_MS} ms / EPP link")
print(f"  Szimuláció hossza     : {SIMULATION_LENGTH_SEC / 60:.0f} perc")
print(f"  Időlépés              : {TIME_STEP_SEC} s")
print(f"  Vizualizáció          : {ENABLE_VISUALIZATION}")
print(f"  Statisztika           : {ENABLE_STATS}")

print("\n[Eredmények időben]")
print("-" * 70)


# -----------------------------
# SZIMULÁCIÓ
# -----------------------------

for step in range(0, SIMULATION_LENGTH_SEC, TIME_STEP_SEC):

    if not is_running:
        break

    current_date = start_date.shiftedBy(float(step))

    sim.reset_topology()

    all_sats = {**sats_leo, **sats_geo}

    xyz_total = {
        name: propagator.propagate(current_date)
                        .getPVCoordinates(om.itrf)
                        .getPosition()
        for name, propagator in all_sats.items()
    }

    geo_total = {
        name: om.get_lat_lon(propagator, current_date)
        for name, propagator in all_sats.items()
    }

    # -----------------------------
    # MŰHOLD-MŰHOLD LINKEK
    # -----------------------------

    sat_names = list(all_sats.keys())

    for i, n1 in enumerate(sat_names):
        for n2 in sat_names[i + 1:]:

            pos1 = xyz_total[n1]
            pos2 = xyz_total[n2]

            if not om.is_los(pos1, pos2):
                continue

            dist_km = pos1.distance(pos2) / 1000.0

            is_geo_link = n1.startswith("GEO") or n2.startswith("GEO")

            if is_geo_link:
                max_dist = GEO_LINK_MAX_DIST_KM
                link_type = "GEO"
            else:
                max_dist = LEO_LEO_MAX_DIST_KM
                link_type = "LEO"

            if dist_km <= max_dist:
                sim.add_link(n1, n2, dist_km, link_type)

    # -----------------------------
    # VÁROS-MŰHOLD LINKEK
    # -----------------------------

    for city, (lat, lon) in cities.items():

        city_xyz = om.get_city_xyz(lat, lon)

        for sat_name, sat_pos in xyz_total.items():

            if not om.is_los(city_xyz, sat_pos):
                continue

            dist_km = city_xyz.distance(sat_pos) / 1000.0

            if sat_name.startswith("L"):
                if dist_km <= CITY_LEO_MAX_DIST_KM:
                    sim.add_link(city, sat_name, dist_km, "CITY")

            elif sat_name.startswith("GEO"):
                if dist_km <= GEO_LINK_MAX_DIST_KM:
                    sim.add_link(city, sat_name, dist_km, "GEO")

    # -----------------------------
    # LEGJOBB ÚTVONAL
    # -----------------------------

    path, e2e_fidelity, e2e_success, latency, epp_count = sim.find_best_route(
        "Stockholm",
        "Sao Paulo"
    )

    if ENABLE_STATS:
        stats.add_step(
            step=step,
            date_str=current_date.toString(om.utc),
            path=path,
            fidelity=e2e_fidelity,
            success=e2e_success,
            latency=latency,
            epp_count=epp_count
        )

    if step % 600 == 0:
        if path:
            print(
                f"t = {step // 60:3d} perc | "
                f"kapcsolat: VAN   | "
                f"hop: {len(path) - 1:2d} | "
                f"EPP={epp_count} | "
                f"F_e2e: {e2e_fidelity:.4f} | "
                f"P_succ: {e2e_success:.6f} | "
                f"latency: {latency:7.2f} ms"
            )
        else:
            print(
                f"t = {step // 60:3d} perc | "
                f"kapcsolat: NINCS | "
                f"hop:  - | "
                f"F_e2e: 0.0000 | "
                f"P_succ: 0.00e+00 | "
                f"latency:    0.00 ms"
            )

    # -----------------------------
    # TÉRKÉPES VIZUALIZÁCIÓ
    # -----------------------------

    if ENABLE_VISUALIZATION:

        ax.clear()

        ax.coastlines(
            resolution="110m",
            color="gray",
            linewidth=0.5,
            zorder=0
        )

        ax.set_global()

        for n1, n2 in sim.G.edges():

            p1 = geo_total[n1] if n1 in geo_total else cities.get(n1)
            p2 = geo_total[n2] if n2 in geo_total else cities.get(n2)

            if p1 is None or p2 is None:
                continue

            is_path = False

            if path and n1 in path and n2 in path:
                if abs(path.index(n1) - path.index(n2)) == 1:
                    is_path = True

            is_geo_link = n1.startswith("GEO") or n2.startswith("GEO")

            ax.plot(
                [p1[1], p2[1]],
                [p1[0], p2[0]],
                color="red" if is_path else "black",
                alpha=1.0 if is_path else (0.12 if is_geo_link else 0.30),
                linewidth=2.5 if is_path else 0.6,
                transform=ccrs.Geodetic(),
                zorder=10 if is_path else 5
            )

        leo_pos = {
            name: pos for name, pos in geo_total.items()
            if name.startswith("L")
        }

        ax.scatter(
            [p[1] for p in leo_pos.values()],
            [p[0] for p in leo_pos.values()],
            color="gold",
            edgecolor="black",
            s=20,
            transform=ccrs.PlateCarree(),
            zorder=20
        )

        if USE_GEO:
            geo_pos = {
                name: pos for name, pos in geo_total.items()
                if name.startswith("GEO")
            }

            ax.scatter(
                [p[1] for p in geo_pos.values()],
                [p[0] for p in geo_pos.values()],
                color="cyan",
                edgecolor="black",
                s=50,
                marker="D",
                transform=ccrs.PlateCarree(),
                zorder=21
            )

        for city, (lat, lon) in cities.items():
            ax.plot(
                lon,
                lat,
                "^",
                color="lime",
                markersize=8,
                transform=ccrs.PlateCarree(),
                zorder=25
            )

            ax.text(
                lon + 3,
                lat + 3,
                city,
                color="black",
                fontsize=9,
                fontweight="bold",
                transform=ccrs.PlateCarree()
            )

        title_msg = f"Idő: {current_date.toString(om.utc)}\n"

        if path:
            title_msg += f"Kvantum út: {' -> '.join(path)}\n"
            title_msg += f"E2E fidelity: {e2e_fidelity:.4f} | "
            title_msg += f"E2E sikeresség: {e2e_success:.6f} | "
            title_msg += f"Késleltetés: {latency:.2f} ms"
        else:
            title_msg += "NINCS KAPCSOLAT"

        ax.set_title(title_msg, fontsize=10, loc="left")

        plt.draw()
        plt.pause(0.01)


print("-" * 70)
print("Szimuláció vége")

if ENABLE_STATS:
    stats.save_to_csv("qkd_results.csv")
    stats.print_summary()
    stats.plot_results()
    plt.show()

if ENABLE_VISUALIZATION:
    plt.ioff()
    plt.show()