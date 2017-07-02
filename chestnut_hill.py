import chinese_postman_lib as cpl
import networkx

def list_contains_stenton(string_list):
  return ('Stenton Avenue' in string_list or 'Stenton Ave' in string_list)

def ch_fixes(g):

  edges_to_purge = []
  for n1, n2 in g.edges_iter():
    if (not g[n1][n2].get('name')) or (g[n1][n2].get('highway') == 'path'):
      edges_to_purge.append((n1, n2))
    if g[n1][n2].get('name') == 'Stenton Ave':
      g[n1][n2]['name'] = 'Stenton Avenue'
    if g[n1][n2].get('name') == 'Northwestern Ave':
      g[n1][n2]['name'] = 'Northwestern Avenue'
  for n1, n2 in edges_to_purge:
     g.remove_edge(n1, n2)

  nodes_to_purge = []
  for node in g:
    streets = cpl.adjoining_streets(g, node)
    lon, lat = g.node[node].get('coordinate')
    if (('Germantown Avenue' in streets and lat < 40.066299) or
        ('Cresheim Valley Drive' in streets and lat < 40.065057) or
        ('Lincoln Drive' in streets and lat < 40.063772) or
        ('McCallum Street' in streets and lat < 40.054860) or
        ('Rex Avenue' in streets and lon < -75.220668) or
        ('Valley Green Road' in streets and lon < -75.218001) or
        (('E Bells Mill Rd' in streets or
          'West Bells Mill Road' in streets or
          'Bells Mill Road' in streets) and lon < -75.225600) or
         ('Stenton Avenue' in streets and lon > -75.188621) or
         ('Stenton Avenue' in streets and lat > 40.0929000)):
       nodes_to_purge.append(node)
    elif 'Stenton Avenue' in streets:
      for neighbor in g[node]:
        if 'Stenton Avenue' not in cpl.adjoining_streets(g, neighbor) and cpl.latitude(g, neighbor) > lat:
          print "I will purge node %s (%s,%s) on %s because it is north from Stenton node %s (%s,%s)." % (neighbor, cpl.latitude(g, neighbor), cpl.longitude(g, neighbor), cpl.adjoining_streets(g, neighbor), node, lat, lon)
          nodes_to_purge.append(neighbor)
    elif 'Northwestern Avenue' in streets:
      for neighbor in g[node]:
        if 'Northwestern Avenue' not in cpl.adjoining_streets(g, neighbor) and cpl.longitude(g, neighbor) < lon:
          print "I will purge a node on %s because it is west from Northwestern." % cpl.adjoining_streets(g, neighbor)
          nodes_to_purge.append(neighbor)

  for node in set(nodes_to_purge):
    g.remove_node(node)

  # Having cut off the borders, we cull everything unreachable from within the
  # borders.
  ch_nodes = set(networkx.dfs_preorder_nodes(g, 110358237))
  non_ch_nodes = set(g.nodes()) - ch_nodes
  for node in non_ch_nodes:
    g.remove_node(node)

ch_filename="/home/mark/git/chinese_postman/data/chestnut_hill.osm"

if __name__ == '__main__':
  g = cpl.make_graph(ch_filename, ch_fixes)
  eulerian_graph = cpl.add_edges_for_euler(g)
  cpl.get_and_format_circuit(eulerian_graph)


