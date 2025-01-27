import collections
import itertools
import math
import operator
import os
import random
import tempfile
import webbrowser
from string import Template

import msprime
import numpy as np
import pandas as pd
import tskit
from IPython.display import HTML, display
from tqdm.auto import tqdm


def running_in_notebook():
    """Checks whether the code is being executed within a Jupyter Notebook.

    Adapted from https://stackoverflow.com/questions/15411967/how-can-i-check-if-code-is-executed-in-the-ipython-notebook

    Returns
    -------
    bool
        True if being executed within a Jupyter Notebook, False otherwise
    """

    try:
        shell = get_ipython().__class__.__name__
        if shell == 'ZMQInteractiveShell':
            return True   # Jupyter notebook or qtconsole
        elif shell == "Shell":
            return True   # Google Colab
        elif shell == "Interpreter":
            return True   # JupyterLite
        elif shell == 'TerminalInteractiveShell':
            return False  # Terminal running IPython
        else:
            return False  # Other type (?)
    except NameError:
        return False      # Probably standard Python interpreter
    
def calculate_evenly_distributed_positions(num_elements, start=0, end=1):
    """Returns a list of `num_elements` evenly distributed positions on a given `length`

    Parameters
    ----------
    num_elements : int
        Number of positions to be returned
    length : int or float
        Range of positions

    Returns
    -------
    List of float positions
    """

    if num_elements > 1:
        w_spacing = (end-start) / (num_elements - 1)
        return [i * w_spacing + start for i in range(num_elements)]
    else:
        return [0.5 * (end-start) + start]
    
def map_value(n, start1, stop1, start2, stop2):
    """Map a value to a new range
    From SO: https://stackoverflow.com/questions/44338698/p5-js-map-function-in-python

    Parameters
    ----------
    n : int or float
    start1 : int or float
    stop1 : int or float
    start2 : int or float
    stop2 : int or float

    Returns
    -------
    mapped
    """
    return (n - start1) / (stop1 - start1) * (stop2 - start2) + start2

def draw_D3(arg_json, force_notebook=False):
    arg_json["source"] = arg_json.copy()
    arg_json["divnum"] = str(random.randint(0,9999999999))
    JS_text = Template("<div id='arg_" + arg_json['divnum'] + "'class='d3arg' style='min-width:" + str(arg_json["width"]+40) + "px; min-height:" + str(arg_json["height"]+80) + "px;'></div><script>$main_text</script>")
    visualizerjs = open(os.path.dirname(__file__) + "/visualizer.js", "r")
    main_text_template = Template(visualizerjs.read())
    visualizerjs.close()
    main_text = main_text_template.safe_substitute(arg_json)
    html = JS_text.safe_substitute({'main_text': main_text})
    css = open(os.path.dirname(__file__) + "/visualizer.css", "r")
    styles = css.read()
    css.close()
    if force_notebook or running_in_notebook():
        display(HTML("<style>"+styles+"</style>" + html))
    else:
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".html") as f:
            url = "file://" + f.name
            f.write("<!DOCTYPE html><html><head><meta charset='utf-8'><style>"+styles+"</style></head><body>" + html + "</body></html>")
        webbrowser.open(url, new=2)

