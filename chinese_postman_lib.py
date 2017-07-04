import geog
import heapq
import math
import networkx
import osmgraph

def neighbors(graph, n0):
  return [(n1, graph[n0][n1].get('name'), graph.node[n1].get('coordinate')) for n1 in graph[n0]]

def get_edge_somehow(graph, n0, n1):
  # this is stupid and I hate myself even more for writing it
  if 0 in graph[n0][n1]:
    return graph[n0][n1][0]
  else:
    return graph[n0][n1]
  
def adjoining_streets(graph, n0):
  return set([get_edge_somehow(graph, n0, n1).get('name')  for n1 in graph[n0]])

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
  print "DEBUG: We are left with these %s streets: %s" % (len(all_edge_names), sorted(all_edge_names)
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

def optimize_dead_ends(in_g, out_g):
  print "DEBUG: There are %s dead ends and %s odd-degree nodes in this graph." % (
      len(dead_ends(in_g)), len(odd_nodes(in_g)))
  for node in dead_ends(in_g):
    new_from = node
    new_to = next(n for n in networkx.dfs_preorder_nodes(
        in_g, node) if len(set(adjoining_streets(in_g,n))) > 1)
    print "DEBUG: I will optimize by adding an edge from %s to %s" % (
        in_g.node[new_from]['pretty_name'], in_g.node[new_to]['pretty_name'])
    add_artificial_edge(in_g, out_g, new_from, new_to)
  print "DEBUG: There are now %s dead ends and %s odd-degree nodes in this graph." % (
      len(dead_ends(out_g)), len(odd_nodes(out_g)))

def graph_of_odd_nodes(g):
  out_graph = networkx.Graph()
  nodes = odd_nodes(g)
  num_odd_nodes = len(nodes)
  print "DEBUG: We will have to add edges to fill in %s odd-degree nodes." % num_odd_nodes
  for i1 in range(len(nodes)):
    print "DEBUG: Starting SSSP lengths for index %s/%s" % (i1, num_odd_nodes)
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
    print "DEBUG: We failed to find these: %s" % remaining_targets
  output = {k: dist[k] for k in targets}
  return output

def add_edges_for_euler(in_g):
  out_g = networkx.MultiGraph(data=in_g)
  optimize_dead_ends(in_g, out_g)
  temp_graph = graph_of_odd_nodes(out_g)
  print "DEBUG: Finished calculating shortest paths, now calculating matching..."
  matching = networkx.max_weight_matching(temp_graph, maxcardinality=True)
  print "DEBUG: Finished calculating matching, now adding new edges..."
  short_matching = {}
  for k in matching:
    if k not in short_matching and matching[k] not in short_matching:
      short_matching[k] = matching[k]
  for source in short_matching:
    add_artificial_edge(in_g, out_g, source, short_matching[source])
  return out_g

def add_artificial_edge(in_g, out_g, source, target):
  new_path = networkx.dijkstra_path(in_g, source=source, target=target, weight='length')
  new_path_streets = []
  new_path_length = 0
  for i in range(1, len(new_path)):
    hop_source = new_path[i - 1]
    hop_target = new_path[i]
    new_path_length += in_g[hop_source][hop_target]['length']
    new_path_streets.append(in_g[hop_source][hop_target].get('name'))
  if len(set(new_path_streets)) == 1:
    new_edge_name = new_path_streets[0]
  else:
    new_edge_name = "the confusing route of %s" % format_list(set(new_path_streets))
  out_g.add_edge(source, target, name=new_edge_name, length=new_path_length)

def get_and_format_circuit(g, source=None):
  circuit = list(networkx.eulerian_circuit(g, source=source))
  print "DEBUG: %s" % circuit
  format_circuit(g, circuit)

def format_circuit(g, circuit):
  total_distance = 0.0
  first_edge = True
  # Once more unto this breach.
  segment_distance = 0.0
  segment_street = None
  segment_direction = None
  segment_origin = None

  for (n1, n2) in circuit:
    if first_edge:
      print "Begin at %s" % g.node[n1]['pretty_name']
      first_edge = False
    lon1, lat1 = g.node[n1].get('coordinate')
    lon2, lat2 = g.node[n2].get('coordinate')
    print "DEBUG: %s (%s,%s) -> %s (%s,%s)" % (n1, lat1, lon1, n2, lat2, lon2)
    current_distance = g.get_edge_data(n1, n2, 0)['length']
    total_distance += current_distance
    segment_distance += current_distance

    if 'name' in g.get_edge_data(n1, n2, 0):
      current_street = g.get_edge_data(n1, n2, 0)['name']
    else:
      current_street = 'Nameless Way'
    current_direction = cardinal_direction(g, n1, n2)

    if (segment_street == current_street) and g.node[n2]['pretty_name'].startswith("a point on") and segment_direction == current_direction:
      continue
    # Okay now what. we know that either it's a new street OR we've arrived at
    # an intersection OR we've changed direction
    if (segment_street == current_street) and g.node[n2]['pretty_name'].startswith("a point on"):
      # We have only changed direction.
      print "Take %s %s (%dm)" % (segment_street, segment_direction, int(round(segment_distance)))
      segment_direction = current_direction
      segment_distance = 0.0
      segment_origin = n1
      # segment_street remains the same
      continue
    if (segment_street == current_street):
      # We have arrived at an intersection or dead end. The segment is over.
      # Print it.
      print "Take %s %s to %s (%dm)" % (segment_street, segment_direction, g.node[n2]['pretty_name'], int(round(segment_distance)))
      segment_direction = None
      segment_distance = 0.0
      segment_origin = None
      segment_street = None
      continue

    # We have begun traversing a new street. Since we are leaving an
    # intersection we can assume we already printed the last edge.
    segment_direction = current_direction
    segment_origin = n1
    segment_street = current_street
    if g.node[n2]['pretty_name'].startswith("a point on"):
      continue
    # We are leaving an interesting node and hopping directly to another.
    print "Take %s %s to %s (%dm)" % (segment_street, segment_direction, g.node[n2]['pretty_name'], int(round(segment_distance)))
    segment_direction = None
    segment_distance = 0.0
    segment_origin = None
    segment_street = None

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
