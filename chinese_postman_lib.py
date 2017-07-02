import geog
import heapq
import math
import networkx
import osmgraph

def neighbors(graph, n0):
  return [(n1, graph[n0][n1].get('name'), graph.node[n1].get('coordinate')) for n1 in graph[n0]]

def adjoining_streets(graph, n0):
  # won't work with multigraphs
  return set([graph[n0][n1].get('name')  for n1 in graph[n0]])

def latitude(graph, n0):
  return graph.node[n0].get('coordinate')[1]

def longitude(graph, n0):
  return graph.node[n0].get('coordinate')[0]

def default_purge(graph):
  # This is just the identity function. But it might get overridden.
  pass

def make_graph(filename, purge_func=default_purge):
  g = osmgraph.parse_file(filename).to_undirected()

  names = make_node_dict(g)
  for n1 in g:
    g.node[n1]['pretty_name'] = names[n1]
  
  purge_func(g)

  all_edge_names = set([g[n1][n2].get('name') for (n1, n2) in g.edges()])
  print "We are left with these %s streets: %s" % (len(all_edge_names), sorted(all_edge_names)
)
  # If a node has been isolated, just remove it for efficiency.
  for n1 in list(g.nodes()):
    if len(g[n1]) == 0:
      g.remove_node(n1)

  # Assign lengths to edges we didn't purge.
  for n1, n2 in g.edges_iter():
    c1, c2 = osmgraph.tools.coordinates(g, (n1, n2))   
    g[n1][n2]['length'] = geog.distance(c1, c2)

  assert(networkx.is_connected(g))

  # It's inefficient to do this twice but we kind of need it earlier for
  # debugging, but the names are prettier after purging.
  names = make_node_dict(g)
  for n1 in g:
    g.node[n1]['pretty_name'] = names[n1]
  
  return g

def nodes_from_line(in_g, lat1, lon1, lat2, lon2, south=True):
  m = (lat1 - lat2) / (lon1 - lon2)
  b = lat1 - (m * lon1)
  output = []
  for node in in_g:
    x, y = in_g.node[node]['coordinate']
    if (y < (m * x + b)) == south:
      output.append(node)
  return output

def make_node_dict(g):
  out_dict = {}
  for n1 in g:
    adjacent_streets = []
    for n2 in g[n1]:
      if 'name' in g[n1][n2]:
        visible_name = g[n1][n2]['name']
      else:
        visible_name = 'Whatever Street'
      adjacent_streets.append(visible_name)
    if len(adjacent_streets) == 0:
      out_dict[n1] = "the middle of nowhere"
    elif len(adjacent_streets) == 1:
      out_dict[n1] = "the dead end of %s" % adjacent_streets[0]
    elif len(set(adjacent_streets)) == 1:
      out_dict[n1] = "a point on %s" % adjacent_streets[0]
    else:
      out_dict[n1] = "the intersection of %s" % format_list(set(adjacent_streets))
  return out_dict

def odd_nodes(g):
  values = []
  degrees = networkx.degree(g)
  for node in degrees:
    if (degrees[node] % 2) == 1:
      values.append(node)
  return values

def dead_ends(g):
  values = []
  degrees = networkx.degree(g)
  for node in degrees:
    if degrees[node] == 1:
      values.append(node)
  return values

def format_list(string_iterable):
  string_list = list(string_iterable)
  if len(string_list) == 0:
    return '[error]'
  if len(string_list) == 1:
    return string_list[0]
  if len(string_list) == 2:
    return '%s & %s' % (string_list[0], string_list[1])
  return '%s, and %s' % (str.join(', ', string_list[:-1]), string_list[-1])

def optimize_dead_ends(g):
  print "There are %s dead ends in this graph." % len(dead_ends(g))
  for node in dead_ends(g):
    new_from = node
    new_to = g[node].keys()[0]
    print "I will OPTIMIZE by adding an edge from %s to %s" % (new_from, new_to)
    if 'length' not in g[new_from][new_to][0]:
      print "Why does this lack a distance? %s" % g[new_from][new_to]
    new_weight = g[new_from][new_to][0]['length']
    if 'name' in g[new_to][new_from][0]:
      new_name = '%s (added as backtracker)' % g[new_from][new_to][0]['name']
    else:
      new_name = 'nameless backtracker edge' 
    g.add_edge(new_from, new_to, name=new_name, length=new_weight)
  print "There are now %s dead ends in this graph." % len(dead_ends(g))
  print "There are now %s odd nodes in this graph." % len(odd_nodes(g))

def graph_of_odd_nodes(g):
  out_graph = networkx.Graph()
  nodes = odd_nodes(g)
  num_odd_nodes = len(nodes)
  print "We will have to add edges to fill in %s odd-degree nodes." % num_odd_nodes
  for i1 in range(len(nodes)):
    print "Starting SSSP lengths for index %s/%s" % (i1, num_odd_nodes)
    source = nodes[i1]
    targets = [nodes[i2] for i2 in range(i1 + 1, len(nodes))]
    lengths = dijkstra_single_source_multi_target(g, source, targets)
    for target in lengths:
      out_graph.add_edge(source, target, weight=(-1 * lengths[target]))
  return out_graph