class D3ARG:
    """Stores the ARG in a D3.js friendly format ready for plotting

    See 'Alternative Constructors' for common ways of creating this object

    Attributes
    ----------
    nodes : list
        List of node dicts that contain info about the nodes
    edges : list
        List of edge dicts that contain info about the edges
    breakpoints : list
        List of breakpoint dicts that contain info about the breakpoints
    num_samples : int
        The number of samples in the ARG (with flag=1)
    sample_order : list
        Ordered list of sample IDs

    Alternative Constructors
    ------------------------
    from_ts(ts)
        Creates a D3ARG from a tskit.TreeSequence
    
    from_json(json)
        Creates a D3ARG from a saved custom JSON

    Methods
    -------
    draw(
        width=500,
        height=500,
        tree_highlighting=True,
        y_axis_labels=True,
        y_axis_scale="rank",
        line_type="ortho",
        subset_nodes=[],
        include_node_labels=True
    )
        Draws the ARG using D3.js

    set_node_labels(labels={})
        Customizes node labels in visualization

    reset_node_labels()
        Sets the node labels back to default values

    """

    def __init__(self, nodes, edges, mutations, breakpoints, num_samples, sample_order):
        """Initializes a D3ARG object

        This is the generalized function for initializing a D3ARG object. It is most
        often called by another method, such as from_ts() or from_json(), though it
        can be used separately if the parameters are in the correct format.

        Parameters
        ----------
        nodes : pandas.DataFrame
            Contains info about the nodes
        edges : pandas.DataFrame
            Contains info about the edges
        breakpoints : pandas.DataFrame
            Contains info about the breakpoints
        num_samples : int
            Number of samples in the ARG. Useful for various calculations when plotting
        sample_order : list or np.array
            Order of the sample ID from left to right when plotting
        """

        self.nodes = nodes
        self.edges = edges
        self.mutations = mutations
        self.breakpoints = breakpoints
        self.num_samples = num_samples
        self.sample_order = sample_order

    def __str__(self):
        """Prints attributes of D3ARG object"""
        return f"Nodes:\n{self.nodes}\n\nEdges:\n{self.edges}\n\nMutations:\n{self.mutations}\n\nBreakpoints:\n{self.breakpoints}\n\nNumber of Samples: {self.num_samples}\nSample Order: {self.sample_order}"
        
    @classmethod
    def from_ts(cls, ts, ignore_unattached_nodes=False, progress=None):
        """Converts a tskit tree sequence into a D3ARG object
        
        Parameters
        ----------
        ts : tskit.TreeSequence
            Note: if tree sequence marks recombination nodes, it must use 2-RE format similar to that
            used by msprime.sim_ancestry(...,record_full_arg=True).
        ignore_unattached_nodes : bool
            Whether to include all nodes or ignore nodes that are completely
            unattached. Default is False.
        
        Returns
        -------
        D3ARG : a corresponding D3ARG object ready to be plotted
        """

        in_edges = np.unique(np.append(ts.edges_parent, ts.edges_child))
        samples = []
        order = ts.first().nodes(order="minlex_postorder")
        for n in order:
            if ts.node(n).is_sample():
                if ignore_unattached_nodes and n not in in_edges:
                    continue
                samples.append(n)
        rcnm = np.where(ts.nodes_flags == 131072)[0][1::2]  # NB should probably be (ts.nodes_flags & msprime.NODE_IS_RE_EVENT) != 0
        edges, mutations = cls._convert_edges_table(ts=ts, recombination_nodes_to_merge=rcnm, progress=progress)
        nodes = cls._convert_nodes_table(ts=ts, recombination_nodes_to_merge=rcnm, ignore_unattached_nodes=ignore_unattached_nodes, progress=progress)
        return cls(
            nodes=nodes,
            edges=edges,
            mutations=mutations,
            breakpoints=cls._identify_breakpoints(ts=ts),
            num_samples=len(samples),
            sample_order=samples
        )
    
    @classmethod
    def from_json(cls, json):
        """Converts a saved custom JSON into the D3ARG object
        
        Parameters
        ----------
        json : list of dictionaries
            the custom output of that is downloaded from the visualizer.
            See plotting.md for more details on the format of the json structure

        Returns
        -------
        D3ARG : a corresponding D3ARG object ready to be plotted
        """

        width = json["width"]
        x_shift = 50
        if json["y_axis"]["include_labels"]:
            x_shift = 100
            width -= 50
        nodes = pd.DataFrame(json["data"]["nodes"])
        nodes["x_pos_01"] = (nodes["x"] - x_shift) / (width-100)
        samples = nodes.loc[nodes["flag"]==1,["id", "fx"]]
        return cls(
            nodes=nodes,
            edges=pd.DataFrame(json["data"]["links"]),
            mutations=pd.DataFrame(json["data"]["mutations"]),
            breakpoints=pd.DataFrame(json["data"]["breakpoints"]),
            num_samples=samples.shape[0],
            sample_order=[sample for _, sample in sorted(zip(samples["fx"], samples["id"]))]
        )

    def _convert_nodes_table(ts, recombination_nodes_to_merge, ignore_unattached_nodes, progress=None):
        """Creates nodes JSON from the tskit.TreeSequence nodes table
        
        A "reference" is the id of another node that is used to determine a property in the
        graph. Example: recombination nodes should have the same x position as their child, unless their child is
        also a recombination node. This isn't yet implemented automatically in the layout as it breaks the force
        layout.

        Parameters
        ----------
        ts : tskit.TreeSequence
            tree sequence must have marked recombination nodes, such as using
            msprime.sim_ancestry(...,record_full_arg=True)
        recombination_nodes_to_merge : list or numpy.Array
            IDs of recombination nodes that need to be converted to their alternate ID
        ignore_unattached_nodes : bool
            Whether to include all nodes or ignore nodes that are completely
            unattached

        Returns
        -------
        nodes : list
            List of dictionaries containing information about a given node
        """
        node_lookup = np.arange(ts.num_nodes)  # maps original node IDs to the plotted node ID
        merge_with_prev_node = np.zeros(ts.num_nodes, dtype=bool)
        merge_with_prev_node[recombination_nodes_to_merge] = True
        merge_with_prev_node = np.logical_and(merge_with_prev_node, ts.nodes_flags & msprime.NODE_IS_RE_EVENT != 0)
        node_lookup[merge_with_prev_node] = node_lookup[merge_with_prev_node] - 1  # plotted ID is ID of prev node

        if ignore_unattached_nodes:
            omit_nodes = np.ones(ts.num_nodes, dtype=bool)
            omit_nodes[ts.edges_parent] = False
            omit_nodes[ts.edges_child] = False

        nodes = {
            u: {
                "id": u,
                "flag": flags,
                "time": time,
                "child_of": set(),  # will later convert to list
                "parent_of": set(),  # will later convert to list
                "size": 150,
                "symbol": "d3.symbolCircle",
                "fill": "#1eebb1",
                "stroke": "#053e4e",
                "stroke_width": 4,
                "include_label": "true",
                "x_pos_reference": -1,
            }
            for u, (flags, time) in enumerate(zip(ts.nodes_flags, ts.nodes_time))
            if not (ignore_unattached_nodes and omit_nodes[u]) and not merge_with_prev_node[u]
        }
        
        for edge in ts.edges():
            nodes[node_lookup[edge.child]]['child_of'].add(int(node_lookup[edge.parent]))
            nodes[node_lookup[edge.parent]]['parent_of'].add(int(node_lookup[edge.child]))

        for u in tqdm(nodes.keys(), desc="Nodes", disable=not progress):
            info = nodes[u]
            info['child_of'] = sorted(info['child_of'])
            info['parent_of'] = unique_parent_of = sorted(info['parent_of'])

            if info["flag"] == 131072:
                info["label"] = str(u)+"/"+str(u+1)
                if (len(unique_parent_of) == 1) and not (ts.nodes_flags[unique_parent_of[0]] & msprime.NODE_IS_RE_EVENT != 0):
                    info["x_pos_reference"] = unique_parent_of[0]
            else:
                info["label"] = str(u)
                if (len(unique_parent_of) == 1) and (len(info['child_of']) > 0):
                    # ignores roots as that is necessary to avoid stacking
                    info["x_pos_reference"] = unique_parent_of[0]
        return pd.DataFrame(nodes.values())

    def _convert_edges_table(ts, recombination_nodes_to_merge, progress=None):
        """Creates edges JSON from the tskit.TreeSequence edges table

        Merges the recombination nodes, identified by the smaller of the two IDs. The direction
        that the edge should go relates to the positions of not just the nodes connected by that edge, but also the
        other edges connected to the child. See the JS for all of the different scenarios; still working through
        that.

        Parameters
        ----------
        ts : tskit.TreeSequence
            tree sequence must have marked recombination nodes, such as using
            msprime.sim_ancestry(...,record_full_arg=True)
        recombination_nodes_to_merge : list or numpy.Array
            IDs of recombination nodes that need to be converted to their alternate ID

        Returns
        -------
        links : list
            List of dictionaries containing information about a given link
        """
        ID = 0
        edge_id_reference = {}
        links = []  # a list of parent_links (will be flattened and returned as a pandas array)
        # iterate over unique parent/child combos. Take advantage of the fact that edges
        # in a tree sequence are always ordered by parent ID.
        t = tqdm(total=ts.num_edges, desc="Edges", disable=not progress)
        for parent, edges in itertools.groupby(ts.edges(), operator.attrgetter("parent")):
            parent_time = ts.node(parent).time
            parent_links = []  # all links for this parent
            if parent in recombination_nodes_to_merge:
                parent -= 1
                ID = links[-1][0]["id"]  # to account for prev parent_links being overwritten
            else:
                edges_for_child = {}  # This is a new parent: make a new array
            for edge in edges:
                t.update(1)
                if edge.child not in edges_for_child:
                    edges_for_child[edge.child] = [edge]
                else:
                    edges_for_child[edge.child].append(edge)
            for child, equivalent_edges in edges_for_child.items():
                child_time = ts.node(child).time
                region_size = 0
                bounds = ""
                alternative_child = -1
                alternative_parent = -1
                if (ts.nodes_flags[parent] & msprime.NODE_IS_RE_EVENT) == 0:
                    children = np.array(list(edges_for_child.keys()))
                    if len(children) > 2:
                        alternative_child = children[np.where(children != child)][0]
                    elif len(children) > 1:
                        alternative_child = children[np.where(children != child)][0]
                    else:
                        alternative_child = -1 # this occurs when converting from SLiM simulations, needs to have better handling
                    if alternative_child in recombination_nodes_to_merge:
                        alternative_child -= 1
                if (ts.nodes_flags[child] & msprime.NODE_IS_RE_EVENT) != 0:
                    if child in recombination_nodes_to_merge:
                        alt_id = child - 1
                    else:
                        alt_id = child + 1
                    alt_id_parents = ts.edges_parent[ts.edges_child == alt_id]
                    if len(alt_id_parents):
                        alternative_parent = alt_id_parents[0]
                    else:
                        alternative_parent = -1
                if child in recombination_nodes_to_merge:
                    child = child - 1
                for edge in equivalent_edges:
                    edge_id_reference[edge.id] = (ID, parent, child, parent_time, child_time)
                    bounds += f"{edge.left}-{edge.right} "
                    region_size += edge.right - edge.left
                parent_links.append({
                    "id": ID,
                    "source": parent,
                    "source_time": parent_time,
                    "target": child,
                    "target_time": child_time,
                    "bounds": bounds[:-1],
                    "alt_parent": alternative_parent, #recombination nodes have an alternative parent
                    "alt_child": alternative_child,
                    "region_fraction": region_size / ts.sequence_length,
                    "stroke": "#053e4e"
                })
                ID += 1
            if edge.parent in recombination_nodes_to_merge:
                # We must replace the previous parent_links array with all the details from this one,
                # which will contain all edges for both recombination parents
                links[-1] = parent_links
            else:
                links.append(parent_links)
        t.close()
        edges_output = pd.DataFrame(l for parent_links in links for l in parent_links)
        mutations = []
        for site in tqdm(
            ts.sites(),
            total=ts.num_sites,
            desc="Sites",
            disable=(not progress) or (ts.num_sites == 0)
        ):
            for mut in site.mutations:
                new_edge = edge_id_reference[mut.edge]
                mut_time = mut.time
                if (tskit.is_unknown_time(mut_time)):
                    # Hacky way of placing mutations with unknown times randomly along
                    # an edge. Essentially, giving them a false time just for plotting.
                    middle = (new_edge[3] + new_edge[4]) / 2
                    plot_time = middle + random.uniform(-(new_edge[3]-middle),(new_edge[3]-middle))
                    fill = "gold"
                    mut_time = -1
                else:
                    plot_time = mut.time
                    fill = "orange"
                inherited_state = site.ancestral_state if mut.parent == tskit.NULL else ts.mutation(mut.parent).derived_state
                mutations.append({
                    "edge": new_edge[0],
                    "source": new_edge[1],
                    "target": new_edge[2],
                    "time": mut_time,
                    "plot_time": plot_time,
                    "site_id": site.id,
                    "position": site.position,
                    "position_01": site.position/ts.sequence_length,
                    "ancestral": site.ancestral_state,
                    "inherited": inherited_state,
                    "derived": mut.derived_state,
                    "fill": fill
                })
        mutations_output = pd.DataFrame(mutations, columns=["edge","source","target","time","plot_time","site_id","position","position_01","ancestral","inherited","derived","fill"])
        return edges_output, mutations_output
   
    def _identify_breakpoints(ts):
        """Creates breakpoints JSON from the tskit.TreeSequence

        Parameters
        ----------
        ts : tskit.TreeSequence
            tree sequence must have marked recombination nodes, such as using
            msprime.sim_ancestry(...,record_full_arg=True)
        
        Returns
        -------
        breakpoints : list
            List of dictionaries containing information about breakpoints
        """
        
        breakpoints = []
        start = 0
        id = 0
        for bp in ts.breakpoints():
            bp = float(bp)
            if bp != 0:
                breakpoints.append({
                    "id": id,
                    "start": start,
                    "stop": bp,
                    "x_pos_01":(start/ts.sequence_length),
                    "width_01":((bp - start)/ts.sequence_length),
                    "fill":"#053e4e"
                })
                start = bp
                id += 1
        return pd.DataFrame(breakpoints)
    
    def set_node_labels(self, labels):
        """Sets custom node labels

        Updates node labels based on the D3ARG node "id" using the labels dictionary.
        Final labels will always be strings. Do not rely on the ordering of the
        labels dictionary.

        Parameters
        ----------
        labels : dict
            ID of the node and its new label
        """
        df_id_index = self.nodes.set_index("id")
        try:
            keys = np.fromiter(labels.keys(), dtype=int)
        except ValueError as e:
            raise ValueError("Keys in labels must be integers.") from e
        try:
            df_id_index.loc[keys, 'label'] = [str(v) for v in labels.values()]
        except KeyError as e:
            raise ValueError("Node IDs in labels must be IDs of nodes in the graph.") from e
        self.nodes['label'] = df_id_index['label'].values

    def reset_all_node_labels(self):
        """Resets node labels to default (based on msprime IDs)"""

        for node in self.nodes:
            if node["flag"] == 131072:
                node["label"] = str(node["id"]) + "/" + str(node["id"]+1)
            else:
                node["label"] = str(node["id"])

    def reset_all_node_styles(self):
        """Resets node styles to default (same as when assigned using D3ARG.from_ts)
        
        WARNING: This might not match the initial styles if using D3ARG.from_json
        """

        self.nodes["size"] = 150
        self.nodes["symbol"] = "d3.symbolCircle"
        self.nodes["fill"] = "#1eebb1"
        self.nodes["stroke"] = "#053e4e"
        self.nodes["stroke_width"] = 4
        self.nodes["include_label"] = "true"

    def set_all_node_styles(self, size="", symbol="", fill="", stroke="", stroke_width="", include_label=""):
        """Sets the styling of all of the nodes at once for a specific option.

        If optional parameter not provided, that styling option will be ignored and unchanged.

        Parameters
        ----------
        size : int
            Size in pixels of the node
        symbol : string
            D3 symbol (see https://d3js.org/d3-shape/symbol)
        fill : string
            Color of the node, "#XXXXXX" form
        stroke : string
            Color of the stroke around the node, "#XXXXXX" form
        stroke_width : int
            Pixel width for the stroke around the node
        include_labels : string
            "true" or "false" (will need to update this to bool eventually)
        """

        if size != "":
            self.nodes["size"] = size
        if symbol != "":
            self.nodes["symbol"] = symbol
        if fill != "":
            self.nodes["fill"] = fill
        if stroke != "":
            self.nodes["stroke"] = stroke
        if stroke_width != "":
            self.nodes["stroke_width"] = stroke_width
        if include_label != "":
            self.nodes["include_label"] = include_label
        
    def set_node_styles(self, styles):
        """Individually control the styling of each node.

        Parameters
        ----------
        styles : list
            List of dicts, one per node, with the styling keys: id, size, symbol, fill, stroke, stroke_width,
            include_label. "id" is the only mandatory key. Only nodes that need styles updated need to
            be provided.
        """

        for node in styles:
            for key in node.keys():
                if key in ["size", "symbol", "fill", "stroke", "stroke_width", "include_label"]:
                    self.nodes.loc[self.nodes["id"]==node["id"], key] = node[key]
        
    def set_edge_colors(self, colors):
        """Set the color of each edge in the ARG

        Parameters
        ----------
        colors : dict
            ID of the edge and its new color
        """

        for id in colors:
            if id in self.edges["id"]:
                self.edges.loc[self.edges["id"]==id, "stroke"] = colors[id]
            else:
                raise ValueError(f"Edge '{id}' not in the graph. Cannot update the edge stroke. Make sure all IDs are integers.")

    def set_all_edge_colors(self, color):
        """Sets the edge strokes to the specified color"""

        self.edges["stroke"] = color   
    
    def reset_all_edge_colors(self):
        """Resets the edge strokes to the default (#053e4e)"""

        self.edges["stroke"] = "#053e4e"

    def set_all_breakpoint_fills(self, color):
        """Sets the fill of genome bar blocks to the specified color"""

        self.breakpoints["fill"] = color

    def reset_all_breakpoint_fills(self):
        """Sets the fill of genome bar blocks to the specified color"""

        self.breakpoints["fill"] = "#053e4e"

    def set_breakpoint_fills(self, colors):
        """Set the fill of each breakpoint block in the ARG

        Parameters
        ----------
        colors : dict
            ID of the edge and its new color
        """

        for id in colors:
            if id in self.breakpoints["id"]:
                self.breakpoints.loc[self.breakpoints["id"]==id, "fill"] = colors[id]
            else:
                raise ValueError(f"Breakpoint '{id}' not in the graph. Cannot update the breakpoint fill. Make sure all IDs are integers.")

    def _check_all_nodes_are_samples(self, nodes):
        """Checks whether the list of nodes includes only samples

        Returns False
        
        Parameter
        ---------
        nodes : list
            List of potential sample nodes

        Returns
        -------
        tuple :
            bool : whether all nodes in list are samples
            int/None : the ID of the first node that is not a sample
        """

        for node in nodes:
            found = list(self.nodes.loc[self.nodes["id"] == int(node)]["flag"])
            if len(found) > 0:
                if len(found) == 1:
                    if found[0] != 1:
                        return False, node
                else:
                    ValueError(f"Multiple entries for Node '{node}' in the graph.")
            else:
                raise ValueError(f"Node '{node}' not in the graph.")
        return True, None

    def _calculate_sample_order(self, order=None):
        """Sets the ordering of the sample nodes (tips) within the ARG
    
        Sample nodes in order list will come first, then any samples nodes not provided will be included
        in minlex_postorder. Checks that only sample nodes are provided in order.

        Parameter
        ---------
        order : list
            Sample nodes in desired order. Must only include sample nodes, but does not
            need to include all sample nodes.

        Returns
        -------
        order : list
            Sample nodes in desired order, including those not originally provided
        """

        if order == None:
            order = []
        check_samples = self._check_all_nodes_are_samples(nodes=order)
        if not check_samples[0]:
            raise ValueError(f"Node '{check_samples[1]}' not a sample and cannot be included in sample order.")
        for node in self.sample_order:
            found = self.nodes.loc[self.nodes["id"] == int(node)].iloc[0]
            if found["flag"] == 1 and found["id"] not in order:
                order.append(found["id"])
        return order
    
    def _prepare_json(
            self,
            plot_type,
            nodes,
            edges,
            mutations,
            breakpoints,
            width=500,
            height=500,
            tree_highlighting=True,
            y_axis_labels=True,
            y_axis_scale="rank",
            edge_type="line",
            variable_edge_width=False,
            include_underlink=True,
            sample_order=None,
            title=None,
            show_mutations=False,
            ignore_mutation_times=True,
            include_mutation_labels=False,
            condense_mutations=True,
            rotate_tip_labels=False
        ):
        """Creates the required JSON for both draw() and draw_node()

        Parameters
        ----------
        plot_type :
            Options:
                "full"
                "node"
        nodes : pd.DataFrame
            The nodes to be plotted, potentially subset of original graph
        edges : pd.DataFrame
            The edges to be plotted, potentially subset of original graph
        mutations : pd.DataFrame
            The mutations to be plotted, potentially subset of original graph
        breakpoints : pd.DataFrame
            The breakpoints to be plotted, potentially subset of original graph
        width : int
            Width of the force layout graph plot in pixels (default=500)
        height : int
            Height of the force layout graph plot in pixels (default=500)
        tree_highlighting : bool
            Include the interactive chromosome at the bottom of the figure to
            to let users highlight trees in the ARG (default=True)
        y_axis_labels : bool
            Includes labelled y-axis on the left of the figure (default=True)
        y_axis_scale : string
            Scale used for the positioning nodes along the y-axis. Options:
                "rank" (default) - equal vertical spacing between nodes
                "time" - vertical spacing is proportional to the time
                "log_time" - proportional to the log of time
        edge_type : string
            Pathing type for edges between nodes. Options:
                "line" (default) - simple straight lines between the nodes
                "ortho" - custom pathing (see pathing.md for more details, should only be used with full ARGs)
        variable_edge_width : bool
            Scales the stroke width of edges in the visualization will be proportional to the fraction of
            sequence in which that edge is found. (default=False)
        include_underlink : bool
            Includes an "underlink" for each edge gives a gap during edge crosses. This is currently only
            implemented for `edge_type="ortho"`. (default=True)
        sample_order : list
            Sample nodes IDs in desired order. Must only include sample nodes IDs, but does not
            need to include all sample nodes IDs. (default=None, order is set by first tree in tree sequence)
        title : str
            Title to be put at the top of the figure. (default=None, ignored)
        show_mutations : bool
            Whether to add mutations to the graph. (default=False)
        ignore_mutation_times : bool
            Whether to plot mutations evenly on edge (True) or at there specified times (False). (default=True, ignored)
        include_mutation_labels : bool
            Whether to add the full label (position_index:inherited:derived) for each mutation. (default=False)
        rotate_tip_labels : bool
            Rotates tip labels by 90 degrees. (default=False)
            
        Returns
        -------
        arg : list
            List of dictionaries (JSON) with all of the data need to plot in D3.js
        """

        y_axis_ticks = []
        y_axis_text = []
        transformed_nodes = []
        transformed_muts = []
        
        x_shift = 50
        if y_axis_labels:
            x_shift = 100

        y_shift = 50
        if title:
            y_shift = 100
        
        if not show_mutations:
            tick_times = nodes["time"]
        elif ignore_mutation_times:
            tick_times = nodes["time"]
        else:
            tick_times = pd.concat([nodes["time"],mutations["plot_time"]], axis=0).sort_values(ignore_index=True)
        
        if plot_type == "full":
            sample_positions = calculate_evenly_distributed_positions(num_elements=self.num_samples, start=x_shift, end=(width-100)+x_shift)
            sample_order = self._calculate_sample_order(order=sample_order)
        else:
            sample_positions = []

        max_time = max(tick_times)
        h_spacing = 1 / (len(np.unique(tick_times))-1)
        unique_times = list(np.unique(tick_times)) # Determines the rank (y position) of each time point 

        node_y_pos = {}
        for index, node in nodes.iterrows():
            if "x_pos_01" in node:
                node["fx"] = node["x_pos_01"] * (width-100) + x_shift
            elif (node["flag"] == 1) and (plot_type == "full"):
                node["fx"] = sample_positions[sample_order.index(node["id"])]
            else:
                node["x"] = 0.5 * (width-100) + x_shift
            if y_axis_scale == "time":
                fy = (1-node["time"]/max_time) * (height-100) + y_shift
            elif y_axis_scale == "log_time":
                fy = (1-math.log(node["time"]+1)/math.log(max_time)) * (height-100) + y_shift
            else:
                fy = (1-unique_times.index(node["time"])*h_spacing) * (height-100) + y_shift
                y_axis_text.append(node["time"])
                y_axis_ticks.append(fy)
            node["fy"] = fy
            node["y"] = node["fy"]
            node_y_pos[node["id"]] = node["fy"] 
            transformed_nodes.append(node.to_dict())

        transformed_muts = []
        if show_mutations:
            if (edge_type == "line") and (len(mutations.index) > 0):
                if condense_mutations:
                    for edge, muts in mutations.sort_values(["time"],ascending=False).groupby("edge"):
                        muts["content"] = muts["inherited"] + muts["position"].astype(int).astype(str) + muts["derived"] #+ ":" + muts["time"].astype(int).astype(str)            
                        if y_axis_labels:
                            x_pos = muts["position_01"] * width + 50
                        else:
                            x_pos = muts["position_01"] * width
                        source = int(muts.iloc[0]["source"])
                        target = int(muts.iloc[0]["target"])
                        source_y = node_y_pos[source]
                        target_y = node_y_pos[target]
                        fy = (source_y + target_y) / 2
                        transformed_muts.append({
                            "edge": edge,
                            "source": source,
                            "target": target,
                            "y": fy,
                            "fy": fy,
                            "site_id": edge,
                            "x_pos": list(x_pos),
                            "fill": "pink",
                            "active": "false",
                            "label": "⨉"+str(muts.shape[0]),
                            "content": "<br>".join(muts.content)
                        })
                elif ignore_mutation_times:
                    for index, edge in edges.iterrows():
                        source_y = node_y_pos[edge["source"]]
                        target_y = node_y_pos[edge["target"]]
                        muts = mutations.loc[mutations["edge"] == edge["id"]].reset_index()
                        mutation_count = len(muts.index)
                        for m, mut in muts.iterrows():
                            fy = source_y - (source_y - target_y)/(mutation_count+1)*(m+1)# - 10*(m-((mutation_count-1)/2))
                            if y_axis_labels:
                                x_pos = mut["position_01"] * width + 50
                            else:
                                x_pos = mut["position_01"] * width
                            label = mut["inherited"] + str(int(mut["position"])) + mut["derived"]
                            content = mut["inherited"] + str(int(mut["position"])) + mut["derived"] #+ ":" + str(int(mut["time"]))
                            transformed_muts.append({
                                "edge": edge["id"],
                                "source": edge["source"],
                                "target": edge["target"],
                                "time": mut.time,
                                "y": fy,
                                "fy": fy,
                                "site_id": mut.site_id,
                                "position_01": mut.position_01,
                                "position": mut.position,
                                "x_pos": x_pos,
                                "ancestral": mut.ancestral,
                                "inherited": mut.inherited,
                                "derived": mut.derived,
                                "fill": mut.fill,
                                "active": "false",
                                "label": label,
                                "content": content
                            })
                else:
                    for index, mut in mutations.iterrows():
                        if y_axis_scale == "time":
                            fy = (1-mut["plot_time"]/max_time) * (height-100) + y_shift
                        elif y_axis_scale == "log_time":
                            fy = (1-math.log(mut["plot_time"]+1)/math.log(max_time)) * (height-100) + y_shift
                        else:
                            fy = (1-unique_times.index(mut["plot_time"])*h_spacing) * (height-100) + y_shift
                            if mut["plot_time"] in mutations["time"].values:
                                y_axis_text.append(mut["plot_time"])
                                y_axis_ticks.append(fy)
                        if y_axis_labels:
                            mut["x_pos"] = mut["position_01"] * width + 50
                        else:
                            mut["x_pos"] = mut["position_01"] * width
                        mut["fy"] = fy
                        mut["y"] = mut["fy"]
                        mut["position_index"] = mut.site_id
                        mut["label"] = mut["inherited"] + str(int(mut["position"])) + mut["derived"]
                        mut["content"] = mut["inherited"] + str(int(mut["position"])) + mut["derived"] #+ ":" + str(int(mut["time"]))
                        transformed_muts.append(mut.to_dict())

        if tree_highlighting:
            height += 75

        if y_axis_scale == "time":
            y_axis_text = calculate_evenly_distributed_positions(10, start=0, end=max_time)
            y_axis_ticks = [(1-time/max_time) * (height-100) + y_shift for time in y_axis_text]
        elif y_axis_scale == "log_time":
            digits = int(math.log10(max_time))+1
            if (max_time - 10**(digits-1) < 10**(digits-1)): # this just removes the tick mark if its likely there is overlap
                digits -= 1
            y_axis_text = [0] + [10**i for i in range(1, digits)] + [max_time]
            y_axis_ticks = [(1-math.log(time+1)/math.log(max_time)) * (height-100) + y_shift for time in y_axis_text]

        y_axis_text = [round(t) for t in set(y_axis_text)]
        
        transformed_bps = breakpoints.loc[:,:]
        if y_axis_labels:
            transformed_bps["x_pos"] = transformed_bps["x_pos_01"] * width + 50
        else:
            transformed_bps["x_pos"] = transformed_bps["x_pos_01"] * width
        transformed_bps["width"] = transformed_bps["width_01"] * width
        transformed_bps["included"] = "true"
        transformed_bps = transformed_bps.to_dict("records")

        if y_axis_labels:
            width += 50

        if title:
            height += 50

        arg = {
            "data":{
                "nodes":transformed_nodes,
                "links":edges.to_dict("records"),
                "mutations":transformed_muts,
                "breakpoints":transformed_bps,
                "evenly_distributed_positions":sample_positions
            },
            "width":width,
            "height":height,
            "y_axis":{
                "include_labels":str(y_axis_labels).lower(),
                "ticks":sorted(list(set(y_axis_ticks)), reverse=True),
                "text":sorted(list(y_axis_text)),
                "max_min":[max(y_axis_ticks),min(y_axis_ticks)],
                "scale":y_axis_scale,
            },
            "edges":{
                "type":edge_type,
                "variable_width":str(variable_edge_width).lower(),
                "include_underlink":str(include_underlink).lower()
            },
            "condense_mutations":str(condense_mutations).lower(),
            "include_mutation_labels":str(include_mutation_labels).lower(),
            "tree_highlighting":str(tree_highlighting).lower(),
            "title":str(title),
            "rotate_tip_labels":str(rotate_tip_labels).lower(),
            "plot_type":plot_type
        }
        return arg


    def _get_summary_node_subs(self, node, summary_nodes):
        if type(node) == str:
            descendants = []
            sn_id = int(node.replace("S", ""))
            for sn in summary_nodes[sn_id]:
                descendants.extend(self.get_summary_descendants(sn, summary_nodes))
            return descendants
        return [node]

    def _get_edge_collapse_order(self, zoom):
        """Generates a sequence of edge collapses up to a specified zoom level

        Parameters
        ----------
        zoom : int
            The level of detail that you want. Larger numbers equate to less detail/more collapsing

        Returns
        -------
        summary_nodes : list
            Ordered list of edge collapses by increasing branch length
        """

        branch_lengths = self.edges.loc[:,["source", "target"]].join((self.edges["source_time"] - self.edges["target_time"]).rename("edge_length")).sort_values("edge_length")
        counter = 0
        largest_summary_node = [i for i in self.nodes["id"]]
        summary_nodes = []
        for edge in branch_lengths.itertuples():
            if counter >= zoom:
                break
            if self.nodes.loc[self.nodes["id"] == edge.target]["flag"].iloc[0] != 1:
                source_i = self.nodes[self.nodes["id"] == edge.source].index[0]
                target_i = self.nodes[self.nodes["id"] == edge.target].index[0]
                if largest_summary_node[source_i] != largest_summary_node[target_i]:
                    summary_nodes.append([largest_summary_node[source_i], largest_summary_node[target_i]])
                    indices = [i for i, x in enumerate(largest_summary_node) if (x == largest_summary_node[source_i]) or (x == largest_summary_node[target_i])]
                    # Surely a better way to do this using numpy but the typing within the array can get tricky
                    for i in indices:
                        largest_summary_node[i] = f"S{counter}"
                    counter += 1
        return summary_nodes

    def _collapse_graph(self, zoom):
        """Collapses the graph to a specified zoom level

        Parameters
        ----------
        zoom : int
            The level of detail that you want. Larger numbers equate to less detail/more collapsing
        
        Returns
        -------
        nodes : pd.DataFrame
            Collapsed nodes table including necessary summary nodes
        edges : pd.DataFrame
            Collapsed nodes table with new source/target IDs
        """

        if zoom > 0:
            edge_collapses = self._get_edge_collapse_order(zoom=zoom)
            nodes = self.nodes
            # Previously, the "id" is of type int64, but because we will have IDs for summary nodes
            # this needs to be changed to object. Could be improved, though may require changes more
            # broadly to "id" typing. Or having a different ID convention for summary nodes.
            nodes = nodes.astype(dtype={"id":"object"})
            edges = self.edges
            edges = edges.astype(dtype={"source":"object", "target":"object"})
            for i,ec in enumerate(edge_collapses):
                nodes_to_drop = nodes.loc[nodes["id"].isin(ec)]
                edges.loc[edges["source"].isin(ec), "source"] = f"S{i}"
                edges.loc[edges["target"].isin(ec), "target"] = f"S{i}"
                # By simply changing the source/target IDs without further checks, it is 
                # possible to have edges that have the same source and target IDs. The visualizer
                # does not care, though if there are many edges it could slow down the simulation.
                nodes = nodes.drop(nodes_to_drop.index)
                new_node = pd.DataFrame([{
                    "id":f"S{i}",
                    "flag":99,
                    "time":nodes_to_drop["time"].mean(),
                    "child_of":nodes_to_drop["child_of"].sum(),
                    "parent_of":nodes_to_drop["parent_of"].sum(),
                    # These don't work as intended, and instead need to be updated with the summary node IDs
                    "size":150,
                    "symbol":"d3.symbolCircle",
                    "fill":"#FFFFFF",
                    "stroke":"#053e4e",
                    "stroke_width":4,
                    "include_label":"true",
                    "x_pos_reference":-1,
                    "label":f"S{i}"
                }])
                nodes = pd.concat([nodes, new_node]).reset_index(drop=True)
                # This is inefficient for large graphs and would need more thought
            return nodes, edges
        return self.nodes, self.edges


    def draw(
            self,
            width=500,
            height=500,
            tree_highlighting=True,
            y_axis_labels=True,
            y_axis_scale="rank",
            edge_type="line",
            variable_edge_width=False,
            include_underlink=True,
            sample_order=None,
            title=None,
            show_mutations=False,
            ignore_mutation_times=True,
            include_mutation_labels=False,
            condense_mutations=False,
            force_notebook=False,
            rotate_tip_labels=False,
            zoom=0
        ):
        """Draws the D3ARG using D3.js by sending a custom JSON object to visualizer.js 

        Parameters
        ----------
        width : int
            Width of the force layout graph plot in pixels (default=500)
        height : int
            Height of the force layout graph plot in pixels (default=500)
        tree_highlighting : bool
            Include the interactive chromosome at the bottom of the figure to
            to let users highlight trees in the ARG (default=True)
        y_axis_labels : bool
            Includes labelled y-axis on the left of the figure (default=True)
        y_axis_scale : string
            Scale used for the positioning nodes along the y-axis. Options:
                "rank" (default) - equal vertical spacing between nodes
                "time" - vertical spacing is proportional to the time
                "log_time" - proportional to the log of time
        edge_type : string
            Pathing type for edges between nodes. Options:
                "line" (default) - simple straight lines between the nodes
                "ortho" - custom pathing (see pathing.md for more details, should only be used with full ARGs)
        variable_edge_width : bool
            Scales the stroke width of edges in the visualization will be proportional to the fraction of
            sequence in which that edge is found. (default=False)
        include_underlink : bool
            Includes an "underlink" for each edge gives a gap during edge crosses. This is currently only
            implemented for `edge_type="ortho"`. (default=True)
        sample_order : list
            Sample nodes IDs in desired order. Must only include sample nodes IDs, but does not
            need to include all sample nodes IDs. (default=None, order is set by first tree in tree sequence)
        title : str
            Title to be put at the top of the figure. (default=None, ignored)
        show_mutations : bool
            Whether to add mutations to the graph. Only available when `edge_type="line"`. (default=False)
        ignore_mutation_times : bool
            Whether to plot mutations evenly on edge (True) or at there specified times (False). (default=True, ignored)
        include_mutation_labels : bool
            Whether to add the full label (position_index:inherited:derived) for each mutation. (default=False)
        condense_mutations : bool
            Whether to merge all mutations along an edge into a single mutation symbol. (default=False)
        force_notebook : bool
            Forces the the visualizer to display as a notebook. Possibly necessary for untested environments. (default=False)
        rotate_tip_labels : bool
            Rotates tip labels by 90 degrees. (default=False)
        zoom : int
            The level of detail that you want. Larger numbers equate to less detail/more collapsing
        """
        
        if condense_mutations:
            if not ignore_mutation_times:
                print("WARNING: `condense_mutations=True` forces `ignore_mutation_times=True`.")
                ignore_mutation_times = True

        included_nodes, included_edges = self._collapse_graph(zoom=zoom)        

        arg = self._prepare_json(
            plot_type="full",
            nodes=included_nodes,
            edges=included_edges,
            mutations=self.mutations,
            breakpoints=self.breakpoints,
            width=width,
            height=height,
            tree_highlighting=tree_highlighting,
            y_axis_labels=y_axis_labels,
            y_axis_scale=y_axis_scale,
            edge_type=edge_type,
            variable_edge_width=variable_edge_width,
            include_underlink=include_underlink,
            sample_order=sample_order,
            title=title,
            show_mutations=show_mutations,
            ignore_mutation_times=ignore_mutation_times,
            include_mutation_labels=include_mutation_labels,
            condense_mutations=condense_mutations,
            rotate_tip_labels=rotate_tip_labels
        )
        draw_D3(arg_json=arg, force_notebook=force_notebook)

    def subset_graph(self, node, degree):
        """Subsets the graph to focus around a specific node

        Parameters
        ----------
        node : int or list
            Node ID or list of node IDs that will be central to the subgraph
        degree : int or list(int, int)
            Number of degrees above (older than) and below (younger than) the central
            node to include in the subgraph (default=1). If this is a list, the
            number of degrees above is taken from the first element and
            the number of degrees below from the last element.

        Returns
        -------
        included_nodes : pd.DataFrame
            The nodes to be plotted, potentially subset of original graph
        included_edges : pd.DataFrame
            The edges to be plotted, potentially subset of original graph
        included_mutations : pd.DataFrame
            The mutations to be plotted, potentially subset of original graph
        included_breakpoints : pd.DataFrame
            The breakpoints to be plotted, potentially subset of original graph
        """

        if type(node) == int:
            if node not in self.nodes.id.values:
                raise ValueError(f"Node '{node}' not in the graph.")
            node = [node]
        else:
            for n in node:
                if n not in self.nodes.id.values:
                    raise ValueError(f"Node '{n}' not in the graph.")

        try:
            older_degree = degree[0]
            younger_degree = degree[-1]
        except TypeError:
            older_degree = younger_degree = degree

        nodes = node[:]
        first = True

        # Inefficient loop, doesn't acknowledge that some edges could be shared
        # between focal nodes. These duplicates are dropped eventually, but
        # a better function would not add them to start.
        for focal in node:
            
            above = [focal]
            below = [focal]

            for od in range(older_degree+1):
                new_above = []
                for n in above:
                    to_add = self.edges.loc[self.edges["target"] == n, :]
                    if od == older_degree:
                        to_add = to_add.loc[to_add["source"].isin(nodes), :]
                    if first:
                        included_edges = to_add
                        first = False
                    else:
                        included_edges = pd.concat([included_edges, to_add], ignore_index=True)
                    new_above.extend(list(to_add["source"]))
                above = new_above
                nodes.extend(new_above)

            for yd in range(younger_degree+1):
                new_below = []
                for n in below:
                    to_add = self.edges.loc[self.edges["source"] == n, :]
                    if yd == younger_degree:
                        to_add = to_add.loc[to_add["target"].isin(nodes), :]
                    if first:
                        included_edges = to_add
                        first = False
                    else:
                        included_edges = pd.concat([included_edges, to_add], ignore_index=True)
                    new_below.extend(list(to_add["target"]))
                below = new_below
                nodes.extend(new_below)

        included_edges = included_edges.drop_duplicates()
        included_nodes = self.nodes.loc[self.nodes["id"].isin(list(set(nodes))), :]

        ni_child, ni_parent = [], []
        for n in included_nodes["id"]:
            all_nodes_parents = self.edges[((self.edges["target"] == n) | (self.edges["source"] == n))]
            included_nodes_parents = included_edges[((included_edges["target"] == n) | (included_edges["source"] == n))]
            not_included = pd.merge(all_nodes_parents, included_nodes_parents, indicator=True, how='outer').query('_merge=="left_only"').drop('_merge', axis=1)
            ni_child.append(sum(not_included["source"] == n))
            ni_parent.append(sum(not_included["target"] == n))
        included_nodes = included_nodes.assign(not_included_children=ni_child, not_included_parents=ni_parent)

        included_mutations = self.mutations.loc[self.mutations["edge"].isin(included_edges["id"]),:]

        # need to add a check that confirms the ordering of breakpoints is always increasing in position
        included_breakpoints = []
        for j,bp in self.breakpoints.iterrows():
            if j == 0:
                current_region = bp
            important_bp = False
            bp["included"] = "false"
            for i,edge in included_edges.iterrows():
                bounds = edge["bounds"].split(" ")
                for b in bounds:
                    b = b.split("-")
                    start = float(b[0])
                    stop = float(b[1])
                    # assumes edge lengths are always larger than breakpoints which should be true here
                    if (start <= bp["start"]) and (stop >= bp["stop"]):
                        bp["included"] = "true"
                    if (start == bp["start"]) or (stop == bp["start"]):
                        important_bp = True
            if (bp["included"] == "false") and (current_region["included"] == "true"):
                important_bp = True
            if j > 0:
                if important_bp:
                    included_breakpoints.append(current_region)
                    current_region = bp
                else:
                    current_region["stop"] = bp["stop"]
                    current_region["width_01"] += bp["width_01"]
        included_breakpoints.append(current_region) # make sure to append the last region
        included_breakpoints = pd.DataFrame(included_breakpoints)

        return collections.namedtuple('IncludedInfo', ['nodes', 'edges', 'mutations', 'breakpoints'])(
            included_nodes, included_edges, included_mutations, included_breakpoints
        )

    def draw_node(
            self,
            node,   # may want to change this parameter name if it's confusing that it can take multiple nodes.
            width=500,
            height=500,
            degree=1,
            y_axis_labels=True,
            y_axis_scale="rank",
            tree_highlighting=True,
            title=None,
            show_mutations=False,
            ignore_mutation_times=True,
            include_mutation_labels=False,
            condense_mutations=False,
            return_included_nodes=False,
            force_notebook=False,
            rotate_tip_labels=False
        ):
        """Draws a subgraph of the D3ARG using D3.js by sending a custom JSON object to visualizer.js

        Parameters
        ----------
        node : int or list
            Node ID or list of node IDs that will be central to the subgraph
        width : int
            Width of the force layout graph plot in pixels (default=500)
        height : int
            Height of the force layout graph plot in pixels (default=500)
        degree : int or list(int, int)
            Number of degrees above (older than) and below (younger than) the central
            node to include in the subgraph (default=1). If this is a list, the
            number of degrees above is taken from the first element and
            the number of degrees below from the last element.
        y_axis_labels : bool
            Includes labelled y-axis on the left of the figure (default=True)
        y_axis_scale : string
            Scale used for the positioning nodes along the y-axis. Options:
                "rank" (default) - equal vertical spacing between nodes
                "time" - vertical spacing is proportional to the time
                "log_time" - proportional to the log of time
        tree_highlighting : bool
            Include the interactive chromosome at the bottom of the figure to
            to let users highlight trees in the ARG (default=True)
        title : str
            Title to be put at the top of the figure. (default=None, ignored)
        show_mutations : bool
            Whether to add mutations to the graph. (default=False)
        ignore_mutation_times : bool
            Whether to plot mutations evenly on edge (True) or at there specified times (False). (default=True, ignored)
        include_mutation_labels : bool
            Whether to add the full label (position_index:inherited:derived) for each mutation. (default=False)
        condense_mutations : bool
            Whether to merge all mutations along an edge into a single mutation symbol. (default=False)
        return_included_nodes : bool
            Returns a list of nodes plotted in the subgraph. (default=False)
        force_notebook : bool
            Forces the the visualizer to display as a notebook. Possibly necessary for untested environments. (default=False)
        rotate_tip_labels : bool
            Rotates tip labels by 90 degrees. (default=False)
        """

        if condense_mutations:
            if not ignore_mutation_times:
                print("WARNING: `condense_mutations=True` forces `ignore_mutation_times=True`.")
                ignore_mutation_times = True

        included_nodes, included_edges, included_mutations, included_breakpoints = self.subset_graph(node=node, degree=degree)
        arg = self._prepare_json(
            plot_type="node",
            nodes=included_nodes,
            edges=included_edges,
            mutations=included_mutations,
            breakpoints=included_breakpoints,
            width=width,
            height=height,
            tree_highlighting=tree_highlighting,
            y_axis_labels=y_axis_labels,
            y_axis_scale=y_axis_scale,
            title=title,
            show_mutations=show_mutations,
            ignore_mutation_times=ignore_mutation_times,
            include_mutation_labels=include_mutation_labels,
            condense_mutations=condense_mutations,
            rotate_tip_labels=rotate_tip_labels
        )
        draw_D3(arg_json=arg, force_notebook=force_notebook)
        if return_included_nodes:
            return list(included_nodes["id"])
        
    # Alias of draw_node that users may be more likely to use when
    # there are multiple focal nodes.
    draw_nodes = draw_node

    def draw_genome_bar(
            self,
            width=500,
            windows=None,
            include_mutations=False,
            force_notebook=False
        ):
        """Draws a genome bar for the D3ARG using D3.js

        Parameters
        ----------
        width : int
            Width of the force layout graph plot in pixels (default=500)
        windows : list of lists
            Each list is are the start and end positions of the windows. Multiple windows can be included.
            (Default is None, ignored)
        include_mutations : bool
            Whether to add ticks for mutations along the genome bar
        force_notebook : bool
            Forces the the visualizer to display as a notebook. Possibly necessary for untested environments. (default=False)
        """

        transformed_bps = self.breakpoints.loc[:,:]
        transformed_bps["x_pos"] = transformed_bps["x_pos_01"] * width
        transformed_bps["width"] = transformed_bps["width_01"] * width
        transformed_bps["included"] = "true"
        transformed_bps = transformed_bps.to_dict("records")

        start = float(self.breakpoints["start"].min())
        stop = float(self.breakpoints["stop"].max())

        transformed_windows = []
        if windows != None:
            for window in windows:
                x_pos_01 = map_value(window[0], start, stop, 0, 1)
                width_01 = map_value(window[1], start, stop, 0, 1) - x_pos_01
                transformed_windows.append({
                    "x_pos": x_pos_01 * width,
                    "width": width_01 * width
                })

        if include_mutations:
            transformed_mutations = self.mutations.loc[:,:]
            transformed_mutations["x_pos"] = transformed_mutations["position_01"] * width
            transformed_mutations = transformed_mutations.to_dict("records")
        else:
            transformed_mutations = []

        genome_bar_json = {
            "data":{
                "breakpoints":transformed_bps,
                "windows":transformed_windows,
                "mutations":transformed_mutations
            },
            "width":width
        }
        
        genome_bar_json["source"] = genome_bar_json.copy()
        genome_bar_json["divnum"] = str(random.randint(0,9999999999))
        JS_text = Template("<div id='genome_bar_" + genome_bar_json['divnum'] + "'class='d3arg' style='min-width:" + str(genome_bar_json["width"]+40) + "px; min-height:180px;'></div><script>$main_text</script>")
        breakpointsjs = open(os.path.dirname(__file__) + "/alternative_plots/genome_bar.js", "r")
        main_text_template = Template(breakpointsjs.read())
        breakpointsjs.close()
        main_text = main_text_template.safe_substitute(genome_bar_json)
        html = JS_text.safe_substitute({'main_text': main_text})
        css = open(os.path.dirname(__file__) + "/visualizer.css", "r")
        styles = css.read()
        css.close()
        if force_notebook or running_in_notebook():
            display(HTML("<style>"+styles+"</style><script src='https://cdn.rawgit.com/eligrey/canvas-toBlob.js/f1a01896135ab378aa5c0118eadd81da55e698d8/canvas-toBlob.js'></script><script src='https://cdn.rawgit.com/eligrey/FileSaver.js/e9d941381475b5df8b7d7691013401e171014e89/FileSaver.min.js'></script><script src='https://d3js.org/d3.v7.min.js'></script>" + html))
        else:
            with tempfile.NamedTemporaryFile("w", delete=False, suffix=".html") as f:
                url = "file://" + f.name
                f.write("<!DOCTYPE html><html><head><style>"+styles+"</style><script src='https://cdn.rawgit.com/eligrey/canvas-toBlob.js/f1a01896135ab378aa5c0118eadd81da55e698d8/canvas-toBlob.js'></script><script src='https://cdn.rawgit.com/eligrey/FileSaver.js/e9d941381475b5df8b7d7691013401e171014e89/FileSaver.min.js'></script><script src='https://d3js.org/d3.v7.min.js'></script></head><body>" + html + "</body></html>")
            webbrowser.open(url, new=2)

    