import pandas as pd
import matplotlib.pyplot as plt


class StatsManager:
    def __init__(self):
        self.data = []

    def add_step(self, step, date_str, path, fidelity, success, latency, epp_count):
        self.data.append({
            "step": step,
            "time": date_str,
            "connected": path is not None,
            "fidelity": fidelity if path else 0.0,
            "success": success if path else 0.0,
            "latency_ms": latency if path else 0.0,
            "hop_count": (len(path) - 1) if path else 0,
            "epp_count": epp_count if path else 0
        })

    def save_to_csv(self, filename="qkd_results.csv"):
        df = pd.DataFrame(self.data)
        df.to_csv(filename, index=False)
        print(f"Adatok elmentve: {filename}")

    def print_summary(self):
        df = pd.DataFrame(self.data)

        if df.empty:
            print("Nincs statisztikai adat.")
            return

        connected_df = df[df["connected"]]

        availability = df["connected"].mean() * 100.0

        print("\n--- SZIMULÁCIÓS ÖSSZEFOGLALÓ ---")
        print(f"Időlépések száma: {len(df)}")
        print(f"Kapcsolat elérhetősége: {availability:.2f}%")

        if connected_df.empty:
            print("Nem volt sikeres végpont-végpont kapcsolat.")
            return

        print(f"Átlagos fidelity: {connected_df['fidelity'].mean():.4f}")
        print(f"Átlagos sikeresség: {connected_df['success'].mean():.6f}")
        print(f"Átlagos késleltetés: {connected_df['latency_ms'].mean():.2f} ms")
        print(f"Átlagos hop szám: {connected_df['hop_count'].mean():.2f}")
        print(f"Max késleltetés: {connected_df['latency_ms'].max():.2f} ms")
        print(f"Min fidelity: {connected_df['fidelity'].min():.4f}")
        print(f"Átlagos EPP link szám: {connected_df['epp_count'].mean():.2f}")
        print(f"Max EPP link szám: {connected_df['epp_count'].max()}")

    def plot_results(self):
        df = pd.DataFrame(self.data)

        if df.empty:
            print("Nincs adat a rajzoláshoz.")
            return

        time_min = df["step"] / 60.0

        # Fidelity
        plt.figure(figsize=(12, 4))
        plt.plot(time_min, df["fidelity"], linewidth=2, label="E2E fidelity")
        plt.title("Végpont-végpont fidelity időben")
        plt.xlabel("Idő (perc)")
        plt.ylabel("Fidelity")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()

        # Sikeresség log skálán
        plt.figure(figsize=(12, 4))
        plt.plot(time_min, df["success"], linewidth=1.8, label="E2E sikeresség")
        plt.yscale("log")
        plt.title("Végpont-végpont sikerességi valószínűség időben (log skála)")
        plt.xlabel("Idő (perc)")
        plt.ylabel("Sikeresség")
        plt.grid(True, alpha=0.3, which="both")
        plt.legend()
        plt.tight_layout()

        # Latency
        plt.figure(figsize=(12, 4))
        plt.fill_between(time_min, df["latency_ms"], alpha=0.2)
        plt.plot(time_min, df["latency_ms"], linewidth=1.5, label="Késleltetés")
        plt.title("Késleltetés időben")
        plt.xlabel("Idő (perc)")
        plt.ylabel("Késleltetés (ms)")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()

        # Kapcsolat megléte
        # plt.figure(figsize=(12, 3))
        # plt.plot(time_min, df["connected"].astype(int), drawstyle="steps-post")
        # plt.title("Kapcsolat elérhetősége időben")
        # plt.xlabel("Idő (perc)")
        # plt.ylabel("Kapcsolat")
        # plt.yticks([0, 1], ["Nincs", "Van"])
        # plt.ylim(-0.1, 1.1)
        # plt.grid(True, alpha=0.3)
        # plt.tight_layout()

        # Hop szám
        plt.figure(figsize=(12, 4))
        plt.plot(time_min, df["hop_count"], drawstyle="steps-post", linewidth=1.5)
        plt.title("Útvonal hop száma időben")
        plt.xlabel("Idő (perc)")
        plt.ylabel("Hop szám")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        # EPP linkek száma az útvonalon
        plt.figure(figsize=(12, 4))
        plt.plot(time_min, df["epp_count"], drawstyle="steps-post", linewidth=1.8)
        plt.title("EPP-t használó linkek száma az útvonalon")
        plt.xlabel("Idő (perc)")
        plt.ylabel("EPP linkek száma")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        # hop vs epp
        plt.figure(figsize=(12, 4))
        plt.plot(time_min, df["hop_count"], drawstyle="steps-post", linewidth=1.5, label="Hop szám")
        plt.plot(time_min, df["epp_count"], drawstyle="steps-post", linewidth=1.5, label="EPP linkek")
        plt.title("Hop szám és EPP használat időben")
        plt.xlabel("Idő (perc)")
        plt.ylabel("Darab")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()

        #fidelity vs epp
        plt.figure(figsize=(7, 5))
        plt.scatter(df["epp_count"], df["fidelity"], alpha=0.7)
        plt.title("E2E fidelity az EPP használat függvényében")
        plt.xlabel("EPP linkek száma")
        plt.ylabel("E2E fidelity")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        #fidelity vs hop
        plt.figure(figsize=(7, 5))
        plt.scatter(df["hop_count"], df["fidelity"], alpha=0.7)
        plt.title("E2E fidelity a hop szám függvényében")
        plt.xlabel("Hop szám")
        plt.ylabel("E2E fidelity")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()