# This algorithm runs the SSSP formula using the whole graph but terminating
# once we get a certain subset of targets. Maybe there's a modified Floyd-
# Warshall that can solve the larger problem better.
def dijkstra_single_source_multi_target(g, source, targets):
  remaining_targets = set(targets)
  dist = {source: 0}
  prev = {}
  q = []
  for target in targets:
    heapq.heappush(q, (float('inf'), target))
  heapq.heappush(q, (0, source))
  while q and remaining_targets:
    du, u = heapq.heappop(q)
    for v in g[u]:
      alt = du + g[u][v][0]['length']
      if (v not in dist) or (alt < dist[v]):
        dist[v] = alt
        prev[v] = u
        heapq.heappush(q, (alt, v))
        remaining_targets.discard(v)
  if remaining_targets:
    print "We failed to find these: %s" % remaining_targets
  output = {k: dist[k] for k in targets}
  return output

def add_edges_for_euler(in_g):
  out_g = networkx.MultiGraph(data=in_g)
  optimize_dead_ends(out_g)
  temp_graph = graph_of_odd_nodes(out_g)
  print "Finished calculating shortest paths, now calculating matching..."
  matching = networkx.max_weight_matching(temp_graph, maxcardinality=True)
  print "Finished calculating matching, now adding new edges..."
  short_matching = {}
  for k in matching:
    if k not in short_matching and matching[k] not in short_matching:
      short_matching[k] = matching[k]
  for source in short_matching:
    new_path = networkx.dijkstra_path(in_g, source=source, target=short_matching[source], weight='length')
    new_path_streets = []
    new_path_length = 0
    for i in range(1, len(new_path)):
      new_from = new_path[i - 1]
      new_to = new_path[i]
      new_path_length += in_g[new_from][new_to]['length']
      new_path_streets.append(in_g[new_from][new_to].get('name'))
    if len(set(new_path_streets)) == 1:
      new_edge_name = new_path_streets[0]
    else:
      new_edge_name = "the confusing route of %s" % format_list(set(new_path_streets))
    out_g.add_edge(source, short_matching[source], name=new_edge_name, length=new_path_length)
  return out_g

def get_and_format_circuit(g, source=None):
  circuit = list(networkx.eulerian_circuit(g, source=source))
  print circuit
  format_circuit(g, circuit)

def format_circuit(g, circuit):
  total_distance = 0.0
  for (n1, n2) in circuit:
    lon1, lat1 = g.node[n1].get('coordinate')
    lon2, lat2 = g.node[n2].get('coordinate')
    print "DEBUG: %s (%s,%s) -> %s (%s,%s)" % (n1, lat1, lon1, n2, lat2, lon2)
    edge_length = g.get_edge_data(n1, n2, 0)['length']
    total_distance += edge_length
    if 'name' in g.get_edge_data(n1, n2, 0):
      visible_name = g.get_edge_data(n1, n2, 0)['name']
    else:
      visible_name = 'Nameless Way'
    if g.node[n1]['pretty_name'].startswith("a point on") and g.node[n1]['pretty_name'] == g.node[n2]['pretty_name']:
      print "Continue %s on %s (%dm)" % (cardinal_direction(g, n1, n2), visible_name, int(round(edge_length)))
    else: # print it and reset variables
      print "Take %s %s to %s (%dm)" % (visible_name, cardinal_direction(g, n1, n2), g.node[n2]['pretty_name'], int(round(edge_length)))
  print "Total distance was %dm" % int(round(total_distance))

def cardinal_direction(g, source, dest):
  lon1, lat1 = g.node[source].get('coordinate')
  lon2, lat2 = g.node[dest].get('coordinate')
  dx = lon2 - lon1
  dy = lat2 - lat1
  angle_pis = math.atan2(dy, dx) / math.pi
  if angle_pis >= (-1.0/8)  and angle_pis < (1.0/8):
    return "east"
  if angle_pis >= (1.0/8) and angle_pis < (3.0/8):
    return "northeast"
  if angle_pis >= (3.0/8) and angle_pis < (5.0/8):
    return "north"
  if angle_pis >= (5.0 / 8) and angle_pis < (7.0/8):
    return "northwest"
  if angle_pis >= (7.0/8) or angle_pis < (-7.0/8):
    return "west"
  if angle_pis >= (-7.0/8) and angle_pis < (-5.0/8):
    return "southwest"
  if angle_pis >= (-5.0/8) and angle_pis < (-3.0/8):
    return "south"
  if angle_pis >= (-3.0/8) and angle_pis < (-1.0/8):
    return "southeast"
  return "mark fucked up the cardinal directions badly"
