import networkx as nx
import math


class NetworkSimulator:
    def __init__(
        self,
        channels=10,
        alpha=0.0005,
        min_fidelity=0.70,
        damage_fraction=0.07,
        target_link_fidelity=0.97,
        epp_mode="never",
        processing_delay_ms=1.0,
        epp_delay_ms=5.0,
        target_e2e_fidelity=0.75,
        max_e2e_epp_rounds=5
    ):
        self.G = nx.Graph()

        # Párhuzamos kvantumcsatornák száma
        self.W = channels

        # Csillapítási tényező [1/km]
        self.alpha = alpha

        # Minimális elfogadott link fidelity
        self.min_fidelity = min_fidelity

        # A veszteség/zaj mekkora része okoz kvantumállapot-sérülést
        self.damage_fraction = damage_fraction

        # EPP működési mód
        self.epp_mode = epp_mode

        # Adaptív EPP küszöb
        self.target_link_fidelity = target_link_fidelity

        # Hoponkénti késleltetés [ms]
        self.processing_delay_ms = processing_delay_ms

        # EPP művelet késleltetése linkenként [ms]
        self.epp_delay_ms = epp_delay_ms

        self.target_e2e_fidelity = target_e2e_fidelity
        self.max_e2e_epp_rounds = max_e2e_epp_rounds

    def calculate_channel_loss(self, dist_km):
        # exponenciális csillapítási modell.
        # transmission: annak aránya, ami a csatornán átjut
        # loss: annak aránya, ami elveszik
        
        transmission = math.exp(-self.alpha * dist_km)
        loss = 1.0 - transmission

        return transmission, loss

    def calculate_initial_fidelity(self, dist_km):
        # Fidelity modell:
        # Nem a teljes loss rontja a fidelityt, hanem annak csak egy része.

        # - kiszámoljuk a csatornaveszteséget
        # - feltesszük, hogy ennek damage_fraction része sérti a kvantumállapotot
        # - ez adja a kezdeti link fidelityt

        _, loss = self.calculate_channel_loss(dist_km)

        damage = self.damage_fraction * loss
        fidelity = 1.0 - damage

        return max(0.25, min(1.0, fidelity))

    def apply_epp(self, F):
        # purification modell.
        # F_out = 3F^2 / (1 - 2F + 4F^2)

        # ha F elég nagy, különben nem javítunk rajta.
        if F <= 0.25:
            return F, 1.0

        denominator = 1.0 - 2.0 * F + 4.0 * F * F

        if denominator <= 0.0:
            return F, 0.0

        purified_fidelity = (3.0 * F * F) / denominator

        # Conventional EPP efficiency
        efficiency = (2.0 - F + 2.0 * F * F) / 3.0

        purified_fidelity = max(0.0, min(1.0, purified_fidelity))
        efficiency = max(0.0, min(1.0, efficiency))

        return purified_fidelity, efficiency

    def calculate_quantum_metrics(self, dist_km):
        # - p_success: legalább egy sikeres csatorna valószínűsége W párhuzamos csatornából
        # - fidelity: link fidelity, (EPP)
        # - epp_efficiency: purification hatékonysága
        transmission, _ = self.calculate_channel_loss(dist_km)

        # Egy csatorna sikeressége
        p_single = transmission

        # W párhuzamos csatornából legalább egy sikeres
        p_success = 1.0 - (1.0 - p_single) ** self.W

        # Kezdeti link fidelity sérülési arány alapján
        raw_fidelity = self.calculate_initial_fidelity(dist_km)

        fidelity = raw_fidelity
        epp_used = False
        epp_efficiency = 1.0


        if self.epp_mode == "always":
            fidelity, epp_efficiency = self.apply_epp(raw_fidelity)
            p_success *= epp_efficiency
            epp_used = True

        elif self.epp_mode == "adaptive":
            if raw_fidelity < self.target_link_fidelity:
                fidelity, epp_efficiency = self.apply_epp(raw_fidelity)
                p_success *= epp_efficiency
                epp_used = True

        elif self.epp_mode == "never":
            pass


        #ötlet - nem link fidelityre, hanem target e2e fidelityre optimalizálni
        # 1. gráf EPP nélkül
        # 2. útvonalkeresés
        # 3. E2E fidelity
        # 4. ha E2E F >= X kész
        # 5. ha nem akkor a legrosszabb linken EPP
        #(6. újraszámolni routingot)
        # 7. addig ismételni amíg eléri X-et az F

        elif self.epp_mode == "e2e_adaptive":
            pass

        return p_success, fidelity, epp_efficiency, epp_used


    def apply_e2e_adaptive_epp(self, path):
        path_edges = []

        for i in range(len(path) - 1):
            u = path[i]
            v = path[i + 1]
            edge = self.G[u][v]

            path_edges.append({
                "u": u,
                "v": v,
                "dist": edge["dist"],
                "fidelity": edge["fidelity"],
                "p_success": edge["p_success"],
                "epp_used": edge["epp_used"]
            })

        epp_rounds = 0

        while epp_rounds < self.max_e2e_epp_rounds:
            e2e_fidelity = 1.0

            for edge in path_edges:
                e2e_fidelity *= edge["fidelity"]

            if e2e_fidelity >= self.target_e2e_fidelity:
                break

            worst_edge = min(path_edges, key=lambda e: e["fidelity"])

            new_fidelity, efficiency = self.apply_epp(worst_edge["fidelity"])

            if new_fidelity <= worst_edge["fidelity"]:
                break

            worst_edge["fidelity"] = new_fidelity
            worst_edge["p_success"] *= efficiency
            worst_edge["epp_used"] = True

            epp_rounds += 1

        return path_edges, epp_rounds

    def add_link(self, node1, node2, dist_km, link_type):
        p_success, fidelity, epp_efficiency, epp_used = self.calculate_quantum_metrics(dist_km)

        if fidelity < self.min_fidelity:
            return

        if p_success <= 0.0:
            return

        weight = -math.log(p_success)

        self.G.add_edge(
            node1,
            node2,
            weight=weight,
            p_success=p_success,
            fidelity=fidelity,
            epp_efficiency=epp_efficiency,
            dist=dist_km,
            link_type=link_type,
            epp_used=epp_used
        )

    def find_best_route(self, start_node, end_node):
        try:
            path = nx.shortest_path(
                self.G,
                start_node,
                end_node,
                weight="weight"
            )

            if self.epp_mode == "e2e_adaptive":
                path_edges, _ = self.apply_e2e_adaptive_epp(path)
            else:
                path_edges = []

                for i in range(len(path) - 1):
                    edge = self.G[path[i]][path[i + 1]]
                    path_edges.append({
                        "u": path[i],
                        "v": path[i + 1],
                        "dist": edge["dist"],
                        "fidelity": edge["fidelity"],
                        "p_success": edge["p_success"],
                        "epp_used": edge["epp_used"]
                    })

            e2e_fidelity = 1.0
            total_dist = 0.0
            total_success_log = 0.0
            epp_count = 0

            for edge in path_edges:
                e2e_fidelity *= edge["fidelity"]
                total_dist += edge["dist"]
                total_success_log += math.log(edge["p_success"])

                if edge["epp_used"]:
                    epp_count += 1

            e2e_success = math.exp(total_success_log)

            hop_count = len(path) - 1

            propagation_latency = total_dist / 300000.0 * 1000.0
            processing_latency = hop_count * self.processing_delay_ms
            epp_latency = epp_count * self.epp_delay_ms

            latency = propagation_latency + processing_latency + epp_latency

            return path, e2e_fidelity, e2e_success, latency, epp_count

        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None, 0.0, 0.0, 0.0, 0

    def reset_topology(self):
        self.G.clear()