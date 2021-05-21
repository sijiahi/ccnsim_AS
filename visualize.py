import matplotlib as mpl
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
class visualizer:
    def __init__(self, G, pos = None):
        self.G = G
        if pos == None:
            self.pos = nx.spring_layout(G, seed=20210512)
        else:
            self.pos = pos
    def set_pos(pos):
        self.pos = pos
    def directed_graph(self):
        G = self.G
        G = nx.random_k_out_graph(10, 3, 0.5, seed=seed)
        node_sizes = [3 + 10 * i for i in range(len(G))]
        M = G.number_of_edges()
        edge_colors = range(2, M + 2)
        edge_alphas = [(5 + i) / (M + 4) for i in range(M)]
        cmap = plt.cm.plasma
        nodes = nx.draw_networkx_nodes(G, self.pos, node_size=node_sizes, node_color="indigo")
        edges = nx.draw_networkx_edges(
            G,
            self.pos,
            node_size=node_sizes,
            arrowstyle="->",
            arrowsize=10,
            edge_color=edge_colors,
            edge_cmap=cmap,
            width=2,
        )
        # set alpha value for each edge
        for i in range(M):
            edges[i].set_alpha(edge_alphas[i])

        pc = mpl.collections.PatchCollection(edges, cmap=cmap)
        pc.set_array(edge_colors)
        plt.colorbar(pc)
        ax = plt.gca()
        ax.set_axis_off()
        plt.show()
        
    def simple_graph(self, node_size = 20, alpha = 0.4, size = 10):
        G = self.G
        Gcc = G.subgraph(sorted(nx.connected_components(G), key=len, reverse=True)[0])
        fig = plt.figure("Degree of a random graph", figsize=(size, size))
        ax0 = fig.subplots()
        plt.title('Simple graph')
        nx.draw_networkx_nodes(Gcc, self.pos, ax = ax0, node_size=node_size)
        nx.draw_networkx_edges(Gcc, self.pos, ax = ax0, alpha=alpha)
        plt.show()
        
    def label_graph(self, font_size = 20, alpha = 0.4, node_size = 140):
        G = self.G
        Gcc = G.subgraph(sorted(nx.connected_components(G), key=len, reverse=True)[0])
        fig = plt.figure(figsize=(10, 10))
        ax0 = fig.subplots()
        nx.draw_networkx_nodes(Gcc, self.pos, ax = ax0, node_size = node_size)
        nx.draw_networkx_edges(Gcc, self.pos, ax = ax0, alpha=0.6)
        pos = dict()
        for p in self.pos:  # raise text positions
            #pos[p] = [p[0]+0.05, p[1]+0.04]
            pos[p] = self.pos[p][0]+0.1*font_size,self.pos[p][1]+0.0875*font_size
        plt.title('label graph')
        nx.draw_networkx_labels(G, pos, ax = ax0, font_size = font_size)
        plt.show()
        
        
    def degree_graph(self):
        G = self.G
        degree_sequence = sorted([d for n, d in G.degree()], reverse=True)
        dmax = max(degree_sequence)
        fig = plt.figure("Degree of a random graph", figsize=(10, 10))
        # Create a gridspec for adding subplots of different sizes
        axgrid = fig.add_gridspec(5, 4)
        ax0 = fig.add_subplot(axgrid[0:3, :])
        Gcc = G.subgraph(sorted(nx.connected_components(G), key=len, reverse=True)[0])
        nx.draw_networkx_nodes(Gcc, self.pos, ax=ax0, node_size=20)
        nx.draw_networkx_edges(Gcc, self.pos, ax=ax0, alpha=0.4)
        ax0.set_title("Connected components of G")
        ax0.set_axis_off()

        ax1 = fig.add_subplot(axgrid[3:, :2])
        ax1.plot(degree_sequence, "b-", marker="o")
        ax1.set_title("Degree Rank Plot")
        ax1.set_ylabel("Degree")
        ax1.set_xlabel("Rank")

        ax2 = fig.add_subplot(axgrid[3:, 2:])
        ax2.bar(*np.unique(degree_sequence, return_counts=True))
        ax2.set_title("Degree histogram")
        ax2.set_xlabel("Degree")
        ax2.set_ylabel("# of Nodes")

        fig.tight_layout()
        plt.show()
    def chess_praph(self):
        G = self.G
        print(
            f"Loaded {G.number_of_edges()} chess games between {G.number_of_nodes()} players\n"
        )
        # identify connected components of the undirected version
        H = G.to_undirected()
        Gcc = [H.subgraph(c) for c in nx.connected_components(H)]
        if len(Gcc) > 1:
            print(f"Note the disconnected component consisting of:\n{Gcc[1].nodes()}")

        # find all games with B97 opening (as described in ECO)
        openings = {game_info["ECO"] for (white, black, game_info) in G.edges(data=True)}
        print(f"\nFrom a total of {len(openings)} different openings,")
        print("the following games used the Sicilian opening")
        print('with the Najdorff 7...Qb6 "Poisoned Pawn" variation.\n')

        for (white, black, game_info) in G.edges(data=True):
            if game_info["ECO"] == "B97":
                summary = f"{white} vs {black}\n"
                for k, v in game_info.items():
                    summary += f"   {k}: {v}\n"
                summary += "\n"
                print(summary)

        # make new undirected graph H without multi-edges
        H = nx.Graph(G)

        # edge width is proportional number of games played
        edgewidth = [len(G.get_edge_data(u, v)) for u, v in H.edges()]

        # node size is proportional to number of games won
        wins = dict.fromkeys(G.nodes(), 0.0)
        for (u, v, d) in G.edges(data=True):
            r = d["Result"].split("-")
            if r[0] == "1":
                wins[u] += 1.0
            elif r[0] == "1/2":
                wins[u] += 0.5
                wins[v] += 0.5
            else:
                wins[v] += 1.0
        nodesize = [wins[v] * 50 for v in H]

        # Generate layout for visualization
        pos = nx.kamada_kawai_layout(H)
        # Manual tweaking to limit node label overlap in the visualization
        pos["Reshevsky, Samuel H"] += (0.05, -0.10)
        pos["Botvinnik, Mikhail M"] += (0.03, -0.06)
        pos["Smyslov, Vassily V"] += (0.05, -0.03)

        fig, ax = plt.subplots(figsize=(12, 12))
        # Visualize graph components
        nx.draw_networkx_edges(H, pos, alpha=0.3, width=edgewidth, edge_color="m")
        nx.draw_networkx_nodes(H, pos, node_size=nodesize, node_color="#210070", alpha=0.9)
        label_options = {"ec": "k", "fc": "white", "alpha": 0.7}
        nx.draw_networkx_labels(H, pos, font_size=14, bbox=label_options)

        # Title/legend
        font = {"fontname": "Helvetica", "color": "k", "fontweight": "bold", "fontsize": 14}
        ax.set_title("World Chess Championship Games: 1886 - 1985", font)
        # Change font color for legend
        font["color"] = "r"

        ax.text(
            0.80,
            0.10,
            "edge width = # games played",
            horizontalalignment="center",
            transform=ax.transAxes,
            fontdict=font,
        )
        ax.text(
            0.80,
            0.06,
            "node size = # games won",
            horizontalalignment="center",
            transform=ax.transAxes,
            fontdict=font,
        )

        # Resize figure for label readibility
        ax.margins(0.1, 0.05)
        fig.tight_layout()
        plt.axis("off")
        plt.show()
    def weighted_graph(self):
        G = self.G
        elarge = [(u, v) for (u, v, d) in G.edges(data=True) if d["weight"] > 0.5]
        esmall = [(u, v) for (u, v, d) in G.edges(data=True) if d["weight"] <= 0.5]

        # nodes
        nx.draw_networkx_nodes(G, self.pos, node_size=700)

        # edges
        nx.draw_networkx_edges(G, self.pos, edgelist=elarge, width=6)
        nx.draw_networkx_edges(
            G, self.pos, edgelist=esmall, width=6, alpha=0.5, edge_color="b", style="dashed"
        )

        # labels
        nx.draw_networkx_labels(G, self.pos, font_size=20, font_family="sans-serif")

        ax = plt.gca()
        ax.margins(0.08)
        plt.axis("off")
        plt.tight_layout()
        plt.show()
